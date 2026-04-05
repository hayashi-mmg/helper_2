"""管理者用データアクセスログAPI。"""
import math
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_role
from app.core.database import get_db
from app.crud.logging_audit import get_data_access_report, list_data_access_logs
from app.db.models.user import User
from app.schemas.admin import PaginationInfo
from app.schemas.logging_audit import (
    DataAccessLogListResponse,
    DataAccessLogResponse,
    DataAccessReportResponse,
    DataAccessReportSummary,
)

router = APIRouter(prefix="/admin/data-access-logs", tags=["管理：データアクセスログ"])


@router.get("", response_model=DataAccessLogListResponse)
async def list_access_logs(
    accessor_user_id: uuid.UUID | None = None,
    target_user_id: uuid.UUID | None = None,
    access_type: str | None = None,
    resource_type: str | None = None,
    has_assignment: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    logs, total = await list_data_access_logs(
        db,
        accessor_user_id=accessor_user_id,
        target_user_id=target_user_id,
        access_type=access_type,
        resource_type=resource_type,
        has_assignment=has_assignment,
        date_from=date_from,
        date_to=date_to,
        page=page,
        limit=limit,
    )

    return DataAccessLogListResponse(
        data_access_logs=[
            DataAccessLogResponse(
                id=str(log.id),
                accessor_user_id=str(log.accessor_user_id) if log.accessor_user_id else None,
                accessor_email=log.accessor_email,
                accessor_role=log.accessor_role,
                target_user_id=str(log.target_user_id) if log.target_user_id else None,
                target_user_name=log.target_user_name,
                access_type=log.access_type,
                resource_type=log.resource_type,
                data_fields=log.data_fields,
                endpoint=log.endpoint,
                http_method=log.http_method,
                ip_address=str(log.ip_address),
                has_assignment=log.has_assignment,
                created_at=log.created_at,
            )
            for log in logs
        ],
        pagination=PaginationInfo(
            page=page,
            limit=limit,
            total=total,
            total_pages=math.ceil(total / limit) if total else 0,
            has_next=page * limit < total,
            has_prev=page > 1,
        ),
    )


@router.get("/report", response_model=DataAccessReportResponse)
async def access_report(
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    period: str = Query("daily"),
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    summary = await get_data_access_report(db, date_from=date_from, date_to=date_to)
    return DataAccessReportResponse(
        period=period,
        date_from=date_from,
        date_to=date_to,
        summary=DataAccessReportSummary(**summary),
    )


@router.get("/user/{user_id}", response_model=DataAccessLogListResponse)
async def user_access_history(
    user_id: uuid.UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    logs, total = await list_data_access_logs(
        db, target_user_id=user_id, page=page, limit=limit
    )

    return DataAccessLogListResponse(
        data_access_logs=[
            DataAccessLogResponse(
                id=str(log.id),
                accessor_user_id=str(log.accessor_user_id) if log.accessor_user_id else None,
                accessor_email=log.accessor_email,
                accessor_role=log.accessor_role,
                target_user_id=str(log.target_user_id) if log.target_user_id else None,
                target_user_name=log.target_user_name,
                access_type=log.access_type,
                resource_type=log.resource_type,
                data_fields=log.data_fields,
                endpoint=log.endpoint,
                http_method=log.http_method,
                ip_address=str(log.ip_address),
                has_assignment=log.has_assignment,
                created_at=log.created_at,
            )
            for log in logs
        ],
        pagination=PaginationInfo(
            page=page,
            limit=limit,
            total=total,
            total_pages=math.ceil(total / limit) if total else 0,
            has_next=page * limit < total,
            has_prev=page > 1,
        ),
    )
