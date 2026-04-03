from datetime import datetime

from pydantic import BaseModel, Field


INGREDIENT_CATEGORIES = ("野菜", "肉類", "魚介類", "卵・乳製品", "調味料", "穀類", "その他")


class RecipeIngredientItem(BaseModel):
    name: str = Field(max_length=100)
    quantity: str | None = Field(None, max_length=50)
    category: str = Field(default="その他", pattern="^(野菜|肉類|魚介類|卵・乳製品|調味料|穀類|その他)$")
    sort_order: int = Field(default=0, ge=0)


class IngredientsUpdateRequest(BaseModel):
    ingredients: list[RecipeIngredientItem]


class RecipeIngredientResponse(BaseModel):
    id: str
    name: str
    quantity: str | None = None
    category: str
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


class RecipeIngredientsListResponse(BaseModel):
    recipe_id: str
    recipe_name: str
    ingredients: list[RecipeIngredientResponse]
