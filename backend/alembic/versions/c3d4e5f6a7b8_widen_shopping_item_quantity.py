"""widen_shopping_item_quantity

Widen shopping_items.quantity from VARCHAR(50) to VARCHAR(200)
to accommodate aggregated quantity text from multiple recipes.

Revision ID: c3d4e5f6a7b8
Revises: b7c8d9e0f1a2
Create Date: 2026-04-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'shopping_items', 'quantity',
        existing_type=sa.String(length=50),
        type_=sa.String(length=200),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'shopping_items', 'quantity',
        existing_type=sa.String(length=200),
        type_=sa.String(length=50),
        existing_nullable=True,
    )
