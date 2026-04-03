import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.recipe_ingredient import RecipeIngredient


async def get_ingredients_by_recipe(
    db: AsyncSession, recipe_id: uuid.UUID,
) -> list[RecipeIngredient]:
    result = await db.execute(
        select(RecipeIngredient)
        .where(RecipeIngredient.recipe_id == recipe_id)
        .order_by(RecipeIngredient.sort_order, RecipeIngredient.created_at)
    )
    return list(result.scalars().all())


async def replace_ingredients(
    db: AsyncSession, recipe_id: uuid.UUID, items: list[dict],
) -> list[RecipeIngredient]:
    """既存食材を全削除し、新しいリストで置き換える（PUT semantics）。"""
    await db.execute(
        delete(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe_id)
    )

    ingredients = []
    for item in items:
        ingredient = RecipeIngredient(recipe_id=recipe_id, **item)
        db.add(ingredient)
        ingredients.append(ingredient)

    await db.flush()
    for ing in ingredients:
        await db.refresh(ing)
    return ingredients


async def get_ingredients_by_recipe_ids(
    db: AsyncSession, recipe_ids: list[uuid.UUID],
) -> list[RecipeIngredient]:
    if not recipe_ids:
        return []
    result = await db.execute(
        select(RecipeIngredient)
        .where(RecipeIngredient.recipe_id.in_(recipe_ids))
        .order_by(RecipeIngredient.recipe_id, RecipeIngredient.sort_order)
    )
    return list(result.scalars().all())
