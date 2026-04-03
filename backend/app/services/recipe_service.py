import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.recipe import create_recipe, delete_recipe, get_recipe_by_id, get_recipes, update_recipe
from app.services.cache_service import TTL_RECIPE, cache_delete_pattern, cache_get, cache_set


def _cache_key(user_id: uuid.UUID, **kwargs) -> str:
    parts = [f"recipes:{user_id}"]
    for k, v in sorted(kwargs.items()):
        if v is not None:
            parts.append(f"{k}={v}")
    return ":".join(parts)


async def list_recipes(
    db: AsyncSession,
    user_id: uuid.UUID,
    category: str | None = None,
    type_: str | None = None,
    difficulty: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list, int]:
    # キャッシュ確認（検索クエリはキャッシュしない）
    if not search:
        key = _cache_key(user_id, category=category, type=type_, difficulty=difficulty, page=page, limit=limit)
        cached = await cache_get(key)
        if cached:
            return cached["recipes"], cached["total"]

    recipes, total = await get_recipes(db, user_id, category, type_, difficulty, search, page, limit)

    # 検索以外はキャッシュ
    if not search:
        key = _cache_key(user_id, category=category, type=type_, difficulty=difficulty, page=page, limit=limit)
        await cache_set(key, {
            "recipes": [{"id": str(r.id), "name": r.name} for r in recipes],
            "total": total,
        }, TTL_RECIPE)

    return recipes, total


async def get_recipe(db: AsyncSession, recipe_id: uuid.UUID):
    return await get_recipe_by_id(db, recipe_id)


async def create_new_recipe(db: AsyncSession, user_id: uuid.UUID, data: dict):
    recipe = await create_recipe(db, user_id, data)
    await cache_delete_pattern(f"recipes:{user_id}:*")
    return recipe


async def update_existing_recipe(db: AsyncSession, recipe, updates: dict):
    updated = await update_recipe(db, recipe, updates)
    await cache_delete_pattern(f"recipes:{recipe.user_id}:*")
    return updated


async def remove_recipe(db: AsyncSession, recipe):
    await delete_recipe(db, recipe)
    await cache_delete_pattern(f"recipes:{recipe.user_id}:*")
