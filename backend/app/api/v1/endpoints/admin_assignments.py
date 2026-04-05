"""管理者用アサイン管理API。"""
import math
import uuid
from datetime import date, time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_role
from app.core.database import get_db
from app.crud.admin import (
    check_duplicate_assignment,
    create_assignment,
    create_audit_log,
    get_assignment_by_id,
    get_my_assignments,
    get_user_by_id,
    list_assignments,
)
from app.crud.user import update_user
from app.db.models.user import User
from app.schemas.admin import (
    AssignmentCreate,
    AssignmentListResponse,
    AssignmentResponse,
    AssignmentUpdate,
    AssignmentUserBrief,
    PaginationInfo,
)

router = APIRouter(tags=["管理：アサイン"])


def _build_response(a) -> AssignmentResponse:
    return AssignmentResponse(
        id=str(a.id),
        helper=AssignmentUserBrief(id=str(a.helper.id), full_name=a.helper.full_name, role=a.helper.role),
        senior=AssignmentUserBrief(id=str(a.senior.id), full_name=a.senior.full_name, role=a.senior.role),
        assigned_by=AssignmentUserBrief(
            id=str(a.assigned_by_user.id), full_name=a.assigned_by_user.full_name, role=a.assigned_by_user.role,
        ),
        status=a.status,
        visit_frequency=a.visit_frequency,
        preferred_days=a.preferred_days,
        preferred_time_start=str(a.preferred_time_start) if a.preferred_time_start else None,
        preferred_time_end=str(a.preferred_time_end) if a.preferred_time_end else None,
        notes=a.notes,
        start_date=a.start_date,
        end_date=a.end_date,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


# ---------------------------------------------------------------------------
# アサイン一覧（管理者用）
# ---------------------------------------------------------------------------
@router.get("/admin/assignments", response_model=AssignmentListResponse)
async def admin_list_assignments(
    helper_id: uuid.UUID | None = None,
    senior_id: uuid.UUID | None = None,
    assignment_status: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    assignments, total = await list_assignments(
        db, helper_id=helper_id, senior_id=senior_id, status=assignment_status,
        page=page, limit=limit,
    )
    total_pages = math.ceil(total / limit) if total else 0
    return AssignmentListResponse(
        assignments=[_build_response(a) for a in assignments],
        pagination=PaginationInfo(
            page=page, limit=limit, total=total, total_pages=total_pages,
            has_next=page < total_pages, has_prev=page > 1,
        ),
    )


# ---------------------------------------------------------------------------
# アサイン作成
# ---------------------------------------------------------------------------
@router.post("/admin/assignments", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_assignment(
    data: AssignmentCreate,
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    helper = await get_user_by_id(db, uuid.UUID(data.helper_id))
    if not helper or helper.role != "helper" or not helper.is_active:
        raise HTTPException(status_code=422, detail="有効なヘルパーユーザーを指定してください")

    senior = await get_user_by_id(db, uuid.UUID(data.senior_id))
    if not senior or senior.role != "senior" or not senior.is_active:
        raise HTTPException(status_code=422, detail="有効な利用者ユーザーを指定してください")

    if await check_duplicate_assignment(db, helper.id, senior.id):
        raise HTTPException(status_code=409, detail="このヘルパーと利用者の組み合わせには既にアクティブなアサインが存在します")

    kwargs = {
        "helper_id": helper.id,
        "senior_id": senior.id,
        "assigned_by": current_user.id,
        "visit_frequency": data.visit_frequency,
        "preferred_days": data.preferred_days,
        "notes": data.notes,
        "start_date": data.start_date or date.today(),
        "end_date": data.end_date,
    }
    if data.preferred_time_start:
        kwargs["preferred_time_start"] = time.fromisoformat(data.preferred_time_start)
    if data.preferred_time_end:
        kwargs["preferred_time_end"] = time.fromisoformat(data.preferred_time_end)

    assignment = await create_assignment(db, **kwargs)
    await create_audit_log(
        db, user=current_user, action="assignment.create", resource_type="assignment",
        resource_id=assignment.id,
        changes={"helper_id": {"new": data.helper_id}, "senior_id": {"new": data.senior_id}},
    )
    return _build_response(assignment)


# ---------------------------------------------------------------------------
# アサイン詳細
# ---------------------------------------------------------------------------
@router.get("/admin/assignments/{assignment_id}", response_model=AssignmentResponse)
async def admin_get_assignment(
    assignment_id: uuid.UUID,
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    assignment = await get_assignment_by_id(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="アサインが見つかりません")
    return _build_response(assignment)


# ---------------------------------------------------------------------------
# アサイン更新
# ---------------------------------------------------------------------------
@router.put("/admin/assignments/{assignment_id}", response_model=AssignmentResponse)
async def admin_update_assignment(
    assignment_id: uuid.UUID,
    data: AssignmentUpdate,
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    assignment = await get_assignment_by_id(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="アサインが見つかりません")

    updates = data.model_dump(exclude_unset=True)
    if "preferred_time_start" in updates and updates["preferred_time_start"]:
        updates["preferred_time_start"] = time.fromisoformat(updates["preferred_time_start"])
    if "preferred_time_end" in updates and updates["preferred_time_end"]:
        updates["preferred_time_end"] = time.fromisoformat(updates["preferred_time_end"])

    for key, value in updates.items():
        if value is not None:
            setattr(assignment, key, value)
    await db.flush()
    await db.refresh(assignment, attribute_names=["helper", "senior", "assigned_by_user"])

    await create_audit_log(
        db, user=current_user, action="assignment.update", resource_type="assignment",
        resource_id=assignment.id, changes=updates,
    )
    return _build_response(assignment)


# ---------------------------------------------------------------------------
# アサイン終了（論理削除）
# ---------------------------------------------------------------------------
@router.delete("/admin/assignments/{assignment_id}", status_code=status.HTTP_200_OK)
async def admin_delete_assignment(
    assignment_id: uuid.UUID,
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    assignment = await get_assignment_by_id(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="アサインが見つかりません")

    assignment.status = "inactive"
    assignment.end_date = date.today()
    await db.flush()

    await create_audit_log(
        db, user=current_user, action="assignment.delete", resource_type="assignment",
        resource_id=assignment.id,
    )
    return {"message": "アサインを終了しました"}


# ---------------------------------------------------------------------------
# 特定ユーザーのアサイン取得
# ---------------------------------------------------------------------------
@router.get("/admin/users/{user_id}/assignments", response_model=AssignmentListResponse)
async def admin_user_assignments(
    user_id: uuid.UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role("system_admin")),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import or_
    from app.db.models.user_assignment import UserAssignment
    from sqlalchemy import select, func
    from sqlalchemy.orm import selectinload

    query = (
        select(UserAssignment)
        .options(
            selectinload(UserAssignment.helper),
            selectinload(UserAssignment.senior),
            selectinload(UserAssignment.assigned_by_user),
        )
        .where(or_(UserAssignment.helper_id == user_id, UserAssignment.senior_id == user_id))
    )
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0
    total_pages = math.ceil(total / limit) if total else 0

    query = query.order_by(UserAssignment.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    assignments = result.scalars().unique().all()

    return AssignmentListResponse(
        assignments=[_build_response(a) for a in assignments],
        pagination=PaginationInfo(
            page=page, limit=limit, total=total, total_pages=total_pages,
            has_next=page < total_pages, has_prev=page > 1,
        ),
    )


# ---------------------------------------------------------------------------
# 自分のアサイン取得
# ---------------------------------------------------------------------------
@router.get("/assignments/my", response_model=AssignmentListResponse)
async def my_assignments(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    assignments, total = await get_my_assignments(db, current_user, page=page, limit=limit)
    total_pages = math.ceil(total / limit) if total else 0
    return AssignmentListResponse(
        assignments=[_build_response(a) for a in assignments],
        pagination=PaginationInfo(
            page=page, limit=limit, total=total, total_pages=total_pages,
            has_next=page < total_pages, has_prev=page > 1,
        ),
    )
