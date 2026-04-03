import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.menu import (
    build_menu_response,
    clear_weekly_menu,
    copy_weekly_menu,
    get_weekly_menu,
    upsert_weekly_menu,
)
from app.services.cache_service import TTL_MENU, cache_delete, cache_get, cache_set


def _cache_key(user_id: uuid.UUID, week_start: date) -> str:
    return f"menu:{user_id}:{week_start}"


async def get_menu(db: AsyncSession, user_id: uuid.UUID, week_start: date) -> dict:
    key = _cache_key(user_id, week_start)
    cached = await cache_get(key)
    if cached:
        return cached

    menu = await get_weekly_menu(db, user_id, week_start)
    result = await build_menu_response(menu, week_start)

    await cache_set(key, result, TTL_MENU)
    return result


async def update_menu(db: AsyncSession, user_id: uuid.UUID, week_start: date, menus_data: dict) -> dict:
    menu = await upsert_weekly_menu(db, user_id, week_start, menus_data)
    result = await build_menu_response(menu, week_start)

    await cache_delete(_cache_key(user_id, week_start))
    return result


async def copy_menu(db: AsyncSession, user_id: uuid.UUID, source_week: date, target_week: date) -> dict | None:
    menu = await copy_weekly_menu(db, user_id, source_week, target_week)
    if not menu:
        return None

    result = await build_menu_response(menu, target_week)
    await cache_delete(_cache_key(user_id, target_week))
    return result


async def clear_menu(db: AsyncSession, user_id: uuid.UUID, week_start: date) -> None:
    await clear_weekly_menu(db, user_id, week_start)
    await cache_delete(_cache_key(user_id, week_start))
