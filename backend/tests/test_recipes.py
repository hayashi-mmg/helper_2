"""レシピ API テスト。

仕様: GET/POST /recipes, GET/PUT/DELETE /recipes/{id}
フィルタ: category, type, difficulty, search
ページネーション: page, limit
"""
import pytest
from httpx import AsyncClient

from app.db.models import Recipe, User
from tests.conftest import auth_headers


class TestListRecipes:
    """レシピ一覧取得のテスト。"""

    async def test_list_empty(self, client: AsyncClient, senior_user: User):
        """レシピが0件の場合、空リストが返ること。"""
        res = await client.get("/api/v1/recipes", headers=auth_headers(senior_user))
        assert res.status_code == 200
        data = res.json()
        assert data["recipes"] == []
        assert data["pagination"]["total"] == 0

    async def test_list_with_recipes(self, client: AsyncClient, senior_user: User, sample_recipes: list[Recipe]):
        """レシピ一覧が正しく返ること。"""
        res = await client.get("/api/v1/recipes", headers=auth_headers(senior_user))
        assert res.status_code == 200
        data = res.json()
        assert len(data["recipes"]) == 5
        assert data["pagination"]["total"] == 5

    async def test_filter_by_category(self, client: AsyncClient, senior_user: User, sample_recipes: list[Recipe]):
        """カテゴリでフィルタできること。"""
        res = await client.get(
            "/api/v1/recipes", params={"category": "和食"},
            headers=auth_headers(senior_user),
        )
        assert res.status_code == 200
        recipes = res.json()["recipes"]
        assert all(r["category"] == "和食" for r in recipes)

    async def test_filter_by_difficulty(self, client: AsyncClient, senior_user: User, sample_recipes: list[Recipe]):
        """難易度でフィルタできること。"""
        res = await client.get(
            "/api/v1/recipes", params={"difficulty": "簡単"},
            headers=auth_headers(senior_user),
        )
        assert res.status_code == 200
        recipes = res.json()["recipes"]
        assert all(r["difficulty"] == "簡単" for r in recipes)

    async def test_search(self, client: AsyncClient, senior_user: User, sample_recipes: list[Recipe]):
        """名前で検索できること。"""
        res = await client.get(
            "/api/v1/recipes", params={"search": "カレー"},
            headers=auth_headers(senior_user),
        )
        assert res.status_code == 200
        recipes = res.json()["recipes"]
        assert len(recipes) == 1
        assert "カレー" in recipes[0]["name"]

    async def test_pagination(self, client: AsyncClient, senior_user: User, sample_recipes: list[Recipe]):
        """ページネーションが正しく動作すること。"""
        res = await client.get(
            "/api/v1/recipes", params={"page": 1, "limit": 2},
            headers=auth_headers(senior_user),
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["recipes"]) == 2
        assert data["pagination"]["total"] == 5
        assert data["pagination"]["total_pages"] == 3
        assert data["pagination"]["has_next"] is True
        assert data["pagination"]["has_prev"] is False

    async def test_pagination_last_page(self, client: AsyncClient, senior_user: User, sample_recipes: list[Recipe]):
        """最終ページの has_next が False であること。"""
        res = await client.get(
            "/api/v1/recipes", params={"page": 3, "limit": 2},
            headers=auth_headers(senior_user),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["pagination"]["has_next"] is False
        assert data["pagination"]["has_prev"] is True

    async def test_list_unauthenticated(self, client: AsyncClient):
        """未認証で 401 が返ること。"""
        res = await client.get("/api/v1/recipes")
        assert res.status_code == 401


class TestCreateRecipe:
    """レシピ作成のテスト。"""

    async def test_create_success(self, client: AsyncClient, senior_user: User):
        """レシピが正しく作成されること。"""
        res = await client.post(
            "/api/v1/recipes",
            headers=auth_headers(senior_user),
            json={
                "name": "新レシピ",
                "category": "和食",
                "type": "主菜",
                "difficulty": "簡単",
                "cooking_time": 15,
                "ingredients": "卵 1個",
                "instructions": "1. 焼く",
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "新レシピ"
        assert data["category"] == "和食"
        assert data["cooking_time"] == 15
        assert "id" in data

    async def test_create_invalid_category(self, client: AsyncClient, senior_user: User):
        """無効なカテゴリで 422 が返ること。"""
        res = await client.post(
            "/api/v1/recipes",
            headers=auth_headers(senior_user),
            json={
                "name": "不正レシピ",
                "category": "フランス料理",
                "type": "主菜",
                "difficulty": "簡単",
                "cooking_time": 10,
            },
        )
        assert res.status_code == 422

    async def test_create_invalid_difficulty(self, client: AsyncClient, senior_user: User):
        """無効な難易度で 422 が返ること。"""
        res = await client.post(
            "/api/v1/recipes",
            headers=auth_headers(senior_user),
            json={
                "name": "不正レシピ",
                "category": "和食",
                "type": "主菜",
                "difficulty": "超難しい",
                "cooking_time": 10,
            },
        )
        assert res.status_code == 422

    async def test_create_missing_required(self, client: AsyncClient, senior_user: User):
        """必須フィールド不足で 422 が返ること。"""
        res = await client.post(
            "/api/v1/recipes",
            headers=auth_headers(senior_user),
            json={"name": "名前だけ"},
        )
        assert res.status_code == 422


class TestGetRecipe:
    """レシピ詳細取得のテスト。"""

    async def test_get_success(self, client: AsyncClient, senior_user: User, sample_recipe: Recipe):
        """レシピ詳細が正しく返ること。"""
        res = await client.get(
            f"/api/v1/recipes/{sample_recipe.id}",
            headers=auth_headers(senior_user),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "目玉焼き"
        assert data["ingredients"] == "卵 2個\n油 少々"

    async def test_get_not_found(self, client: AsyncClient, senior_user: User):
        """存在しないレシピで 404 が返ること。"""
        import uuid
        res = await client.get(
            f"/api/v1/recipes/{uuid.uuid4()}",
            headers=auth_headers(senior_user),
        )
        assert res.status_code == 404


class TestUpdateRecipe:
    """レシピ更新のテスト。"""

    async def test_update_success(self, client: AsyncClient, senior_user: User, sample_recipe: Recipe):
        """レシピを更新できること。"""
        res = await client.put(
            f"/api/v1/recipes/{sample_recipe.id}",
            headers=auth_headers(senior_user),
            json={"name": "更新された目玉焼き", "cooking_time": 10},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "更新された目玉焼き"
        assert data["cooking_time"] == 10

    async def test_update_forbidden(self, client: AsyncClient, helper_user: User, sample_recipe: Recipe):
        """他人のレシピを更新しようとすると 403 が返ること。"""
        res = await client.put(
            f"/api/v1/recipes/{sample_recipe.id}",
            headers=auth_headers(helper_user),
            json={"name": "不正更新"},
        )
        assert res.status_code == 403


class TestDeleteRecipe:
    """レシピ削除のテスト。"""

    async def test_delete_success(self, client: AsyncClient, senior_user: User, sample_recipe: Recipe):
        """レシピを削除（論理削除）できること。"""
        res = await client.delete(
            f"/api/v1/recipes/{sample_recipe.id}",
            headers=auth_headers(senior_user),
        )
        assert res.status_code == 204

        # 削除後は取得できないこと
        res = await client.get(
            f"/api/v1/recipes/{sample_recipe.id}",
            headers=auth_headers(senior_user),
        )
        assert res.status_code == 404

    async def test_delete_forbidden(self, client: AsyncClient, helper_user: User, sample_recipe: Recipe):
        """他人のレシピを削除しようとすると 403 が返ること。"""
        res = await client.delete(
            f"/api/v1/recipes/{sample_recipe.id}",
            headers=auth_headers(helper_user),
        )
        assert res.status_code == 403
