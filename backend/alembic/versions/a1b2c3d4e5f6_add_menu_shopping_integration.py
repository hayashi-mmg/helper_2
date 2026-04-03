"""add_menu_shopping_integration

Add recipe_ingredients and pantry_items tables.
Extend shopping_items with recipe_ingredient_id and is_excluded.

Revision ID: a1b2c3d4e5f6
Revises: d6705e4ea030
Create Date: 2026-03-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'd6705e4ea030'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- recipe_ingredients ---
    op.create_table(
        'recipe_ingredients',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('recipe_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('quantity', sa.String(length=50), nullable=True),
        sa.Column('category', sa.String(length=30), nullable=False, server_default='その他'),
        sa.Column('sort_order', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_recipe_ingredients_recipe_id', 'recipe_ingredients', ['recipe_id'])
    op.create_index('idx_recipe_ingredients_name', 'recipe_ingredients', ['name'])
    op.create_index('idx_recipe_ingredients_category', 'recipe_ingredients', ['category'])

    # --- pantry_items ---
    op.create_table(
        'pantry_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=30), nullable=False, server_default='その他'),
        sa.Column('is_available', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'name'),
    )
    op.create_index('idx_pantry_items_user_id', 'pantry_items', ['user_id'])
    op.create_index('idx_pantry_items_available', 'pantry_items', ['user_id', 'is_available'])

    # --- shopping_items 拡張 ---
    op.add_column('shopping_items', sa.Column(
        'recipe_ingredient_id', sa.UUID(), nullable=True,
    ))
    op.add_column('shopping_items', sa.Column(
        'is_excluded', sa.Boolean(), nullable=False, server_default='false',
    ))
    op.create_foreign_key(
        'fk_shopping_items_recipe_ingredient',
        'shopping_items', 'recipe_ingredients',
        ['recipe_ingredient_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index('idx_shopping_items_recipe_ingredient', 'shopping_items', ['recipe_ingredient_id'])
    op.create_index('idx_shopping_items_excluded', 'shopping_items', ['shopping_request_id', 'is_excluded'])


def downgrade() -> None:
    # --- shopping_items 拡張のロールバック ---
    op.drop_index('idx_shopping_items_excluded', table_name='shopping_items')
    op.drop_index('idx_shopping_items_recipe_ingredient', table_name='shopping_items')
    op.drop_constraint('fk_shopping_items_recipe_ingredient', 'shopping_items', type_='foreignkey')
    op.drop_column('shopping_items', 'is_excluded')
    op.drop_column('shopping_items', 'recipe_ingredient_id')

    # --- pantry_items ---
    op.drop_index('idx_pantry_items_available', table_name='pantry_items')
    op.drop_index('idx_pantry_items_user_id', table_name='pantry_items')
    op.drop_table('pantry_items')

    # --- recipe_ingredients ---
    op.drop_index('idx_recipe_ingredients_category', table_name='recipe_ingredients')
    op.drop_index('idx_recipe_ingredients_name', table_name='recipe_ingredients')
    op.drop_index('idx_recipe_ingredients_recipe_id', table_name='recipe_ingredients')
    op.drop_table('recipe_ingredients')
