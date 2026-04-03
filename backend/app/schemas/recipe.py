from datetime import datetime

from pydantic import BaseModel, Field


class RecipeCreate(BaseModel):
    name: str = Field(max_length=100)
    category: str = Field(pattern="^(和食|洋食|中華|その他)$")
    type: str = Field(pattern="^(主菜|副菜|汁物|ご飯|その他)$")
    difficulty: str = Field(pattern="^(簡単|普通|難しい)$")
    cooking_time: int = Field(gt=0)
    ingredients: str | None = None
    instructions: str | None = None
    memo: str | None = None
    recipe_url: str | None = None


class RecipeUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    category: str | None = Field(None, pattern="^(和食|洋食|中華|その他)$")
    type: str | None = Field(None, pattern="^(主菜|副菜|汁物|ご飯|その他)$")
    difficulty: str | None = Field(None, pattern="^(簡単|普通|難しい)$")
    cooking_time: int | None = Field(None, gt=0)
    ingredients: str | None = None
    instructions: str | None = None
    memo: str | None = None
    recipe_url: str | None = None


class RecipeResponse(BaseModel):
    id: str
    name: str
    category: str
    type: str
    difficulty: str
    cooking_time: int
    ingredients: str | None = None
    instructions: str | None = None
    memo: str | None = None
    recipe_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginationInfo(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class RecipeListResponse(BaseModel):
    recipes: list[RecipeResponse]
    pagination: PaginationInfo
