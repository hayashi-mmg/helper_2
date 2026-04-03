"""献立管理 API テスト。

仕様: GET /menus/week, PUT /menus/week, POST /menus/week/copy, POST /menus/week/clear
"""
import pytest
from datetime import date, timedelta
from httpx import AsyncClient

from app.db.models import Recipe, User
from tests.conftest import auth_headers


class TestGetWeeklyMenu:
    """週間献立取得のテスト。"""

    async def test_get_empty_menu(self, client: AsyncClient, senior_user: User):
        """献立未設定時は空のメニューが返ること。"""
        res = await client.get("/api/v1/menus/week", headers=auth_headers(senior_user))
        assert res.status_code == 200
        data = res.json()
        assert "week_start" in data
        assert "menus" in data
        assert "summary" in data
        # 全曜日が存在すること
        for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            assert day in data["menus"]
            assert data["menus"][day]["breakfast"] == []
            assert data["menus"][day]["dinner"] == []
        assert data["summary"]["total_recipes"] == 0

    async def test_get_with_date_param(self, client: AsyncClient, senior_user: User):
        """date パラメータで指定した週の献立が返ること。"""
        res = await client.get(
            "/api/v1/menus/week",
            params={"date": "2025-07-14"},
            headers=auth_headers(senior_user),
        )
        assert res.status_code == 200
        # 2025-07-14 は月曜日
        assert res.json()["week_start"] == "2025-07-14"

    async def test_get_normalizes_to_monday(self, client: AsyncClient, senior_user: User):
        """水曜日を指定しても月曜日に正規化されること。"""
        res = await client.get(
            "/api/v1/menus/week",
            params={"date": "2025-07-16"},  # 水曜日
            headers=auth_headers(senior_user),
        )
        assert res.status_code == 200
        assert res.json()["week_start"] == "2025-07-14"  # 月曜日

    async def test_get_unauthenticated(self, client: AsyncClient):
        """未認証で 401 が返ること。"""
        res = await client.get("/api/v1/menus/week")
        assert res.status_code == 401


class TestUpdateWeeklyMenu:
    """週間献立更新のテスト。"""

    async def test_update_success(self, client: AsyncClient, senior_user: User, sample_recipe: Recipe):
        """献立を更新できること。"""
        res = await client.put(
            "/api/v1/menus/week",
            headers=auth_headers(senior_user),
            json={
                "week_start": "2025-07-14",
                "menus": {
                    "monday": {
                        "breakfast": [{"recipe_id": str(sample_recipe.id), "recipe_type": "主菜"}],
                        "dinner": [],
                    },
                },
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["menus"]["monday"]["breakfast"]) == 1
        assert data["menus"]["monday"]["breakfast"][0]["recipe"]["name"] == "目玉焼き"
        assert data["summary"]["total_recipes"] == 1

    async def test_update_multiple_meals(
        self, client: AsyncClient, senior_user: User, sample_recipes: list[Recipe],
    ):
        """複数のレシピを1日に設定できること。"""
        r1, r2, r3 = sample_recipes[:3]
        res = await client.put(
            "/api/v1/menus/week",
            headers=auth_headers(senior_user),
            json={
                "week_start": "2025-07-14",
                "menus": {
                    "tuesday": {
                        "breakfast": [{"recipe_id": str(r1.id), "recipe_type": "汁物"}],
                        "dinner": [
                            {"recipe_id": str(r2.id), "recipe_type": "主菜"},
                            {"recipe_id": str(r3.id), "recipe_type": "副菜"},
                        ],
                    },
                },
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["menus"]["tuesday"]["dinner"]) == 2
        assert data["summary"]["total_recipes"] == 3

    async def test_update_replaces_existing(
        self, client: AsyncClient, senior_user: User, sample_recipes: list[Recipe],
    ):
        """更新すると既存の献立が置換されること。"""
        headers = auth_headers(senior_user)
        first_recipe = sample_recipes[0]
        second_recipe = sample_recipes[1]
        # 初回設定
        await client.put(
            "/api/v1/menus/week",
            headers=headers,
            json={
                "week_start": "2025-08-04",
                "menus": {
                    "monday": {"breakfast": [{"recipe_id": str(first_recipe.id), "recipe_type": "主菜"}], "dinner": []},
                },
            },
        )
        # 上書き
        res = await client.put(
            "/api/v1/menus/week",
            headers=headers,
            json={
                "week_start": "2025-08-04",
                "menus": {
                    "monday": {"breakfast": [{"recipe_id": str(second_recipe.id), "recipe_type": "汁物"}], "dinner": []},
                },
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["menus"]["monday"]["breakfast"]) == 1
        # 上書き後は1レシピのみであること（置換を確認）
        assert data["summary"]["total_recipes"] == 1


class TestCopyWeeklyMenu:
    """週間献立コピーのテスト。"""

    async def test_copy_success(self, client: AsyncClient, senior_user: User, sample_recipe: Recipe):
        """先週の献立をコピーできること。"""
        headers = auth_headers(senior_user)
        # ソース週を設定
        await client.put(
            "/api/v1/menus/week",
            headers=headers,
            json={
                "week_start": "2025-07-07",
                "menus": {
                    "monday": {"breakfast": [{"recipe_id": str(sample_recipe.id), "recipe_type": "主菜"}], "dinner": []},
                },
            },
        )
        # コピー
        res = await client.post(
            "/api/v1/menus/week/copy",
            headers=headers,
            json={"source_week": "2025-07-07", "target_week": "2025-07-14"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["week_start"] == "2025-07-14"
        assert len(data["menus"]["monday"]["breakfast"]) == 1

    async def test_copy_same_week_error(self, client: AsyncClient, senior_user: User):
        """同じ週へのコピーが 400 で拒否されること。"""
        res = await client.post(
            "/api/v1/menus/week/copy",
            headers=auth_headers(senior_user),
            json={"source_week": "2025-07-14", "target_week": "2025-07-14"},
        )
        assert res.status_code == 400

    async def test_copy_nonexistent_source(self, client: AsyncClient, senior_user: User):
        """存在しないソース週のコピーが 404 で拒否されること。"""
        res = await client.post(
            "/api/v1/menus/week/copy",
            headers=auth_headers(senior_user),
            json={"source_week": "2099-01-06", "target_week": "2099-01-13"},
        )
        assert res.status_code == 404


class TestClearWeeklyMenu:
    """週間献立クリアのテスト。"""

    async def test_clear_success(self, client: AsyncClient, senior_user: User, sample_recipe: Recipe):
        """献立をクリアできること。"""
        headers = auth_headers(senior_user)
        # 設定
        await client.put(
            "/api/v1/menus/week",
            headers=headers,
            json={
                "week_start": "2025-09-01",
                "menus": {
                    "monday": {"breakfast": [{"recipe_id": str(sample_recipe.id), "recipe_type": "主菜"}], "dinner": []},
                },
            },
        )
        # クリア
        res = await client.post(
            "/api/v1/menus/week/clear",
            headers=headers,
            json={"week_start": "2025-09-01"},
        )
        assert res.status_code == 204

        # クリア後は空であること
        res = await client.get(
            "/api/v1/menus/week",
            params={"date": "2025-09-01"},
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["summary"]["total_recipes"] == 0

    async def test_clear_nonexistent(self, client: AsyncClient, senior_user: User):
        """存在しない週のクリアも 204 が返ること（冪等）。"""
        res = await client.post(
            "/api/v1/menus/week/clear",
            headers=auth_headers(senior_user),
            json={"week_start": "2099-12-01"},
        )
        assert res.status_code == 204
