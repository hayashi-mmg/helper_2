import json
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from app.core.config import settings
from app.websocket.manager import manager

router = APIRouter()


def _authenticate_ws(token: str) -> str | None:
    """WebSocket接続用のトークン認証。user_id を返す。"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload.get("sub")
    except JWTError:
        return None


@router.websocket("/ws/messages")
async def websocket_messages(websocket: WebSocket):
    # クエリパラメータからトークンを取得
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="認証トークンが必要です")
        return

    user_id = _authenticate_ws(token)
    if not user_id:
        await websocket.close(code=4001, reason="無効なトークンです")
        return

    await manager.connect(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                # クライアントからのメッセージを受信者に転送
                receiver_id = message.get("receiver_id")
                if receiver_id:
                    await manager.send_to_user(receiver_id, {
                        "type": "new_message",
                        "sender_id": user_id,
                        "content": message.get("content", ""),
                        "timestamp": datetime.utcnow().isoformat(),
                    })
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
