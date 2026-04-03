import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.task import (
    complete_task,
    create_task,
    delete_task,
    get_task_by_id,
    get_tasks_for_date,
    update_task,
)


async def get_daily_tasks(
    db: AsyncSession,
    helper_user_id: uuid.UUID | None = None,
    senior_user_id: uuid.UUID | None = None,
    target_date: date | None = None,
) -> list:
    return await get_tasks_for_date(db, helper_user_id=helper_user_id, senior_user_id=senior_user_id, target_date=target_date or date.today())


async def get_task(db: AsyncSession, task_id: uuid.UUID):
    return await get_task_by_id(db, task_id)


async def create_new_task(db: AsyncSession, data: dict):
    return await create_task(db, data)


async def update_existing_task(db: AsyncSession, task, updates: dict):
    return await update_task(db, task, updates)


async def complete_existing_task(db: AsyncSession, task, helper_user_id: uuid.UUID, data: dict):
    return await complete_task(db, task, helper_user_id, data)


async def remove_task(db: AsyncSession, task):
    return await delete_task(db, task)


async def generate_daily_report(
    db: AsyncSession,
    user_id: uuid.UUID,
    target_date: date,
) -> dict:
    """日次レポートを生成する。"""
    tasks = await get_tasks_for_date(db, helper_user_id=user_id, target_date=target_date)

    total = len(tasks)
    completed = sum(1 for t in tasks if t.status == "completed")
    in_progress = sum(1 for t in tasks if t.status == "in_progress")
    pending = sum(1 for t in tasks if t.status == "pending")

    total_minutes = 0
    task_summaries = []
    for t in tasks:
        summary = {
            "task_id": str(t.id),
            "title": t.title,
            "task_type": t.task_type,
            "status": t.status,
        }
        if t.status == "completed" and t.estimated_minutes:
            total_minutes += t.estimated_minutes
        task_summaries.append(summary)

    return {
        "date": str(target_date),
        "summary": {
            "total_tasks": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "total_work_minutes": total_minutes,
        },
        "tasks": task_summaries,
    }
