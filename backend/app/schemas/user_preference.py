"""ユーザー設定 Pydantic スキーマ。

仕様: docs/theme_system_specification.md §6.2 / §7
"""
from pydantic import BaseModel, ConfigDict, Field


class UserPreferencesRead(BaseModel):
    theme_id: str | None = None
    font_size_override: str | None = None


class UserPreferencesUpdate(BaseModel):
    """部分更新。None のフィールドは未指定として扱い、既存値を維持する。

    明示的にクリアしたい場合は専用の DELETE エンドポイントを追加予定。
    """

    theme_id: str | None = Field(default=None, max_length=40)
    font_size_override: str | None = Field(default=None, max_length=20)

    model_config = ConfigDict(extra="forbid")
