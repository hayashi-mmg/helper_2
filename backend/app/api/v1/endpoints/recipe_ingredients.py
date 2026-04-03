import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.crud.recipe import get_recipe_by_id
from app.crud.recipe_ingredient import get_ingredients_by_recipe, replace_ingredients
from app.db.models.user import User
from app.schemas.recipe_ingredient import (
    IngredientsUpdateRequest,
    RecipeIngredientResponse,
    RecipeIngredientsListResponse,
)

router = APIRouter(prefix="/recipes", tags=["レシピ食材"])


@router.get("/{recipe_id}/ingredients", response_model=RecipeIngredientsListResponse)
async def get_recipe_ingredients(
    recipe_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    recipe = await get_recipe_by_id(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="レシピが見つかりません")

    ingredients = await get_ingredients_by_recipe(db, recipe_id)
    return RecipeIngredientsListResponse(
        recipe_id=str(recipe.id),
        recipe_name=recipe.name,
        ingredients=[
            RecipeIngredientResponse(
                id=str(ing.id), name=ing.name, quantity=ing.quantity,
                category=ing.category, sort_order=ing.sort_order,
                created_at=ing.created_at,
            )
            for ing in ingredients
        ],
    )


@router.put("/{recipe_id}/ingredients", response_model=RecipeIngredientsListResponse)
async def update_recipe_ingredients(
    recipe_id: uuid.UUID,
    data: IngredientsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    recipe = await get_recipe_by_id(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="レシピが見つかりません")
    if recipe.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="権限がありません")

    items = [item.model_dump() for item in data.ingredients]
    ingredients = await replace_ingredients(db, recipe_id, items)

    return RecipeIngredientsListResponse(
        recipe_id=str(recipe.id),
        recipe_name=recipe.name,
        ingredients=[
            RecipeIngredientResponse(
                id=str(ing.id), name=ing.name, quantity=ing.quantity,
                category=ing.category, sort_order=ing.sort_order,
                created_at=ing.created_at,
            )
            for ing in ingredients
        ],
    )
