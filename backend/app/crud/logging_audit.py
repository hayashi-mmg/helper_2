import hashlib
import uuid
from datetime import datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.compliance_log import ComplianceLog
from app.db.models.data_access_log import DataAccessLog
from app.db.models.frontend_error_log import FrontendErrorLog
from app.db.models.user import User
from app.db.models.user_assignment import UserAssignment


# ---------------------------------------------------------------------------
# データアクセスログ CRUD
# ---------------------------------------------------------------------------
async def create_data_access_log(db: AsyncSession, **kwargs) -> DataAccessLog:
    log = DataAccessLog(**kwargs)
    db.add(log)
    await db.flush()
    return log


async def bulk_create_data_access_logs(db: AsyncSession, logs: list[dict]) -> int:
    """バッチでデータアクセスログを挿入する。"""
    if not logs:
        return 0
    for log_data in logs:
        db.add(DataAccessLog(**log_data))
    await db.flush()
    return len(logs)


async def list_data_access_logs(
    db: AsyncSession,
    *,
    accessor_user_id: uuid.UUID | None = None,
    target_user_id: uuid.UUID | None = None,
    access_type: str | None = None,
    resource_type: str | None = None,
    has_assignment: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    limit: int = 50,
) -> tuple[list[DataAccessLog], int]:
    query = select(DataAccessLog)

    if accessor_user_id:
        query = query.where(DataAccessLog.accessor_user_id == accessor_user_id)
    if target_user_id:
        query = query.where(DataAccessLog.target_user_id == target_user_id)
    if access_type:
        query = query.where(DataAccessLog.access_type == access_type)
    if resource_type:
        query = query.where(DataAccessLog.resource_type == resource_type)
    if has_assignment is not None:
        query = query.where(DataAccessLog.has_assignment == has_assignment)
    if date_from:
        query = query.where(DataAccessLog.created_at >= date_from)
    if date_to:
        query = query.where(DataAccessLog.created_at <= date_to)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(DataAccessLog.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    return result.scalars().all(), total


async def get_data_access_report(
    db: AsyncSession,
    *,
    date_from: datetime,
    date_to: datetime,
) -> dict:
    """データアクセスの集計レポートを生成する。"""
    base_filter = and_(
        DataAccessLog.created_at >= date_from,
        DataAccessLog.created_at <= date_to,
    )

    total = (await db.execute(
        select(func.count()).where(base_filter)
    )).scalar() or 0

    unique_accessors = (await db.execute(
        select(func.count(func.distinct(DataAccessLog.accessor_user_id))).where(base_filter)
    )).scalar() or 0

    unique_targets = (await db.execute(
        select(func.count(func.distinct(DataAccessLog.target_user_id))).where(base_filter)
    )).scalar() or 0

    unassigned = (await db.execute(
        select(func.count()).where(and_(base_filter, DataAccessLog.has_assignment == False))  # noqa: E712
    )).scalar() or 0

    exports = (await db.execute(
        select(func.count()).where(and_(base_filter, DataAccessLog.access_type == "export"))
    )).scalar() or 0

    return {
        "total_access_count": total,
        "unique_accessors": unique_accessors,
        "unique_targets": unique_targets,
        "unassigned_access_count": unassigned,
        "export_count": exports,
    }


async def check_has_assignment(
    db: AsyncSession, accessor_user_id: uuid.UUID, target_user_id: uuid.UUID
) -> bool:
    """アクセス者と対象者の間にアクティブなアサインが存在するかチェック。"""
    result = await db.execute(
        select(func.count()).where(
            and_(
                UserAssignment.status == "active",
                (
                    (UserAssignment.helper_id == accessor_user_id)
                    & (UserAssignment.senior_id == target_user_id)
                )
                | (
                    (UserAssignment.helper_id == target_user_id)
                    & (UserAssignment.senior_id == accessor_user_id)
                ),
            )
        )
    )
    return (result.scalar() or 0) > 0


# ---------------------------------------------------------------------------
# コンプライアンスログ CRUD
# ---------------------------------------------------------------------------
async def create_compliance_log(db: AsyncSession, **kwargs) -> ComplianceLog:
    log = ComplianceLog(**kwargs)
    db.add(log)
    await db.flush()
    return log


async def get_compliance_log_by_id(db: AsyncSession, log_id: uuid.UUID) -> ComplianceLog | None:
    result = await db.execute(select(ComplianceLog).where(ComplianceLog.id == log_id))
    return result.scalar_one_or_none()


async def list_compliance_logs(
    db: AsyncSession,
    *,
    event_type: str | None = None,
    target_user_id: uuid.UUID | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    limit: int = 50,
) -> tuple[list[ComplianceLog], int]:
    query = select(ComplianceLog)

    if event_type:
        query = query.where(ComplianceLog.event_type == event_type)
    if target_user_id:
        query = query.where(ComplianceLog.target_user_id == target_user_id)
    if status:
        query = query.where(ComplianceLog.status == status)
    if date_from:
        query = query.where(ComplianceLog.created_at >= date_from)
    if date_to:
        query = query.where(ComplianceLog.created_at <= date_to)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(ComplianceLog.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    return result.scalars().all(), total


async def update_compliance_log(
    db: AsyncSession, log: ComplianceLog, **kwargs
) -> ComplianceLog:
    for key, value in kwargs.items():
        setattr(log, key, value)
    await db.flush()
    await db.refresh(log)
    return log


async def get_retention_report(db: AsyncSession) -> dict:
    """データ保持状況レポートを生成する。"""
    from app.db.models.audit_log import AuditLog

    tables_info = []
    now = datetime.utcnow()

    # audit_logs: 6ヶ月
    audit_total = (await db.execute(select(func.count()).select_from(AuditLog))).scalar() or 0
    audit_oldest_result = await db.execute(select(func.min(AuditLog.created_at)))
    audit_oldest = audit_oldest_result.scalar()
    audit_due = (await db.execute(
        select(func.count()).where(AuditLog.created_at < now - timedelta(days=180))
    )).scalar() or 0
    tables_info.append({
        "table_name": "audit_logs",
        "retention_period": "6 months",
        "total_records": audit_total,
        "oldest_record": audit_oldest,
        "records_due_for_deletion": audit_due,
    })

    # data_access_logs: 3年
    dal_total = (await db.execute(select(func.count()).select_from(DataAccessLog))).scalar() or 0
    dal_oldest_result = await db.execute(select(func.min(DataAccessLog.created_at)))
    dal_oldest = dal_oldest_result.scalar()
    dal_due = (await db.execute(
        select(func.count()).where(DataAccessLog.created_at < now - timedelta(days=365 * 3))
    )).scalar() or 0
    tables_info.append({
        "table_name": "data_access_logs",
        "retention_period": "3 years",
        "total_records": dal_total,
        "oldest_record": dal_oldest,
        "records_due_for_deletion": dal_due,
    })

    # compliance_logs: 3年
    cl_total = (await db.execute(select(func.count()).select_from(ComplianceLog))).scalar() or 0
    cl_oldest_result = await db.execute(select(func.min(ComplianceLog.created_at)))
    cl_oldest = cl_oldest_result.scalar()
    cl_due = (await db.execute(
        select(func.count()).where(
            and_(ComplianceLog.created_at < now - timedelta(days=365 * 3), ComplianceLog.status == "completed")
        )
    )).scalar() or 0
    tables_info.append({
        "table_name": "compliance_logs",
        "retention_period": "3 years",
        "total_records": cl_total,
        "oldest_record": cl_oldest,
        "records_due_for_deletion": cl_due,
    })

    # frontend_error_logs: 90日
    fe_total = (await db.execute(select(func.count()).select_from(FrontendErrorLog))).scalar() or 0
    fe_oldest_result = await db.execute(select(func.min(FrontendErrorLog.created_at)))
    fe_oldest = fe_oldest_result.scalar()
    fe_due = (await db.execute(
        select(func.count()).where(FrontendErrorLog.created_at < now - timedelta(days=90))
    )).scalar() or 0
    tables_info.append({
        "table_name": "frontend_error_logs",
        "retention_period": "90 days",
        "total_records": fe_total,
        "oldest_record": fe_oldest,
        "records_due_for_deletion": fe_due,
    })

    # 未対応のコンプライアンス請求
    pending_counts = {}
    for event_type in ("disclosure_request", "correction_request", "deletion_request"):
        count = (await db.execute(
            select(func.count()).where(
                and_(
                    ComplianceLog.event_type == event_type,
                    ComplianceLog.status.in_(["pending", "in_progress"]),
                )
            )
        )).scalar() or 0
        pending_counts[f"{event_type}s"] = count

    overdue = (await db.execute(
        select(func.count()).where(
            and_(
                ComplianceLog.status.in_(["pending", "in_progress"]),
                ComplianceLog.deadline_at < now,
            )
        )
    )).scalar() or 0
    pending_counts["overdue_requests"] = overdue

    return {
        "tables": tables_info,
        "pending_requests": pending_counts,
    }


# ---------------------------------------------------------------------------
# フロントエンドエラーログ CRUD
# ---------------------------------------------------------------------------
async def upsert_frontend_error(
    db: AsyncSession,
    *,
    error_type: str,
    message: str,
    url: str,
    stack: str | None = None,
    component_name: str | None = None,
    user_agent_category: str | None = None,
) -> FrontendErrorLog:
    """フロントエンドエラーをUPSERT（重複時はカウント加算）する。"""
    stack_hash = hashlib.sha256((stack or message).encode()).hexdigest()

    stmt = pg_insert(FrontendErrorLog).values(
        error_type=error_type,
        message=message,
        stack_hash=stack_hash,
        component_name=component_name,
        url=url,
        user_agent_category=user_agent_category,
        occurrence_count=1,
        first_seen_at=datetime.utcnow(),
        last_seen_at=datetime.utcnow(),
        affected_user_count=1,
    )

    stmt = stmt.on_conflict_do_update(
        index_elements=["stack_hash", "url"],
        set_={
            "occurrence_count": FrontendErrorLog.occurrence_count + 1,
            "last_seen_at": datetime.utcnow(),
            "affected_user_count": FrontendErrorLog.affected_user_count + 1,
        },
    )

    await db.execute(stmt)
    await db.flush()

    # 返却用に取得
    result = await db.execute(
        select(FrontendErrorLog).where(
            and_(FrontendErrorLog.stack_hash == stack_hash, FrontendErrorLog.url == url)
        )
    )
    return result.scalar_one()
