import uuid
from math import ceil

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.recipe import Recipe


async def get_recipes(
    db: AsyncSession,
    user_id: uuid.UUID,
    category: str | None = None,
    type_: str | None = None,
    difficulty: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[Recipe], int]:
    query = select(Recipe).where(Recipe.user_id == user_id, Recipe.is_active == True)  # noqa: E712

    if category:
        query = query.where(Recipe.category == category)
    if type_:
        query = query.where(Recipe.type == type_)
    if difficulty:
        query = query.where(Recipe.difficulty == difficulty)
    if search:
        query = query.where(Recipe.name.ilike(f"%{search}%"))

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.order_by(Recipe.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    recipes = list(result.scalars().all())

    return recipes, total


async def get_recipe_by_id(db: AsyncSession, recipe_id: uuid.UUID) -> Recipe | None:
    result = await db.execute(select(Recipe).where(Recipe.id == recipe_id, Recipe.is_active == True))  # noqa: E712
    return result.scalar_one_or_none()


async def create_recipe(db: AsyncSession, user_id: uuid.UUID, data: dict) -> Recipe:
    recipe = Recipe(user_id=user_id, **data)
    db.add(recipe)
    await db.flush()
    await db.refresh(recipe)
    return recipe


async def update_recipe(db: AsyncSession, recipe: Recipe, updates: dict) -> Recipe:
    for key, value in updates.items():
        if value is not None:
            setattr(recipe, key, value)
    await db.flush()
    await db.refresh(recipe)
    return recipe


async def delete_recipe(db: AsyncSession, recipe: Recipe) -> None:
    recipe.is_active = False
    await db.flush()
