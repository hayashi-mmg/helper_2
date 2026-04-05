"""管理者用ユーザー管理APIテスト。"""
import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


class TestAdminListUsers:
    """GET /api/v1/admin/users"""

    async def test_list_users_as_admin(self, client: AsyncClient, admin_user, senior_user, helper_user):
        resp = await client.get("/api/v1/admin/users", headers=auth_headers(admin_user))
        assert resp.status_code == 200
        data = resp.json()
        assert data["pagination"]["total"] >= 3
        assert len(data["users"]) >= 3

    async def test_list_users_filter_by_role(self, client: AsyncClient, admin_user, senior_user, helper_user):
        resp = await client.get("/api/v1/admin/users?role=senior", headers=auth_headers(admin_user))
        assert resp.status_code == 200
        for u in resp.json()["users"]:
            assert u["role"] == "senior"

    async def test_list_users_search(self, client: AsyncClient, admin_user, senior_user):
        resp = await client.get("/api/v1/admin/users?search=テスト太郎", headers=auth_headers(admin_user))
        assert resp.status_code == 200
        assert any(u["full_name"] == "テスト太郎" for u in resp.json()["users"])

    async def test_list_users_forbidden_for_non_admin(self, client: AsyncClient, senior_user):
        resp = await client.get("/api/v1/admin/users", headers=auth_headers(senior_user))
        assert resp.status_code == 403

    async def test_list_users_forbidden_for_helper(self, client: AsyncClient, helper_user):
        resp = await client.get("/api/v1/admin/users", headers=auth_headers(helper_user))
        assert resp.status_code == 403


class TestAdminCreateUser:
    """POST /api/v1/admin/users"""

    async def test_create_user(self, client: AsyncClient, admin_user):
        resp = await client.post(
            "/api/v1/admin/users",
            json={
                "email": "newuser@test.com",
                "full_name": "新規ユーザー",
                "role": "senior",
                "phone": "090-0000-0000",
                "care_level": 3,
            },
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newuser@test.com"
        assert data["role"] == "senior"
        assert "temporary_password" in data
        assert len(data["temporary_password"]) > 0

    async def test_create_user_duplicate_email(self, client: AsyncClient, admin_user, senior_user):
        resp = await client.post(
            "/api/v1/admin/users",
            json={"email": "senior@test.com", "full_name": "重複テスト", "role": "senior"},
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 409

    async def test_create_user_invalid_role(self, client: AsyncClient, admin_user):
        resp = await client.post(
            "/api/v1/admin/users",
            json={"email": "bad@test.com", "full_name": "不正ロール", "role": "invalid"},
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 422

    async def test_create_helper_with_certification(self, client: AsyncClient, admin_user):
        resp = await client.post(
            "/api/v1/admin/users",
            json={
                "email": "newhelper@test.com",
                "full_name": "新規ヘルパー",
                "role": "helper",
                "certification_number": "H-99999",
            },
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 201
        assert resp.json()["role"] == "helper"


class TestAdminGetUser:
    """GET /api/v1/admin/users/{user_id}"""

    async def test_get_user_detail(self, client: AsyncClient, admin_user, senior_user):
        resp = await client.get(
            f"/api/v1/admin/users/{senior_user.id}", headers=auth_headers(admin_user)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "senior@test.com"
        assert data["care_level"] == 2

    async def test_get_nonexistent_user(self, client: AsyncClient, admin_user):
        resp = await client.get(
            "/api/v1/admin/users/00000000-0000-0000-0000-000000000000",
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 404


class TestAdminUpdateUser:
    """PUT /api/v1/admin/users/{user_id}"""

    async def test_update_user(self, client: AsyncClient, admin_user, senior_user):
        resp = await client.put(
            f"/api/v1/admin/users/{senior_user.id}",
            json={"full_name": "更新太郎", "care_level": 3},
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["full_name"] == "更新太郎"
        assert data["care_level"] == 3

    async def test_update_user_email_conflict(self, client: AsyncClient, admin_user, senior_user, helper_user):
        resp = await client.put(
            f"/api/v1/admin/users/{senior_user.id}",
            json={"email": "helper@test.com"},
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 409


class TestAdminDeactivateUser:
    """PUT /api/v1/admin/users/{user_id}/deactivate"""

    async def test_deactivate_user(self, client: AsyncClient, admin_user, senior_user):
        resp = await client.put(
            f"/api/v1/admin/users/{senior_user.id}/deactivate",
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    async def test_deactivate_already_inactive(self, client: AsyncClient, admin_user, inactive_user):
        resp = await client.put(
            f"/api/v1/admin/users/{inactive_user.id}/deactivate",
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 409

    async def test_cannot_deactivate_last_admin(self, client: AsyncClient, admin_user):
        resp = await client.put(
            f"/api/v1/admin/users/{admin_user.id}/deactivate",
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 409
        assert "最後のシステム管理者" in resp.json()["detail"]


class TestAdminActivateUser:
    """PUT /api/v1/admin/users/{user_id}/activate"""

    async def test_activate_user(self, client: AsyncClient, admin_user, inactive_user):
        resp = await client.put(
            f"/api/v1/admin/users/{inactive_user.id}/activate",
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True

    async def test_activate_already_active(self, client: AsyncClient, admin_user, senior_user):
        resp = await client.put(
            f"/api/v1/admin/users/{senior_user.id}/activate",
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 409


class TestAdminResetPassword:
    """POST /api/v1/admin/users/{user_id}/reset-password"""

    async def test_reset_password(self, client: AsyncClient, admin_user, senior_user):
        resp = await client.post(
            f"/api/v1/admin/users/{senior_user.id}/reset-password",
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "temporary_password" in data
        assert data["sessions_invalidated"] is True

    async def test_reset_password_nonexistent(self, client: AsyncClient, admin_user):
        resp = await client.post(
            "/api/v1/admin/users/00000000-0000-0000-0000-000000000000/reset-password",
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 404
