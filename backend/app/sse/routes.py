import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.db.models.user import User

router = APIRouter()

# イベントキュー（ユーザーごと）
_event_queues: dict[str, asyncio.Queue] = {}


def get_event_queue(user_id: str) -> asyncio.Queue:
    if user_id not in _event_queues:
        _event_queues[user_id] = asyncio.Queue()
    return _event_queues[user_id]


async def publish_task_event(user_id: str, event_type: str, data: dict) -> None:
    """タスクイベントを対象ユーザーに発行する。"""
    queue = get_event_queue(user_id)
    event = {
        "type": event_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    }
    await queue.put(event)


async def _event_generator(user_id: str, request: Request):
    queue = get_event_queue(user_id)
    try:
        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"event: {event['type']}\ndata: {json.dumps(event['data'], default=str)}\n\n"
            except asyncio.TimeoutError:
                # キープアライブ
                yield f": keepalive\n\n"
    finally:
        # クリーンアップ
        if user_id in _event_queues and _event_queues[user_id].empty():
            del _event_queues[user_id]


@router.get("/sse/task-updates")
async def task_updates_sse(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return StreamingResponse(
        _event_generator(str(current_user.id), request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
