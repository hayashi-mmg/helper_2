"""管理者テーマ CRUD API 統合テスト。

docs/theme_system_implementation_plan.md §5.2.3
"""
import copy

import pytest
from httpx import AsyncClient

from app.services.theme_presets import STANDARD
from tests.conftest import auth_headers


def _valid_custom_definition(theme_id: str = "custom_a") -> dict:
    """テスト用のカスタムテーマ定義(standard コピー)。"""
    defn = copy.deepcopy(STANDARD)
    defn["id"] = theme_id
    defn["name"] = "カスタム A"
    return defn


class TestAdminCreateTheme:
    async def test_non_admin_forbidden(
        self, client: AsyncClient, seeded_themes, senior_user
    ):
        resp = await client.post(
            "/api/v1/admin/themes",
            json={
                "theme_key": "custom_a",
                "name": "カスタム A",
                "definition": _valid_custom_definition(),
            },
            headers=auth_headers(senior_user),
        )
        assert resp.status_code == 403

    async def test_create_success(
        self, client: AsyncClient, seeded_themes, admin_user
    ):
        resp = await client.post(
            "/api/v1/admin/themes",
            json={
                "theme_key": "custom_a",
                "name": "カスタム A",
                "description": "テスト用",
                "definition": _valid_custom_definition(),
                "is_active": True,
            },
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["theme_key"] == "custom_a"
        assert body["is_builtin"] is False

    async def test_duplicate_key_conflict(
        self, client: AsyncClient, seeded_themes, admin_user
    ):
        resp = await client.post(
            "/api/v1/admin/themes",
            json={
                "theme_key": "standard",  # 組込みと衝突
                "name": "重複",
                "definition": _valid_custom_definition("standard"),
            },
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 409

    async def test_validation_font_size(
        self, client: AsyncClient, seeded_themes, admin_user
    ):
        bad = _valid_custom_definition("custom_small")
        bad["fonts"]["baseSizePx"] = 14
        resp = await client.post(
            "/api/v1/admin/themes",
            json={
                "theme_key": "custom_small",
                "name": "小さいフォント",
                "definition": bad,
            },
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["code"] == "THEME_VALIDATION_FAILED"
        codes = [e["code"] for e in detail["errors"]]
        assert "font_size_too_small" in codes

    async def test_validation_low_contrast(
        self, client: AsyncClient, seeded_themes, admin_user
    ):
        bad = _valid_custom_definition("custom_lowc")
        bad["semanticTokens"]["text.primary"] = "#bbbbbb"
        resp = await client.post(
            "/api/v1/admin/themes",
            json={
                "theme_key": "custom_lowc",
                "name": "低コントラスト",
                "definition": bad,
            },
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 422


class TestAdminUpdateTheme:
    async def test_update_custom_theme(
        self, client: AsyncClient, seeded_themes, admin_user
    ):
        # 先にカスタムを作成
        await client.post(
            "/api/v1/admin/themes",
            json={
                "theme_key": "custom_u",
                "name": "旧名",
                "definition": _valid_custom_definition("custom_u"),
            },
            headers=auth_headers(admin_user),
        )
        resp = await client.put(
            "/api/v1/admin/themes/custom_u",
            json={"name": "新名"},
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "新名"

    async def test_builtin_name_update_allowed(
        self, client: AsyncClient, seeded_themes, admin_user
    ):
        resp = await client.put(
            "/api/v1/admin/themes/standard",
            json={"description": "更新後の説明"},
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200

    async def test_builtin_definition_update_forbidden(
        self, client: AsyncClient, seeded_themes, admin_user
    ):
        resp = await client.put(
            "/api/v1/admin/themes/standard",
            json={"definition": _valid_custom_definition("standard")},
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "THEME_BUILTIN_IMMUTABLE"


class TestAdminDeleteTheme:
    async def test_delete_custom(self, client: AsyncClient, seeded_themes, admin_user):
        await client.post(
            "/api/v1/admin/themes",
            json={
                "theme_key": "custom_del",
                "name": "削除対象",
                "definition": _valid_custom_definition("custom_del"),
            },
            headers=auth_headers(admin_user),
        )
        resp = await client.delete(
            "/api/v1/admin/themes/custom_del", headers=auth_headers(admin_user)
        )
        assert resp.status_code == 204

    async def test_delete_builtin_forbidden(
        self, client: AsyncClient, seeded_themes, admin_user
    ):
        resp = await client.delete(
            "/api/v1/admin/themes/standard", headers=auth_headers(admin_user)
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "THEME_BUILTIN_DELETE_FORBIDDEN"

    async def test_delete_default_theme_forbidden(
        self, client: AsyncClient, seeded_themes, admin_user, db
    ):
        # カスタム作成 → 既定に指定 → 削除試行 → 409
        await client.post(
            "/api/v1/admin/themes",
            json={
                "theme_key": "default_test",
                "name": "既定候補",
                "definition": _valid_custom_definition("default_test"),
            },
            headers=auth_headers(admin_user),
        )
        resp = await client.put(
            "/api/v1/admin/settings/default_theme_id",
            json={"value": "default_test"},
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200

        del_resp = await client.delete(
            "/api/v1/admin/themes/default_test", headers=auth_headers(admin_user)
        )
        assert del_resp.status_code == 409
        assert del_resp.json()["detail"]["code"] == "THEME_IN_USE_AS_DEFAULT"


class TestAdminSetDefaultTheme:
    async def test_set_valid_theme(
        self, client: AsyncClient, seeded_themes, admin_user
    ):
        resp = await client.put(
            "/api/v1/admin/settings/default_theme_id",
            json={"value": "warm"},
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 200
        assert resp.json()["value"] == "warm"

    async def test_set_nonexistent_rejected(
        self, client: AsyncClient, seeded_themes, admin_user
    ):
        resp = await client.put(
            "/api/v1/admin/settings/default_theme_id",
            json={"value": "nope"},
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 422

    async def test_set_inactive_rejected(
        self, client: AsyncClient, seeded_themes, admin_user, db
    ):
        from sqlalchemy import update
        from app.db.models.theme import Theme

        await db.execute(
            update(Theme).where(Theme.theme_key == "warm").values(is_active=False)
        )
        await db.commit()

        resp = await client.put(
            "/api/v1/admin/settings/default_theme_id",
            json={"value": "warm"},
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 422


class TestAuditLog:
    async def test_theme_create_audited(
        self, client: AsyncClient, seeded_themes, admin_user
    ):
        await client.post(
            "/api/v1/admin/themes",
            json={
                "theme_key": "custom_audit",
                "name": "監査確認",
                "definition": _valid_custom_definition("custom_audit"),
            },
            headers=auth_headers(admin_user),
        )
        logs = await client.get(
            "/api/v1/admin/audit-logs?action=theme.create",
            headers=auth_headers(admin_user),
        )
        assert logs.status_code == 200
        items = logs.json()["audit_logs"]
        assert any(
            log["action"] == "theme.create" and "custom_audit" in str(log.get("changes"))
            for log in items
        )
