"""ユーザー API テスト。

仕様: GET /users/me, PUT /users/me
"""
import pytest
from httpx import AsyncClient

from app.db.models import User
from tests.conftest import auth_headers


class TestGetProfile:
    """プロファイル取得のテスト。"""

    async def test_get_me_senior(self, client: AsyncClient, senior_user: User):
        """利用者のプロファイルが正しく返ること。"""
        res = await client.get("/api/v1/users/me", headers=auth_headers(senior_user))
        assert res.status_code == 200
        data = res.json()
        assert data["email"] == "senior@test.com"
        assert data["full_name"] == "テスト太郎"
        assert data["role"] == "senior"
        assert data["phone"] == "090-1234-5678"
        assert data["address"] == "東京都渋谷区"
        assert data["emergency_contact"] == "090-9876-5432"
        assert data["medical_notes"] == "高血圧"
        assert data["care_level"] == 2
        assert data["is_active"] is True

    async def test_get_me_helper(self, client: AsyncClient, helper_user: User):
        """ヘルパーのプロファイルが正しく返ること。"""
        res = await client.get("/api/v1/users/me", headers=auth_headers(helper_user))
        assert res.status_code == 200
        data = res.json()
        assert data["role"] == "helper"
        assert data["certification_number"] == "H-12345"

    async def test_get_me_unauthenticated(self, client: AsyncClient):
        """未認証で 401 が返ること。"""
        res = await client.get("/api/v1/users/me")
        assert res.status_code == 401


class TestUpdateProfile:
    """プロファイル更新のテスト。"""

    async def test_update_name(self, client: AsyncClient, senior_user: User):
        """氏名を更新できること。"""
        res = await client.put(
            "/api/v1/users/me",
            headers=auth_headers(senior_user),
            json={"full_name": "更新太郎"},
        )
        assert res.status_code == 200
        assert res.json()["full_name"] == "更新太郎"

    async def test_update_phone_address(self, client: AsyncClient, helper_user: User):
        """電話番号・住所を更新できること。"""
        res = await client.put(
            "/api/v1/users/me",
            headers=auth_headers(helper_user),
            json={"phone": "090-9999-0000", "address": "大阪府大阪市"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["phone"] == "090-9999-0000"
        assert data["address"] == "大阪府大阪市"

    async def test_update_emergency_contact(self, client: AsyncClient, senior_user: User):
        """緊急連絡先を更新できること。"""
        res = await client.put(
            "/api/v1/users/me",
            headers=auth_headers(senior_user),
            json={"emergency_contact": "090-1111-0000"},
        )
        assert res.status_code == 200
        assert res.json()["emergency_contact"] == "090-1111-0000"

    async def test_update_medical_notes(self, client: AsyncClient, senior_user: User):
        """医療メモを更新できること。"""
        res = await client.put(
            "/api/v1/users/me",
            headers=auth_headers(senior_user),
            json={"medical_notes": "高血圧、糖尿病"},
        )
        assert res.status_code == 200
        assert res.json()["medical_notes"] == "高血圧、糖尿病"

    async def test_update_unauthenticated(self, client: AsyncClient):
        """未認証で 401 が返ること。"""
        res = await client.put("/api/v1/users/me", json={"full_name": "不正"})
        assert res.status_code == 401
