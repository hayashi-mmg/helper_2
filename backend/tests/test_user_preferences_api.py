"""ユーザー設定 API 統合テスト。

docs/theme_system_implementation_plan.md §5.2.2
"""
import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


class TestGetMyPreferences:
    async def test_empty_preferences_returns_null_fields(
        self, client: AsyncClient, seeded_themes, senior_user
    ):
        resp = await client.get(
            "/api/v1/users/me/preferences", headers=auth_headers(senior_user)
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["theme_id"] is None
        assert body["font_size_override"] is None

    async def test_requires_auth(self, client: AsyncClient, seeded_themes):
        resp = await client.get("/api/v1/users/me/preferences")
        assert resp.status_code == 401


class TestUpdateMyPreferences:
    async def test_set_theme_id(self, client: AsyncClient, seeded_themes, senior_user):
        resp = await client.put(
            "/api/v1/users/me/preferences",
            json={"theme_id": "warm"},
            headers=auth_headers(senior_user),
        )
        assert resp.status_code == 200
        assert resp.json()["theme_id"] == "warm"

        # 再取得で永続化を確認
        resp2 = await client.get(
            "/api/v1/users/me/preferences", headers=auth_headers(senior_user)
        )
        assert resp2.json()["theme_id"] == "warm"

    async def test_update_theme_id_overwrites(
        self, client: AsyncClient, seeded_themes, senior_user
    ):
        await client.put(
            "/api/v1/users/me/preferences",
            json={"theme_id": "warm"},
            headers=auth_headers(senior_user),
        )
        resp = await client.put(
            "/api/v1/users/me/preferences",
            json={"theme_id": "calm"},
            headers=auth_headers(senior_user),
        )
        assert resp.status_code == 200
        assert resp.json()["theme_id"] == "calm"

    async def test_nonexistent_theme_id_rejected(
        self, client: AsyncClient, seeded_themes, senior_user
    ):
        resp = await client.put(
            "/api/v1/users/me/preferences",
            json={"theme_id": "nonexistent"},
            headers=auth_headers(senior_user),
        )
        assert resp.status_code == 422

    async def test_inactive_theme_id_rejected(
        self, client: AsyncClient, seeded_themes, senior_user, db
    ):
        from sqlalchemy import update
        from app.db.models.theme import Theme

        await db.execute(
            update(Theme).where(Theme.theme_key == "warm").values(is_active=False)
        )
        await db.commit()

        resp = await client.put(
            "/api/v1/users/me/preferences",
            json={"theme_id": "warm"},
            headers=auth_headers(senior_user),
        )
        assert resp.status_code == 422

    async def test_font_size_override_persists(
        self, client: AsyncClient, seeded_themes, senior_user
    ):
        resp = await client.put(
            "/api/v1/users/me/preferences",
            json={"font_size_override": "large"},
            headers=auth_headers(senior_user),
        )
        assert resp.status_code == 200
        assert resp.json()["font_size_override"] == "large"
