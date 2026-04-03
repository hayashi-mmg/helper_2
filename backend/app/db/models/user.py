import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Basic info
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(Text)

    # Senior-specific
    emergency_contact: Mapped[str | None] = mapped_column(String(100))
    medical_notes: Mapped[str | None] = mapped_column(Text)
    care_level: Mapped[int | None] = mapped_column(Integer)

    # Helper-specific
    certification_number: Mapped[str | None] = mapped_column(String(50))
    specialization: Mapped[list[str] | None] = mapped_column(ARRAY(Text))

    # System
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    recipes: Mapped[list["Recipe"]] = relationship(back_populates="user", cascade="all, delete-orphan")  # noqa: F821
    weekly_menus: Mapped[list["WeeklyMenu"]] = relationship(back_populates="user", cascade="all, delete-orphan")  # noqa: F821
    sent_messages: Mapped[list["Message"]] = relationship(  # noqa: F821
        back_populates="sender", foreign_keys="Message.sender_id", cascade="all, delete-orphan"
    )
    received_messages: Mapped[list["Message"]] = relationship(  # noqa: F821
        back_populates="receiver", foreign_keys="Message.receiver_id", cascade="all, delete-orphan"
    )
    qr_tokens: Mapped[list["QRToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")  # noqa: F821
    pantry_items: Mapped[list["PantryItem"]] = relationship(back_populates="user", cascade="all, delete-orphan")  # noqa: F821
