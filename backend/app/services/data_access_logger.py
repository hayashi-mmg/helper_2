"""個人データアクセスログ記録サービス。

バッファリングとバッチ書き込みでパフォーマンスへの影響を最小化する。
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.crud.logging_audit import bulk_create_data_access_logs, check_has_assignment
from app.services.log_integrity import LogIntegrityManager

logger = logging.getLogger(__name__)


class DataAccessLogger:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        hmac_key: str = "",
        buffer_size: int = 50,
    ):
        self.session_factory = session_factory
        self.integrity = LogIntegrityManager(hmac_key) if hmac_key else None
        self.buffer_size = buffer_size
        self._buffer: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()

    async def log_access(
        self,
        *,
        db: AsyncSession,
        accessor_user_id: uuid.UUID,
        accessor_email: str,
        accessor_role: str,
        target_user_id: uuid.UUID,
        target_user_name: str,
        access_type: str,
        resource_type: str,
        data_fields: list[str] | None = None,
        endpoint: str,
        http_method: str,
        ip_address: str,
        user_agent: str = "",
    ) -> None:
        """個人データアクセスをバッファに追加する。

        自分自身のデータアクセスは記録しない。
        """
        if accessor_user_id == target_user_id:
            return

        has_assignment = await check_has_assignment(db, accessor_user_id, target_user_id)

        log_data = {
            "accessor_user_id": accessor_user_id,
            "accessor_email": accessor_email,
            "accessor_role": accessor_role,
            "target_user_id": target_user_id,
            "target_user_name": target_user_name,
            "access_type": access_type,
            "resource_type": resource_type,
            "data_fields": data_fields,
            "endpoint": endpoint,
            "http_method": http_method,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "has_assignment": has_assignment,
        }

        if self.integrity:
            log_data["log_hash"] = self.integrity.sign_entry(log_data)

        async with self._lock:
            self._buffer.append(log_data)
            if len(self._buffer) >= self.buffer_size:
                await self._flush()

    async def _flush(self) -> None:
        """バッファ内のログをDBに一括書き込みする。"""
        if not self._buffer:
            return

        logs_to_write = self._buffer.copy()
        self._buffer.clear()

        try:
            async with self.session_factory() as session:
                await bulk_create_data_access_logs(session, logs_to_write)
                await session.commit()
        except Exception:
            logger.exception("データアクセスログのバッチ書き込みに失敗しました")

    async def flush(self) -> None:
        """外部から呼び出し可能なフラッシュ。定期フラッシュ用。"""
        async with self._lock:
            await self._flush()

    @property
    def buffer_count(self) -> int:
        return len(self._buffer)
