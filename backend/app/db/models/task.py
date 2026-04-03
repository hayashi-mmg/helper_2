import uuid
from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    senior_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    helper_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)

    # Task info
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    task_type: Mapped[str] = mapped_column(String(20), nullable=False)  # cooking, cleaning, shopping, special
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    estimated_minutes: Mapped[int | None] = mapped_column(Integer)

    # Schedule
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    scheduled_start_time: Mapped[time | None] = mapped_column(Time)
    scheduled_end_time: Mapped[time | None] = mapped_column(Time)

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)

    # System
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    senior: Mapped["User"] = relationship(foreign_keys=[senior_user_id])  # noqa: F821
    helper: Mapped["User | None"] = relationship(foreign_keys=[helper_user_id])  # noqa: F821
    completions: Mapped[list["TaskCompletion"]] = relationship(back_populates="task", cascade="all, delete-orphan")


class TaskCompletion(Base):
    __tablename__ = "task_completions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    helper_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_minutes: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    next_notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    task: Mapped["Task"] = relationship(back_populates="completions")
    helper: Mapped["User"] = relationship()  # noqa: F821
