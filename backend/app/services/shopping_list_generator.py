"""献立から買い物リストを自動生成するサービス。"""
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.pantry import get_available_pantry_names
from app.crud.recipe_ingredient import get_ingredients_by_recipe_ids
from app.db.models.menu import WeeklyMenu, WeeklyMenuRecipe
from app.db.models.recipe import Recipe
from app.db.models.recipe_ingredient import RecipeIngredient
from app.db.models.shopping import ShoppingItem, ShoppingRequest


# 買い物リストに含めない食材（購入不要）
_SKIP_INGREDIENTS = {"水", "氷", "お湯", "熱湯", "ぬるま湯", "冷水"}


@dataclass
class AggregatedIngredient:
    """集約された食材情報。"""
    name: str
    category: str
    quantities: list[str] = field(default_factory=list)  # ("レシピ名", "数量") のペア
    recipe_names: list[str] = field(default_factory=list)
    ingredient_ids: list[uuid.UUID] = field(default_factory=list)


async def _get_menu_recipe_ids(
    db: AsyncSession, user_id: uuid.UUID, week_start: date,
) -> tuple[WeeklyMenu | None, list[uuid.UUID], dict[uuid.UUID, str]]:
    """指定週の献立から全レシピID とレシピ名マップを取得。"""
    result = await db.execute(
        select(WeeklyMenu)
        .where(WeeklyMenu.user_id == user_id, WeeklyMenu.week_start == week_start)
        .options(selectinload(WeeklyMenu.recipes).selectinload(WeeklyMenuRecipe.recipe))
    )
    menu = result.scalar_one_or_none()
    if not menu or not menu.recipes:
        return menu, [], {}

    recipe_ids = []
    recipe_name_map: dict[uuid.UUID, str] = {}
    for entry in menu.recipes:
        if entry.recipe_id not in recipe_name_map:
            recipe_ids.append(entry.recipe_id)
            recipe_name_map[entry.recipe_id] = entry.recipe.name
    return menu, recipe_ids, recipe_name_map


def _aggregate_ingredients(
    ingredients: list[RecipeIngredient],
    recipe_name_map: dict[uuid.UUID, str],
) -> list[AggregatedIngredient]:
    """同名食材を集約する。"""
    grouped: dict[str, AggregatedIngredient] = {}

    for ing in ingredients:
        key = ing.name.strip()
        if key in _SKIP_INGREDIENTS:
            continue
        recipe_name = recipe_name_map.get(ing.recipe_id, "不明")

        if key not in grouped:
            grouped[key] = AggregatedIngredient(name=key, category=ing.category)

        agg = grouped[key]
        if ing.quantity:
            agg.quantities.append(f"{recipe_name} {ing.quantity}")
        agg.recipe_names.append(recipe_name)
        agg.ingredient_ids.append(ing.id)

    return list(grouped.values())


def _build_quantity_text(agg: AggregatedIngredient) -> str | None:
    """集約された数量テキストを生成。"""
    if not agg.quantities:
        return None
    if len(agg.quantities) == 1:
        return agg.quantities[0].split(" ", 1)[-1] if " " in agg.quantities[0] else agg.quantities[0]
    text = "（" + " + ".join(agg.quantities) + "）"
    if len(text) > 200:
        text = text[:197] + "…）"
    return text


async def generate_shopping_list_from_menu(
    db: AsyncSession,
    user_id: uuid.UUID,
    week_start: date,
    helper_user_id: uuid.UUID,
    notes: str | None = None,
) -> tuple[ShoppingRequest, dict[uuid.UUID, list[str]]]:
    """
    献立から買い物リストを生成する。

    Returns:
        (ShoppingRequest, item_id→recipe_sources のマッピング)
    """
    # 1. 献立のレシピを取得
    menu, recipe_ids, recipe_name_map = await _get_menu_recipe_ids(db, user_id, week_start)
    if not recipe_ids:
        return None, {}

    # 2. 全食材を取得
    ingredients = await get_ingredients_by_recipe_ids(db, recipe_ids)

    # 3. 同名食材を集約
    aggregated = _aggregate_ingredients(ingredients, recipe_name_map)

    # 4. パントリーで在庫チェック
    pantry_names = await get_available_pantry_names(db, user_id)

    # 5. ShoppingRequest + ShoppingItems を生成
    request = ShoppingRequest(
        senior_user_id=user_id,
        helper_user_id=helper_user_id,
        request_date=week_start,
        status="pending",
        notes=notes,
    )
    db.add(request)
    await db.flush()

    item_recipe_sources: dict[uuid.UUID, list[str]] = {}

    for agg in aggregated:
        is_excluded = agg.name in pantry_names
        shopping_category = agg.category or "その他"
        quantity_text = _build_quantity_text(agg)

        # 最初の ingredient_id をリンク（追跡用）
        first_ingredient_id = agg.ingredient_ids[0] if agg.ingredient_ids else None

        item = ShoppingItem(
            shopping_request_id=request.id,
            item_name=agg.name,
            category=shopping_category,
            quantity=quantity_text,
            recipe_ingredient_id=first_ingredient_id,
            is_excluded=is_excluded,
            status="pending",
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)

        # 出典レシピ名（重複排除、順序保持）
        seen = set()
        unique_sources = []
        for rn in agg.recipe_names:
            if rn not in seen:
                seen.add(rn)
                unique_sources.append(rn)
        item_recipe_sources[item.id] = unique_sources

    await db.flush()
    await db.refresh(request)
    return request, item_recipe_sources
