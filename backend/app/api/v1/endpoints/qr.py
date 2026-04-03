import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, create_refresh_token, get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.qr_auth import generate_qr_image_base64, generate_qr_token_string, get_qr_expiration, hash_token
from app.crud.qr import create_qr_token, get_qr_token_by_hash, mark_qr_used
from app.db.models.user import User
from app.schemas.qr import QRGenerateResponse, QRValidateRequest, QRValidateResponse

router = APIRouter(prefix="/qr", tags=["QR認証"])


@router.get("/generate/{user_id}", response_model=QRGenerateResponse)
async def generate_qr(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # ケアマネージャーまたは本人のみ生成可能
    if current_user.role not in ("care_manager",) and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="QRコード生成の権限がありません")

    # 対象ユーザーの存在確認
    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))  # noqa: E712
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ユーザーが見つかりません")

    # トークン生成
    raw_token = generate_qr_token_string()
    token_hashed = hash_token(raw_token)
    expires_at = get_qr_expiration(hours=24)

    await create_qr_token(db, user_id, token_hashed, purpose="login", expires_at=expires_at)

    # QR画像生成
    qr_base64 = generate_qr_image_base64(raw_token)

    return QRGenerateResponse(
        qr_token=raw_token,
        qr_image_base64=qr_base64,
        expires_at=expires_at,
    )


@router.post("/validate", response_model=QRValidateResponse)
async def validate_qr(
    data: QRValidateRequest,
    db: AsyncSession = Depends(get_db),
):
    token_hashed = hash_token(data.token)
    qr = await get_qr_token_by_hash(db, token_hashed)

    if not qr:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="無効なQRコードです")

    if qr.is_used:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="このQRコードは既に使用されています")

    # timezone-aware と naive の比較を安全に行う
    now = datetime.utcnow()
    expires = qr.expires_at.replace(tzinfo=None) if qr.expires_at.tzinfo else qr.expires_at
    if expires < now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="QRコードの有効期限が切れています")

    # ユーザー取得
    result = await db.execute(select(User).where(User.id == qr.user_id, User.is_active == True))  # noqa: E712
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="ユーザーが見つかりません")

    # QRトークンを使用済みにする
    await mark_qr_used(db, qr)

    # JWTトークン発行
    user.last_login_at = datetime.utcnow()
    access_token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    refresh_token = create_refresh_token(str(user.id))

    return QRValidateResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={"id": str(user.id), "email": user.email, "full_name": user.full_name, "role": user.role},
    )
