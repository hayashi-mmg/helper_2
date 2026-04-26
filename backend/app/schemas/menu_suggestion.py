"""AI献立提案の入出力スキーマ。"""

from datetime import date

from pydantic import BaseModel, Field


class MenuSuggestionRequest(BaseModel):
    week_start: date
    dietary_restrictions: list[str] = Field(default_factory=list)  # 例: "柔らかい食事", "塩分控えめ"
    avoid_ingredients: list[str] = Field(default_factory=list)
    notes: str | None = None


class SuggestedRecipeRef(BaseModel):
    recipe_id: str
    name: str
    recipe_type: str = Field(pattern="^(主菜|副菜|汁物|ご飯|その他)$")
    cooking_time: int


class SuggestedMealSlot(BaseModel):
    breakfast: list[SuggestedRecipeRef] = Field(default_factory=list)
    dinner: list[SuggestedRecipeRef] = Field(default_factory=list)


class WeeklyMenuSuggestionResponse(BaseModel):
    week_start: date
    menus: dict[str, SuggestedMealSlot]  # monday..sunday
    rationale: str | None = None
