"""認証 API テスト。

仕様: POST /auth/login, /auth/register, /auth/refresh, /auth/logout
"""
import pytest
from httpx import AsyncClient

from app.db.models import User
from tests.conftest import auth_headers


# ============================================================
# POST /auth/login
# ============================================================
class TestLogin:
    """ログインエンドポイントのテスト。"""

    async def test_login_success(self, client: AsyncClient, senior_user: User):
        """正しい認証情報でログインできること。"""
        res = await client.post("/api/v1/auth/login", json={
            "email": "senior@test.com",
            "password": "password123",
        })
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 1800  # 30分 * 60秒
        assert data["user"]["email"] == "senior@test.com"
        assert data["user"]["role"] == "senior"
        assert data["user"]["full_name"] == "テスト太郎"

    async def test_login_wrong_password(self, client: AsyncClient, senior_user: User):
        """パスワード不一致で 401 が返ること。"""
        res = await client.post("/api/v1/auth/login", json={
            "email": "senior@test.com",
            "password": "wrongpassword",
        })
        assert res.status_code == 401

    async def test_login_nonexistent_email(self, client: AsyncClient):
        """存在しないメールアドレスで 401 が返ること。"""
        res = await client.post("/api/v1/auth/login", json={
            "email": "nobody@test.com",
            "password": "password123",
        })
        assert res.status_code == 401

    async def test_login_inactive_user(self, client: AsyncClient, inactive_user: User):
        """無効ユーザーのログインが拒否されること。"""
        res = await client.post("/api/v1/auth/login", json={
            "email": "inactive@test.com",
            "password": "password123",
        })
        assert res.status_code == 403

    async def test_login_missing_fields(self, client: AsyncClient):
        """必須フィールド不足で 422 が返ること。"""
        res = await client.post("/api/v1/auth/login", json={"email": "test@test.com"})
        assert res.status_code == 422


# ============================================================
# POST /auth/register
# ============================================================
class TestRegister:
    """ユーザー登録エンドポイントのテスト。"""

    async def test_register_success(self, client: AsyncClient):
        """新規ユーザーが登録できること。"""
        res = await client.post("/api/v1/auth/register", json={
            "email": "newuser@test.com",
            "password": "securepass123",
            "full_name": "新規ユーザー",
            "role": "helper",
            "phone": "090-5555-6666",
        })
        assert res.status_code == 201
        data = res.json()
        assert "access_token" in data
        assert data["user"]["email"] == "newuser@test.com"
        assert data["user"]["role"] == "helper"

    async def test_register_duplicate_email(self, client: AsyncClient, senior_user: User):
        """既存メールアドレスの登録が 409 で拒否されること。"""
        res = await client.post("/api/v1/auth/register", json={
            "email": "senior@test.com",
            "password": "password123",
            "full_name": "重複ユーザー",
            "role": "senior",
        })
        assert res.status_code == 409

    async def test_register_invalid_role(self, client: AsyncClient):
        """無効なロールの登録が 400 で拒否されること。"""
        res = await client.post("/api/v1/auth/register", json={
            "email": "badrole@test.com",
            "password": "password123",
            "full_name": "不正ロール",
            "role": "admin",
        })
        assert res.status_code == 400

    async def test_register_all_roles(self, client: AsyncClient):
        """全ロール（senior, helper, care_manager）が登録できること。"""
        for i, role in enumerate(["senior", "helper", "care_manager"]):
            res = await client.post("/api/v1/auth/register", json={
                "email": f"role_{role}_{i}@test.com",
                "password": "password123",
                "full_name": f"ロール{role}",
                "role": role,
            })
            assert res.status_code == 201, f"Failed for role: {role}"
            assert res.json()["user"]["role"] == role


# ============================================================
# POST /auth/refresh
# ============================================================
class TestRefresh:
    """トークンリフレッシュのテスト。"""

    async def test_refresh_success(self, client: AsyncClient, helper_user: User):
        """有効なトークンでリフレッシュできること。"""
        res = await client.post(
            "/api/v1/auth/refresh",
            headers=auth_headers(helper_user),
        )
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["expires_in"] == 1800

    async def test_refresh_no_token(self, client: AsyncClient):
        """トークンなしで 401 が返ること。"""
        res = await client.post("/api/v1/auth/refresh")
        assert res.status_code == 401


# ============================================================
# POST /auth/logout
# ============================================================
class TestLogout:
    """ログアウトのテスト。"""

    async def test_logout_success(self, client: AsyncClient, senior_user: User):
        """ログアウトが成功すること。"""
        res = await client.post(
            "/api/v1/auth/logout",
            headers=auth_headers(senior_user),
        )
        assert res.status_code == 200
        assert "ログアウト" in res.json()["message"]

    async def test_logout_no_token(self, client: AsyncClient):
        """未認証でログアウトすると 401 が返ること。"""
        res = await client.post("/api/v1/auth/logout")
        assert res.status_code == 401
