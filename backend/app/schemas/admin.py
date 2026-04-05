from datetime import date, datetime, time

from pydantic import BaseModel, EmailStr


# ---------------------------------------------------------------------------
# ページネーション
# ---------------------------------------------------------------------------
class PaginationInfo(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


# ---------------------------------------------------------------------------
# ユーザー管理
# ---------------------------------------------------------------------------
class AdminUserCreate(BaseModel):
    email: EmailStr
    full_name: str
    role: str
    phone: str | None = None
    address: str | None = None
    emergency_contact: str | None = None
    medical_notes: str | None = None
    care_level: int | None = None
    certification_number: str | None = None
    specialization: list[str] | None = None


class AdminUserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    role: str | None = None
    phone: str | None = None
    address: str | None = None
    emergency_contact: str | None = None
    medical_notes: str | None = None
    care_level: int | None = None
    certification_number: str | None = None
    specialization: list[str] | None = None


class AdminUserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    phone: str | None = None
    address: str | None = None
    emergency_contact: str | None = None
    medical_notes: str | None = None
    care_level: int | None = None
    certification_number: str | None = None
    specialization: list[str] | None = None
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class AdminUserCreateResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    temporary_password: str
    created_at: datetime
    message: str = "一時パスワードを安全にユーザーに伝達してください。初回ログイン時にパスワード変更が必要です。"


class AdminUserListResponse(BaseModel):
    users: list[AdminUserResponse]
    pagination: PaginationInfo


class PasswordResetResponse(BaseModel):
    user_id: str
    temporary_password: str
    message: str = "パスワードがリセットされました。一時パスワードを安全にユーザーに伝達してください。"
    sessions_invalidated: bool = True


# ---------------------------------------------------------------------------
# アサイン管理
# ---------------------------------------------------------------------------
class AssignmentUserBrief(BaseModel):
    id: str
    full_name: str
    role: str

    model_config = {"from_attributes": True}


class AssignmentCreate(BaseModel):
    helper_id: str
    senior_id: str
    visit_frequency: str | None = None
    preferred_days: list[int] | None = None
    preferred_time_start: str | None = None
    preferred_time_end: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None


class AssignmentUpdate(BaseModel):
    visit_frequency: str | None = None
    preferred_days: list[int] | None = None
    preferred_time_start: str | None = None
    preferred_time_end: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None
    status: str | None = None


class AssignmentResponse(BaseModel):
    id: str
    helper: AssignmentUserBrief
    senior: AssignmentUserBrief
    assigned_by: AssignmentUserBrief
    status: str
    visit_frequency: str | None = None
    preferred_days: list[int] | None = None
    preferred_time_start: str | None = None
    preferred_time_end: str | None = None
    notes: str | None = None
    start_date: date
    end_date: date | None = None
    created_at: datetime
    updated_at: datetime | None = None


class AssignmentListResponse(BaseModel):
    assignments: list[AssignmentResponse]
    pagination: PaginationInfo


# ---------------------------------------------------------------------------
# 監査ログ
# ---------------------------------------------------------------------------
class AuditLogResponse(BaseModel):
    id: str
    user_id: str | None = None
    user_email: str | None = None
    user_role: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    changes: dict | None = None
    metadata: dict | None = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    audit_logs: list[AuditLogResponse]
    pagination: PaginationInfo


# ---------------------------------------------------------------------------
# ダッシュボード・レポート
# ---------------------------------------------------------------------------
class DashboardStats(BaseModel):
    total_users: int
    users_by_role: dict[str, int]
    active_users: int
    inactive_users: int
    new_users_this_month: int
    active_assignments: int
    tasks_completed_this_week: int
    login_count_today: int
    generated_at: datetime


# ---------------------------------------------------------------------------
# システム設定
# ---------------------------------------------------------------------------
class SystemSettingResponse(BaseModel):
    setting_key: str
    setting_value: dict | str | int | bool
    category: str
    description: str | None = None
    is_sensitive: bool
    updated_at: datetime | None = None


class SystemSettingUpdate(BaseModel):
    value: dict | str | int | bool | float


class SystemSettingListResponse(BaseModel):
    settings: list[SystemSettingResponse]


# ---------------------------------------------------------------------------
# 通知
# ---------------------------------------------------------------------------
class NotificationResponse(BaseModel):
    id: str
    title: str
    body: str
    notification_type: str
    priority: str
    reference_type: str | None = None
    reference_id: str | None = None
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    pagination: PaginationInfo


class BroadcastNotificationRequest(BaseModel):
    title: str
    body: str
    notification_type: str = "system"
    priority: str = "normal"
    target_roles: list[str] | None = None


class SendNotificationRequest(BaseModel):
    user_id: str
    title: str
    body: str
    notification_type: str = "admin"
    priority: str = "normal"
