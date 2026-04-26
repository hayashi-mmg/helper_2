"""管理者がLLM生成献立を任意ユーザーへ取り込むサービス。

- 既存レシピは name で再利用、無いものは新規作成
- 週単位献立を upsert
- 必要なら買い物リストも同週で再生成

`dry_run=True` の場合は最後に rollback してプレビューだけ返す。
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.admin import create_audit_log
from app.crud.menu import upsert_weekly_menu
from app.db.models.recipe import Recipe
from app.db.models.recipe_ingredient import RecipeIngredient
from app.db.models.shopping import ShoppingItem, ShoppingRequest
from app.db.models.user import User
from app.schemas.admin_menu_import import (
    MenuImportRequest,
    MenuImportResponse,
    ShoppingListResult,
    TargetUserBrief,
)
from app.services.recipe_ingestion import parse_ingredients_text
from app.services.shopping_list_generator import generate_shopping_list_from_menu

DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def _normalize_week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


async def _resolve_target_user(db: AsyncSession, payload: MenuImportRequest) -> User:
    if payload.target_user_id:
        try:
            uid = uuid.UUID(payload.target_user_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="target_user_id が不正です")
        result = await db.execute(select(User).where(User.id == uid))
    else:
        result = await db.execute(select(User).where(User.email == payload.target_user_email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="対象ユーザーが見つかりません")
    return user


async def _upsert_recipes(
    db: AsyncSession,
    user_id: uuid.UUID,
    payload: MenuImportRequest,
) -> tuple[int, int, dict[str, uuid.UUID]]:
    """payload.recipes を upsert し、(created, reused, name→id マップ) を返す。"""
    existing_result = await db.execute(select(Recipe).where(Recipe.user_id == user_id))
    name_to_id: dict[str, uuid.UUID] = {r.name: r.id for r in existing_result.scalars().all()}

    created = 0
    reused = 0
    seen_in_payload: set[str] = set()

    for r in payload.recipes:
        if r.name in seen_in_payload:
            continue
        seen_in_payload.add(r.name)

        if r.name in name_to_id:
            reused += 1
            continue

        recipe = Recipe(
            user_id=user_id,
            name=r.name,
            category=r.category,
            type=r.type,
            difficulty=r.difficulty,
            cooking_time=r.cooking_time,
            ingredients=r.ingredients_text,
            instructions=r.instructions,
            memo=r.memo,
            recipe_url=r.recipe_url,
        )
        db.add(recipe)
        await db.flush()

        for ing in parse_ingredients_text(r.ingredients_text):
            db.add(RecipeIngredient(recipe_id=recipe.id, **ing))

        name_to_id[recipe.name] = recipe.id
        created += 1

    if created > 0:
        await db.flush()

    return created, reused, name_to_id


def _validate_menu(payload: MenuImportRequest, name_to_id: dict[str, uuid.UUID]) -> list[str]:
    """menu の day キー、recipe_type、recipe_name の存在を検証。違反があれば 422 を投げる。"""
    valid_days = set(DAYS)
    invalid_days = [d for d in payload.menu.keys() if d not in valid_days]
    if invalid_days:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"不正な曜日キー: {invalid_days}（許可: {DAYS}）",
        )

    missing: list[str] = []
    for day, slot in payload.menu.items():
        for meal_type in ("breakfast", "dinner"):
            for ref in getattr(slot, meal_type):
                if ref.recipe_name not in name_to_id:
                    missing.append(f"{day}/{meal_type}: {ref.recipe_name}")
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"レシピが見つかりません: {missing}",
        )

    return []


def _build_menus_dict(payload: MenuImportRequest, name_to_id: dict[str, uuid.UUID]) -> dict:
    out: dict[str, dict[str, list[dict]]] = {}
    for day, slot in payload.menu.items():
        out[day] = {
            "breakfast": [
                {"recipe_id": str(name_to_id[ref.recipe_name]), "recipe_type": ref.recipe_type}
                for ref in slot.breakfast
            ],
            "dinner": [
                {"recipe_id": str(name_to_id[ref.recipe_name]), "recipe_type": ref.recipe_type}
                for ref in slot.dinner
            ],
        }
    return out


async def _replace_shopping_list(
    db: AsyncSession,
    *,
    target_user_id: uuid.UUID,
    week_start: date,
    helper_user_id: uuid.UUID,
) -> tuple[ShoppingListResult | None, bool]:
    """既存の同週リクエストを削除→生成。生成不可（レシピ無し等）なら None を返す。"""
    existing_q = await db.execute(
        select(ShoppingRequest).where(
            ShoppingRequest.senior_user_id == target_user_id,
            ShoppingRequest.request_date == week_start,
        )
    )
    existing = existing_q.scalars().all()
    replaced_existing = False
    if existing:
        for req in existing:
            await db.execute(delete(ShoppingItem).where(ShoppingItem.shopping_request_id == req.id))
            await db.execute(delete(ShoppingRequest).where(ShoppingRequest.id == req.id))
        await db.flush()
        replaced_existing = True

    request, _ = await generate_shopping_list_from_menu(
        db,
        user_id=target_user_id,
        week_start=week_start,
        helper_user_id=helper_user_id,
        notes=None,
    )
    if request is None:
        return None, replaced_existing

    # items を再ロード
    reloaded = await db.execute(
        select(ShoppingRequest)
        .where(ShoppingRequest.id == request.id)
        .options(selectinload(ShoppingRequest.items))
    )
    request = reloaded.scalar_one()
    total = len(request.items)
    excluded = sum(1 for i in request.items if i.is_excluded)

    return (
        ShoppingListResult(
            request_id=str(request.id),
            total_items=total,
            excluded_items=excluded,
            active_items=total - excluded,
            replaced_existing=replaced_existing,
        ),
        replaced_existing,
    )


async def import_menu_for_user(
    db: AsyncSession,
    payload: MenuImportRequest,
    actor: User,
) -> MenuImportResponse:
    from app.crud.menu import get_weekly_menu

    target = await _resolve_target_user(db, payload)
    week_start = _normalize_week_start(payload.week_start)

    pre_existing = await get_weekly_menu(db, target.id, week_start)
    replaced_menu = pre_existing is not None

    created, reused, name_to_id = await _upsert_recipes(db, target.id, payload)
    warnings = _validate_menu(payload, name_to_id)

    menus_dict = _build_menus_dict(payload, name_to_id)
    await upsert_weekly_menu(db, target.id, week_start, menus_dict)

    shopping_result: ShoppingListResult | None = None
    if payload.generate_shopping_list:
        helper_id = actor.id
        if payload.helper_user_id:
            try:
                helper_id = uuid.UUID(payload.helper_user_id)
            except ValueError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="helper_user_id が不正です")
        shopping_result, _ = await _replace_shopping_list(
            db,
            target_user_id=target.id,
            week_start=week_start,
            helper_user_id=helper_id,
        )
        if shopping_result is None:
            warnings.append("買い物リストを生成できませんでした（レシピ食材情報が不足）")

    # rollback すると ORM オブジェクトが expire するため、必要な値を先に取得する
    target_brief = TargetUserBrief(
        id=str(target.id),
        email=target.email,
        full_name=target.full_name,
        role=target.role,
    )

    if payload.dry_run:
        await db.rollback()
        applied = False
    else:
        await create_audit_log(
            db,
            user=actor,
            action="menu_import",
            resource_type="weekly_menu",
            resource_id=None,
            metadata={
                "target_user_id": target_brief.id,
                "target_user_email": target_brief.email,
                "week_start": week_start.isoformat(),
                "created_recipe_count": created,
                "reused_recipe_count": reused,
                "replaced_menu": replaced_menu,
                "shopping_list_generated": shopping_result is not None,
                "shopping_total_items": shopping_result.total_items if shopping_result else 0,
            },
        )
        await db.commit()
        applied = True

    return MenuImportResponse(
        applied=applied,
        target_user=target_brief,
        week_start=week_start,
        created_recipe_count=created,
        reused_recipe_count=reused,
        replaced_menu=replaced_menu,
        shopping_list=shopping_result,
        warnings=warnings,
    )
