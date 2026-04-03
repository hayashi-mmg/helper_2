from datetime import date, datetime, time

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    senior_user_id: str
    title: str = Field(max_length=100)
    description: str | None = None
    task_type: str = Field(pattern="^(cooking|cleaning|shopping|special)$")
    priority: str = Field(default="medium", pattern="^(high|medium|low)$")
    estimated_minutes: int | None = None
    scheduled_date: date
    scheduled_start_time: time | None = None
    scheduled_end_time: time | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(None, max_length=100)
    description: str | None = None
    task_type: str | None = Field(None, pattern="^(cooking|cleaning|shopping|special)$")
    priority: str | None = Field(None, pattern="^(high|medium|low)$")
    estimated_minutes: int | None = None
    scheduled_date: date | None = None
    scheduled_start_time: time | None = None
    scheduled_end_time: time | None = None
    status: str | None = Field(None, pattern="^(pending|in_progress|completed|cancelled)$")


class TaskCompleteRequest(BaseModel):
    actual_minutes: int | None = None
    notes: str | None = None
    next_notes: str | None = None


class DailyReportRequest(BaseModel):
    date: date


class TaskResponse(BaseModel):
    id: str
    senior_user_id: str
    helper_user_id: str | None = None
    title: str
    description: str | None = None
    task_type: str
    priority: str
    estimated_minutes: int | None = None
    scheduled_date: date
    scheduled_start_time: time | None = None
    scheduled_end_time: time | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
