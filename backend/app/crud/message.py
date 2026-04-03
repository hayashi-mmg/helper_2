import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.message import Message


async def get_messages(
    db: AsyncSession,
    user_id: uuid.UUID,
    partner_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Message], int]:
    query = select(Message).where(
        or_(Message.sender_id == user_id, Message.receiver_id == user_id)
    )

    if partner_id:
        query = query.where(
            or_(
                (Message.sender_id == user_id) & (Message.receiver_id == partner_id),
                (Message.sender_id == partner_id) & (Message.receiver_id == user_id),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Message.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    messages = list(result.scalars().all())

    return messages, total


async def create_message(db: AsyncSession, sender_id: uuid.UUID, receiver_id: uuid.UUID, content: str, message_type: str = "normal") -> Message:
    message = Message(
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=content,
        message_type=message_type,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)
    return message


async def mark_as_read(db: AsyncSession, message: Message) -> Message:
    message.is_read = True
    message.read_at = datetime.utcnow()
    await db.flush()
    await db.refresh(message)
    return message
