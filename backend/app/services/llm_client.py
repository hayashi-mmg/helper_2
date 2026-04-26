"""Ollama クライアント（AI献立提案用）。

Windowsホスト上のOllamaサーバーとHTTP通信する非同期クライアント。
Dockerコンテナ内からは `host.docker.internal:11434` を経由してアクセスする。
"""

import json
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Ollama 連携で発生するエラーの基底クラス。"""


class OllamaUnavailableError(OllamaError):
    """Ollama に接続できない（未起動・ネットワーク不達など）。"""


class OllamaTimeoutError(OllamaError):
    """Ollama からの応答がタイムアウトした。"""


class OllamaInvalidJSONError(OllamaError):
    """Ollama の応答が有効な JSON でない（リトライ後も失敗）。"""


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout_seconds = timeout_seconds or settings.OLLAMA_TIMEOUT_SECONDS

    async def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.4,
        num_ctx: int = 8192,
    ) -> dict:
        """Ollama /api/chat を `format:"json"` で呼び、パース済みの dict を返す。

        無効JSONの場合は温度 0.2 で 1 回リトライ。リトライも失敗すれば
        ``OllamaInvalidJSONError`` を送出する。
        """
        try:
            content = await self._chat_raw(system_prompt, user_prompt, temperature, num_ctx)
        except httpx.ReadTimeout as e:
            logger.warning("Ollama timeout: %s", e)
            raise OllamaTimeoutError("Ollama からの応答がタイムアウトしました") from e
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            logger.warning("Ollama unavailable: %s", e)
            raise OllamaUnavailableError("Ollama に接続できません") from e

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.info("Ollama returned invalid JSON, retrying with lower temperature")

        try:
            retry_content = await self._chat_raw(system_prompt, user_prompt, 0.2, num_ctx)
            return json.loads(retry_content)
        except (httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout, json.JSONDecodeError) as e:
            logger.warning("Ollama JSON parse failed after retry: %s", e)
            raise OllamaInvalidJSONError("Ollama の応答を解析できませんでした") from e

    async def _chat_raw(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        num_ctx: int,
    ) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {
                "temperature": temperature,
                "num_ctx": num_ctx,
            },
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        return data.get("message", {}).get("content", "")
