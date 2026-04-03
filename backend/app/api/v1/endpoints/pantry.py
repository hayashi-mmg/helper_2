import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.crud.pantry import (
    delete_pantry_item,
    get_pantry_item_by_id,
    get_pantry_items,
    upsert_pantry_items,
)
from app.db.models.user import User
from app.schemas.pantry import (
    PantryItemResponse,
    PantryListResponse,
    PantryUpdateRequest,
)

router = APIRouter(prefix="/pantry", tags=["パントリー"])


@router.get("", response_model=PantryListResponse)
async def list_pantry(
    available_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items = await get_pantry_items(db, current_user.id, available_only)
    return PantryListResponse(
        pantry_items=[
            PantryItemResponse(
                id=str(item.id), name=item.name, category=item.category,
                is_available=item.is_available, updated_at=item.updated_at,
            )
            for item in items
        ],
        total=len(items),
    )


@router.put("", response_model=PantryListResponse)
async def update_pantry(
    data: PantryUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items_data = [item.model_dump() for item in data.items]
    items = await upsert_pantry_items(db, current_user.id, items_data)

    return PantryListResponse(
        pantry_items=[
            PantryItemResponse(
                id=str(item.id), name=item.name, category=item.category,
                is_available=item.is_available, updated_at=item.updated_at,
            )
            for item in items
        ],
        total=len(items),
    )


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pantry_item_endpoint(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await get_pantry_item_by_id(db, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="パントリーアイテムが見つかりません")
    if item.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="権限がありません")
    await delete_pantry_item(db, item)
