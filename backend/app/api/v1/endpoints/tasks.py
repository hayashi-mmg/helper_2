import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.crud.task import complete_task, create_task, delete_task, get_task_by_id, get_tasks_for_date, update_task
from app.db.models.user import User
from app.schemas.task import DailyReportRequest, TaskCompleteRequest, TaskCreate, TaskResponse, TaskUpdate
from app.services.task_service import generate_daily_report

router = APIRouter(prefix="/tasks", tags=["作業管理"])


@router.get("/today", response_model=list[TaskResponse])
async def get_today_tasks(
    user_id: uuid.UUID | None = None,
    target_date: date | None = Query(None, alias="date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if target_date is None:
        target_date = date.today()

    helper_id = current_user.id if current_user.role == "helper" else None
    senior_id = user_id or (current_user.id if current_user.role == "senior" else None)

    tasks = await get_tasks_for_date(db, helper_user_id=helper_id, senior_user_id=senior_id, target_date=target_date)

    return [
        TaskResponse(
            id=str(t.id), senior_user_id=str(t.senior_user_id),
            helper_user_id=str(t.helper_user_id) if t.helper_user_id else None,
            title=t.title, description=t.description, task_type=t.task_type,
            priority=t.priority, estimated_minutes=t.estimated_minutes,
            scheduled_date=t.scheduled_date, scheduled_start_time=t.scheduled_start_time,
            scheduled_end_time=t.scheduled_end_time, status=t.status,
            created_at=t.created_at, updated_at=t.updated_at,
        )
        for t in tasks
    ]


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task_endpoint(
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task_data = data.model_dump()
    task_data["senior_user_id"] = uuid.UUID(task_data["senior_user_id"])
    if current_user.role == "helper":
        task_data["helper_user_id"] = current_user.id

    task = await create_task(db, task_data)
    return TaskResponse(
        id=str(task.id), senior_user_id=str(task.senior_user_id),
        helper_user_id=str(task.helper_user_id) if task.helper_user_id else None,
        title=task.title, description=task.description, task_type=task.task_type,
        priority=task.priority, estimated_minutes=task.estimated_minutes,
        scheduled_date=task.scheduled_date, scheduled_start_time=task.scheduled_start_time,
        scheduled_end_time=task.scheduled_end_time, status=task.status,
        created_at=task.created_at, updated_at=task.updated_at,
    )


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task_endpoint(
    task_id: uuid.UUID,
    data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="作業が見つかりません")

    task = await update_task(db, task, data.model_dump(exclude_unset=True))
    return TaskResponse(
        id=str(task.id), senior_user_id=str(task.senior_user_id),
        helper_user_id=str(task.helper_user_id) if task.helper_user_id else None,
        title=task.title, description=task.description, task_type=task.task_type,
        priority=task.priority, estimated_minutes=task.estimated_minutes,
        scheduled_date=task.scheduled_date, scheduled_start_time=task.scheduled_start_time,
        scheduled_end_time=task.scheduled_end_time, status=task.status,
        created_at=task.created_at, updated_at=task.updated_at,
    )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_endpoint(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="作業が見つかりません")

    await delete_task(db, task)


@router.put("/{task_id}/complete")
async def complete_task_endpoint(
    task_id: uuid.UUID,
    data: TaskCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="作業が見つかりません")

    completion = await complete_task(
        db, task, current_user.id,
        actual_minutes=data.actual_minutes,
        notes=data.notes,
        next_notes=data.next_notes,
    )
    return {"message": "作業を完了しました", "completed_at": str(completion.completed_at)}


@router.post("/reports/daily")
async def submit_daily_report(
    data: DailyReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await generate_daily_report(db, current_user.id, data.date)
    return report
