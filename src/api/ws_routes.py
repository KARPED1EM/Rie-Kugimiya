from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import asyncio
import logging
import os
import base64

from ..message_server import (
    MessageService,
    WebSocketManager,
    Message,
    MessageType,
    TypingState,
)
from ..rin_client import RinClient
from ..config import character_config, llm_defaults, ui_defaults
from ..utils.logger import unified_logger

logger = logging.getLogger(__name__)

router = APIRouter()

message_service = MessageService()
ws_manager = WebSocketManager()
rin_clients = {}


class AvatarUploadRequest(BaseModel):
    user_id: str
    avatar_data: str  # base64 encoded image data

# Set WebSocket manager for unified logger
unified_logger.set_ws_manager(ws_manager)


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Yuzuriha Rin Virtual Character System",
        "active_conversations": len(ws_manager.active_connections),
        "active_websockets": sum(
            len(ws_set) for ws_set in ws_manager.active_connections.values()
        ),
    }


@router.get("/config/defaults")
async def get_config_defaults():
    """Get default configuration values"""
    return {
        "llm": {
            "provider": llm_defaults.provider,
            "model_openai": llm_defaults.model_openai,
            "model_anthropic": llm_defaults.model_anthropic,
            "model_deepseek": llm_defaults.model_deepseek,
            "model_custom": llm_defaults.model_custom,
        },
        "character": {
            "name": character_config.default_name,
            "persona": character_config.default_persona,
        },
        "ui": {
            "enable_emotion_theme": ui_defaults.enable_emotion_theme,
        },
    }


@router.get("/config")
async def get_config():
    """Get saved configuration from database"""
    try:
        config = message_service.db.get_config()
        if config:
            return JSONResponse(content=config)
        else:
            # Return defaults if no config saved
            return JSONResponse(content={
                "provider": llm_defaults.provider,
                "model": llm_defaults.model_deepseek,
                "persona": character_config.default_persona,
                "character_name": character_config.default_name,
                "user_nickname": "鲨鲨",
                "enable_emotion_theme": ui_defaults.enable_emotion_theme,
                "debug_mode": False
            })
    except Exception as e:
        logger.error(f"Error getting config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get config")


class ConfigSaveRequest(BaseModel):
    provider: str
    api_key: str
    base_url: Optional[str] = None
    model: str
    persona: str = ""
    character_name: str = "Rin"
    user_nickname: str = "鲨鲨"
    enable_emotion_theme: bool = True
    debug_mode: bool = False


@router.post("/config")
async def save_config(request: ConfigSaveRequest):
    """Save configuration to database"""
    try:
        config_dict = request.dict()
        success = message_service.db.save_config(config_dict)

        if success:
            return JSONResponse(content={"success": True, "message": "Config saved successfully"})
        else:
            raise HTTPException(status_code=500, detail="Failed to save config")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save config")


@router.post("/shutdown")
async def shutdown_server():
    """Request graceful shutdown of the backend process"""
    logger.warning("Shutdown requested via API, terminating process")

    async def _terminate():
        await asyncio.sleep(0.2)
        os._exit(0)

    asyncio.create_task(_terminate())
    return {"status": "shutting_down"}


def get_or_create_rin_client(conversation_id: str, llm_config: dict) -> RinClient:
    """Get or create Rin client for conversation"""
    if conversation_id not in rin_clients:
        rin_clients[conversation_id] = RinClient(
            message_service=message_service,
            ws_manager=ws_manager,
            llm_config=llm_config,
        )
    return rin_clients[conversation_id]


@router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket, conversation_id: str, user_id: str = Query(default="user")
):
    await ws_manager.connect(websocket, conversation_id, user_id)

    try:
        # 确保打招呼消息存在（使用默认名称，后续会通过init_rin更新）
        await message_service.ensure_greeting_messages(
            conversation_id,
            assistant_name=character_config.default_name,
            user_name="鲨鲨"
        )

        history = await message_service.get_messages(conversation_id)
        history_event = message_service.create_history_event(history)
        await ws_manager.send_to_websocket(websocket, history_event.model_dump())

        while True:
            data = await websocket.receive_json()
            await handle_client_message(websocket, conversation_id, user_id, data)

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, conversation_id)
        await message_service.clear_user_typing_state(user_id, conversation_id)

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        ws_manager.disconnect(websocket, conversation_id)


async def handle_client_message(
    websocket: WebSocket, conversation_id: str, user_id: str, data: dict
):
    """Handle incoming client message"""
    msg_type = data.get("type")

    if msg_type == "sync":
        await handle_sync(websocket, conversation_id, data)

    elif msg_type == "message":
        await handle_user_message(websocket, conversation_id, user_id, data)

    elif msg_type == "typing":
        await handle_typing_state(websocket, conversation_id, user_id, data)

    elif msg_type == "recall":
        await handle_recall(websocket, conversation_id, user_id, data)

    elif msg_type == "clear":
        await handle_clear(websocket, conversation_id, user_id)

    elif msg_type == "init_rin":
        await handle_init_rin(conversation_id, data)

    elif msg_type == "debug_mode":
        await handle_debug_mode(websocket, conversation_id, data)


async def handle_sync(websocket: WebSocket, conversation_id: str, data: dict):
    """Handle incremental sync request"""
    after_timestamp = data.get("after_timestamp", 0)

    messages = await message_service.get_messages(
        conversation_id, after_timestamp=after_timestamp
    )

    event = message_service.create_history_event(messages)
    await ws_manager.send_to_websocket(websocket, event.model_dump())


async def handle_user_message(
    websocket: WebSocket, conversation_id: str, user_id: str, data: dict
):
    """Handle user message"""
    from ..utils.logger import LogCategory, broadcast_log_if_needed

    content = data.get("content", "").strip()
    if not content:
        return

    await message_service.clear_user_typing_state(user_id, conversation_id)

    message = Message(
        id=data.get("id", f"msg-{datetime.now().timestamp()}"),
        conversation_id=conversation_id,
        sender_id=user_id,
        type=MessageType.TEXT,
        content=content,
        timestamp=datetime.now().timestamp(),
        metadata=data.get("metadata", {}),
    )

    # Log user message
    log_entry = unified_logger.info(
        f"User message received: '{content[:50]}{'...' if len(content) > 50 else ''}'",
        category=LogCategory.MESSAGE,
        metadata={"content": content, "message_id": message.id}
    )
    await broadcast_log_if_needed(log_entry)

    await message_service.save_message(message)

    event = message_service.create_message_event(message)
    await ws_manager.send_to_conversation(
        conversation_id, event.model_dump(), exclude_ws=None
    )

    if conversation_id in rin_clients:
        rin_client = rin_clients[conversation_id]
        await rin_client.process_user_message(message)


async def handle_typing_state(
    websocket: WebSocket, conversation_id: str, user_id: str, data: dict
):
    """Handle typing state update"""
    is_typing = data.get("is_typing", False)

    typing_state = TypingState(
        user_id=user_id,
        conversation_id=conversation_id,
        is_typing=is_typing,
        timestamp=datetime.now().timestamp(),
    )

    await message_service.set_typing_state(typing_state)

    event = message_service.create_typing_event(typing_state)
    await ws_manager.send_to_conversation(
        conversation_id, event.model_dump(), exclude_ws=websocket
    )


async def handle_recall(
    websocket: WebSocket, conversation_id: str, user_id: str, data: dict
):
    """
    Handle message recall

    创建一个新的recall_event消息并广播给所有客户端
    """
    message_id = data.get("message_id")
    if not message_id:
        return

    # 创建撤回事件消息
    recall_event = await message_service.recall_message(
        message_id, conversation_id, recalled_by=user_id
    )

    if recall_event:
        # 广播撤回事件作为普通消息
        event = message_service.create_message_event(recall_event)
        await ws_manager.send_to_conversation(
            conversation_id, event.model_dump(), exclude_ws=None
        )


async def handle_clear(websocket: WebSocket, conversation_id: str, user_id: str):
    """Handle conversation clear"""
    success = await message_service.clear_conversation(conversation_id)

    if success:
        # First, send clear event to all clients
        event = message_service.create_clear_event(conversation_id)
        await ws_manager.send_to_conversation(
            conversation_id, event.model_dump(), exclude_ws=None
        )

        # Get character name and user nickname from rin_clients if available
        assistant_name = character_config.default_name
        user_nickname = "鲨鲨"
        if conversation_id in rin_clients:
            rin_client = rin_clients[conversation_id]
            if hasattr(rin_client, 'character_name'):
                assistant_name = rin_client.character_name
            # Get user nickname from llm_client config
            if hasattr(rin_client, 'llm_client') and hasattr(rin_client.llm_client, 'config'):
                user_nickname = rin_client.llm_client.config.user_nickname or "鲨鲨"

        # Immediately create greeting messages after clearing
        created = await message_service.ensure_greeting_messages(
            conversation_id,
            assistant_name=assistant_name,
            user_name=user_nickname
        )

        # If greeting messages were created, broadcast them to all clients
        if created:
            greeting_messages = await message_service.get_messages(conversation_id)
            for msg in greeting_messages:
                msg_event = message_service.create_message_event(msg)
                await ws_manager.send_to_conversation(
                    conversation_id, msg_event.model_dump(), exclude_ws=None
                )


async def handle_init_rin(conversation_id: str, data: dict):
    """Initialize Rin client for conversation"""
    llm_config = data.get("llm_config", {})

    if not llm_config:
        logger.warning(f"Empty LLM config for conversation {conversation_id}")
        return

    try:
        rin_client = get_or_create_rin_client(conversation_id, llm_config)
        await rin_client.start(conversation_id)
        logger.info(f"Rin client initialized for conversation {conversation_id}")
    except Exception as e:
        logger.error(f"Failed to initialize Rin client: {e}", exc_info=True)


async def handle_debug_mode(websocket: WebSocket, conversation_id: str, data: dict):
    """Handle debug mode toggle"""
    from ..utils.logger import LogCategory

    enabled = data.get("enabled", False)

    if enabled:
        ws_manager.enable_debug_mode(websocket, conversation_id)
        unified_logger.enable_debug_mode(True)
        logger.info(f"Debug mode enabled for conversation {conversation_id}")
    else:
        ws_manager.disable_debug_mode(websocket, conversation_id)
        unified_logger.enable_debug_mode(False)
        logger.info(f"Debug mode disabled for conversation {conversation_id}")


@router.get("/avatar/{user_id}")
async def get_user_avatar(user_id: str):
    """Get user avatar (base64 encoded)"""
    try:
        avatar_data = message_service.db.get_user_avatar(user_id)
        if avatar_data:
            return JSONResponse(content={"avatar_data": avatar_data})
        else:
            return JSONResponse(content={"avatar_data": None})
    except Exception as e:
        logger.error(f"Error getting avatar for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get avatar")


@router.post("/avatar")
async def upload_user_avatar(request: AvatarUploadRequest):
    """Upload user avatar (base64 encoded)"""
    try:
        # Validate base64 data
        user_id = request.user_id
        avatar_data = request.avatar_data

        # Check if it's a valid base64 string and starts with data:image
        if not avatar_data.startswith("data:image/"):
            raise HTTPException(status_code=400, detail="Invalid image data format")

        # Check file size (limit to 5MB base64 encoded)
        if len(avatar_data) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Avatar size too large (max 5MB)")

        success = message_service.db.save_user_avatar(user_id, avatar_data)

        if success:
            return JSONResponse(content={"success": True, "message": "Avatar uploaded successfully"})
        else:
            raise HTTPException(status_code=500, detail="Failed to save avatar")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading avatar for user {request.user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upload avatar")


@router.delete("/avatar/{user_id}")
async def delete_user_avatar(user_id: str):
    """Delete user avatar"""
    try:
        success = message_service.db.delete_user_avatar(user_id)

        if success:
            return JSONResponse(content={"success": True, "message": "Avatar deleted successfully"})
        else:
            raise HTTPException(status_code=500, detail="Failed to delete avatar")
    except Exception as e:
        logger.error(f"Error deleting avatar for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete avatar")
