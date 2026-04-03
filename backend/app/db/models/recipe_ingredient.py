import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True)

    # Ingredient info
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    quantity: Mapped[str | None] = mapped_column(String(50))
    category: Mapped[str] = mapped_column(String(30), nullable=False, default="その他")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # System
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    recipe: Mapped["Recipe"] = relationship(back_populates="structured_ingredients")  # noqa: F821
