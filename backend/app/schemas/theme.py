"""テーマシステム Pydantic スキーマ。

仕様: docs/theme_system_specification.md §3
"""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# ThemeDefinition
# ---------------------------------------------------------------------------
class ThemeColorsSemantic(BaseModel):
    success: str
    danger: str
    warn: str
    info: str

    model_config = ConfigDict(extra="allow")


class ThemeColors(BaseModel):
    brand: dict[str, str]
    semantic: ThemeColorsSemantic
    neutral: dict[str, str]

    @field_validator("brand")
    @classmethod
    def brand_has_500(cls, v: dict[str, str]) -> dict[str, str]:
        if "500" not in v:
            raise ValueError("brand.500 は必須です")
        return v


class ThemeFonts(BaseModel):
    body: str
    heading: str
    mono: str | None = None
    baseSizePx: int = Field(ge=1)


class ThemeRadii(BaseModel):
    sm: str | None = None
    md: str | None = None
    lg: str | None = None
    full: str | None = None

    model_config = ConfigDict(extra="allow")


class ThemeMeta(BaseModel):
    previewImageUrl: str | None = None
    tags: list[str] | None = None

    model_config = ConfigDict(extra="allow")


class ThemeDefinition(BaseModel):
    schema_version: Literal["1.0"]
    id: str = Field(pattern=r"^[a-z0-9_-]{2,40}$")
    name: str = Field(max_length=60)
    description: str | None = Field(default=None, max_length=240)
    author: str | None = Field(default=None, max_length=60)
    colors: ThemeColors
    semanticTokens: dict[str, str] | None = None
    fonts: ThemeFonts
    radii: ThemeRadii
    density: Literal["compact", "comfortable", "spacious"]
    meta: ThemeMeta | None = None

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Theme CRUD
# ---------------------------------------------------------------------------
class ThemeSummary(BaseModel):
    theme_key: str
    name: str
    description: str | None = None
    is_builtin: bool
    is_active: bool
    preview_image_url: str | None = None
    updated_at: datetime


class ThemeSummaryListResponse(BaseModel):
    themes: list[ThemeSummary]


class ThemeRead(BaseModel):
    theme_key: str
    name: str
    description: str | None = None
    definition: dict[str, Any]
    is_builtin: bool
    is_active: bool
    updated_at: datetime


class ThemeCreate(BaseModel):
    theme_key: str = Field(pattern=r"^[a-z0-9_-]{2,40}$", max_length=40)
    name: str = Field(max_length=60)
    description: str | None = Field(default=None, max_length=240)
    definition: dict[str, Any]
    is_active: bool = True


class ThemeUpdate(BaseModel):
    """カスタムテーマ更新用。組込みは name / description / is_active のみ反映。"""

    name: str | None = Field(default=None, max_length=60)
    description: str | None = Field(default=None, max_length=240)
    definition: dict[str, Any] | None = None
    is_active: bool | None = None
