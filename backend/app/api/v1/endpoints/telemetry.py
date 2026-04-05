"""フロントエンドテレメトリ受信API。"""
import logging
import re

from fastapi import APIRouter, Request, status

from app.schemas.logging_audit import FrontendLogBatchRequest, FrontendLogBatchResponse

router = APIRouter(prefix="/telemetry", tags=["テレメトリ"])

logger = logging.getLogger("frontend_telemetry")

# PII検出パターン
_PII_PATTERNS = [
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),  # メールアドレス
    re.compile(r"\d{2,4}-\d{2,4}-\d{3,4}"),  # 電話番号パターン
]


def _sanitize(text: str | None) -> str | None:
    """テキストからPIIパターンを除去する。"""
    if not text:
        return text
    for pattern in _PII_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


@router.post("/frontend-logs", response_model=FrontendLogBatchResponse, status_code=status.HTTP_202_ACCEPTED)
async def receive_frontend_logs(
    body: FrontendLogBatchRequest,
    request: Request,
):
    """フロントエンドから送信されたログバッチを受信する。

    認証不要（Beacon APIからの送信をサポートするため）。
    ログはアプリケーションログに出力し、Promtail経由でLokiに送信される。
    """
    accepted_count = 0
    client_ip = request.client.host if request.client else "unknown"

    for entry in body.logs:
        sanitized_message = _sanitize(entry.message)
        sanitized_stack = _sanitize(entry.stack)

        log_data = {
            "event": "frontend_log",
            "log_type": entry.type,
            "message": sanitized_message,
            "url": entry.url,
            "client_ip": client_ip,
        }

        if entry.type == "accessibility_usage":
            log_data["feature"] = entry.feature
            log_data["action"] = entry.action
            log_data["value"] = entry.value

        if sanitized_stack:
            log_data["stack"] = sanitized_stack[:2000]

        if entry.component_name:
            log_data["component_name"] = entry.component_name

        logger.info(str(log_data))
        accepted_count += 1

    return FrontendLogBatchResponse(accepted=True, count=accepted_count)
