"""管理者用システム管理API（監査ログ、ダッシュボード、設定、通知）。"""
import math
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_role
from app.core.database import get_db
from app.crud.admin import (
    create_audit_log,
    create_bulk_notifications,
    create_notification,
    get_dashboard_stats,
    get_setting,
    list_audit_logs,
    list_notifications,
    list_settings,
    update_setting,
)
from app.db.models.notification import Notification
from app.db.models.user import User
from app.schemas.admin import (
    AuditLogListResponse,
    AuditLogResponse,
    BroadcastNotificationRequest,
    DashboardStats,
    NotificationListResponse,
    NotificationResponse,
    PaginationInfo,
    SendNotificationRequest,
    SystemSettingListResponse,
    SystemSettingResponse,
    SystemSettingUpdate,
)

router = APIRouter(tags=["管理：システム"])


# ===========================================================================
# 監査ログ
# ===========================================================================
@router.get("/admin/audit-logs", response_model=AuditLogListResponse)
async def admin_list_audit_logs(
    user_id: uuid.UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    logs, total = await list_audit_logs(
        db, user_id=user_id, action=action, resource_type=resource_type,
        page=page, limit=limit,
    )
    total_pages = math.ceil(total / limit) if total else 0
    return AuditLogListResponse(
        audit_logs=[
            AuditLogResponse(
                id=str(log.id), user_id=str(log.user_id) if log.user_id else None,
                user_email=log.user_email, user_role=log.user_role,
                action=log.action, resource_type=log.resource_type,
                resource_id=str(log.resource_id) if log.resource_id else None,
                changes=log.changes, metadata=log.metadata_,
                created_at=log.created_at,
            )
            for log in logs
        ],
        pagination=PaginationInfo(
            page=page, limit=limit, total=total, total_pages=total_pages,
            has_next=page < total_pages, has_prev=page > 1,
        ),
    )


# ===========================================================================
# ダッシュボード
# ===========================================================================
@router.get("/admin/dashboard/stats", response_model=DashboardStats)
async def admin_dashboard_stats(
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    stats = await get_dashboard_stats(db)
    return DashboardStats(**stats)


# ===========================================================================
# システム設定
# ===========================================================================
@router.get("/admin/settings", response_model=SystemSettingListResponse)
async def admin_list_settings(
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    settings = await list_settings(db)
    return SystemSettingListResponse(
        settings=[
            SystemSettingResponse(
                setting_key=s.setting_key,
                setting_value="***" if s.is_sensitive else s.setting_value,
                category=s.category,
                description=s.description,
                is_sensitive=s.is_sensitive,
                updated_at=s.updated_at,
            )
            for s in settings
        ]
    )


@router.get("/admin/settings/{setting_key}", response_model=SystemSettingResponse)
async def admin_get_setting(
    setting_key: str,
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    setting = await get_setting(db, setting_key)
    if not setting:
        raise HTTPException(status_code=404, detail="設定が見つかりません")
    return SystemSettingResponse(
        setting_key=setting.setting_key,
        setting_value="***" if setting.is_sensitive else setting.setting_value,
        category=setting.category,
        description=setting.description,
        is_sensitive=setting.is_sensitive,
        updated_at=setting.updated_at,
    )


@router.put("/admin/settings/{setting_key}", response_model=SystemSettingResponse)
async def admin_update_setting(
    setting_key: str,
    data: SystemSettingUpdate,
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    setting = await get_setting(db, setting_key)
    if not setting:
        raise HTTPException(status_code=404, detail="設定が見つかりません")

    old_value = setting.setting_value
    setting = await update_setting(db, setting, data.value, current_user.id)

    await create_audit_log(
        db, user=current_user, action="setting.update", resource_type="system_setting",
        changes={"setting_key": setting_key, "old": str(old_value), "new": str(data.value)},
    )

    return SystemSettingResponse(
        setting_key=setting.setting_key,
        setting_value="***" if setting.is_sensitive else setting.setting_value,
        category=setting.category,
        description=setting.description,
        is_sensitive=setting.is_sensitive,
        updated_at=setting.updated_at,
    )


# ===========================================================================
# 通知（自分用）
# ===========================================================================
@router.get("/notifications", response_model=NotificationListResponse)
async def get_my_notifications(
    is_read: bool | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notifs, total = await list_notifications(db, current_user.id, is_read=is_read, page=page, limit=limit)
    total_pages = math.ceil(total / limit) if total else 0
    return NotificationListResponse(
        notifications=[
            NotificationResponse(
                id=str(n.id), title=n.title, body=n.body,
                notification_type=n.notification_type, priority=n.priority,
                reference_type=n.reference_type,
                reference_id=str(n.reference_id) if n.reference_id else None,
                is_read=n.is_read, read_at=n.read_at, created_at=n.created_at,
            )
            for n in notifs
        ],
        pagination=PaginationInfo(
            page=page, limit=limit, total=total, total_pages=total_pages,
            has_next=page < total_pages, has_prev=page > 1,
        ),
    )


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == current_user.id
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="通知が見つかりません")

    notif.is_read = True
    notif.read_at = datetime.utcnow()
    await db.flush()
    return {"message": "既読にしました"}


@router.put("/notifications/read-all")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == False)  # noqa: E712
        .values(is_read=True, read_at=datetime.utcnow())
    )
    await db.flush()
    return {"message": "全件既読にしました"}


# ===========================================================================
# 通知管理（管理者用）
# ===========================================================================
@router.post("/admin/notifications/broadcast", status_code=status.HTTP_201_CREATED)
async def admin_broadcast_notification(
    data: BroadcastNotificationRequest,
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    query = select(User.id).where(User.is_active == True)  # noqa: E712
    if data.target_roles:
        query = query.where(User.role.in_(data.target_roles))
    result = await db.execute(query)
    user_ids = [row[0] for row in result.all()]

    count = await create_bulk_notifications(
        db, user_ids, title=data.title, body=data.body,
        notification_type=data.notification_type, priority=data.priority,
    )
    await create_audit_log(
        db, user=current_user, action="notification.broadcast", resource_type="notification",
        changes={"target_roles": data.target_roles, "count": count},
    )
    return {"message": f"{count}件の通知を送信しました", "count": count}


@router.post("/admin/notifications/send", status_code=status.HTTP_201_CREATED)
async def admin_send_notification(
    data: SendNotificationRequest,
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    target_user = await db.execute(select(User).where(User.id == uuid.UUID(data.user_id)))
    if not target_user.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    await create_notification(
        db, user_id=uuid.UUID(data.user_id), title=data.title, body=data.body,
        notification_type=data.notification_type, priority=data.priority,
    )
    await create_audit_log(
        db, user=current_user, action="notification.send", resource_type="notification",
        changes={"target_user_id": data.user_id},
    )
    return {"message": "通知を送信しました"}
