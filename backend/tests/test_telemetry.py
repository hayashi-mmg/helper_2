"""フロントエンドテレメトリAPIのテスト。"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_receive_frontend_logs(client: AsyncClient):
    """フロントエンドログバッチを受信できる。"""
    resp = await client.post(
        "/api/v1/telemetry/frontend-logs",
        json={
            "logs": [
                {
                    "type": "js_error",
                    "message": "Cannot read property 'name' of undefined",
                    "stack": "TypeError: Cannot read property...\n  at /users/test/app.js:10",
                    "url": "/dashboard",
                    "user_agent": "Mozilla/5.0",
                    "timestamp": "2026-04-04T10:00:00Z",
                },
                {
                    "type": "accessibility_usage",
                    "message": "font_size_changed",
                    "feature": "font_size",
                    "action": "change",
                    "value": "24px",
                    "url": "/settings",
                    "timestamp": "2026-04-04T10:01:00Z",
                },
            ],
            "client_timestamp": "2026-04-04T10:01:05Z",
        },
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["accepted"] is True
    assert data["count"] == 2


@pytest.mark.asyncio
async def test_receive_empty_logs(client: AsyncClient):
    """空のログバッチを受け付ける。"""
    resp = await client.post(
        "/api/v1/telemetry/frontend-logs",
        json={"logs": []},
    )
    assert resp.status_code == 202
    assert resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_pii_sanitization(client: AsyncClient):
    """PIIパターンはサニタイズされる（レスポンスは成功する）。"""
    resp = await client.post(
        "/api/v1/telemetry/frontend-logs",
        json={
            "logs": [
                {
                    "type": "js_error",
                    "message": "Error for user test@example.com with phone 090-1234-5678",
                    "url": "/profile",
                    "timestamp": "2026-04-04T10:00:00Z",
                }
            ],
        },
    )
    assert resp.status_code == 202
    assert resp.json()["accepted"] is True


@pytest.mark.asyncio
async def test_invalid_log_type_rejected(client: AsyncClient):
    """無効なログタイプは422を返す。"""
    resp = await client.post(
        "/api/v1/telemetry/frontend-logs",
        json={
            "logs": [
                {
                    "type": "invalid_type",
                    "message": "test",
                    "url": "/test",
                }
            ],
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_no_auth_required(client: AsyncClient):
    """テレメトリAPIは認証不要。"""
    resp = await client.post(
        "/api/v1/telemetry/frontend-logs",
        json={
            "logs": [
                {
                    "type": "js_error",
                    "message": "test error",
                    "url": "/test",
                }
            ],
        },
    )
    assert resp.status_code == 202
