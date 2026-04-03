"""メッセージ API テスト。

仕様: GET /messages, POST /messages, PUT /messages/{id}/read
"""
import uuid

import pytest
from httpx import AsyncClient

from app.db.models import Message, User
from tests.conftest import auth_headers


class TestListMessages:
    """メッセージ一覧取得テスト。"""

    async def test_list_messages(
        self, client: AsyncClient, senior_user: User, helper_user: User, sample_message: Message,
    ):
        """受信メッセージが取得できること。"""
        res = await client.get("/api/v1/messages", headers=auth_headers(senior_user))
        assert res.status_code == 200
        data = res.json()
        assert "messages" in data
        assert "pagination" in data
        assert len(data["messages"]) >= 1

    async def test_list_with_partner_filter(
        self, client: AsyncClient, senior_user: User, helper_user: User, sample_message: Message,
    ):
        """パートナーIDでフィルタできること。"""
        res = await client.get(
            "/api/v1/messages",
            params={"partner_id": str(helper_user.id)},
            headers=auth_headers(senior_user),
        )
        assert res.status_code == 200
        messages = res.json()["messages"]
        assert len(messages) >= 1
        for msg in messages:
            assert str(helper_user.id) in [msg["sender_id"], msg["receiver_id"]]

    async def test_list_pagination(
        self, client: AsyncClient, senior_user: User, helper_user: User, sample_message: Message,
    ):
        """ページネーションが正しく動作すること。"""
        res = await client.get(
            "/api/v1/messages",
            params={"limit": 1, "offset": 0},
            headers=auth_headers(senior_user),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["pagination"]["limit"] == 1
        assert data["pagination"]["offset"] == 0
        assert "total" in data["pagination"]
        assert "has_more" in data["pagination"]

    async def test_list_empty(self, client: AsyncClient, care_manager_user: User):
        """メッセージがない場合、空リストが返ること。"""
        res = await client.get("/api/v1/messages", headers=auth_headers(care_manager_user))
        assert res.status_code == 200
        assert res.json()["messages"] == []

    async def test_list_unauthenticated(self, client: AsyncClient):
        """未認証で 401 が返ること。"""
        res = await client.get("/api/v1/messages")
        assert res.status_code == 401


class TestSendMessage:
    """メッセージ送信テスト。"""

    async def test_send_success(self, client: AsyncClient, helper_user: User, senior_user: User):
        """メッセージを送信できること。"""
        res = await client.post(
            "/api/v1/messages",
            headers=auth_headers(helper_user),
            json={
                "receiver_id": str(senior_user.id),
                "content": "テストメッセージです",
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["content"] == "テストメッセージです"
        assert data["sender_id"] == str(helper_user.id)
        assert data["receiver_id"] == str(senior_user.id)
        assert data["message_type"] == "normal"
        assert data["is_read"] is False

    async def test_send_urgent_message(self, client: AsyncClient, helper_user: User, senior_user: User):
        """緊急メッセージを送信できること。"""
        res = await client.post(
            "/api/v1/messages",
            headers=auth_headers(helper_user),
            json={
                "receiver_id": str(senior_user.id),
                "content": "緊急連絡です",
                "message_type": "urgent",
            },
        )
        assert res.status_code == 201
        assert res.json()["message_type"] == "urgent"

    async def test_send_missing_content(self, client: AsyncClient, helper_user: User, senior_user: User):
        """content がない場合 422 が返ること。"""
        res = await client.post(
            "/api/v1/messages",
            headers=auth_headers(helper_user),
            json={"receiver_id": str(senior_user.id)},
        )
        assert res.status_code == 422


class TestMarkAsRead:
    """既読マークテスト。"""

    async def test_mark_as_read_success(
        self, client: AsyncClient, senior_user: User, sample_message: Message,
    ):
        """受信者がメッセージを既読にできること。"""
        res = await client.put(
            f"/api/v1/messages/{sample_message.id}/read",
            headers=auth_headers(senior_user),
        )
        assert res.status_code == 200

    async def test_mark_as_read_not_receiver(
        self, client: AsyncClient, helper_user: User, sample_message: Message,
    ):
        """送信者が既読にしようとすると 403 が返ること。"""
        # sample_message は helper -> senior なので helper は receiver ではない
        res = await client.put(
            f"/api/v1/messages/{sample_message.id}/read",
            headers=auth_headers(helper_user),
        )
        assert res.status_code == 403

    async def test_mark_as_read_not_found(self, client: AsyncClient, senior_user: User):
        """存在しないメッセージの既読で 404 が返ること。"""
        res = await client.put(
            f"/api/v1/messages/{uuid.uuid4()}/read",
            headers=auth_headers(senior_user),
        )
        assert res.status_code == 404
