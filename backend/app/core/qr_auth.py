import base64
import hashlib
import io
import secrets
from datetime import datetime, timedelta

import qrcode


def generate_qr_token_string() -> str:
    """QRコード用のランダムトークン文字列を生成する。"""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """トークンをSHA-256でハッシュする（DB保存用）。"""
    return hashlib.sha256(token.encode()).hexdigest()


def get_qr_expiration(hours: int = 24) -> datetime:
    """QRトークンの有効期限を返す。"""
    return datetime.utcnow() + timedelta(hours=hours)


def generate_qr_image_base64(data: str) -> str:
    """データからQRコード画像をBase64文字列として生成する。"""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")
