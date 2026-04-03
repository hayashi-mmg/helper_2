"""QR認証 API テスト。

仕様: GET /qr/generate/{user_id}, POST /qr/validate
"""
import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.qr_auth import generate_qr_token_string, hash_token
from app.db.models import QRToken, User
from tests.conftest import auth_headers


class TestGenerateQR:
    """QRコード生成テスト。"""

    async def test_generate_for_self(self, client: AsyncClient, senior_user: User):
        """本人がQRコードを生成できること。"""
        res = await client.get(
            f"/api/v1/qr/generate/{senior_user.id}",
            headers=auth_headers(senior_user),
        )
        assert res.status_code == 200
        data = res.json()
        assert "qr_token" in data
        assert "qr_image_base64" in data
        assert "expires_at" in data
        # Base64 が有効であること
        assert len(data["qr_image_base64"]) > 100

    async def test_generate_by_care_manager(
        self, client: AsyncClient, care_manager_user: User, senior_user: User,
    ):
        """ケアマネージャーが利用者のQRコードを生成できること。"""
        res = await client.get(
            f"/api/v1/qr/generate/{senior_user.id}",
            headers=auth_headers(care_manager_user),
        )
        assert res.status_code == 200
        assert "qr_token" in res.json()

    async def test_generate_forbidden_for_other_user(
        self, client: AsyncClient, helper_user: User, senior_user: User,
    ):
        """ヘルパーが他人のQRコードを生成しようとすると 403 が返ること。"""
        res = await client.get(
            f"/api/v1/qr/generate/{senior_user.id}",
            headers=auth_headers(helper_user),
        )
        assert res.status_code == 403

    async def test_generate_user_not_found(self, client: AsyncClient, care_manager_user: User):
        """存在しないユーザーのQR生成で 404 が返ること。"""
        res = await client.get(
            f"/api/v1/qr/generate/{uuid.uuid4()}",
            headers=auth_headers(care_manager_user),
        )
        assert res.status_code == 404

    async def test_generate_unauthenticated(self, client: AsyncClient, senior_user: User):
        """未認証で 401 が返ること。"""
        res = await client.get(f"/api/v1/qr/generate/{senior_user.id}")
        assert res.status_code == 401


class TestValidateQR:
    """QRコード検証テスト。"""

    async def test_validate_success(
        self, client: AsyncClient, senior_user: User, db: AsyncSession,
    ):
        """有効なQRトークンでログインできること。"""
        # トークンを直接DBに作成
        raw_token = generate_qr_token_string()
        qr = QRToken(
            user_id=senior_user.id,
            token_hash=hash_token(raw_token),
            purpose="login",
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        db.add(qr)
        await db.commit()

        res = await client.post("/api/v1/qr/validate", json={"token": raw_token})
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "senior@test.com"
        assert data["user"]["role"] == "senior"

    async def test_validate_expired_token(
        self, client: AsyncClient, senior_user: User, db: AsyncSession,
    ):
        """期限切れQRトークンで 401 が返ること。"""
        raw_token = generate_qr_token_string()
        qr = QRToken(
            user_id=senior_user.id,
            token_hash=hash_token(raw_token),
            purpose="login",
            expires_at=datetime.utcnow() - timedelta(hours=1),  # 期限切れ
        )
        db.add(qr)
        await db.commit()

        res = await client.post("/api/v1/qr/validate", json={"token": raw_token})
        assert res.status_code == 401

    async def test_validate_used_token(
        self, client: AsyncClient, senior_user: User, db: AsyncSession,
    ):
        """使用済みQRトークンで 401 が返ること。"""
        raw_token = generate_qr_token_string()
        qr = QRToken(
            user_id=senior_user.id,
            token_hash=hash_token(raw_token),
            purpose="login",
            expires_at=datetime.utcnow() + timedelta(hours=24),
            is_used=True,
        )
        db.add(qr)
        await db.commit()

        res = await client.post("/api/v1/qr/validate", json={"token": raw_token})
        assert res.status_code == 401

    async def test_validate_invalid_token(self, client: AsyncClient):
        """無効なトークンで 401 が返ること。"""
        res = await client.post("/api/v1/qr/validate", json={"token": "completely-invalid-token"})
        assert res.status_code == 401

    async def test_validate_missing_token(self, client: AsyncClient):
        """トークンなしで 422 が返ること。"""
        res = await client.post("/api/v1/qr/validate", json={})
        assert res.status_code == 422

    async def test_validate_marks_as_used(
        self, client: AsyncClient, senior_user: User, db: AsyncSession,
    ):
        """検証後にトークンが使用済みになること。"""
        raw_token = generate_qr_token_string()
        qr = QRToken(
            user_id=senior_user.id,
            token_hash=hash_token(raw_token),
            purpose="login",
            expires_at=datetime.utcnow() + timedelta(hours=24),
            max_uses=1,
        )
        db.add(qr)
        await db.commit()

        # 1回目: 成功
        res = await client.post("/api/v1/qr/validate", json={"token": raw_token})
        assert res.status_code == 200

        # 2回目: 使用済みで失敗
        res = await client.post("/api/v1/qr/validate", json={"token": raw_token})
        assert res.status_code == 401


class TestQRAuthHelpers:
    """QR認証ヘルパー関数のユニットテスト。"""

    def test_generate_token_uniqueness(self):
        """生成されるトークンが毎回異なること。"""
        tokens = {generate_qr_token_string() for _ in range(100)}
        assert len(tokens) == 100

    def test_hash_token_deterministic(self):
        """同じ入力に対して同じハッシュが返ること。"""
        token = "test-token-123"
        assert hash_token(token) == hash_token(token)

    def test_hash_token_different_input(self):
        """異なる入力に対して異なるハッシュが返ること。"""
        assert hash_token("token-a") != hash_token("token-b")
