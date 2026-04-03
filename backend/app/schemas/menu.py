from datetime import date, datetime

from pydantic import BaseModel, Field


class MenuRecipeRef(BaseModel):
    recipe_id: str
    recipe_type: str = Field(pattern="^(主菜|副菜|汁物|ご飯|その他)$")


class MealSlot(BaseModel):
    breakfast: list[MenuRecipeRef] = []
    dinner: list[MenuRecipeRef] = []


class WeeklyMenuUpdate(BaseModel):
    week_start: date
    menus: dict[str, MealSlot] = {}  # monday..sunday


class WeeklyMenuCopy(BaseModel):
    source_week: date
    target_week: date


class WeeklyMenuClear(BaseModel):
    week_start: date


# --- Response ---

class RecipeBrief(BaseModel):
    id: str
    name: str
    cooking_time: int

    model_config = {"from_attributes": True}


class MenuRecipeEntry(BaseModel):
    recipe_type: str
    recipe: RecipeBrief


class MealSlotResponse(BaseModel):
    breakfast: list[MenuRecipeEntry] = []
    dinner: list[MenuRecipeEntry] = []


class CategoryDistribution(BaseModel):
    pass

    model_config = {"extra": "allow"}


class MenuSummary(BaseModel):
    total_recipes: int
    avg_cooking_time: int
    category_distribution: dict[str, int]


class WeeklyMenuResponse(BaseModel):
    week_start: date
    menus: dict[str, MealSlotResponse]
    summary: MenuSummary
