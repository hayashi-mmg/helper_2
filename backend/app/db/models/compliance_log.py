import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

COMPLIANCE_EVENT_TYPES = (
    "consent_given", "consent_withdrawn",
    "disclosure_request", "correction_request",
    "deletion_request", "usage_stop_request",
    "breach_detected", "breach_reported_ppc", "breach_notified_user",
    "retention_expired", "data_deleted",
    "third_party_provision",
)


class ComplianceLog(Base):
    __tablename__ = "compliance_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # イベント種別
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # 対象者
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    target_user_name: Mapped[str | None] = mapped_column(String(255))

    # 操作者（管理者）
    handled_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    handler_email: Mapped[str | None] = mapped_column(String(255))

    # 請求・イベント詳細
    request_details: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # ステータス管理
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    # 期限管理
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 対応結果
    response_details: Mapped[dict | None] = mapped_column(JSONB)

    # ログ完全性
    log_hash: Mapped[str | None] = mapped_column(String(64))

    # 記録日時
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_compliance_event_type", "event_type"),
        Index("idx_compliance_target", "target_user_id", "created_at"),
        Index("idx_compliance_status", "status", postgresql_where=(status != "completed")),
        Index("idx_compliance_deadline", "deadline_at", postgresql_where=(status == "pending")),
        Index("idx_compliance_created", "created_at"),
    )
