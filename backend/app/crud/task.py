import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.task import Task, TaskCompletion


async def get_tasks_for_date(
    db: AsyncSession,
    helper_user_id: uuid.UUID | None = None,
    senior_user_id: uuid.UUID | None = None,
    target_date: date | None = None,
) -> list[Task]:
    query = select(Task).options(selectinload(Task.completions))

    if helper_user_id:
        query = query.where(Task.helper_user_id == helper_user_id)
    if senior_user_id:
        query = query.where(Task.senior_user_id == senior_user_id)
    if target_date:
        query = query.where(Task.scheduled_date == target_date)

    query = query.order_by(Task.scheduled_start_time, Task.priority.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_task_by_id(db: AsyncSession, task_id: uuid.UUID) -> Task | None:
    result = await db.execute(
        select(Task).options(selectinload(Task.completions)).where(Task.id == task_id)
    )
    return result.scalar_one_or_none()


async def create_task(db: AsyncSession, data: dict) -> Task:
    task = Task(**data)
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


async def update_task(db: AsyncSession, task: Task, updates: dict) -> Task:
    for key, value in updates.items():
        if value is not None:
            setattr(task, key, value)
    await db.flush()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task: Task) -> None:
    task.status = "cancelled"
    await db.flush()


async def complete_task(
    db: AsyncSession,
    task: Task,
    helper_user_id: uuid.UUID,
    actual_minutes: int | None = None,
    notes: str | None = None,
    next_notes: str | None = None,
) -> TaskCompletion:
    task.status = "completed"

    completion = TaskCompletion(
        task_id=task.id,
        helper_user_id=helper_user_id,
        completed_at=datetime.utcnow(),
        actual_minutes=actual_minutes,
        notes=notes,
        next_notes=next_notes,
    )
    db.add(completion)
    await db.flush()
    await db.refresh(completion)
    return completion
