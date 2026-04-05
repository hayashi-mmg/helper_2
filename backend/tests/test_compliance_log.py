"""コンプライアンスログのテスト。"""
import uuid
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.db.models.compliance_log import ComplianceLog
from app.db.models.user import User
from tests.conftest import auth_headers


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession) -> User:
    user = User(
        email="admin_cl@test.com",
        password_hash=hash_password("password123"),
        role="system_admin",
        full_name="管理者CL",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def senior_user(db: AsyncSession) -> User:
    user = User(
        email="senior_cl@test.com",
        password_hash=hash_password("password123"),
        role="senior",
        full_name="利用者CL",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def helper_user(db: AsyncSession) -> User:
    user = User(
        email="helper_cl@test.com",
        password_hash=hash_password("password123"),
        role="helper",
        full_name="ヘルパーCL",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_compliance_log(db: AsyncSession, admin_user: User, senior_user: User) -> ComplianceLog:
    log = ComplianceLog(
        event_type="disclosure_request",
        target_user_id=senior_user.id,
        target_user_name=senior_user.full_name,
        handled_by=admin_user.id,
        handler_email=admin_user.email,
        request_details={
            "request_type": "disclosure",
            "requested_data": ["personal_info"],
            "identity_verified": True,
        },
        status="pending",
        deadline_at=datetime.utcnow() + timedelta(days=14),
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


# ---------------------------------------------------------------------------
# テスト: コンプライアンス請求の作成
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_data_request(client: AsyncClient, admin_user: User, senior_user: User):
    """開示請求を作成できる。"""
    resp = await client.post(
        "/api/v1/admin/compliance/data-requests",
        headers=auth_headers(admin_user),
        json={
            "event_type": "disclosure_request",
            "target_user_id": str(senior_user.id),
            "request_details": {
                "request_type": "disclosure",
                "requested_data": ["personal_info", "access_logs"],
                "identity_verified": True,
            },
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["event_type"] == "disclosure_request"
    assert data["status"] == "pending"
    assert data["target_user_name"] == "利用者CL"
    assert data["deadline_at"] is not None


@pytest.mark.asyncio
async def test_create_data_request_invalid_user(client: AsyncClient, admin_user: User):
    """存在しないユーザーへの請求は404を返す。"""
    resp = await client.post(
        "/api/v1/admin/compliance/data-requests",
        headers=auth_headers(admin_user),
        json={
            "event_type": "disclosure_request",
            "target_user_id": str(uuid.uuid4()),
            "request_details": {"request_type": "disclosure"},
        },
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# テスト: 請求ステータスの更新（ライフサイクル）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_update_data_request_lifecycle(
    client: AsyncClient, admin_user: User, sample_compliance_log: ComplianceLog
):
    """請求のステータスをpending→in_progress→completedと遷移できる。"""
    log_id = str(sample_compliance_log.id)

    # pending → in_progress
    resp = await client.patch(
        f"/api/v1/admin/compliance/data-requests/{log_id}",
        headers=auth_headers(admin_user),
        json={"status": "in_progress"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"

    # in_progress → completed
    resp = await client.patch(
        f"/api/v1/admin/compliance/data-requests/{log_id}",
        headers=auth_headers(admin_user),
        json={
            "status": "completed",
            "response_details": {
                "disclosed_data": ["personal_info"],
                "delivery_method": "書面郵送",
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["completed_at"] is not None
    assert data["response_details"]["delivery_method"] == "書面郵送"


# ---------------------------------------------------------------------------
# テスト: 漏えい報告の作成
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_breach_report(client: AsyncClient, admin_user: User):
    """漏えい報告を作成できる。"""
    resp = await client.post(
        "/api/v1/admin/compliance/breach-reports",
        headers=auth_headers(admin_user),
        json={
            "event_type": "breach_detected",
            "request_details": {
                "incident_type": "unauthorized_access",
                "description": "不正アクセスの検知",
                "affected_users_count": 3,
                "severity": "high",
            },
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["event_type"] == "breach_detected"
    assert data["status"] == "pending"
    assert data["deadline_at"] is not None


# ---------------------------------------------------------------------------
# テスト: 保持状況レポート
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_retention_report(client: AsyncClient, admin_user: User):
    """保持状況レポートを取得できる。"""
    resp = await client.get(
        "/api/v1/admin/compliance/retention-report",
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "tables" in data
    assert "pending_requests" in data
    table_names = [t["table_name"] for t in data["tables"]]
    assert "audit_logs" in table_names
    assert "data_access_logs" in table_names
    assert "compliance_logs" in table_names
    assert "frontend_error_logs" in table_names


# ---------------------------------------------------------------------------
# テスト: 同意ログ一覧
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_consent_logs(client: AsyncClient, admin_user: User, db: AsyncSession, senior_user: User):
    """同意ログを取得できる。"""
    log = ComplianceLog(
        event_type="consent_given",
        target_user_id=senior_user.id,
        target_user_name=senior_user.full_name,
        request_details={"consent_type": "privacy_policy", "version": "1.0"},
        status="completed",
    )
    db.add(log)
    await db.commit()

    resp = await client.get(
        "/api/v1/admin/compliance/consent-logs",
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["compliance_logs"]) == 1
    assert data["compliance_logs"][0]["event_type"] == "consent_given"


# ---------------------------------------------------------------------------
# テスト: 権限チェック
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_compliance_requires_admin(client: AsyncClient, helper_user: User):
    """system_admin以外はコンプライアンスAPIにアクセスできない。"""
    resp = await client.get("/api/v1/admin/compliance/consent-logs", headers=auth_headers(helper_user))
    assert resp.status_code == 403

    resp = await client.get("/api/v1/admin/compliance/data-requests", headers=auth_headers(helper_user))
    assert resp.status_code == 403

    resp = await client.get("/api/v1/admin/compliance/retention-report", headers=auth_headers(helper_user))
    assert resp.status_code == 403
