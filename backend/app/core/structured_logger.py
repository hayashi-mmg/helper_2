"""構造化JSONログフォーマッタとリクエストコンテキスト管理。"""
import json
import logging
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

# リクエストごとのコンテキスト変数
request_trace_id: ContextVar[str] = ContextVar("request_trace_id", default="")
request_user_id: ContextVar[str | None] = ContextVar("request_user_id", default=None)


class StructuredFormatter(logging.Formatter):
    """構造化JSON形式のログフォーマッタ。"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "backend",
            "trace_id": request_trace_id.get() or str(uuid.uuid4()),
            "message": record.getMessage(),
            "logger": record.name,
        }

        user_id = request_user_id.get()
        if user_id:
            log_entry["user_id"] = user_id

        if hasattr(record, "event"):
            log_entry["event"] = record.event
        if hasattr(record, "metadata"):
            log_entry["metadata"] = record.metadata

        return json.dumps(log_entry, ensure_ascii=False, default=str)


def setup_structured_logging() -> None:
    """アプリケーション全体の構造化ログを設定する。"""
    formatter = StructuredFormatter()

    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)

    # ファイルハンドラー追加（Promtailが収集するパス）
    # 本番環境ではFileHandler、テスト環境ではStreamHandlerのみ
    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.INFO)
    if not app_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        app_logger.addHandler(handler)
