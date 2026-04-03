"""買い物管理 API テスト。

仕様: GET /shopping/requests, POST /shopping/requests, PUT /shopping/items/{id}
"""
import pytest
from datetime import date
from httpx import AsyncClient

from app.db.models import ShoppingRequest, ShoppingItem, User
from tests.conftest import auth_headers


class TestListShoppingRequests:
    """買い物依頼一覧テスト。"""

    async def test_list_requests(
        self, client: AsyncClient, helper_user: User, sample_shopping_request: ShoppingRequest,
    ):
        """依頼一覧が取得できること。"""
        res = await client.get("/api/v1/shopping/requests", headers=auth_headers(helper_user))
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 1
        req = data[0]
        assert "items" in req
        assert len(req["items"]) == 3

    async def test_list_filter_by_status(
        self, client: AsyncClient, helper_user: User, sample_shopping_request: ShoppingRequest,
    ):
        """ステータスでフィルタできること。"""
        res = await client.get(
            "/api/v1/shopping/requests",
            params={"status": "pending"},
            headers=auth_headers(helper_user),
        )
        assert res.status_code == 200
        data = res.json()
        assert all(r["status"] == "pending" for r in data)

    async def test_list_filter_no_match(
        self, client: AsyncClient, helper_user: User, sample_shopping_request: ShoppingRequest,
    ):
        """マッチしないステータスで空リストが返ること。"""
        res = await client.get(
            "/api/v1/shopping/requests",
            params={"status": "completed"},
            headers=auth_headers(helper_user),
        )
        assert res.status_code == 200
        assert res.json() == []

    async def test_list_unauthenticated(self, client: AsyncClient):
        """未認証で 401 が返ること。"""
        res = await client.get("/api/v1/shopping/requests")
        assert res.status_code == 401


class TestCreateShoppingRequest:
    """買い物依頼作成テスト。"""

    async def test_create_success(self, client: AsyncClient, helper_user: User, senior_user: User):
        """買い物依頼を作成できること。"""
        res = await client.post(
            "/api/v1/shopping/requests",
            headers=auth_headers(helper_user),
            json={
                "senior_user_id": str(senior_user.id),
                "request_date": str(date.today()),
                "notes": "午前中にお願いします",
                "items": [
                    {"item_name": "卵", "category": "食材", "quantity": "1パック"},
                    {"item_name": "醤油", "category": "調味料", "quantity": "1本"},
                ],
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "pending"
        assert len(data["items"]) == 2
        assert data["items"][0]["item_name"] == "卵"
        assert data["items"][0]["status"] == "pending"
        assert data["notes"] == "午前中にお願いします"

    async def test_create_with_all_categories(self, client: AsyncClient, helper_user: User, senior_user: User):
        """全カテゴリのアイテムを含む依頼を作成できること。"""
        items = [
            {"item_name": "米", "category": "食材"},
            {"item_name": "塩", "category": "調味料"},
            {"item_name": "ティッシュ", "category": "日用品"},
            {"item_name": "風邪薬", "category": "医薬品"},
            {"item_name": "乾電池", "category": "その他"},
        ]
        res = await client.post(
            "/api/v1/shopping/requests",
            headers=auth_headers(helper_user),
            json={
                "senior_user_id": str(senior_user.id),
                "request_date": str(date.today()),
                "items": items,
            },
        )
        assert res.status_code == 201
        assert len(res.json()["items"]) == 5

    async def test_create_missing_items(self, client: AsyncClient, helper_user: User, senior_user: User):
        """アイテムなしの依頼で 422 が返ること。"""
        res = await client.post(
            "/api/v1/shopping/requests",
            headers=auth_headers(helper_user),
            json={
                "senior_user_id": str(senior_user.id),
                "request_date": str(date.today()),
            },
        )
        assert res.status_code == 422


class TestUpdateShoppingItem:
    """買い物アイテム更新テスト。"""

    async def test_update_status_purchased(
        self, client: AsyncClient, helper_user: User, sample_shopping_request: ShoppingRequest,
        db,
    ):
        """アイテムを購入済みに更新できること。"""
        # フィクスチャのリクエストからアイテムIDを取得
        res = await client.get("/api/v1/shopping/requests", headers=auth_headers(helper_user))
        items = res.json()[0]["items"]
        item_id = items[0]["id"]

        res = await client.put(
            f"/api/v1/shopping/items/{item_id}",
            headers=auth_headers(helper_user),
            json={"status": "purchased"},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "purchased"

    async def test_update_status_unavailable(
        self, client: AsyncClient, helper_user: User, sample_shopping_request: ShoppingRequest,
    ):
        """アイテムを入手不可に更新できること。"""
        res = await client.get("/api/v1/shopping/requests", headers=auth_headers(helper_user))
        items = res.json()[0]["items"]
        item_id = items[1]["id"]

        res = await client.put(
            f"/api/v1/shopping/items/{item_id}",
            headers=auth_headers(helper_user),
            json={"status": "unavailable"},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "unavailable"

    async def test_update_invalid_status(
        self, client: AsyncClient, helper_user: User, sample_shopping_request: ShoppingRequest,
    ):
        """無効なステータスで 422 が返ること。"""
        res = await client.get("/api/v1/shopping/requests", headers=auth_headers(helper_user))
        items = res.json()[0]["items"]
        item_id = items[0]["id"]

        res = await client.put(
            f"/api/v1/shopping/items/{item_id}",
            headers=auth_headers(helper_user),
            json={"status": "returned"},
        )
        assert res.status_code == 422

    async def test_update_item_not_found(self, client: AsyncClient, helper_user: User):
        """存在しないアイテムの更新で 404 が返ること。"""
        import uuid
        res = await client.put(
            f"/api/v1/shopping/items/{uuid.uuid4()}",
            headers=auth_headers(helper_user),
            json={"status": "purchased"},
        )
        assert res.status_code == 404
