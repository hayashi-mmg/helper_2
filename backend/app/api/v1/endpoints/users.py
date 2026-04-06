from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, hash_password, verify_password
from app.core.database import get_db
from app.crud.user import update_user
from app.db.models.user import User
from app.schemas.user import PasswordChangeRequest, PasswordChangeResponse, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["ユーザー"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        phone=current_user.phone,
        address=current_user.address,
        emergency_contact=current_user.emergency_contact,
        medical_notes=current_user.medical_notes,
        care_level=current_user.care_level,
        certification_number=current_user.certification_number,
        specialization=current_user.specialization,
        is_active=current_user.is_active,
        last_login_at=current_user.last_login_at,
        created_at=current_user.created_at,
    )


@router.put("/me/password", response_model=PasswordChangeResponse)
async def change_password(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="現在のパスワードが正しくありません",
        )
    await update_user(db, current_user, {"password_hash": hash_password(data.new_password)})
    return PasswordChangeResponse()


@router.put("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updates = data.model_dump(exclude_unset=True)
    user = await update_user(db, current_user, updates)
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        phone=user.phone,
        address=user.address,
        emergency_contact=user.emergency_contact,
        medical_notes=user.medical_notes,
        care_level=user.care_level,
        certification_number=user.certification_number,
        specialization=user.specialization,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )
