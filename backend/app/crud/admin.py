import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.audit_log import AuditLog
from app.db.models.notification import Notification
from app.db.models.system_setting import SystemSetting
from app.db.models.task import Task
from app.db.models.user import User
from app.db.models.user_assignment import UserAssignment


# ---------------------------------------------------------------------------
# ユーザー管理 CRUD
# ---------------------------------------------------------------------------
async def list_users(
    db: AsyncSession,
    *,
    role: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> tuple[list[User], int]:
    query = select(User)

    if role is not None:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if search:
        query = query.where(
            or_(User.full_name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%"))
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    sort_col = getattr(User, sort_by, User.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    return result.scalars().all(), total


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def count_active_admins(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count()).where(
            and_(User.role == "system_admin", User.is_active == True)  # noqa: E712
        )
    )
    return result.scalar() or 0


# ---------------------------------------------------------------------------
# アサイン管理 CRUD
# ---------------------------------------------------------------------------
async def list_assignments(
    db: AsyncSession,
    *,
    helper_id: uuid.UUID | None = None,
    senior_id: uuid.UUID | None = None,
    status: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[UserAssignment], int]:
    query = select(UserAssignment).options(
        selectinload(UserAssignment.helper),
        selectinload(UserAssignment.senior),
        selectinload(UserAssignment.assigned_by_user),
    )

    if helper_id:
        query = query.where(UserAssignment.helper_id == helper_id)
    if senior_id:
        query = query.where(UserAssignment.senior_id == senior_id)
    if status:
        query = query.where(UserAssignment.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(UserAssignment.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    return result.scalars().unique().all(), total


async def get_assignment_by_id(db: AsyncSession, assignment_id: uuid.UUID) -> UserAssignment | None:
    result = await db.execute(
        select(UserAssignment)
        .options(
            selectinload(UserAssignment.helper),
            selectinload(UserAssignment.senior),
            selectinload(UserAssignment.assigned_by_user),
        )
        .where(UserAssignment.id == assignment_id)
    )
    return result.scalar_one_or_none()


async def check_duplicate_assignment(
    db: AsyncSession, helper_id: uuid.UUID, senior_id: uuid.UUID
) -> bool:
    result = await db.execute(
        select(func.count()).where(
            and_(
                UserAssignment.helper_id == helper_id,
                UserAssignment.senior_id == senior_id,
                UserAssignment.status == "active",
            )
        )
    )
    return (result.scalar() or 0) > 0


async def create_assignment(db: AsyncSession, **kwargs) -> UserAssignment:
    assignment = UserAssignment(**kwargs)
    db.add(assignment)
    await db.flush()
    await db.refresh(assignment, attribute_names=["helper", "senior", "assigned_by_user"])
    return assignment


async def get_my_assignments(
    db: AsyncSession, user: User, page: int = 1, limit: int = 20
) -> tuple[list[UserAssignment], int]:
    query = select(UserAssignment).options(
        selectinload(UserAssignment.helper),
        selectinload(UserAssignment.senior),
        selectinload(UserAssignment.assigned_by_user),
    )
    if user.role == "helper":
        query = query.where(UserAssignment.helper_id == user.id)
    elif user.role == "senior":
        query = query.where(UserAssignment.senior_id == user.id)
    else:
        query = query.where(UserAssignment.assigned_by == user.id)

    query = query.where(UserAssignment.status == "active")
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(UserAssignment.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    return result.scalars().unique().all(), total


# ---------------------------------------------------------------------------
# 監査ログ CRUD
# ---------------------------------------------------------------------------
async def create_audit_log(
    db: AsyncSession,
    *,
    user: User | None = None,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID | None = None,
    changes: dict | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    log = AuditLog(
        user_id=user.id if user else None,
        user_email=user.email if user else None,
        user_role=user.role if user else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        changes=changes,
        metadata_=metadata,
    )
    db.add(log)
    await db.flush()
    return log


async def list_audit_logs(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    page: int = 1,
    limit: int = 50,
) -> tuple[list[AuditLog], int]:
    query = select(AuditLog)

    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(AuditLog.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    return result.scalars().all(), total


# ---------------------------------------------------------------------------
# ダッシュボード
# ---------------------------------------------------------------------------
async def get_dashboard_stats(db: AsyncSession) -> dict:
    # ユーザー集計
    user_counts = await db.execute(
        select(User.role, User.is_active, func.count()).group_by(User.role, User.is_active)
    )
    rows = user_counts.all()

    users_by_role: dict[str, int] = {}
    active = 0
    inactive = 0
    total = 0
    for role, is_active_flag, count in rows:
        users_by_role[role] = users_by_role.get(role, 0) + count
        total += count
        if is_active_flag:
            active += count
        else:
            inactive += count

    # 今月の新規ユーザー
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_this_month = (
        await db.execute(
            select(func.count()).where(User.created_at >= month_start)
        )
    ).scalar() or 0

    # アクティブアサイン数
    active_assignments = (
        await db.execute(
            select(func.count()).where(UserAssignment.status == "active")
        )
    ).scalar() or 0

    # 今週のタスク完了数
    week_start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    tasks_completed = (
        await db.execute(
            select(func.count()).where(
                and_(Task.status == "completed", Task.updated_at >= week_start)
            )
        )
    ).scalar() or 0

    # 今日のログイン数
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    login_today = (
        await db.execute(
            select(func.count()).where(User.last_login_at >= today_start)
        )
    ).scalar() or 0

    return {
        "total_users": total,
        "users_by_role": users_by_role,
        "active_users": active,
        "inactive_users": inactive,
        "new_users_this_month": new_this_month,
        "active_assignments": active_assignments,
        "tasks_completed_this_week": tasks_completed,
        "login_count_today": login_today,
        "generated_at": datetime.utcnow(),
    }


# ---------------------------------------------------------------------------
# システム設定 CRUD
# ---------------------------------------------------------------------------
async def list_settings(db: AsyncSession) -> list[SystemSetting]:
    result = await db.execute(select(SystemSetting).order_by(SystemSetting.category, SystemSetting.setting_key))
    return result.scalars().all()


async def get_setting(db: AsyncSession, key: str) -> SystemSetting | None:
    result = await db.execute(select(SystemSetting).where(SystemSetting.setting_key == key))
    return result.scalar_one_or_none()


async def update_setting(db: AsyncSession, setting: SystemSetting, value, updated_by: uuid.UUID) -> SystemSetting:
    setting.setting_value = value if isinstance(value, dict) else {"value": value}
    setting.updated_by = updated_by
    await db.flush()
    await db.refresh(setting)
    return setting


# ---------------------------------------------------------------------------
# 通知 CRUD
# ---------------------------------------------------------------------------
async def list_notifications(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    is_read: bool | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[Notification], int]:
    query = select(Notification).where(Notification.user_id == user_id)
    if is_read is not None:
        query = query.where(Notification.is_read == is_read)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Notification.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    return result.scalars().all(), total


async def create_notification(db: AsyncSession, **kwargs) -> Notification:
    notification = Notification(**kwargs)
    db.add(notification)
    await db.flush()
    return notification


async def create_bulk_notifications(
    db: AsyncSession,
    user_ids: list[uuid.UUID],
    *,
    title: str,
    body: str,
    notification_type: str,
    priority: str,
) -> int:
    count = 0
    for uid in user_ids:
        db.add(Notification(
            user_id=uid,
            title=title,
            body=body,
            notification_type=notification_type,
            priority=priority,
        ))
        count += 1
    await db.flush()
    return count
