import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, INET, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DataAccessLog(Base):
    __tablename__ = "data_access_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 誰がアクセスしたか（WHO）
    accessor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    accessor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    accessor_role: Mapped[str] = mapped_column(String(20), nullable=False)

    # 誰のデータか（WHOSE）
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    target_user_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # 何にアクセスしたか（WHAT）
    access_type: Mapped[str] = mapped_column(String(20), nullable=False)  # read, write, export, delete
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    data_fields: Mapped[list[str] | None] = mapped_column(ARRAY(Text))

    # どのようにアクセスしたか（HOW）
    endpoint: Mapped[str] = mapped_column(String(200), nullable=False)
    http_method: Mapped[str] = mapped_column(String(10), nullable=False)
    ip_address: Mapped[str] = mapped_column(INET, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text)

    # アクセスコンテキスト
    has_assignment: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    access_purpose: Mapped[str | None] = mapped_column(String(100))

    # ログ完全性
    log_hash: Mapped[str | None] = mapped_column(String(64))

    # 記録日時
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("idx_data_access_target", "target_user_id", "created_at"),
        Index("idx_data_access_accessor", "accessor_user_id", "created_at"),
        Index("idx_data_access_type", "access_type", "resource_type"),
        Index("idx_data_access_created", "created_at"),
        Index(
            "idx_data_access_unassigned", "has_assignment", "created_at",
            postgresql_where=(~has_assignment),
        ),
    )
