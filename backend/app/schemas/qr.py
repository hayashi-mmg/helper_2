from datetime import datetime

from pydantic import BaseModel


class QRGenerateResponse(BaseModel):
    qr_token: str
    qr_image_base64: str
    expires_at: datetime


class QRValidateRequest(BaseModel):
    token: str


class QRValidateResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict
