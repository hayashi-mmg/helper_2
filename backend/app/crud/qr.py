import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.qr_token import QRToken


async def create_qr_token(
    db: AsyncSession,
    user_id: uuid.UUID,
    token_hash: str,
    purpose: str,
    expires_at: datetime,
    max_uses: int = 1,
) -> QRToken:
    qr = QRToken(
        user_id=user_id,
        token_hash=token_hash,
        purpose=purpose,
        expires_at=expires_at,
        max_uses=max_uses,
    )
    db.add(qr)
    await db.flush()
    await db.refresh(qr)
    return qr


async def get_qr_token_by_hash(db: AsyncSession, token_hash: str) -> QRToken | None:
    result = await db.execute(
        select(QRToken).where(QRToken.token_hash == token_hash)
    )
    return result.scalar_one_or_none()


async def mark_qr_used(db: AsyncSession, qr: QRToken) -> None:
    qr.use_count += 1
    if qr.use_count >= qr.max_uses:
        qr.is_used = True
    qr.used_at = datetime.utcnow()
    await db.flush()
