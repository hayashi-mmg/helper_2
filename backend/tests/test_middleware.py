"""ミドルウェア・ヘルスチェック・メトリクスのテスト。

仕様: GET /health, GET /metrics, セキュリティヘッダー, レスポンスタイム
"""
import pytest
from httpx import AsyncClient

from app.db.models import User
from tests.conftest import auth_headers


class TestHealthCheck:
    """ヘルスチェックエンドポイントのテスト。"""

    async def test_health_returns_status(self, client: AsyncClient):
        """ヘルスチェックが正しいフォーマットで返ること。"""
        res = await client.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert "version" in data
        assert data["version"] == "1.0.0"
        assert "uptime_seconds" in data
        assert "services" in data
        assert "database" in data["services"]
        assert "redis" in data["services"]

    async def test_health_db_status(self, client: AsyncClient):
        """DBステータスが含まれること。"""
        res = await client.get("/api/v1/health")
        data = res.json()
        db_status = data["services"]["database"]
        assert "status" in db_status


class TestMetrics:
    """メトリクスエンドポイントのテスト。"""

    async def test_metrics_returns_data(self, client: AsyncClient):
        """メトリクスが正しいフォーマットで返ること。"""
        res = await client.get("/api/v1/metrics")
        assert res.status_code == 200
        data = res.json()
        assert "uptime_seconds" in data
        assert "websocket_connections" in data
        assert isinstance(data["websocket_connections"], int)
        assert "services" in data


class TestSecurityHeaders:
    """セキュリティヘッダーミドルウェアのテスト。"""

    async def test_x_content_type_options(self, client: AsyncClient):
        """X-Content-Type-Options ヘッダーが設定されること。"""
        res = await client.get("/api/v1/health")
        assert res.headers.get("x-content-type-options") == "nosniff"

    async def test_x_frame_options(self, client: AsyncClient):
        """X-Frame-Options ヘッダーが設定されること。"""
        res = await client.get("/api/v1/health")
        assert res.headers.get("x-frame-options") == "DENY"

    async def test_x_xss_protection(self, client: AsyncClient):
        """X-XSS-Protection ヘッダーが設定されること。"""
        res = await client.get("/api/v1/health")
        assert res.headers.get("x-xss-protection") == "1; mode=block"

    async def test_referrer_policy(self, client: AsyncClient):
        """Referrer-Policy ヘッダーが設定されること。"""
        res = await client.get("/api/v1/health")
        assert res.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


class TestResponseTimingHeader:
    """リクエストログミドルウェアのテスト。"""

    async def test_response_time_header(self, client: AsyncClient):
        """X-Response-Time ヘッダーが設定されること。"""
        res = await client.get("/api/v1/health")
        response_time = res.headers.get("x-response-time")
        assert response_time is not None
        assert response_time.endswith("ms")


class TestAPIEndpointSecurity:
    """APIの認証セキュリティテスト。"""

    async def test_protected_endpoints_require_auth(self, client: AsyncClient):
        """保護されたエンドポイントが認証を要求すること。"""
        protected_endpoints = [
            ("GET", "/api/v1/users/me"),
            ("PUT", "/api/v1/users/me"),
            ("GET", "/api/v1/recipes"),
            ("POST", "/api/v1/recipes"),
            ("GET", "/api/v1/tasks/today"),
            ("POST", "/api/v1/tasks"),
            ("GET", "/api/v1/messages"),
            ("POST", "/api/v1/messages"),
            ("GET", "/api/v1/shopping/requests"),
            ("POST", "/api/v1/shopping/requests"),
            ("GET", "/api/v1/menus/week"),
            ("PUT", "/api/v1/menus/week"),
        ]
        for method, url in protected_endpoints:
            if method == "GET":
                res = await client.get(url)
            elif method == "POST":
                res = await client.post(url, json={})
            elif method == "PUT":
                res = await client.put(url, json={})
            assert res.status_code == 401, f"{method} {url} should require auth, got {res.status_code}"

    async def test_invalid_token_rejected(self, client: AsyncClient):
        """不正なトークンが拒否されること。"""
        res = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid-jwt-token"},
        )
        assert res.status_code == 401

    async def test_expired_token_rejected(self, client: AsyncClient):
        """有効期限切れのトークンが拒否されること（形式不正としても 401）。"""
        res = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxfQ.invalid"},
        )
        assert res.status_code == 401
