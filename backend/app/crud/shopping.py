import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.shopping import ShoppingItem, ShoppingRequest


async def get_shopping_requests(
    db: AsyncSession,
    user_id: uuid.UUID,
    status: str | None = None,
) -> list[ShoppingRequest]:
    query = (
        select(ShoppingRequest)
        .options(selectinload(ShoppingRequest.items))
        .where(
            (ShoppingRequest.senior_user_id == user_id) | (ShoppingRequest.helper_user_id == user_id)
        )
    )
    if status:
        query = query.where(ShoppingRequest.status == status)

    query = query.order_by(ShoppingRequest.request_date.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_shopping_request_by_id(db: AsyncSession, request_id: uuid.UUID) -> ShoppingRequest | None:
    result = await db.execute(
        select(ShoppingRequest)
        .options(selectinload(ShoppingRequest.items))
        .where(ShoppingRequest.id == request_id)
    )
    return result.scalar_one_or_none()


async def create_shopping_request(db: AsyncSession, data: dict, items_data: list[dict]) -> ShoppingRequest:
    request = ShoppingRequest(**data)
    db.add(request)
    await db.flush()

    for item_data in items_data:
        item = ShoppingItem(shopping_request_id=request.id, **item_data)
        db.add(item)

    await db.flush()
    await db.refresh(request)
    return request


async def update_shopping_item(db: AsyncSession, item_id: uuid.UUID, updates: dict) -> ShoppingItem | None:
    result = await db.execute(select(ShoppingItem).where(ShoppingItem.id == item_id))
    item = result.scalar_one_or_none()
    if item is None:
        return None

    for key, value in updates.items():
        if value is not None:
            setattr(item, key, value)

    await db.flush()
    await db.refresh(item)
    return item
