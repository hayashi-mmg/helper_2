"""献立→買い物リスト統合テスト。"""
import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PantryItem, Recipe, RecipeIngredient, User, WeeklyMenu
from tests.conftest import auth_headers


@pytest.mark.asyncio
class TestGenerateFromMenu:
    async def test_full_flow_generate(
        self, client: AsyncClient, senior_user: User, helper_user: User,
        menu_with_recipes: WeeklyMenu,
    ):
        """献立→買い物リスト生成の一連フロー。"""
        payload = {
            "week_start": str(menu_with_recipes.week_start),
            "notes": "テスト生成",
        }
        res = await client.post(
            "/api/v1/shopping/requests/generate-from-menu",
            json=payload, headers=auth_headers(senior_user),
        )
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "pending"
        assert data["notes"] == "テスト生成"
        assert data["source_menu_week"] == str(menu_with_recipes.week_start)
        assert len(data["items"]) > 0
        assert data["summary"]["total_items"] > 0

    async def test_generate_with_pantry_exclusion(
        self, client: AsyncClient, senior_user: User, helper_user: User,
        menu_with_recipes: WeeklyMenu, sample_pantry: list[PantryItem],
    ):
        """パントリー登録済み食材が自動除外される。"""
        payload = {
            "week_start": str(menu_with_recipes.week_start),
        }
        res = await client.post(
            "/api/v1/shopping/requests/generate-from-menu",
            json=payload, headers=auth_headers(senior_user),
        )
        assert res.status_code == 201
        data = res.json()

        # しょうゆ・みりんはパントリーに在庫ありなので除外される
        excluded = [i for i in data["items"] if i["is_excluded"]]
        excluded_names = [i["item_name"] for i in excluded]
        assert "しょうゆ" in excluded_names
        assert "みりん" in excluded_names

        # 鶏もも肉はパントリーにないので除外されない
        chicken = [i for i in data["items"] if i["item_name"] == "鶏もも肉"]
        assert len(chicken) == 1
        assert chicken[0]["is_excluded"] is False

        assert data["summary"]["excluded_items"] >= 2

    async def test_generate_aggregates_same_ingredient(
        self, client: AsyncClient, senior_user: User, helper_user: User,
        menu_with_recipes: WeeklyMenu,
    ):
        """同名食材が集約される。"""
        payload = {
            "week_start": str(menu_with_recipes.week_start),
        }
        res = await client.post(
            "/api/v1/shopping/requests/generate-from-menu",
            json=payload, headers=auth_headers(senior_user),
        )
        data = res.json()

        # 鶏もも肉は2レシピで使われるが1行に集約
        chicken = [i for i in data["items"] if i["item_name"] == "鶏もも肉"]
        assert len(chicken) == 1
        assert len(chicken[0]["recipe_sources"]) == 2

        # しょうゆも2レシピで使われるが1行に集約
        soy = [i for i in data["items"] if i["item_name"] == "しょうゆ"]
        assert len(soy) == 1
        assert len(soy[0]["recipe_sources"]) == 2

    async def test_generate_recipe_sources(
        self, client: AsyncClient, senior_user: User, helper_user: User,
        menu_with_recipes: WeeklyMenu,
    ):
        """各食材のrecipe_sourcesが正しく記録される。"""
        payload = {
            "week_start": str(menu_with_recipes.week_start),
        }
        res = await client.post(
            "/api/v1/shopping/requests/generate-from-menu",
            json=payload, headers=auth_headers(senior_user),
        )
        data = res.json()

        # 卵は親子丼のみ
        egg = [i for i in data["items"] if i["item_name"] == "卵"]
        assert len(egg) == 1
        assert "親子丼" in egg[0]["recipe_sources"]

    async def test_generate_nonexistent_week(
        self, client: AsyncClient, senior_user: User, helper_user: User,
    ):
        """存在しない週で404エラー。"""
        payload = {
            "week_start": "2099-01-01",
        }
        res = await client.post(
            "/api/v1/shopping/requests/generate-from-menu",
            json=payload, headers=auth_headers(senior_user),
        )
        assert res.status_code == 404

    async def test_generate_requires_auth(self, client: AsyncClient, helper_user: User):
        """未認証で401エラー。"""
        payload = {
            "week_start": "2025-07-13",
        }
        res = await client.post("/api/v1/shopping/requests/generate-from-menu", json=payload)
        assert res.status_code == 401


@pytest.mark.asyncio
class TestToggleExclude:
    async def test_toggle_exclude_after_generate(
        self, client: AsyncClient, senior_user: User, helper_user: User,
        menu_with_recipes: WeeklyMenu,
    ):
        """生成後に手動で除外/復元ができる。"""
        # 生成
        payload = {
            "week_start": str(menu_with_recipes.week_start),
        }
        gen_res = await client.post(
            "/api/v1/shopping/requests/generate-from-menu",
            json=payload, headers=auth_headers(senior_user),
        )
        data = gen_res.json()
        item = data["items"][0]
        item_id = item["id"]

        # 除外
        res = await client.put(
            f"/api/v1/shopping/items/{item_id}/exclude",
            json={"is_excluded": True},
            headers=auth_headers(senior_user),
        )
        assert res.status_code == 200
        assert res.json()["is_excluded"] is True

        # 復元
        res2 = await client.put(
            f"/api/v1/shopping/items/{item_id}/exclude",
            json={"is_excluded": False},
            headers=auth_headers(senior_user),
        )
        assert res2.status_code == 200
        assert res2.json()["is_excluded"] is False

    async def test_toggle_exclude_nonexistent(self, client: AsyncClient, senior_user: User):
        """存在しないアイテムIDで404。"""
        fake_id = uuid.uuid4()
        res = await client.put(
            f"/api/v1/shopping/items/{fake_id}/exclude",
            json={"is_excluded": True},
            headers=auth_headers(senior_user),
        )
        assert res.status_code == 404
