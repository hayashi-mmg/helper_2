import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.pantry_item import PantryItem


async def get_pantry_items(
    db: AsyncSession, user_id: uuid.UUID, available_only: bool = False,
) -> list[PantryItem]:
    query = select(PantryItem).where(PantryItem.user_id == user_id)
    if available_only:
        query = query.where(PantryItem.is_available == True)  # noqa: E712
    query = query.order_by(PantryItem.name)
    result = await db.execute(query)
    return list(result.scalars().all())


async def upsert_pantry_items(
    db: AsyncSession, user_id: uuid.UUID, items: list[dict],
) -> list[PantryItem]:
    """UPSERT: user_id+name でマッチ → 存在すれば更新、なければ作成。"""
    results = []
    for item_data in items:
        name = item_data["name"]
        result = await db.execute(
            select(PantryItem).where(
                PantryItem.user_id == user_id,
                PantryItem.name == name,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.category = item_data.get("category", existing.category)
            existing.is_available = item_data.get("is_available", existing.is_available)
            await db.flush()
            await db.refresh(existing)
            results.append(existing)
        else:
            pantry_item = PantryItem(user_id=user_id, **item_data)
            db.add(pantry_item)
            await db.flush()
            await db.refresh(pantry_item)
            results.append(pantry_item)

    return results


async def get_pantry_item_by_id(
    db: AsyncSession, item_id: uuid.UUID,
) -> PantryItem | None:
    result = await db.execute(select(PantryItem).where(PantryItem.id == item_id))
    return result.scalar_one_or_none()


async def delete_pantry_item(db: AsyncSession, item: PantryItem) -> None:
    await db.delete(item)
    await db.flush()


async def get_available_pantry_names(
    db: AsyncSession, user_id: uuid.UUID,
) -> set[str]:
    """在庫ありの食材名のセットを返す。"""
    result = await db.execute(
        select(PantryItem.name).where(
            PantryItem.user_id == user_id,
            PantryItem.is_available == True,  # noqa: E712
        )
    )
    return {row[0] for row in result.all()}
