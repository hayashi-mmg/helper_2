"""管理者用コンプライアンスログAPI。"""
import math
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_role
from app.core.database import get_db
from app.crud.logging_audit import (
    create_compliance_log,
    get_compliance_log_by_id,
    get_retention_report,
    list_compliance_logs,
    update_compliance_log,
)
from app.crud.admin import get_user_by_id
from app.db.models.compliance_log import COMPLIANCE_EVENT_TYPES
from app.db.models.user import User
from app.schemas.admin import PaginationInfo
from app.schemas.logging_audit import (
    ComplianceBreachReportCreate,
    ComplianceDataRequestCreate,
    ComplianceDataRequestUpdate,
    ComplianceLogListResponse,
    ComplianceLogResponse,
    RetentionReportResponse,
    RetentionTableInfo,
)

router = APIRouter(prefix="/admin/compliance", tags=["管理：コンプライアンス"])

REQUEST_DEADLINE_DAYS = 14
BREACH_REPORT_DEADLINE_HOURS = 72


def _log_to_response(log) -> ComplianceLogResponse:
    return ComplianceLogResponse(
        id=str(log.id),
        event_type=log.event_type,
        target_user_id=str(log.target_user_id) if log.target_user_id else None,
        target_user_name=log.target_user_name,
        handled_by=str(log.handled_by) if log.handled_by else None,
        handler_email=log.handler_email,
        request_details=log.request_details,
        status=log.status,
        deadline_at=log.deadline_at,
        completed_at=log.completed_at,
        response_details=log.response_details,
        created_at=log.created_at,
        updated_at=log.updated_at,
    )


# ---------------------------------------------------------------------------
# 同意ログ
# ---------------------------------------------------------------------------
@router.get("/consent-logs", response_model=ComplianceLogListResponse)
async def list_consent_logs(
    target_user_id: uuid.UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    logs, total = await list_compliance_logs(
        db,
        event_type="consent_given",
        target_user_id=target_user_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        limit=limit,
    )
    return ComplianceLogListResponse(
        compliance_logs=[_log_to_response(log) for log in logs],
        pagination=PaginationInfo(
            page=page, limit=limit, total=total,
            total_pages=math.ceil(total / limit) if total else 0,
            has_next=page * limit < total, has_prev=page > 1,
        ),
    )


# ---------------------------------------------------------------------------
# データ主体権利行使ログ
# ---------------------------------------------------------------------------
@router.get("/data-requests", response_model=ComplianceLogListResponse)
async def list_data_requests(
    status_filter: str | None = Query(None, alias="status"),
    event_type: str | None = None,
    target_user_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    logs, total = await list_compliance_logs(
        db,
        event_type=event_type,
        target_user_id=target_user_id,
        status=status_filter,
        page=page,
        limit=limit,
    )
    return ComplianceLogListResponse(
        compliance_logs=[_log_to_response(log) for log in logs],
        pagination=PaginationInfo(
            page=page, limit=limit, total=total,
            total_pages=math.ceil(total / limit) if total else 0,
            has_next=page * limit < total, has_prev=page > 1,
        ),
    )


@router.post("/data-requests", response_model=ComplianceLogResponse, status_code=status.HTTP_201_CREATED)
async def create_data_request(
    body: ComplianceDataRequestCreate,
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    target = await get_user_by_id(db, uuid.UUID(body.target_user_id))
    if not target:
        raise HTTPException(status_code=404, detail="対象ユーザーが見つかりません")

    log = await create_compliance_log(
        db,
        event_type=body.event_type,
        target_user_id=target.id,
        target_user_name=target.full_name,
        handled_by=current_user.id,
        handler_email=current_user.email,
        request_details=body.request_details,
        status="pending",
        deadline_at=datetime.utcnow() + timedelta(days=REQUEST_DEADLINE_DAYS),
    )
    return _log_to_response(log)


@router.patch("/data-requests/{request_id}", response_model=ComplianceLogResponse)
async def update_data_request(
    request_id: uuid.UUID,
    body: ComplianceDataRequestUpdate,
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    log = await get_compliance_log_by_id(db, request_id)
    if not log:
        raise HTTPException(status_code=404, detail="コンプライアンスログが見つかりません")

    updates = {"status": body.status}
    if body.response_details:
        updates["response_details"] = body.response_details
    if body.status == "completed":
        updates["completed_at"] = datetime.utcnow()

    log = await update_compliance_log(db, log, **updates)
    return _log_to_response(log)


# ---------------------------------------------------------------------------
# 漏えい報告
# ---------------------------------------------------------------------------
@router.get("/breach-reports", response_model=ComplianceLogListResponse)
async def list_breach_reports(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    logs, total = await list_compliance_logs(
        db,
        event_type="breach_detected",
        page=page,
        limit=limit,
    )
    return ComplianceLogListResponse(
        compliance_logs=[_log_to_response(log) for log in logs],
        pagination=PaginationInfo(
            page=page, limit=limit, total=total,
            total_pages=math.ceil(total / limit) if total else 0,
            has_next=page * limit < total, has_prev=page > 1,
        ),
    )


@router.post("/breach-reports", response_model=ComplianceLogResponse, status_code=status.HTTP_201_CREATED)
async def create_breach_report(
    body: ComplianceBreachReportCreate,
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    target_name = None
    if body.target_user_id:
        target = await get_user_by_id(db, uuid.UUID(body.target_user_id))
        target_name = target.full_name if target else None

    log = await create_compliance_log(
        db,
        event_type=body.event_type,
        target_user_id=uuid.UUID(body.target_user_id) if body.target_user_id else None,
        target_user_name=target_name,
        handled_by=current_user.id,
        handler_email=current_user.email,
        request_details=body.request_details,
        status="pending",
        deadline_at=datetime.utcnow() + timedelta(hours=BREACH_REPORT_DEADLINE_HOURS),
    )
    return _log_to_response(log)


# ---------------------------------------------------------------------------
# 保持状況レポート
# ---------------------------------------------------------------------------
@router.get("/retention-report", response_model=RetentionReportResponse)
async def retention_report(
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    report = await get_retention_report(db)
    return RetentionReportResponse(
        generated_at=datetime.utcnow(),
        tables=[RetentionTableInfo(**t) for t in report["tables"]],
        pending_requests=report["pending_requests"],
    )
