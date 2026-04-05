import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FrontendErrorLog(Base):
    __tablename__ = "frontend_error_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # エラー識別
    error_type: Mapped[str] = mapped_column(String(30), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    stack_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    component_name: Mapped[str | None] = mapped_column(String(100))

    # 発生状況
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    user_agent_category: Mapped[str | None] = mapped_column(String(50))

    # 集約情報
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # 影響範囲
    affected_user_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # 記録日時
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("idx_frontend_error_dedup", "stack_hash", "url", unique=True),
        Index("idx_frontend_error_type", "error_type", "last_seen_at"),
        Index("idx_frontend_error_count", occurrence_count.desc()),
        Index("idx_frontend_error_created", "created_at"),
    )
