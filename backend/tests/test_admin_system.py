"""管理者用システム管理APIテスト（監査ログ、ダッシュボード、設定、通知）。"""
import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


class TestAuditLogs:
    """GET /api/v1/admin/audit-logs"""

    async def test_audit_log_created_on_user_create(self, client: AsyncClient, admin_user):
        # ユーザーを作成して監査ログが生成されることを確認
        await client.post(
            "/api/v1/admin/users",
            json={"email": "audit_test@test.com", "full_name": "監査テスト", "role": "senior"},
            headers=auth_headers(admin_user),
        )
        resp = await client.get(
            "/api/v1/admin/audit-logs?action=user.create",
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200
        logs = resp.json()["audit_logs"]
        assert len(logs) >= 1
        assert logs[0]["action"] == "user.create"

    async def test_audit_logs_forbidden_for_non_admin(self, client: AsyncClient, senior_user):
        resp = await client.get("/api/v1/admin/audit-logs", headers=auth_headers(senior_user))
        assert resp.status_code == 403

    async def test_audit_logs_filter_by_resource_type(self, client: AsyncClient, admin_user):
        # まずユーザー作成で監査ログを生成
        await client.post(
            "/api/v1/admin/users",
            json={"email": "filter_test@test.com", "full_name": "フィルタテスト", "role": "helper"},
            headers=auth_headers(admin_user),
        )
        resp = await client.get(
            "/api/v1/admin/audit-logs?resource_type=user",
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200
        for log in resp.json()["audit_logs"]:
            assert log["resource_type"] == "user"


class TestDashboard:
    """GET /api/v1/admin/dashboard/stats"""

    async def test_dashboard_stats(self, client: AsyncClient, admin_user, senior_user, helper_user):
        resp = await client.get("/api/v1/admin/dashboard/stats", headers=auth_headers(admin_user))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_users"] >= 3
        assert "users_by_role" in data
        assert "active_users" in data
        assert "generated_at" in data

    async def test_dashboard_forbidden_for_non_admin(self, client: AsyncClient, helper_user):
        resp = await client.get("/api/v1/admin/dashboard/stats", headers=auth_headers(helper_user))
        assert resp.status_code == 403


class TestSystemSettings:
    """システム設定管理テスト"""

    async def test_list_settings(self, client: AsyncClient, admin_user, sample_setting):
        resp = await client.get("/api/v1/admin/settings", headers=auth_headers(admin_user))
        assert resp.status_code == 200
        settings = resp.json()["settings"]
        assert len(settings) >= 1

    async def test_get_setting(self, client: AsyncClient, admin_user, sample_setting):
        resp = await client.get(
            "/api/v1/admin/settings/password_min_length",
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200
        assert resp.json()["setting_key"] == "password_min_length"

    async def test_get_nonexistent_setting(self, client: AsyncClient, admin_user):
        resp = await client.get(
            "/api/v1/admin/settings/nonexistent_key",
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 404

    async def test_update_setting(self, client: AsyncClient, admin_user, sample_setting):
        resp = await client.put(
            "/api/v1/admin/settings/password_min_length",
            json={"value": 12},
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200

    async def test_settings_forbidden_for_non_admin(self, client: AsyncClient, care_manager_user):
        resp = await client.get("/api/v1/admin/settings", headers=auth_headers(care_manager_user))
        assert resp.status_code == 403


class TestNotifications:
    """通知管理テスト"""

    async def test_get_my_notifications(self, client: AsyncClient, senior_user, sample_notification):
        resp = await client.get("/api/v1/notifications", headers=auth_headers(senior_user))
        assert resp.status_code == 200
        data = resp.json()
        assert data["pagination"]["total"] >= 1
        assert data["notifications"][0]["title"] == "テスト通知"

    async def test_mark_notification_read(self, client: AsyncClient, senior_user, sample_notification):
        resp = await client.put(
            f"/api/v1/notifications/{sample_notification.id}/read",
            headers=auth_headers(senior_user),
        )
        assert resp.status_code == 200

        # 確認：既読フィルタ
        resp2 = await client.get(
            "/api/v1/notifications?is_read=true",
            headers=auth_headers(senior_user),
        )
        assert resp2.status_code == 200
        assert resp2.json()["pagination"]["total"] >= 1

    async def test_mark_all_read(self, client: AsyncClient, senior_user, sample_notification):
        resp = await client.put("/api/v1/notifications/read-all", headers=auth_headers(senior_user))
        assert resp.status_code == 200

    async def test_broadcast_notification(self, client: AsyncClient, admin_user, senior_user, helper_user):
        resp = await client.post(
            "/api/v1/admin/notifications/broadcast",
            json={
                "title": "メンテナンスのお知らせ",
                "body": "明日メンテナンスを実施します",
                "notification_type": "system",
                "priority": "high",
                "target_roles": ["senior", "helper"],
            },
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 201
        assert resp.json()["count"] >= 2

    async def test_send_individual_notification(self, client: AsyncClient, admin_user, senior_user):
        resp = await client.post(
            "/api/v1/admin/notifications/send",
            json={
                "user_id": str(senior_user.id),
                "title": "個別通知テスト",
                "body": "テスト本文",
            },
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 201

    async def test_broadcast_forbidden_for_non_admin(self, client: AsyncClient, care_manager_user):
        resp = await client.post(
            "/api/v1/admin/notifications/broadcast",
            json={"title": "テスト", "body": "テスト"},
            headers=auth_headers(care_manager_user),
        )
        assert resp.status_code == 403
