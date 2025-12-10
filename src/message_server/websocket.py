import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_websockets: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, conversation_id: str, user_id: str):
        await websocket.accept()

        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = set()

        self.active_connections[conversation_id].add(websocket)
        self.user_websockets[websocket] = user_id

    def disconnect(self, websocket: WebSocket, conversation_id: str):
        if conversation_id in self.active_connections:
            self.active_connections[conversation_id].discard(websocket)
            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]

        self.user_websockets.pop(websocket, None)

    async def send_to_conversation(self, conversation_id: str, message: dict, exclude_ws: WebSocket = None):
        if conversation_id not in self.active_connections:
            return

        disconnected = set()
        for websocket in self.active_connections[conversation_id]:
            if websocket == exclude_ws:
                continue

            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to websocket: {e}", exc_info=True)
                disconnected.add(websocket)

        for ws in disconnected:
            self.disconnect(ws, conversation_id)

    async def send_to_websocket(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message to single websocket: {e}", exc_info=True)

    def get_user_id(self, websocket: WebSocket) -> str:
        return self.user_websockets.get(websocket, "unknown")

    def get_conversation_connections(self, conversation_id: str) -> Set[WebSocket]:
        return self.active_connections.get(conversation_id, set())

    def get_connection_count(self, conversation_id: str) -> int:
        return len(self.active_connections.get(conversation_id, set()))
