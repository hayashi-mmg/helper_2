"""管理者用アサイン管理APIテスト。"""
import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


class TestAdminListAssignments:
    """GET /api/v1/admin/assignments"""

    async def test_list_assignments(self, client: AsyncClient, admin_user, sample_assignment):
        resp = await client.get("/api/v1/admin/assignments", headers=auth_headers(admin_user))
        assert resp.status_code == 200
        data = resp.json()
        assert data["pagination"]["total"] >= 1
        assert len(data["assignments"]) >= 1

    async def test_list_assignments_filter_status(self, client: AsyncClient, admin_user, sample_assignment):
        resp = await client.get(
            "/api/v1/admin/assignments?status=active", headers=auth_headers(admin_user)
        )
        assert resp.status_code == 200
        for a in resp.json()["assignments"]:
            assert a["status"] == "active"

    async def test_list_assignments_forbidden_for_non_admin(self, client: AsyncClient, helper_user):
        resp = await client.get("/api/v1/admin/assignments", headers=auth_headers(helper_user))
        assert resp.status_code == 403


class TestAdminCreateAssignment:
    """POST /api/v1/admin/assignments"""

    async def test_create_assignment(self, client: AsyncClient, admin_user, helper_user, senior_user):
        resp = await client.post(
            "/api/v1/admin/assignments",
            json={
                "helper_id": str(helper_user.id),
                "senior_id": str(senior_user.id),
                "visit_frequency": "週2回",
                "preferred_days": [2, 4],
                "notes": "テストアサイン",
            },
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["helper"]["id"] == str(helper_user.id)
        assert data["senior"]["id"] == str(senior_user.id)
        assert data["status"] == "active"
        assert data["visit_frequency"] == "週2回"

    async def test_create_duplicate_assignment(
        self, client: AsyncClient, admin_user, helper_user, senior_user, sample_assignment,
    ):
        resp = await client.post(
            "/api/v1/admin/assignments",
            json={"helper_id": str(helper_user.id), "senior_id": str(senior_user.id)},
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 409

    async def test_create_assignment_invalid_helper(self, client: AsyncClient, admin_user, senior_user):
        resp = await client.post(
            "/api/v1/admin/assignments",
            json={"helper_id": str(senior_user.id), "senior_id": str(senior_user.id)},
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 422

    async def test_create_assignment_invalid_senior(self, client: AsyncClient, admin_user, helper_user):
        resp = await client.post(
            "/api/v1/admin/assignments",
            json={"helper_id": str(helper_user.id), "senior_id": str(helper_user.id)},
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 422


class TestAdminGetAssignment:
    """GET /api/v1/admin/assignments/{id}"""

    async def test_get_assignment(self, client: AsyncClient, admin_user, sample_assignment):
        resp = await client.get(
            f"/api/v1/admin/assignments/{sample_assignment.id}",
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    async def test_get_nonexistent_assignment(self, client: AsyncClient, admin_user):
        resp = await client.get(
            "/api/v1/admin/assignments/00000000-0000-0000-0000-000000000000",
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 404


class TestAdminUpdateAssignment:
    """PUT /api/v1/admin/assignments/{id}"""

    async def test_update_assignment(self, client: AsyncClient, admin_user, sample_assignment):
        resp = await client.put(
            f"/api/v1/admin/assignments/{sample_assignment.id}",
            json={"visit_frequency": "毎日", "notes": "更新済み"},
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["visit_frequency"] == "毎日"
        assert data["notes"] == "更新済み"


class TestAdminDeleteAssignment:
    """DELETE /api/v1/admin/assignments/{id}"""

    async def test_delete_assignment(self, client: AsyncClient, admin_user, sample_assignment):
        resp = await client.delete(
            f"/api/v1/admin/assignments/{sample_assignment.id}",
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200

        # 確認：ステータスがinactiveに変更されている
        detail_resp = await client.get(
            f"/api/v1/admin/assignments/{sample_assignment.id}",
            headers=auth_headers(admin_user),
        )
        assert detail_resp.json()["status"] == "inactive"


class TestAdminUserAssignments:
    """GET /api/v1/admin/users/{user_id}/assignments"""

    async def test_get_user_assignments(
        self, client: AsyncClient, admin_user, helper_user, sample_assignment,
    ):
        resp = await client.get(
            f"/api/v1/admin/users/{helper_user.id}/assignments",
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200
        assert resp.json()["pagination"]["total"] >= 1


class TestMyAssignments:
    """GET /api/v1/assignments/my"""

    async def test_my_assignments_as_helper(
        self, client: AsyncClient, helper_user, sample_assignment,
    ):
        resp = await client.get("/api/v1/assignments/my", headers=auth_headers(helper_user))
        assert resp.status_code == 200
        assert resp.json()["pagination"]["total"] >= 1

    async def test_my_assignments_as_senior(
        self, client: AsyncClient, senior_user, sample_assignment,
    ):
        resp = await client.get("/api/v1/assignments/my", headers=auth_headers(senior_user))
        assert resp.status_code == 200
        assert resp.json()["pagination"]["total"] >= 1
