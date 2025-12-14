import logging
from typing import Dict, Set
from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_websockets: Dict[WebSocket, str] = {}
        self.global_connections: Set[WebSocket] = set()
        self.global_debug_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, conversation_id: str, user_id: str):
        await websocket.accept()

        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = set()

        self.active_connections[conversation_id].add(websocket)
        self.user_websockets[websocket] = user_id

    async def connect_global(self, websocket: WebSocket):
        await websocket.accept()
        self.global_connections.add(websocket)

    def disconnect(self, websocket: WebSocket, conversation_id: str):
        if conversation_id in self.active_connections:
            self.active_connections[conversation_id].discard(websocket)
            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]

        self.user_websockets.pop(websocket, None)

    def disconnect_global(self, websocket: WebSocket):
        self.global_connections.discard(websocket)
        self.disable_global_debug_mode(websocket)

    async def send_to_conversation(
        self,
        conversation_id: str,
        message: dict,
        exclude_ws: WebSocket = None,
    ):
        if conversation_id not in self.active_connections:
            return

        disconnected = set()
        for websocket in self.active_connections[conversation_id]:
            if websocket == exclude_ws:
                continue

            try:
                if websocket.application_state != WebSocketState.CONNECTED:
                    disconnected.add(websocket)
                    continue
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to websocket: {e}", exc_info=True)
                disconnected.add(websocket)

        for ws in disconnected:
            self.disconnect(ws, conversation_id)

    async def send_to_user(
        self,
        conversation_id: str,
        user_id: str,
        message: dict,
    ):
        """Send message only to websockets belonging to a specific user in a conversation."""
        if conversation_id not in self.active_connections:
            return

        disconnected = set()
        for websocket in self.active_connections[conversation_id]:
            # Check if this websocket belongs to the specified user
            ws_user_id = self.user_websockets.get(websocket)
            if ws_user_id != user_id:
                continue

            try:
                if websocket.application_state != WebSocketState.CONNECTED:
                    disconnected.add(websocket)
                    continue
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to user websocket: {e}", exc_info=True)
                disconnected.add(websocket)

        for ws in disconnected:
            self.disconnect(ws, conversation_id)

    async def send_to_websocket(self, websocket: WebSocket, message: dict):
        try:
            if websocket.application_state != WebSocketState.CONNECTED:
                return
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message to single websocket: {e}", exc_info=True)

    async def send_toast(self, conversation_id: str, message: str, level: str = "info"):
        """
        Notify frontend via global toast event (not a chat message).
        level: info|success|error|warning (frontend maps warning -> info)
        conversation_id is included for context only.
        """
        await self.send_global(
            {"type": "toast", "data": {"message": message, "level": level, "session_id": conversation_id}},
        )

    async def send_global(self, message: dict):
        if not self.global_connections:
            return
        disconnected = set()
        for websocket in self.global_connections:
            try:
                if websocket.application_state != WebSocketState.CONNECTED:
                    disconnected.add(websocket)
                    continue
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending global message: {e}", exc_info=True)
                disconnected.add(websocket)
        for ws in disconnected:
            self.disconnect_global(ws)

    def get_user_id(self, websocket: WebSocket) -> str:
        return self.user_websockets.get(websocket, "unknown")

    def get_conversation_connections(self, conversation_id: str) -> Set[WebSocket]:
        return self.active_connections.get(conversation_id, set())

    def get_connection_count(self, conversation_id: str) -> int:
        return len(self.active_connections.get(conversation_id, set()))

    def enable_global_debug_mode(self, websocket: WebSocket):
        self.global_debug_connections.add(websocket)

    def disable_global_debug_mode(self, websocket: WebSocket):
        self.global_debug_connections.discard(websocket)

    async def broadcast_global_debug_log(self, log_entry: dict):
        """Broadcast debug logs to global debug connections."""
        if not self.global_debug_connections:
            return
        disconnected = set()
        for websocket in self.global_debug_connections:
            try:
                if websocket.application_state != WebSocketState.CONNECTED:
                    disconnected.add(websocket)
                    continue
                await websocket.send_json({"type": "debug_log", "data": log_entry})
            except Exception:
                # Silently remove disconnected websockets (expected during normal operation)
                disconnected.add(websocket)
        for ws in disconnected:
            self.disable_global_debug_mode(ws)
