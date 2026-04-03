import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.crud.message import create_message, get_messages, mark_as_read
from app.db.models.message import Message
from app.db.models.user import User
from app.schemas.message import MessageCreate, MessageListResponse, MessagePagination, MessageResponse

router = APIRouter(prefix="/messages", tags=["メッセージ"])


@router.get("", response_model=MessageListResponse)
async def list_messages(
    partner_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    messages, total = await get_messages(db, current_user.id, partner_id, limit, offset)

    return MessageListResponse(
        messages=[
            MessageResponse(
                id=str(m.id), sender_id=str(m.sender_id), receiver_id=str(m.receiver_id),
                content=m.content, message_type=m.message_type,
                is_read=m.is_read, read_at=m.read_at, created_at=m.created_at,
            )
            for m in messages
        ],
        pagination=MessagePagination(
            limit=limit, offset=offset, total=total, has_more=(offset + limit) < total,
        ),
    )


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    message = await create_message(
        db, current_user.id, uuid.UUID(data.receiver_id), data.content, data.message_type,
    )
    return MessageResponse(
        id=str(message.id), sender_id=str(message.sender_id), receiver_id=str(message.receiver_id),
        content=message.content, message_type=message.message_type,
        is_read=message.is_read, read_at=message.read_at, created_at=message.created_at,
    )


@router.put("/{message_id}/read")
async def read_message(
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    result = await db.execute(select(Message).where(Message.id == message_id))
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="メッセージが見つかりません")
    if message.receiver_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="権限がありません")

    await mark_as_read(db, message)
    return {"message": "既読にしました"}
