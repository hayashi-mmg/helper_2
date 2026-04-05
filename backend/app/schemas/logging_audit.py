from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.admin import PaginationInfo


# ---------------------------------------------------------------------------
# データアクセスログ
# ---------------------------------------------------------------------------
class DataAccessLogResponse(BaseModel):
    id: str
    accessor_user_id: str | None = None
    accessor_email: str
    accessor_role: str
    target_user_id: str | None = None
    target_user_name: str
    access_type: str
    resource_type: str
    data_fields: list[str] | None = None
    endpoint: str
    http_method: str
    ip_address: str
    has_assignment: bool
    created_at: datetime


class DataAccessLogListResponse(BaseModel):
    data_access_logs: list[DataAccessLogResponse]
    pagination: PaginationInfo


class DataAccessReportSummary(BaseModel):
    total_access_count: int
    unique_accessors: int
    unique_targets: int
    unassigned_access_count: int
    export_count: int


class DataAccessReportResponse(BaseModel):
    period: str
    date_from: datetime
    date_to: datetime
    summary: DataAccessReportSummary


# ---------------------------------------------------------------------------
# コンプライアンスログ
# ---------------------------------------------------------------------------
class ComplianceLogResponse(BaseModel):
    id: str
    event_type: str
    target_user_id: str | None = None
    target_user_name: str | None = None
    handled_by: str | None = None
    handler_email: str | None = None
    request_details: dict
    status: str
    deadline_at: datetime | None = None
    completed_at: datetime | None = None
    response_details: dict | None = None
    created_at: datetime
    updated_at: datetime | None = None


class ComplianceLogListResponse(BaseModel):
    compliance_logs: list[ComplianceLogResponse]
    pagination: PaginationInfo


class ComplianceDataRequestCreate(BaseModel):
    event_type: str = Field(..., pattern=r"^(disclosure_request|correction_request|deletion_request|usage_stop_request)$")
    target_user_id: str
    request_details: dict


class ComplianceDataRequestUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(in_progress|completed|rejected)$")
    response_details: dict | None = None


class ComplianceBreachReportCreate(BaseModel):
    event_type: str = Field(
        ..., pattern=r"^(breach_detected|breach_reported_ppc|breach_notified_user)$"
    )
    request_details: dict
    target_user_id: str | None = None


class RetentionTableInfo(BaseModel):
    table_name: str
    retention_period: str
    total_records: int
    oldest_record: datetime | None = None
    records_due_for_deletion: int


class RetentionReportResponse(BaseModel):
    generated_at: datetime
    tables: list[RetentionTableInfo]
    pending_requests: dict


# ---------------------------------------------------------------------------
# フロントエンドテレメトリ
# ---------------------------------------------------------------------------
class FrontendLogEntry(BaseModel):
    type: str = Field(..., pattern=r"^(js_error|unhandled_rejection|render_error|network_error|accessibility_usage)$")
    message: str | None = None
    stack: str | None = None
    component_name: str | None = None
    url: str | None = None
    user_agent: str | None = None
    timestamp: str | None = None
    feature: str | None = None
    action: str | None = None
    value: str | None = None


class FrontendLogBatchRequest(BaseModel):
    logs: list[FrontendLogEntry] = Field(..., max_length=100)
    client_timestamp: str | None = None


class FrontendLogBatchResponse(BaseModel):
    accepted: bool
    count: int
