import uuid
from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserAssignment(Base):
    __tablename__ = "user_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # アサイン関係
    helper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    senior_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True
    )

    # ステータス
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)

    # スケジュール情報
    visit_frequency: Mapped[str | None] = mapped_column(String(50))
    preferred_days: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))
    preferred_time_start: Mapped[time | None] = mapped_column(Time)
    preferred_time_end: Mapped[time | None] = mapped_column(Time)
    notes: Mapped[str | None] = mapped_column(Text)

    # 期間
    start_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    end_date: Mapped[date | None] = mapped_column(Date)

    # システム情報
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    helper: Mapped["User"] = relationship(foreign_keys=[helper_id])  # noqa: F821
    senior: Mapped["User"] = relationship(foreign_keys=[senior_id])  # noqa: F821
    assigned_by_user: Mapped["User"] = relationship(foreign_keys=[assigned_by])  # noqa: F821
