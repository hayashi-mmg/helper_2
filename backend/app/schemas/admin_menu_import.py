"""管理者向け献立インポート（運用者が任意ユーザーに献立+レシピ+買い物リストを投入）スキーマ。"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, EmailStr, Field, model_validator


class ImportRecipeInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., max_length=20)
    type: str = Field(..., pattern=r"^(主菜|副菜|汁物|ご飯|その他)$")
    difficulty: str = Field(..., max_length=10)
    cooking_time: int = Field(..., ge=0)
    ingredients_text: str | None = None
    instructions: str | None = None
    memo: str | None = None
    recipe_url: str | None = None


class ImportMenuRecipeRef(BaseModel):
    recipe_name: str = Field(..., min_length=1, max_length=100)
    recipe_type: str = Field(..., pattern=r"^(主菜|副菜|汁物|ご飯|その他)$")


class ImportMenuSlot(BaseModel):
    breakfast: list[ImportMenuRecipeRef] = Field(default_factory=list)
    dinner: list[ImportMenuRecipeRef] = Field(default_factory=list)


class MenuImportRequest(BaseModel):
    target_user_id: str | None = None
    target_user_email: EmailStr | None = None
    week_start: date
    recipes: list[ImportRecipeInput] = Field(default_factory=list)
    menu: dict[str, ImportMenuSlot] = Field(default_factory=dict)
    generate_shopping_list: bool = True
    helper_user_id: str | None = None
    dry_run: bool = False

    @model_validator(mode="after")
    def _require_target(self) -> "MenuImportRequest":
        if not self.target_user_id and not self.target_user_email:
            raise ValueError("target_user_id または target_user_email のいずれかを指定してください")
        return self


class SelfMenuImportRequest(BaseModel):
    """非admin向け: 対象は常にログイン中のユーザー。"""
    week_start: date
    recipes: list[ImportRecipeInput] = Field(default_factory=list)
    menu: dict[str, ImportMenuSlot] = Field(default_factory=dict)
    generate_shopping_list: bool = True
    dry_run: bool = False


class TargetUserBrief(BaseModel):
    id: str
    email: str
    full_name: str
    role: str


class ShoppingListResult(BaseModel):
    request_id: str
    total_items: int
    excluded_items: int
    active_items: int
    replaced_existing: bool


class MenuImportResponse(BaseModel):
    applied: bool
    target_user: TargetUserBrief
    week_start: date
    created_recipe_count: int
    reused_recipe_count: int
    replaced_menu: bool
    shopping_list: ShoppingListResult | None = None
    warnings: list[str] = Field(default_factory=list)
