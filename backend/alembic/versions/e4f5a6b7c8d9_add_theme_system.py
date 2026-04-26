"""add_theme_system

Add themes and user_preferences tables, seed 4 preset themes, and
register default_theme_id system setting.

Revision ID: e4f5a6b7c8d9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-22 00:00:00.000000
"""
import json
import uuid
from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.services.theme_presets import BUILTIN_PRESETS


# revision identifiers, used by Alembic.
revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- themes ---
    op.create_table(
        "themes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("theme_key", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("definition", postgresql.JSONB(), nullable=False),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("theme_key", name="uq_themes_theme_key"),
        sa.CheckConstraint("theme_key ~ '^[a-z0-9_-]{2,40}$'", name="ck_themes_key_format"),
    )
    op.create_index("idx_themes_theme_key", "themes", ["theme_key"])
    op.create_index("idx_themes_is_builtin", "themes", ["is_builtin"])

    # --- user_preferences ---
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("preference_key", sa.String(length=60), nullable=False),
        sa.Column("preference_value", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "preference_key", name="uq_user_preferences_user_key"),
    )
    op.create_index("idx_user_preferences_user_id", "user_preferences", ["user_id"])

    # --- seed preset themes ---
    now = datetime.utcnow()
    themes_table = sa.table(
        "themes",
        sa.column("id", sa.UUID()),
        sa.column("theme_key", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("definition", postgresql.JSONB()),
        sa.column("is_builtin", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        themes_table,
        [
            {
                "id": uuid.uuid4(),
                "theme_key": key,
                "name": name,
                "description": description,
                "definition": definition,
                "is_builtin": True,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
            for key, name, description, definition in BUILTIN_PRESETS
        ],
    )

    # --- seed default_theme_id system setting ---
    # setting_value は jsonb 型なので CAST が必須。明示しないと
    # asyncpg/SQLAlchemy がパラメータを VARCHAR としてバインドし、
    # `column "setting_value" is of type jsonb but expression is of type character varying`
    # で失敗する。
    op.execute(
        sa.text(
            "INSERT INTO system_settings (id, setting_key, setting_value, category, description, is_sensitive, created_at, updated_at) "
            "VALUES (:id, :key, CAST(:value AS jsonb), :category, :description, false, :now, :now) "
            "ON CONFLICT (setting_key) DO NOTHING"
        ).bindparams(
            id=uuid.uuid4(),
            key="default_theme_id",
            value=json.dumps("standard"),
            category="general",
            description="未ログイン画面およびユーザー未設定時に適用する既定テーマの theme_key",
            now=now,
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM system_settings WHERE setting_key = 'default_theme_id'"))
    op.drop_index("idx_user_preferences_user_id", table_name="user_preferences")
    op.drop_table("user_preferences")
    op.drop_index("idx_themes_is_builtin", table_name="themes")
    op.drop_index("idx_themes_theme_key", table_name="themes")
    op.drop_table("themes")
