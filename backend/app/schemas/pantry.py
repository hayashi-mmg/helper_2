from datetime import datetime

from pydantic import BaseModel, Field


class PantryItemBase(BaseModel):
    name: str = Field(max_length=100)
    category: str = Field(default="その他", pattern="^(野菜|肉類|魚介類|卵・乳製品|調味料|穀類|その他)$")
    is_available: bool = True


class PantryUpdateRequest(BaseModel):
    items: list[PantryItemBase]


class PantryItemResponse(BaseModel):
    id: str
    name: str
    category: str
    is_available: bool
    updated_at: datetime

    model_config = {"from_attributes": True}


class PantryListResponse(BaseModel):
    pantry_items: list[PantryItemResponse]
    total: int
