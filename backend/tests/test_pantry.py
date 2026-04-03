"""パントリーAPIテスト。"""
import uuid

import pytest
from httpx import AsyncClient

from app.db.models import PantryItem, User
from tests.conftest import auth_headers


@pytest.mark.asyncio
class TestGetPantry:
    async def test_get_pantry_empty(self, client: AsyncClient, senior_user: User):
        """パントリー未登録で空リスト返却。"""
        res = await client.get("/api/v1/pantry", headers=auth_headers(senior_user))
        assert res.status_code == 200
        data = res.json()
        assert data["pantry_items"] == []
        assert data["total"] == 0

    async def test_get_pantry_all(self, client: AsyncClient, senior_user: User, sample_pantry: list[PantryItem]):
        """全アイテム返却（在庫あり・なし両方）。"""
        res = await client.get("/api/v1/pantry", headers=auth_headers(senior_user))
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 3

    async def test_get_pantry_available_only(self, client: AsyncClient, senior_user: User, sample_pantry: list[PantryItem]):
        """available_only=trueで在庫ありのみ。"""
        res = await client.get("/api/v1/pantry?available_only=true", headers=auth_headers(senior_user))
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        assert all(item["is_available"] for item in data["pantry_items"])


@pytest.mark.asyncio
class TestUpdatePantry:
    async def test_update_pantry_create(self, client: AsyncClient, senior_user: User):
        """新規アイテム作成。"""
        payload = {
            "items": [
                {"name": "塩", "category": "調味料", "is_available": True},
                {"name": "こしょう", "category": "調味料", "is_available": True},
            ]
        }
        res = await client.put("/api/v1/pantry", json=payload, headers=auth_headers(senior_user))
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2

    async def test_update_pantry_upsert(self, client: AsyncClient, senior_user: User, sample_pantry: list[PantryItem]):
        """既存アイテムの更新（UPSERT）。"""
        payload = {
            "items": [
                {"name": "しょうゆ", "category": "調味料", "is_available": False},
            ]
        }
        res = await client.put("/api/v1/pantry", json=payload, headers=auth_headers(senior_user))
        assert res.status_code == 200
        data = res.json()
        updated = [i for i in data["pantry_items"] if i["name"] == "しょうゆ"][0]
        assert updated["is_available"] is False

    async def test_update_pantry_invalid_category(self, client: AsyncClient, senior_user: User):
        """不正カテゴリでバリデーションエラー。"""
        payload = {"items": [{"name": "テスト", "category": "不正"}]}
        res = await client.put("/api/v1/pantry", json=payload, headers=auth_headers(senior_user))
        assert res.status_code == 422


@pytest.mark.asyncio
class TestDeletePantryItem:
    async def test_delete_pantry_item(self, client: AsyncClient, senior_user: User, sample_pantry: list[PantryItem]):
        """アイテム削除で204返却。"""
        item_id = sample_pantry[0].id
        res = await client.delete(f"/api/v1/pantry/{item_id}", headers=auth_headers(senior_user))
        assert res.status_code == 204

        # 削除後に取得して件数確認
        res2 = await client.get("/api/v1/pantry", headers=auth_headers(senior_user))
        assert res2.json()["total"] == 2

    async def test_delete_pantry_nonexistent(self, client: AsyncClient, senior_user: User):
        """存在しないIDで404。"""
        fake_id = uuid.uuid4()
        res = await client.delete(f"/api/v1/pantry/{fake_id}", headers=auth_headers(senior_user))
        assert res.status_code == 404

    async def test_delete_pantry_other_user(self, client: AsyncClient, helper_user: User, sample_pantry: list[PantryItem]):
        """他ユーザーのパントリーにアクセス不可。"""
        item_id = sample_pantry[0].id
        res = await client.delete(f"/api/v1/pantry/{item_id}", headers=auth_headers(helper_user))
        assert res.status_code == 403
