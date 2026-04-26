"""管理者献立インポートAPIの統合テスト。

POST /api/v1/admin/menus/import
"""
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.menu import WeeklyMenu, WeeklyMenuRecipe
from app.db.models.recipe import Recipe
from app.db.models.recipe_ingredient import RecipeIngredient
from app.db.models.shopping import ShoppingItem, ShoppingRequest
from tests.conftest import auth_headers


def _next_monday() -> date:
    today = date.today()
    return today + timedelta(days=(7 - today.weekday()) % 7 or 7)


def _basic_payload(
    *,
    target_email: str,
    week_start: date,
    extra_recipes: list[dict] | None = None,
    extra_menu: dict | None = None,
    **overrides,
) -> dict:
    recipes = [
        {
            "name": "鶏の照り焼き",
            "category": "和食",
            "type": "主菜",
            "difficulty": "簡単",
            "cooking_time": 20,
            "ingredients_text": "鶏もも肉 300g\nしょうゆ 大さじ2\nみりん 大さじ2",
        },
        {
            "name": "白ご飯",
            "category": "和食",
            "type": "ご飯",
            "difficulty": "簡単",
            "cooking_time": 30,
            "ingredients_text": "米 2合",
        },
    ]
    if extra_recipes:
        recipes.extend(extra_recipes)

    menu = {
        "monday": {
            "breakfast": [],
            "dinner": [
                {"recipe_name": "鶏の照り焼き", "recipe_type": "主菜"},
                {"recipe_name": "白ご飯", "recipe_type": "ご飯"},
            ],
        },
        "tuesday": {"breakfast": [], "dinner": []},
        "wednesday": {"breakfast": [], "dinner": []},
        "thursday": {"breakfast": [], "dinner": []},
        "friday": {"breakfast": [], "dinner": []},
        "saturday": {"breakfast": [], "dinner": []},
        "sunday": {"breakfast": [], "dinner": []},
    }
    if extra_menu:
        menu.update(extra_menu)

    payload = {
        "target_user_email": target_email,
        "week_start": week_start.isoformat(),
        "recipes": recipes,
        "menu": menu,
    }
    payload.update(overrides)
    return payload


class TestPermission:
    async def test_senior_forbidden(self, client: AsyncClient, senior_user):
        resp = await client.post(
            "/api/v1/admin/menus/import",
            json=_basic_payload(target_email=senior_user.email, week_start=_next_monday()),
            headers=auth_headers(senior_user),
        )
        assert resp.status_code == 403

    async def test_helper_forbidden(self, client: AsyncClient, helper_user, senior_user):
        resp = await client.post(
            "/api/v1/admin/menus/import",
            json=_basic_payload(target_email=senior_user.email, week_start=_next_monday()),
            headers=auth_headers(helper_user),
        )
        assert resp.status_code == 403

    async def test_admin_allowed(self, client: AsyncClient, admin_user, senior_user):
        resp = await client.post(
            "/api/v1/admin/menus/import",
            json=_basic_payload(target_email=senior_user.email, week_start=_next_monday()),
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200


class TestRecipeAndMenuImport:
    async def test_creates_recipes_and_menu(
        self, client: AsyncClient, db: AsyncSession, admin_user, senior_user
    ):
        week_start = _next_monday()
        resp = await client.post(
            "/api/v1/admin/menus/import",
            json=_basic_payload(target_email=senior_user.email, week_start=week_start),
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["applied"] is True
        assert body["created_recipe_count"] == 2
        assert body["reused_recipe_count"] == 0
        assert body["replaced_menu"] is False
        assert body["target_user"]["email"] == senior_user.email

        # DB 確認
        recipes = (await db.execute(select(Recipe).where(Recipe.user_id == senior_user.id))).scalars().all()
        assert {r.name for r in recipes} == {"鶏の照り焼き", "白ご飯"}

        menu = (
            await db.execute(
                select(WeeklyMenu)
                .where(WeeklyMenu.user_id == senior_user.id, WeeklyMenu.week_start == week_start)
                .options(selectinload(WeeklyMenu.recipes))
            )
        ).scalar_one()
        assert len(menu.recipes) == 2
        assert {e.recipe_type for e in menu.recipes} == {"主菜", "ご飯"}

    async def test_reuses_existing_recipe_by_name(
        self, client: AsyncClient, db: AsyncSession, admin_user, senior_user, sample_recipes
    ):
        # sample_recipes に "白ご飯" が含まれている → 再利用される想定
        week_start = _next_monday()
        resp = await client.post(
            "/api/v1/admin/menus/import",
            json=_basic_payload(target_email=senior_user.email, week_start=week_start),
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["created_recipe_count"] == 1  # 鶏の照り焼きのみ新規
        assert body["reused_recipe_count"] == 1  # 白ご飯は既存

        # 同名のRecipe行が複製されていないこと
        recipes = (
            await db.execute(
                select(Recipe).where(Recipe.user_id == senior_user.id, Recipe.name == "白ご飯")
            )
        ).scalars().all()
        assert len(recipes) == 1

    async def test_replaces_existing_menu(
        self, client: AsyncClient, db: AsyncSession, admin_user, senior_user, menu_with_recipes
    ):
        # menu_with_recipes は今週の月曜日に作成されている
        week_start = menu_with_recipes.week_start
        resp = await client.post(
            "/api/v1/admin/menus/import",
            json=_basic_payload(target_email=senior_user.email, week_start=week_start),
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["replaced_menu"] is True


class TestShoppingListSync:
    async def test_generates_shopping_list(
        self, client: AsyncClient, db: AsyncSession, admin_user, senior_user
    ):
        week_start = _next_monday()
        resp = await client.post(
            "/api/v1/admin/menus/import",
            json=_basic_payload(target_email=senior_user.email, week_start=week_start),
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["shopping_list"] is not None
        assert body["shopping_list"]["total_items"] > 0

        items = (
            await db.execute(
                select(ShoppingItem)
                .join(ShoppingRequest)
                .where(
                    ShoppingRequest.senior_user_id == senior_user.id,
                    ShoppingRequest.request_date == week_start,
                )
            )
        ).scalars().all()
        assert len(items) > 0

    async def test_replaces_existing_shopping_list(
        self, client: AsyncClient, db: AsyncSession, admin_user, senior_user, helper_user
    ):
        week_start = _next_monday()
        # 既存の同週リクエストを作成
        existing = ShoppingRequest(
            senior_user_id=senior_user.id,
            helper_user_id=helper_user.id,
            request_date=week_start,
            status="pending",
        )
        db.add(existing)
        await db.commit()

        resp = await client.post(
            "/api/v1/admin/menus/import",
            json=_basic_payload(target_email=senior_user.email, week_start=week_start),
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["shopping_list"]["replaced_existing"] is True

        # 旧 request は削除されている
        remaining = (
            await db.execute(select(ShoppingRequest).where(ShoppingRequest.id == existing.id))
        ).scalar_one_or_none()
        assert remaining is None

    async def test_skip_shopping_list_when_disabled(
        self, client: AsyncClient, db: AsyncSession, admin_user, senior_user
    ):
        week_start = _next_monday()
        resp = await client.post(
            "/api/v1/admin/menus/import",
            json=_basic_payload(
                target_email=senior_user.email,
                week_start=week_start,
                generate_shopping_list=False,
            ),
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["shopping_list"] is None


class TestDryRun:
    async def test_dry_run_does_not_persist(
        self, client: AsyncClient, db: AsyncSession, admin_user, senior_user
    ):
        week_start = _next_monday()
        resp = await client.post(
            "/api/v1/admin/menus/import",
            json=_basic_payload(
                target_email=senior_user.email,
                week_start=week_start,
                dry_run=True,
            ),
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["applied"] is False
        assert body["created_recipe_count"] == 2  # プレビュー値は返る

        # 実際にはDBに何も書かれていない
        recipes = (await db.execute(select(Recipe).where(Recipe.user_id == senior_user.id))).scalars().all()
        assert len(recipes) == 0
        menus = (await db.execute(select(WeeklyMenu).where(WeeklyMenu.user_id == senior_user.id))).scalars().all()
        assert len(menus) == 0
        requests = (
            await db.execute(select(ShoppingRequest).where(ShoppingRequest.senior_user_id == senior_user.id))
        ).scalars().all()
        assert len(requests) == 0


class TestValidation:
    async def test_unknown_recipe_name_returns_422(
        self, client: AsyncClient, admin_user, senior_user
    ):
        week_start = _next_monday()
        payload = _basic_payload(target_email=senior_user.email, week_start=week_start)
        payload["menu"]["monday"]["dinner"].append(
            {"recipe_name": "存在しないレシピ", "recipe_type": "主菜"}
        )
        resp = await client.post(
            "/api/v1/admin/menus/import",
            json=payload,
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 422
        assert "存在しないレシピ" in str(resp.json()["detail"])

    async def test_invalid_recipe_type_returns_422(
        self, client: AsyncClient, admin_user, senior_user
    ):
        week_start = _next_monday()
        payload = _basic_payload(target_email=senior_user.email, week_start=week_start)
        payload["menu"]["monday"]["dinner"][0]["recipe_type"] = "デザート"
        resp = await client.post(
            "/api/v1/admin/menus/import",
            json=payload,
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 422

    async def test_invalid_day_key_returns_422(
        self, client: AsyncClient, admin_user, senior_user
    ):
        week_start = _next_monday()
        payload = _basic_payload(target_email=senior_user.email, week_start=week_start)
        payload["menu"]["funday"] = {"breakfast": [], "dinner": []}
        resp = await client.post(
            "/api/v1/admin/menus/import",
            json=payload,
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 422

    async def test_target_user_not_found_returns_404(
        self, client: AsyncClient, admin_user
    ):
        week_start = _next_monday()
        resp = await client.post(
            "/api/v1/admin/menus/import",
            json=_basic_payload(target_email="ghost@nowhere.com", week_start=week_start),
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 404

    async def test_no_target_returns_422(self, client: AsyncClient, admin_user):
        week_start = _next_monday()
        payload = _basic_payload(target_email="dummy@x.com", week_start=week_start)
        payload.pop("target_user_email")
        resp = await client.post(
            "/api/v1/admin/menus/import",
            json=payload,
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 422
