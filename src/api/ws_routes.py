from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, Any, Optional

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
from src.services.session.session_client import SessionClient
from src.infrastructure.network.websocket_manager import WebSocketManager
from src.core.models.message import MessageType
from src.api.schemas import LLMConfig
from src.infrastructure.utils.logger import (
    unified_logger,
    broadcast_log_if_needed,
    LogCategory,
)
from src.core.config import database_config, llm_defaults
from src.core.models.constants import DEFAULT_USER_ID
from src.utils.url_utils import sanitize_base_url

router = APIRouter()

conn_mgr: Optional[DatabaseConnection] = None
message_repo: Optional[MessageRepository] = None
character_repo: Optional[CharacterRepository] = None
session_repo: Optional[SessionRepository] = None
config_repo: Optional[ConfigRepository] = None
message_service: Optional[MessageService] = None
character_service: Optional[CharacterService] = None
config_service: Optional[ConfigService] = None
ws_manager: Optional[WebSocketManager] = None
session_clients: Dict[str, SessionClient] = {}


async def initialize_services():
    global conn_mgr, message_repo, character_repo, session_repo, config_repo
    global message_service, character_service, config_service, ws_manager

    if conn_mgr is None:
        conn_mgr = DatabaseConnection(database_config.path)

    # Initialize repos/services if missing (supports init order with global WS first).
    if message_repo is None:
        message_repo = MessageRepository(conn_mgr)
    if character_repo is None:
        character_repo = CharacterRepository(conn_mgr)
    if session_repo is None:
        session_repo = SessionRepository(conn_mgr)
    if config_repo is None:
        config_repo = ConfigRepository(conn_mgr)

    if message_service is None:
        message_service = MessageService(message_repo)
    if config_service is None:
        config_service = ConfigService(config_repo)
    if character_service is None:
        character_service = CharacterService(
            character_repo, session_repo, message_service, config_service
        )

    # Always bind to the unified WebSocketManager (single instance per process).
    existing_ws_mgr = getattr(unified_logger, "ws_manager", None)
    if existing_ws_mgr:
        ws_manager = existing_ws_mgr
    else:
        ws_manager = WebSocketManager()
        unified_logger.set_ws_manager(ws_manager)

    # Builtins only need initialization once.
    if getattr(character_service, "_builtin_initialized", False) is not True:
        await character_service.initialize_builtin_characters()
        setattr(character_service, "_builtin_initialized", True)
        log_entry = unified_logger.info(
            "Services initialized", category=LogCategory.WEBSOCKET
        )
        await broadcast_log_if_needed(log_entry)


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket, session_id: str, user_id: str = Query(default=DEFAULT_USER_ID)
):
    await initialize_services()

    # Verify session exists before accepting connection
    session = await session_repo.get_by_id(session_id)
    if not session:
        # Session not found - close connection immediately without logging error
        await websocket.close(code=1008, reason="Session not found")
        return

    await ws_manager.connect(websocket, session_id, user_id)

    try:
        messages = await message_service.get_messages(session_id)
        history_event = {
            "type": "history",
            "data": {
                "messages": [
                    {
                        "id": msg.id,
                        "session_id": msg.session_id,
                        "sender_id": msg.sender_id,
                        "type": msg.type,
                        "content": msg.content,
                        "metadata": msg.metadata,
                        "is_recalled": msg.is_recalled,
                        "is_read": msg.is_read,
                        "timestamp": msg.timestamp,
                    }
                    for msg in messages
                ]
            },
        }
        await ws_manager.send_to_websocket(websocket, history_event)

        while True:
            data = await websocket.receive_json()
            await handle_client_message(websocket, session_id, user_id, data)

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, session_id)
        log_entry = unified_logger.info(
            f"WebSocket disconnected: {user_id} from {session_id}",
            category=LogCategory.WEBSOCKET,
        )
        await broadcast_log_if_needed(log_entry)

    except Exception as e:
        # Log unexpected errors but suppress common connection errors
        if not isinstance(e, (ConnectionResetError, ConnectionAbortedError)):
            log_entry = unified_logger.error(
                f"WebSocket error: {e}",
                category=LogCategory.WEBSOCKET,
                metadata={"exc_info": True},
            )
            await broadcast_log_if_needed(log_entry)
        ws_manager.disconnect(websocket, session_id)


async def handle_client_message(
    websocket: WebSocket, session_id: str, user_id: str, data: Dict[str, Any]
):
    try:
        msg_type = data.get("type")

        if msg_type == "send_message":
            await handle_send_message(session_id, user_id, data)

        elif msg_type == "set_typing":
            await handle_set_typing(session_id, user_id, data)

        elif msg_type == "recall_message":
            await handle_recall_message(session_id, user_id, data)

        elif msg_type == "sync_messages":
            await handle_sync_messages(websocket, session_id, data)

        elif msg_type == "switch_session":
            await handle_switch_session(data)

        elif msg_type == "clear_session":
            await handle_clear_session(session_id)

        elif msg_type == "init_character":
            await handle_init_character(session_id, data)

        elif msg_type == "mark_read":
            await handle_mark_read(session_id, data)

        else:
            log_entry = unified_logger.warning(
                f"Unknown message type: {msg_type}",
                category=LogCategory.WEBSOCKET,
            )
            await broadcast_log_if_needed(log_entry)

    except Exception as e:
        log_entry = unified_logger.error(
            f"Error handling client message: {e}",
            category=LogCategory.WEBSOCKET,
            metadata={"exc_info": True},
        )
        await broadcast_log_if_needed(log_entry)
        error_event = {"type": "error", "data": {"message": str(e)}}
        await ws_manager.send_to_websocket(websocket, error_event)


async def handle_send_message(session_id: str, user_id: str, data: Dict[str, Any]):
    content = data.get("content", "").strip()
    if not content:
        return

    messages = await message_service.send_message_with_time(
        session_id=session_id,
        sender_id=user_id,
        message_type=MessageType.TEXT,
        content=content,
        metadata=data.get("metadata", {}),
    )

    for message in messages:
        event = {
            "type": "message",
            "data": {
                "id": message.id,
                "session_id": message.session_id,
                "sender_id": message.sender_id,
                "type": message.type,
                "content": message.content,
                "metadata": message.metadata,
                "is_recalled": message.is_recalled,
                "is_read": message.is_read,
                "timestamp": message.timestamp,
            },
        }
        await ws_manager.send_to_conversation(session_id, event)

    session_client = session_clients.get(session_id)
    if session_client:
        await session_client.process_user_message(messages[-1])


async def handle_set_typing(session_id: str, user_id: str, data: Dict[str, Any]):
    is_typing = data.get("is_typing", False)

    typing_msg = await message_service.set_typing_state(session_id, user_id, is_typing)

    event = {
        "type": "message",
        "data": {
            "id": typing_msg.id,
            "session_id": typing_msg.session_id,
            "sender_id": typing_msg.sender_id,
            "type": typing_msg.type,
            "content": typing_msg.content,
            "metadata": typing_msg.metadata,
            "is_recalled": typing_msg.is_recalled,
            "is_read": typing_msg.is_read,
            "timestamp": typing_msg.timestamp,
        },
    }
    await ws_manager.send_to_conversation(session_id, event, exclude_ws=None)


async def handle_recall_message(session_id: str, user_id: str, data: Dict[str, Any]):
    message_id = data.get("message_id")
    timestamp = data.get("timestamp", 0)

    if not message_id:
        return

    recall_msg = await message_service.recall_message(
        session_id=session_id,
        message_id=message_id,
        timestamp=timestamp,
        recalled_by=user_id,
    )

    if recall_msg:
        event = {
            "type": "message",
            "data": {
                "id": recall_msg.id,
                "session_id": recall_msg.session_id,
                "sender_id": recall_msg.sender_id,
                "type": recall_msg.type,
                "content": recall_msg.content,
                "metadata": recall_msg.metadata,
                "is_recalled": recall_msg.is_recalled,
                "is_read": recall_msg.is_read,
                "timestamp": recall_msg.timestamp,
            },
        }
        await ws_manager.send_to_conversation(session_id, event)


async def handle_sync_messages(
    websocket: WebSocket, session_id: str, data: Dict[str, Any]
):
    after_timestamp = data.get("after_timestamp", 0)

    messages = await message_service.get_messages(session_id, after_timestamp)

    history_event = {
        "type": "history",
        "data": {
            "messages": [
                {
                    "id": msg.id,
                    "session_id": msg.session_id,
                    "sender_id": msg.sender_id,
                    "type": msg.type,
                    "content": msg.content,
                    "metadata": msg.metadata,
                    "is_recalled": msg.is_recalled,
                    "is_read": msg.is_read,
                    "timestamp": msg.timestamp,
                }
                for msg in messages
            ]
        },
    }
    await ws_manager.send_to_websocket(websocket, history_event)


async def handle_switch_session(data: Dict[str, Any]):
    new_session_id = data.get("session_id")
    if not new_session_id:
        return

    await character_service.switch_active_session(new_session_id)


async def handle_clear_session(session_id: str):
    session = await session_repo.get_by_id(session_id)
    if not session:
        return

    new_session_id = await character_service.recreate_session(session.character_id)
    if new_session_id:
        session_client = session_clients.get(session_id)
        if session_client:
            await session_client.stop()
            del session_clients[session_id]

        event = {
            "type": "session_recreated",
            "data": {"old_session_id": session_id, "new_session_id": new_session_id},
        }
        await ws_manager.send_to_conversation(session_id, event)


async def handle_init_character(session_id: str, data: Dict[str, Any]):
    if session_id in session_clients:
        old_client = session_clients.get(session_id)
        if old_client:
            await old_client.stop()
        session_clients.pop(session_id, None)
        log_entry = unified_logger.info(
            f"SessionClient reinitialized for session {session_id}",
            category=LogCategory.WEBSOCKET,
        )
        await broadcast_log_if_needed(log_entry)

    session = await session_repo.get_by_id(session_id)
    if not session:
        # Silently ignore - likely stale session ID from frontend localStorage after DB changes
        return

    character = await character_service.get_character(session.character_id)
    if not character:
        log_entry = unified_logger.error(
            f"Character {session.character_id} not found",
            category=LogCategory.WEBSOCKET,
        )
        await broadcast_log_if_needed(log_entry)
        return

    config = await config_service.get_all_config()
    llm_config_dict = data.get("llm_config") or {}

    resolved_protocol = (
        llm_config_dict.get("protocol")
        or config.get("llm_protocol")
        or llm_defaults.protocol
    )

    resolved_model = (
        llm_config_dict.get("model")
        or config.get("llm_model")
        or llm_defaults.model
    )

    resolved_api_key = llm_config_dict.get("api_key") or config.get("llm_api_key") or ""
    if not resolved_api_key:
        # Allow init to proceed so UI can load; LLM calls will fail until key set.
        resolved_api_key = "DUMMY_API_KEY"
        log_entry = unified_logger.warning(
            "LLM api_key missing; Rin initialized in limited mode",
            category=LogCategory.WEBSOCKET,
        )
        await broadcast_log_if_needed(log_entry)
        await ws_manager.send_toast(
            session_id,
            "LLM API Key 未设置，请在设置中配置后再开始对话。",
            level="warning",
        )

    normalized_base_url = sanitize_base_url(
        llm_config_dict.get("base_url") or config.get("llm_base_url")
    )
    
    # Handle temperature - can be None (optional)
    resolved_temperature = llm_config_dict.get("temperature")
    if resolved_temperature is None:
        temp_str = config.get("llm_temperature", "")
        if temp_str and temp_str.strip():
            try:
                resolved_temperature = float(temp_str)
            except ValueError:
                resolved_temperature = None
    
    # Handle max_tokens - required, default 1000
    resolved_max_tokens = llm_config_dict.get("max_tokens")
    if resolved_max_tokens is None:
        max_tokens_str = config.get("llm_max_tokens", str(llm_defaults.max_tokens))
        try:
            resolved_max_tokens = int(max_tokens_str)
        except ValueError:
            resolved_max_tokens = llm_defaults.max_tokens
    
    llm_config = LLMConfig(
        protocol=resolved_protocol,
        api_key=resolved_api_key,
        model=resolved_model,
        base_url=normalized_base_url,
        temperature=resolved_temperature,
        max_tokens=resolved_max_tokens,
        persona=character.persona,
        character_name=character.name,
        user_nickname=llm_config_dict.get("user_nickname")
        or config.get("user_nickname"),
    )

    session_client = SessionClient(
        message_service=message_service,
        ws_manager=ws_manager,
        llm_config=llm_config,
        character=character,
    )

    await session_client.start(session_id)
    session_clients[session_id] = session_client

    log_entry = unified_logger.info(
        f"SessionClient initialized for session {session_id} with character {character.name}",
        category=LogCategory.WEBSOCKET,
    )
    await broadcast_log_if_needed(log_entry)


async def handle_mark_read(session_id: str, data: Dict[str, Any]):
    until_ts = float(data.get("until_timestamp") or 0)
    last_read_ts = await message_service.mark_read_until(session_id, until_ts)

    event = {
        "type": "read_state",
        "data": {"session_id": session_id, "last_read_timestamp": last_read_ts},
    }
    await ws_manager.send_to_conversation(session_id, event)


async def cleanup_resources():
    """Clean up all resources when shutting down the application"""
    log_entry = unified_logger.info(
        "Starting cleanup of all resources",
        category=LogCategory.WEBSOCKET,
    )
    await broadcast_log_if_needed(log_entry)

    # Stop all SessionClient instances
    if session_clients:
        log_entry = unified_logger.info(
            f"Stopping {len(session_clients)} SessionClient instances",
            category=LogCategory.WEBSOCKET,
        )
        await broadcast_log_if_needed(log_entry)

        for session_id, session_client in list(session_clients.items()):
            try:
                await session_client.stop()
                log_entry = unified_logger.info(
                    f"Stopped SessionClient for session {session_id}",
                    category=LogCategory.WEBSOCKET,
                )
                await broadcast_log_if_needed(log_entry)
            except Exception as e:
                log_entry = unified_logger.error(
                    f"Error stopping SessionClient for session {session_id}: {e}",
                    category=LogCategory.WEBSOCKET,
                )
                await broadcast_log_if_needed(log_entry)

        session_clients.clear()

    # Close all WebSocket connections
    if ws_manager:
        log_entry = unified_logger.info(
            "Closing all WebSocket connections",
            category=LogCategory.WEBSOCKET,
        )
        await broadcast_log_if_needed(log_entry)

        # Close all conversation WebSocket connections
        for conversation_id in list(ws_manager.active_connections.keys()):
            websockets = list(ws_manager.active_connections.get(conversation_id, set()))
            for websocket in websockets:
                try:
                    # Send close code 1001 (going away) to gracefully close
                    await websocket.close(code=1001, reason="Server shutting down")
                except Exception as e:
                    log_entry = unified_logger.error(
                        f"Error closing WebSocket: {e}",
                        category=LogCategory.WEBSOCKET,
                    )
                    await broadcast_log_if_needed(log_entry)

        # Close all global WebSocket connections
        for websocket in list(ws_manager.global_connections):
            try:
                await websocket.close(code=1001, reason="Server shutting down")
            except Exception as e:
                log_entry = unified_logger.error(
                    f"Error closing global WebSocket: {e}",
                    category=LogCategory.WEBSOCKET,
                )
                await broadcast_log_if_needed(log_entry)

        ws_manager.active_connections.clear()
        ws_manager.global_connections.clear()

    log_entry = unified_logger.info(
        "Cleanup completed",
        category=LogCategory.WEBSOCKET,
    )
    await broadcast_log_if_needed(log_entry)
