from datetime import date, datetime

from pydantic import BaseModel, Field


class ShoppingItemCreate(BaseModel):
    item_name: str = Field(max_length=100)
    category: str = "その他"
    quantity: str | None = None
    memo: str | None = None


class ShoppingItemUpdate(BaseModel):
    status: str | None = Field(None, pattern="^(pending|purchased|unavailable)$")
    memo: str | None = None


class ShoppingItemResponse(BaseModel):
    id: str
    item_name: str
    category: str
    quantity: str | None = None
    memo: str | None = None
    status: str
    is_excluded: bool = False
    recipe_sources: list[str] | None = None
    excluded_reason: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ShoppingRequestCreate(BaseModel):
    senior_user_id: str
    request_date: date
    notes: str | None = None
    items: list[ShoppingItemCreate]


class ShoppingRequestResponse(BaseModel):
    id: str
    senior_user_id: str
    helper_user_id: str
    request_date: date
    status: str
    notes: str | None = None
    items: list[ShoppingItemResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


# --- 献立→買い物リスト生成 ---

class GenerateFromMenuRequest(BaseModel):
    week_start: date
    notes: str | None = None


class GeneratedItemResponse(BaseModel):
    id: str
    item_name: str
    category: str
    quantity: str | None = None
    memo: str | None = None
    status: str
    is_excluded: bool
    excluded_reason: str | None = None
    recipe_sources: list[str]


class GenerateSummary(BaseModel):
    total_items: int
    excluded_items: int
    active_items: int


class GenerateFromMenuResponse(BaseModel):
    id: str
    request_date: date
    status: str
    notes: str | None = None
    source_menu_week: date
    items: list[GeneratedItemResponse]
    summary: GenerateSummary
    created_at: datetime


class ExcludeRequest(BaseModel):
    is_excluded: bool


class ExcludeResponse(BaseModel):
    id: str
    item_name: str
    is_excluded: bool
    status: str
