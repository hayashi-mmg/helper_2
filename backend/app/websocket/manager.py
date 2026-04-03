import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket接続を管理するマネージャー。"""

    def __init__(self):
        # user_id -> list of WebSocket connections
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept()
        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(websocket)
        logger.info(f"WebSocket connected: user={user_id}")

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        if user_id in self._connections:
            self._connections[user_id] = [
                ws for ws in self._connections[user_id] if ws != websocket
            ]
            if not self._connections[user_id]:
                del self._connections[user_id]
        logger.info(f"WebSocket disconnected: user={user_id}")

    async def send_to_user(self, user_id: str, data: dict[str, Any]) -> None:
        connections = self._connections.get(user_id, [])
        disconnected = []
        for ws in connections:
            try:
                await ws.send_text(json.dumps(data, default=str))
            except Exception:
                disconnected.append(ws)
        # 切断された接続をクリーンアップ
        for ws in disconnected:
            self.disconnect(ws, user_id)

    async def broadcast(self, data: dict[str, Any]) -> None:
        for user_id in list(self._connections.keys()):
            await self.send_to_user(user_id, data)

    @property
    def active_connections_count(self) -> int:
        return sum(len(conns) for conns in self._connections.values())


# グローバルインスタンス
manager = ConnectionManager()
