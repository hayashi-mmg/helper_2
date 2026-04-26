"""テーマシステム API 統合テスト(公開 + 認証ユーザー)。

docs/theme_system_implementation_plan.md §5.2.2
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.system_setting import SystemSetting
from app.db.models.theme import Theme
from tests.conftest import auth_headers


class TestPublicDefaultTheme:
    async def test_returns_standard_by_default(self, client: AsyncClient, seeded_themes):
        resp = await client.get("/api/v1/themes/public/default")
        assert resp.status_code == 200
        body = resp.json()
        assert body["theme_key"] == "standard"
        assert body["definition"]["id"] == "standard"

    async def test_no_auth_required(self, client: AsyncClient, seeded_themes):
        # Authorization ヘッダなしで 200
        resp = await client.get("/api/v1/themes/public/default")
        assert resp.status_code == 200

    async def test_cache_control_header(self, client: AsyncClient, seeded_themes):
        resp = await client.get("/api/v1/themes/public/default")
        assert "Cache-Control" in resp.headers
        assert "max-age=300" in resp.headers["Cache-Control"]

    async def test_follows_default_theme_id_setting(
        self, client: AsyncClient, seeded_themes, db: AsyncSession
    ):
        # default_theme_id を warm に変更
        from sqlalchemy import select, update

        await db.execute(
            update(SystemSetting)
            .where(SystemSetting.setting_key == "default_theme_id")
            .values(setting_value={"value": "warm"})
        )
        await db.commit()

        resp = await client.get("/api/v1/themes/public/default")
        assert resp.status_code == 200
        assert resp.json()["theme_key"] == "warm"

    async def test_fallback_when_default_theme_inactive(
        self, client: AsyncClient, seeded_themes, db: AsyncSession
    ):
        # warm を非アクティブに + default を warm に向ける
        from sqlalchemy import update

        await db.execute(update(Theme).where(Theme.theme_key == "warm").values(is_active=False))
        await db.execute(
            update(SystemSetting)
            .where(SystemSetting.setting_key == "default_theme_id")
            .values(setting_value={"value": "warm"})
        )
        await db.commit()

        resp = await client.get("/api/v1/themes/public/default")
        assert resp.status_code == 200
        # standard にフォールバック
        assert resp.json()["theme_key"] == "standard"


class TestListThemes:
    async def test_requires_auth(self, client: AsyncClient, seeded_themes):
        resp = await client.get("/api/v1/themes")
        assert resp.status_code == 401

    async def test_lists_all_presets(self, client: AsyncClient, seeded_themes, senior_user):
        resp = await client.get("/api/v1/themes", headers=auth_headers(senior_user))
        assert resp.status_code == 200
        keys = {t["theme_key"] for t in resp.json()["themes"]}
        assert keys == {"standard", "high-contrast", "warm", "calm"}

    async def test_filter_is_builtin_false_empty(
        self, client: AsyncClient, seeded_themes, senior_user
    ):
        resp = await client.get(
            "/api/v1/themes?is_builtin=false", headers=auth_headers(senior_user)
        )
        assert resp.status_code == 200
        assert resp.json()["themes"] == []


class TestGetTheme:
    async def test_existing(self, client: AsyncClient, seeded_themes, senior_user):
        resp = await client.get(
            "/api/v1/themes/standard", headers=auth_headers(senior_user)
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["theme_key"] == "standard"
        assert "definition" in body

    async def test_not_found(self, client: AsyncClient, seeded_themes, senior_user):
        resp = await client.get(
            "/api/v1/themes/nonexistent", headers=auth_headers(senior_user)
        )
        assert resp.status_code == 404

    async def test_inactive_not_accessible(
        self, client: AsyncClient, seeded_themes, senior_user, db: AsyncSession
    ):
        from sqlalchemy import update

        await db.execute(
            update(Theme).where(Theme.theme_key == "warm").values(is_active=False)
        )
        await db.commit()

        resp = await client.get(
            "/api/v1/themes/warm", headers=auth_headers(senior_user)
        )
        assert resp.status_code == 404
