"""管理者用ユーザー管理API。"""
import math
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, hash_password, require_role
from app.core.database import get_db
from app.crud.admin import (
    count_active_admins,
    create_audit_log,
    get_user_by_id,
    list_users,
)
from app.crud.user import create_user, get_user_by_email, update_user
from app.db.models.user import User
from app.schemas.admin import (
    AdminSetPasswordRequest,
    AdminSetPasswordResponse,
    AdminUserCreate,
    AdminUserCreateResponse,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserUpdate,
    PaginationInfo,
    PasswordResetResponse,
)

router = APIRouter(prefix="/admin/users", tags=["管理：ユーザー"])

VALID_ROLES = {"senior", "helper", "care_manager", "system_admin"}


def _generate_temp_password() -> str:
    return secrets.token_urlsafe(12)


# ---------------------------------------------------------------------------
# ユーザー一覧
# ---------------------------------------------------------------------------
@router.get("", response_model=AdminUserListResponse)
async def admin_list_users(
    role: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = "created_at",
    sort_order: str = "desc",
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    users, total = await list_users(
        db, role=role, is_active=is_active, search=search,
        page=page, limit=limit, sort_by=sort_by, sort_order=sort_order,
    )
    total_pages = math.ceil(total / limit) if total else 0
    return AdminUserListResponse(
        users=[AdminUserResponse(id=str(u.id), email=u.email, full_name=u.full_name,
               role=u.role, phone=u.phone, address=u.address,
               emergency_contact=u.emergency_contact, medical_notes=u.medical_notes,
               care_level=u.care_level, certification_number=u.certification_number,
               specialization=u.specialization, is_active=u.is_active,
               last_login_at=u.last_login_at, created_at=u.created_at,
               updated_at=u.updated_at) for u in users],
        pagination=PaginationInfo(
            page=page, limit=limit, total=total, total_pages=total_pages,
            has_next=page < total_pages, has_prev=page > 1,
        ),
    )


# ---------------------------------------------------------------------------
# ユーザー作成
# ---------------------------------------------------------------------------
@router.post("", response_model=AdminUserCreateResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_user(
    data: AdminUserCreate,
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    if data.role not in VALID_ROLES:
        raise HTTPException(status_code=422, detail=f"無効なロールです。有効値: {', '.join(VALID_ROLES)}")

    existing = await get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(status_code=409, detail="このメールアドレスは既に登録されています")

    temp_password = _generate_temp_password()
    user = await create_user(
        db,
        email=data.email,
        password_hash=hash_password(temp_password),
        full_name=data.full_name,
        role=data.role,
        phone=data.phone,
        address=data.address,
        emergency_contact=data.emergency_contact,
        medical_notes=data.medical_notes,
        care_level=data.care_level,
        certification_number=data.certification_number,
        specialization=data.specialization,
    )

    await create_audit_log(
        db, user=current_user, action="user.create", resource_type="user",
        resource_id=user.id,
        changes={"email": {"new": data.email}, "role": {"new": data.role}, "full_name": {"new": data.full_name}},
    )

    return AdminUserCreateResponse(
        id=str(user.id), email=user.email, full_name=user.full_name,
        role=user.role, is_active=user.is_active,
        temporary_password=temp_password, created_at=user.created_at,
    )


# ---------------------------------------------------------------------------
# ユーザー詳細
# ---------------------------------------------------------------------------
@router.get("/{user_id}", response_model=AdminUserResponse)
async def admin_get_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    return AdminUserResponse(
        id=str(user.id), email=user.email, full_name=user.full_name,
        role=user.role, phone=user.phone, address=user.address,
        emergency_contact=user.emergency_contact, medical_notes=user.medical_notes,
        care_level=user.care_level, certification_number=user.certification_number,
        specialization=user.specialization, is_active=user.is_active,
        last_login_at=user.last_login_at, created_at=user.created_at,
        updated_at=user.updated_at,
    )


# ---------------------------------------------------------------------------
# ユーザー更新
# ---------------------------------------------------------------------------
@router.put("/{user_id}", response_model=AdminUserResponse)
async def admin_update_user(
    user_id: uuid.UUID,
    data: AdminUserUpdate,
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    updates = data.model_dump(exclude_unset=True)
    if "role" in updates and updates["role"] not in VALID_ROLES:
        raise HTTPException(status_code=422, detail=f"無効なロールです。有効値: {', '.join(VALID_ROLES)}")

    if "email" in updates and updates["email"] != user.email:
        existing = await get_user_by_email(db, updates["email"])
        if existing:
            raise HTTPException(status_code=409, detail="このメールアドレスは既に登録されています")

    changes = {}
    for key, new_val in updates.items():
        old_val = getattr(user, key, None)
        if old_val != new_val:
            changes[key] = {"old": str(old_val) if old_val is not None else None, "new": str(new_val)}

    user = await update_user(db, user, updates)

    if changes:
        await create_audit_log(
            db, user=current_user, action="user.update", resource_type="user",
            resource_id=user.id, changes=changes,
        )

    return AdminUserResponse(
        id=str(user.id), email=user.email, full_name=user.full_name,
        role=user.role, phone=user.phone, address=user.address,
        emergency_contact=user.emergency_contact, medical_notes=user.medical_notes,
        care_level=user.care_level, certification_number=user.certification_number,
        specialization=user.specialization, is_active=user.is_active,
        last_login_at=user.last_login_at, created_at=user.created_at,
        updated_at=user.updated_at,
    )


# ---------------------------------------------------------------------------
# ユーザー無効化
# ---------------------------------------------------------------------------
@router.put("/{user_id}/deactivate", response_model=AdminUserResponse)
async def admin_deactivate_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    if not user.is_active:
        raise HTTPException(status_code=409, detail="このユーザーは既に無効化されています")

    if user.role == "system_admin":
        admin_count = await count_active_admins(db)
        if admin_count <= 1:
            raise HTTPException(status_code=409, detail="最後のシステム管理者アカウントを無効化することはできません")

    user = await update_user(db, user, {"is_active": False})
    await create_audit_log(
        db, user=current_user, action="user.deactivate", resource_type="user", resource_id=user.id,
    )

    return AdminUserResponse(
        id=str(user.id), email=user.email, full_name=user.full_name,
        role=user.role, phone=user.phone, address=user.address,
        emergency_contact=user.emergency_contact, medical_notes=user.medical_notes,
        care_level=user.care_level, certification_number=user.certification_number,
        specialization=user.specialization, is_active=user.is_active,
        last_login_at=user.last_login_at, created_at=user.created_at,
        updated_at=user.updated_at,
    )


# ---------------------------------------------------------------------------
# ユーザー有効化
# ---------------------------------------------------------------------------
@router.put("/{user_id}/activate", response_model=AdminUserResponse)
async def admin_activate_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    if user.is_active:
        raise HTTPException(status_code=409, detail="このユーザーは既にアクティブです")

    user = await update_user(db, user, {"is_active": True})
    await create_audit_log(
        db, user=current_user, action="user.activate", resource_type="user", resource_id=user.id,
    )

    return AdminUserResponse(
        id=str(user.id), email=user.email, full_name=user.full_name,
        role=user.role, phone=user.phone, address=user.address,
        emergency_contact=user.emergency_contact, medical_notes=user.medical_notes,
        care_level=user.care_level, certification_number=user.certification_number,
        specialization=user.specialization, is_active=user.is_active,
        last_login_at=user.last_login_at, created_at=user.created_at,
        updated_at=user.updated_at,
    )


# ---------------------------------------------------------------------------
# パスワードリセット
# ---------------------------------------------------------------------------
@router.post("/{user_id}/reset-password", response_model=PasswordResetResponse)
async def admin_reset_password(
    user_id: uuid.UUID,
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    temp_password = _generate_temp_password()
    await update_user(db, user, {"password_hash": hash_password(temp_password)})
    await create_audit_log(
        db, user=current_user, action="user.password_reset", resource_type="user", resource_id=user.id,
    )

    return PasswordResetResponse(user_id=str(user.id), temporary_password=temp_password)


# ---------------------------------------------------------------------------
# パスワード設定（管理者が任意のパスワードを指定）
# ---------------------------------------------------------------------------
@router.put("/{user_id}/set-password", response_model=AdminSetPasswordResponse)
async def admin_set_password(
    user_id: uuid.UUID,
    data: AdminSetPasswordRequest,
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    await update_user(db, user, {"password_hash": hash_password(data.new_password)})
    await create_audit_log(
        db, user=current_user, action="user.password_set", resource_type="user", resource_id=user.id,
    )

    return AdminSetPasswordResponse(user_id=str(user.id))
