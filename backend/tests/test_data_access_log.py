"""データアクセスログのテスト。"""
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.db.models.data_access_log import DataAccessLog
from app.db.models.user import User
from app.db.models.user_assignment import UserAssignment
from tests.conftest import auth_headers


# ---------------------------------------------------------------------------
# ヘルパーフィクスチャ
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def admin_user(db: AsyncSession) -> User:
    user = User(
        email="admin_dal@test.com",
        password_hash=hash_password("password123"),
        role="system_admin",
        full_name="管理者DAL",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def helper_user(db: AsyncSession) -> User:
    user = User(
        email="helper_dal@test.com",
        password_hash=hash_password("password123"),
        role="helper",
        full_name="ヘルパーDAL",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def senior_user(db: AsyncSession) -> User:
    user = User(
        email="senior_dal@test.com",
        password_hash=hash_password("password123"),
        role="senior",
        full_name="利用者DAL",
        phone="090-1234-5678",
        medical_notes="高血圧",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_access_log(db: AsyncSession, helper_user: User, senior_user: User) -> DataAccessLog:
    log = DataAccessLog(
        accessor_user_id=helper_user.id,
        accessor_email=helper_user.email,
        accessor_role=helper_user.role,
        target_user_id=senior_user.id,
        target_user_name=senior_user.full_name,
        access_type="read",
        resource_type="user_profile",
        data_fields=["full_name", "phone", "medical_notes"],
        endpoint="/api/v1/users/" + str(senior_user.id),
        http_method="GET",
        ip_address="192.168.1.100",
        user_agent="test-agent",
        has_assignment=True,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


@pytest_asyncio.fixture
async def assignment(db: AsyncSession, helper_user: User, senior_user: User, admin_user: User) -> UserAssignment:
    a = UserAssignment(
        helper_id=helper_user.id,
        senior_id=senior_user.id,
        assigned_by=admin_user.id,
        status="active",
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


# ---------------------------------------------------------------------------
# テスト: データアクセスログ一覧
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_data_access_logs(client: AsyncClient, admin_user: User, sample_access_log: DataAccessLog):
    """データアクセスログ一覧を取得できる。"""
    resp = await client.get("/api/v1/admin/data-access-logs", headers=auth_headers(admin_user))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data_access_logs"]) == 1
    log = data["data_access_logs"][0]
    assert log["accessor_email"] == "helper_dal@test.com"
    assert log["target_user_name"] == "利用者DAL"
    assert log["access_type"] == "read"
    assert log["resource_type"] == "user_profile"
    assert log["has_assignment"] is True


@pytest.mark.asyncio
async def test_list_data_access_logs_filter_by_target(
    client: AsyncClient, admin_user: User, senior_user: User, sample_access_log: DataAccessLog
):
    """target_user_idでフィルタできる。"""
    resp = await client.get(
        f"/api/v1/admin/data-access-logs?target_user_id={senior_user.id}",
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data_access_logs"]) == 1


@pytest.mark.asyncio
async def test_list_data_access_logs_filter_unassigned(
    client: AsyncClient, admin_user: User, db: AsyncSession, helper_user: User, senior_user: User
):
    """has_assignment=falseでフィルタできる。"""
    log = DataAccessLog(
        accessor_user_id=helper_user.id,
        accessor_email=helper_user.email,
        accessor_role=helper_user.role,
        target_user_id=senior_user.id,
        target_user_name=senior_user.full_name,
        access_type="read",
        resource_type="user_profile",
        endpoint="/api/v1/users/" + str(senior_user.id),
        http_method="GET",
        ip_address="10.0.0.1",
        has_assignment=False,
    )
    db.add(log)
    await db.commit()

    resp = await client.get(
        "/api/v1/admin/data-access-logs?has_assignment=false",
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data_access_logs"]) == 1
    assert data["data_access_logs"][0]["has_assignment"] is False


@pytest.mark.asyncio
async def test_data_access_logs_requires_admin(client: AsyncClient, helper_user: User):
    """system_admin以外はアクセスできない。"""
    resp = await client.get("/api/v1/admin/data-access-logs", headers=auth_headers(helper_user))
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# テスト: データアクセスレポート
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_data_access_report(client: AsyncClient, admin_user: User, sample_access_log: DataAccessLog):
    """データアクセスレポートを取得できる。"""
    resp = await client.get(
        "/api/v1/admin/data-access-logs/report?date_from=2020-01-01T00:00:00&date_to=2030-12-31T23:59:59",
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["total_access_count"] == 1
    assert data["summary"]["unique_accessors"] == 1
    assert data["summary"]["unique_targets"] == 1


# ---------------------------------------------------------------------------
# テスト: 特定利用者のアクセス履歴
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_user_access_history(
    client: AsyncClient, admin_user: User, senior_user: User, sample_access_log: DataAccessLog
):
    """特定利用者のデータアクセス履歴を取得できる。"""
    resp = await client.get(
        f"/api/v1/admin/data-access-logs/user/{senior_user.id}",
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data_access_logs"]) == 1
    assert data["data_access_logs"][0]["target_user_name"] == "利用者DAL"
