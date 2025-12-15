from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional, Dict, Any

from src.infrastructure.database.connection import DatabaseConnection
from src.infrastructure.database.repositories import (
    MessageRepository,
    CharacterRepository,
    SessionRepository,
    ConfigRepository,
)
from src.services.messaging.message_service import MessageService
from src.services.character.character_service import CharacterService
from src.services.config.config_service import ConfigService
from src.infrastructure.network.websocket_manager import WebSocketManager
from src.core.utils.logger import (
    unified_logger,
    broadcast_log_if_needed,
    LogCategory,
)
from src.core.config import database_config

router = APIRouter()

conn_mgr: Optional[DatabaseConnection] = None
message_service: Optional[MessageService] = None
character_service: Optional[CharacterService] = None
config_service: Optional[ConfigService] = None
ws_manager: Optional[WebSocketManager] = None


async def initialize_services():
    global conn_mgr, message_service, character_service, config_service, ws_manager

    if conn_mgr is None:
        conn_mgr = DatabaseConnection(database_config.path)

    message_repo = MessageRepository(conn_mgr)
    character_repo = CharacterRepository(conn_mgr)
    session_repo = SessionRepository(conn_mgr)
    config_repo = ConfigRepository(conn_mgr)

    if message_service is None:
        message_service = MessageService(message_repo)
    if config_service is None:
        config_service = ConfigService(config_repo)
    if character_service is None:
        character_service = CharacterService(
            character_repo, session_repo, message_service, config_service
        )

    existing_ws_mgr = getattr(unified_logger, "ws_manager", None)
    if existing_ws_mgr:
        ws_manager = existing_ws_mgr
    else:
        ws_manager = WebSocketManager()
        unified_logger.set_ws_manager(ws_manager)

    if getattr(character_service, "_builtin_initialized", False) is not True:
        await character_service.initialize_builtin_characters()
        setattr(character_service, "_builtin_initialized", True)


@router.websocket("/ws-global")
async def websocket_global_endpoint(websocket: WebSocket):
    await initialize_services()

    await ws_manager.connect_global(websocket)

    # Send recent buffered logs to new debug clients.
    try:
        for entry in unified_logger.get_recent_logs(200):
            await ws_manager.send_to_websocket(
                websocket, {"type": "debug_log", "data": entry}
            )

        while True:
            data = await websocket.receive_json()
            await handle_global_client_message(websocket, data)

    except WebSocketDisconnect:
        ws_manager.disconnect_global(websocket)
    except Exception as e:
        ws_manager.disconnect_global(websocket)
        log_entry = unified_logger.error(
            f"Global WebSocket error: {e}",
            category=LogCategory.WEBSOCKET,
            metadata={"exc_info": True},
        )
        await broadcast_log_if_needed(log_entry)


async def handle_global_client_message(websocket: WebSocket, data: Dict[str, Any]):
    msg_type = data.get("type")

    if msg_type == "set_debug":
        enabled = bool(data.get("enabled"))
        was_enabled = unified_logger.debug_mode_enabled
        unified_logger.enable_debug_mode(enabled)
        if enabled:
            ws_manager.enable_global_debug_mode(websocket)
            # Emit only on state transition to avoid duplicate "enabled" logs.
            if not was_enabled:
                log_entry = unified_logger.info(
                    "Debug mode enabled", category=LogCategory.WEBSOCKET
                )
                await broadcast_log_if_needed(log_entry)
        else:
            ws_manager.disable_global_debug_mode(websocket)
    else:
        # ignore unknown global messages
        return
