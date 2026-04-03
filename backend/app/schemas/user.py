from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    phone: str | None = None
    address: str | None = None
    emergency_contact: str | None = None
    medical_notes: str | None = None
    care_level: int | None = None
    certification_number: str | None = None
    specialization: list[str] | None = None
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    address: str | None = None
    emergency_contact: str | None = None
    medical_notes: str | None = None
    care_level: int | None = None
    certification_number: str | None = None
    specialization: list[str] | None = None
