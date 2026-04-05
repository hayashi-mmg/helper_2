"""DataAccessLoggerサービスのテスト。"""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.crud.logging_audit import check_has_assignment
from app.db.models.data_access_log import DataAccessLog
from app.db.models.user import User
from app.db.models.user_assignment import UserAssignment
from app.services.data_access_logger import DataAccessLogger
from app.services.log_integrity import LogIntegrityManager
from tests.conftest import TestSessionFactory


HMAC_KEY = "test-hmac-key"


@pytest_asyncio.fixture
async def helper_user(db: AsyncSession) -> User:
    user = User(
        email="helper_svc@test.com",
        password_hash=hash_password("password123"),
        role="helper",
        full_name="ヘルパーSVC",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def senior_user(db: AsyncSession) -> User:
    user = User(
        email="senior_svc@test.com",
        password_hash=hash_password("password123"),
        role="senior",
        full_name="利用者SVC",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession) -> User:
    user = User(
        email="admin_svc@test.com",
        password_hash=hash_password("password123"),
        role="system_admin",
        full_name="管理者SVC",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# テスト: 自分自身のデータアクセスは記録しない
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_self_access_not_logged(db: AsyncSession, senior_user: User):
    """自分自身のデータアクセスはログ記録しない。"""
    logger = DataAccessLogger(TestSessionFactory, hmac_key=HMAC_KEY, buffer_size=1)

    await logger.log_access(
        db=db,
        accessor_user_id=senior_user.id,
        accessor_email=senior_user.email,
        accessor_role=senior_user.role,
        target_user_id=senior_user.id,
        target_user_name=senior_user.full_name,
        access_type="read",
        resource_type="user_profile",
        endpoint="/api/v1/users/me",
        http_method="GET",
        ip_address="127.0.0.1",
    )

    assert logger.buffer_count == 0


# ---------------------------------------------------------------------------
# テスト: アサイン関係の自動チェック
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_has_assignment_check_true(
    db: AsyncSession, helper_user: User, senior_user: User, admin_user: User
):
    """アクティブなアサインがある場合はTrueを返す。"""
    assignment = UserAssignment(
        helper_id=helper_user.id,
        senior_id=senior_user.id,
        assigned_by=admin_user.id,
        status="active",
    )
    db.add(assignment)
    await db.commit()

    result = await check_has_assignment(db, helper_user.id, senior_user.id)
    assert result is True


@pytest.mark.asyncio
async def test_has_assignment_check_false(
    db: AsyncSession, helper_user: User, senior_user: User
):
    """アサインが無い場合はFalseを返す。"""
    result = await check_has_assignment(db, helper_user.id, senior_user.id)
    assert result is False


# ---------------------------------------------------------------------------
# テスト: HMAC署名の自動付与
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_log_access_adds_hmac(db: AsyncSession, helper_user: User, senior_user: User):
    """ログにHMAC署名が自動付与される。"""
    logger = DataAccessLogger(TestSessionFactory, hmac_key=HMAC_KEY, buffer_size=100)

    await logger.log_access(
        db=db,
        accessor_user_id=helper_user.id,
        accessor_email=helper_user.email,
        accessor_role=helper_user.role,
        target_user_id=senior_user.id,
        target_user_name=senior_user.full_name,
        access_type="read",
        resource_type="user_profile",
        endpoint="/api/v1/users/" + str(senior_user.id),
        http_method="GET",
        ip_address="192.168.1.1",
    )

    assert logger.buffer_count == 1

    # バッファ内のログにlog_hashがある
    buffered = logger._buffer[0]
    assert "log_hash" in buffered
    assert len(buffered["log_hash"]) == 64

    # 署名を検証
    integrity = LogIntegrityManager(HMAC_KEY)
    assert integrity.verify_entry(buffered) is True


# ---------------------------------------------------------------------------
# テスト: バッファフラッシュ
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_flush_writes_to_db(db: AsyncSession, helper_user: User, senior_user: User):
    """フラッシュするとバッファがDBに書き込まれる。"""
    logger = DataAccessLogger(TestSessionFactory, hmac_key=HMAC_KEY, buffer_size=100)

    await logger.log_access(
        db=db,
        accessor_user_id=helper_user.id,
        accessor_email=helper_user.email,
        accessor_role=helper_user.role,
        target_user_id=senior_user.id,
        target_user_name=senior_user.full_name,
        access_type="read",
        resource_type="user_profile",
        endpoint="/api/v1/users/" + str(senior_user.id),
        http_method="GET",
        ip_address="192.168.1.1",
    )

    assert logger.buffer_count == 1
    await logger.flush()
    assert logger.buffer_count == 0

    # DBに書き込まれたか確認
    async with TestSessionFactory() as check_session:
        count = (await check_session.execute(
            select(func.count()).select_from(DataAccessLog)
        )).scalar()
        assert count == 1


# ---------------------------------------------------------------------------
# テスト: バッファサイズ到達で自動フラッシュ
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_auto_flush_on_buffer_full(db: AsyncSession, helper_user: User, senior_user: User):
    """バッファサイズに達すると自動でフラッシュされる。"""
    logger = DataAccessLogger(TestSessionFactory, hmac_key=HMAC_KEY, buffer_size=2)

    # 1件目: バッファに溜まる
    await logger.log_access(
        db=db,
        accessor_user_id=helper_user.id,
        accessor_email=helper_user.email,
        accessor_role=helper_user.role,
        target_user_id=senior_user.id,
        target_user_name=senior_user.full_name,
        access_type="read",
        resource_type="user_profile",
        endpoint="/api/v1/users/" + str(senior_user.id),
        http_method="GET",
        ip_address="192.168.1.1",
    )
    assert logger.buffer_count == 1

    # 2件目: バッファサイズ到達で自動フラッシュ
    await logger.log_access(
        db=db,
        accessor_user_id=helper_user.id,
        accessor_email=helper_user.email,
        accessor_role=helper_user.role,
        target_user_id=senior_user.id,
        target_user_name=senior_user.full_name,
        access_type="read",
        resource_type="messages",
        endpoint="/api/v1/messages",
        http_method="GET",
        ip_address="192.168.1.1",
    )
    # 自動フラッシュ後バッファは空
    assert logger.buffer_count == 0

    # DBに2件書き込まれた
    async with TestSessionFactory() as check_session:
        count = (await check_session.execute(
            select(func.count()).select_from(DataAccessLog)
        )).scalar()
        assert count == 2
