import uuid
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.crud.recipe import create_recipe, delete_recipe, get_recipe_by_id, get_recipes, update_recipe
from app.db.models.user import User
from app.schemas.recipe import (
    PaginationInfo,
    RecipeCreate,
    RecipeListResponse,
    RecipeResponse,
    RecipeUpdate,
)

router = APIRouter(prefix="/recipes", tags=["レシピ"])


@router.get("", response_model=RecipeListResponse)
async def list_recipes(
    category: str | None = None,
    type: str | None = Query(None, alias="type"),
    difficulty: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    recipes, total = await get_recipes(db, current_user.id, category, type, difficulty, search, page, limit)
    total_pages = ceil(total / limit) if total > 0 else 0

    return RecipeListResponse(
        recipes=[
            RecipeResponse(
                id=str(r.id), name=r.name, category=r.category, type=r.type,
                difficulty=r.difficulty, cooking_time=r.cooking_time,
                ingredients=r.ingredients, instructions=r.instructions,
                memo=r.memo, recipe_url=r.recipe_url,
                created_at=r.created_at, updated_at=r.updated_at,
            )
            for r in recipes
        ],
        pagination=PaginationInfo(
            page=page, limit=limit, total=total, total_pages=total_pages,
            has_next=page < total_pages, has_prev=page > 1,
        ),
    )


@router.get("/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(
    recipe_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    recipe = await get_recipe_by_id(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="レシピが見つかりません")

    return RecipeResponse(
        id=str(recipe.id), name=recipe.name, category=recipe.category, type=recipe.type,
        difficulty=recipe.difficulty, cooking_time=recipe.cooking_time,
        ingredients=recipe.ingredients, instructions=recipe.instructions,
        memo=recipe.memo, recipe_url=recipe.recipe_url,
        created_at=recipe.created_at, updated_at=recipe.updated_at,
    )


@router.post("", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
async def create_recipe_endpoint(
    data: RecipeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    recipe = await create_recipe(db, current_user.id, data.model_dump())
    return RecipeResponse(
        id=str(recipe.id), name=recipe.name, category=recipe.category, type=recipe.type,
        difficulty=recipe.difficulty, cooking_time=recipe.cooking_time,
        ingredients=recipe.ingredients, instructions=recipe.instructions,
        memo=recipe.memo, recipe_url=recipe.recipe_url,
        created_at=recipe.created_at, updated_at=recipe.updated_at,
    )


@router.put("/{recipe_id}", response_model=RecipeResponse)
async def update_recipe_endpoint(
    recipe_id: uuid.UUID,
    data: RecipeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    recipe = await get_recipe_by_id(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="レシピが見つかりません")
    if recipe.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="権限がありません")

    recipe = await update_recipe(db, recipe, data.model_dump(exclude_unset=True))
    return RecipeResponse(
        id=str(recipe.id), name=recipe.name, category=recipe.category, type=recipe.type,
        difficulty=recipe.difficulty, cooking_time=recipe.cooking_time,
        ingredients=recipe.ingredients, instructions=recipe.instructions,
        memo=recipe.memo, recipe_url=recipe.recipe_url,
        created_at=recipe.created_at, updated_at=recipe.updated_at,
    )


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipe_endpoint(
    recipe_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    recipe = await get_recipe_by_id(db, recipe_id)
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="レシピが見つかりません")
    if recipe.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="権限がありません")

    await delete_recipe(db, recipe)
