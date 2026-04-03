import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class WeeklyMenu(Base):
    __tablename__ = "weekly_menus"
    __table_args__ = (UniqueConstraint("user_id", "week_start"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="weekly_menus")  # noqa: F821
    recipes: Mapped[list["WeeklyMenuRecipe"]] = relationship(back_populates="weekly_menu", cascade="all, delete-orphan")


class WeeklyMenuRecipe(Base):
    __tablename__ = "weekly_menu_recipes"
    __table_args__ = (UniqueConstraint("weekly_menu_id", "day_of_week", "meal_type", "recipe_type"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    weekly_menu_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("weekly_menus.id", ondelete="CASCADE"), nullable=False, index=True)
    recipe_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True)

    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 1=Mon, 7=Sun
    meal_type: Mapped[str] = mapped_column(String(10), nullable=False)  # breakfast, dinner
    recipe_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 主菜, 副菜, etc.

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    weekly_menu: Mapped["WeeklyMenu"] = relationship(back_populates="recipes")
    recipe: Mapped["Recipe"] = relationship(back_populates="menu_entries")  # noqa: F821
