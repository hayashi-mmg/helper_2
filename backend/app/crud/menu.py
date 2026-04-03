import uuid
from collections import Counter
from datetime import date

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.menu import WeeklyMenu, WeeklyMenuRecipe
from app.db.models.recipe import Recipe

DAY_MAP = {
    "monday": 1, "tuesday": 2, "wednesday": 3, "thursday": 4,
    "friday": 5, "saturday": 6, "sunday": 7,
}
DAY_REVERSE = {v: k for k, v in DAY_MAP.items()}


async def get_weekly_menu(
    db: AsyncSession, user_id: uuid.UUID, week_start: date,
) -> WeeklyMenu | None:
    result = await db.execute(
        select(WeeklyMenu)
        .where(WeeklyMenu.user_id == user_id, WeeklyMenu.week_start == week_start)
        .options(selectinload(WeeklyMenu.recipes).selectinload(WeeklyMenuRecipe.recipe))
    )
    return result.scalar_one_or_none()


async def build_menu_response(menu: WeeklyMenu | None, week_start: date) -> dict:
    """WeeklyMenu を API レスポンス用 dict に変換する。"""
    menus: dict[str, dict[str, list]] = {}
    for day_name in DAY_MAP:
        menus[day_name] = {"breakfast": [], "dinner": []}

    recipes_all: list[Recipe] = []

    if menu and menu.recipes:
        for entry in menu.recipes:
            day_name = DAY_REVERSE.get(entry.day_of_week)
            if not day_name:
                continue
            meal = entry.meal_type  # breakfast / dinner
            if meal not in ("breakfast", "dinner"):
                continue
            recipe = entry.recipe
            menus[day_name][meal].append({
                "recipe_type": entry.recipe_type,
                "recipe": {
                    "id": str(recipe.id),
                    "name": recipe.name,
                    "cooking_time": recipe.cooking_time,
                },
            })
            recipes_all.append(recipe)

    total = len(recipes_all)
    avg_time = round(sum(r.cooking_time for r in recipes_all) / total) if total else 0
    cat_dist = dict(Counter(r.category for r in recipes_all))

    return {
        "week_start": week_start,
        "menus": menus,
        "summary": {
            "total_recipes": total,
            "avg_cooking_time": avg_time,
            "category_distribution": cat_dist,
        },
    }


async def upsert_weekly_menu(
    db: AsyncSession, user_id: uuid.UUID, week_start: date, menus_data: dict,
) -> WeeklyMenu:
    menu = await get_weekly_menu(db, user_id, week_start)

    if menu:
        # 既存のレシピエントリを全削除
        await db.execute(
            delete(WeeklyMenuRecipe).where(WeeklyMenuRecipe.weekly_menu_id == menu.id)
        )
    else:
        menu = WeeklyMenu(user_id=user_id, week_start=week_start)
        db.add(menu)
        await db.flush()

    # 新しいエントリを追加
    for day_name, meals in menus_data.items():
        day_num = DAY_MAP.get(day_name)
        if day_num is None:
            continue
        for meal_type in ("breakfast", "dinner"):
            entries = meals.get(meal_type, [])
            for item in entries:
                entry = WeeklyMenuRecipe(
                    weekly_menu_id=menu.id,
                    recipe_id=uuid.UUID(item["recipe_id"]),
                    day_of_week=day_num,
                    meal_type=meal_type,
                    recipe_type=item["recipe_type"],
                )
                db.add(entry)

    await db.flush()

    # リフレッシュして関連データを再読み込み
    return await get_weekly_menu(db, user_id, week_start)


async def copy_weekly_menu(
    db: AsyncSession, user_id: uuid.UUID, source_week: date, target_week: date,
) -> WeeklyMenu | None:
    source = await get_weekly_menu(db, user_id, source_week)
    if not source or not source.recipes:
        return None

    # ソースのデータを menus_data 形式に変換
    menus_data: dict[str, dict[str, list]] = {}
    for entry in source.recipes:
        day_name = DAY_REVERSE.get(entry.day_of_week)
        if not day_name:
            continue
        if day_name not in menus_data:
            menus_data[day_name] = {"breakfast": [], "dinner": []}
        menus_data[day_name][entry.meal_type].append({
            "recipe_id": str(entry.recipe_id),
            "recipe_type": entry.recipe_type,
        })

    return await upsert_weekly_menu(db, user_id, target_week, menus_data)


async def clear_weekly_menu(
    db: AsyncSession, user_id: uuid.UUID, week_start: date,
) -> None:
    menu = await get_weekly_menu(db, user_id, week_start)
    if menu:
        await db.execute(
            delete(WeeklyMenuRecipe).where(WeeklyMenuRecipe.weekly_menu_id == menu.id)
        )
        await db.flush()
