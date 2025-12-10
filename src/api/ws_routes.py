from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from datetime import datetime
import logging

from ..message_server import MessageService, WebSocketManager, Message, MessageType, TypingState
from ..rin_client import RinClient
from ..config import character_config

logger = logging.getLogger(__name__)

router = APIRouter()

message_service = MessageService()
ws_manager = WebSocketManager()
rin_clients = {}


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Yuzuriha Rin Virtual Character System",
        "active_conversations": len(ws_manager.active_connections),
        "active_websockets": sum(len(ws_set) for ws_set in ws_manager.active_connections.values())
    }


def get_or_create_rin_client(conversation_id: str, llm_config: dict) -> RinClient:
    """Get or create Rin client for conversation"""
    if conversation_id not in rin_clients:
        rin_clients[conversation_id] = RinClient(
            message_service=message_service,
            ws_manager=ws_manager,
            llm_config=llm_config
        )
    return rin_clients[conversation_id]


@router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: str,
    user_id: str = Query(default="user")
):
    await ws_manager.connect(websocket, conversation_id, user_id)

    try:
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
    websocket: WebSocket,
    conversation_id: str,
    user_id: str,
    data: dict
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


async def handle_sync(
    websocket: WebSocket,
    conversation_id: str,
    data: dict
):
    """Handle incremental sync request"""
    after_timestamp = data.get("after_timestamp", 0)

    messages = await message_service.get_messages(
        conversation_id,
        after_timestamp=after_timestamp
    )

    event = message_service.create_history_event(messages)
    await ws_manager.send_to_websocket(websocket, event.model_dump())


async def handle_user_message(
    websocket: WebSocket,
    conversation_id: str,
    user_id: str,
    data: dict
):
    """Handle user message"""
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
        metadata=data.get("metadata", {})
    )

    await message_service.save_message(message)

    event = message_service.create_message_event(message)
    await ws_manager.send_to_conversation(
        conversation_id,
        event.model_dump(),
        exclude_ws=None
    )

    if conversation_id in rin_clients:
        rin_client = rin_clients[conversation_id]
        await rin_client.process_user_message(message)


async def handle_typing_state(
    websocket: WebSocket,
    conversation_id: str,
    user_id: str,
    data: dict
):
    """Handle typing state update"""
    is_typing = data.get("is_typing", False)

    typing_state = TypingState(
        user_id=user_id,
        conversation_id=conversation_id,
        is_typing=is_typing,
        timestamp=datetime.now().timestamp()
    )

    await message_service.set_typing_state(typing_state)

    event = message_service.create_typing_event(typing_state)
    await ws_manager.send_to_conversation(
        conversation_id,
        event.model_dump(),
        exclude_ws=websocket
    )


async def handle_recall(
    websocket: WebSocket,
    conversation_id: str,
    user_id: str,
    data: dict
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
        message_id,
        conversation_id,
        recalled_by=user_id
    )

    if recall_event:
        # 广播撤回事件作为普通消息
        event = message_service.create_message_event(recall_event)
        await ws_manager.send_to_conversation(
            conversation_id,
            event.model_dump(),
            exclude_ws=None
        )


async def handle_clear(
    websocket: WebSocket,
    conversation_id: str,
    user_id: str
):
    """Handle conversation clear"""
    success = await message_service.clear_conversation(conversation_id)

    if success:
        event = message_service.create_clear_event(conversation_id)
        await ws_manager.send_to_conversation(
            conversation_id,
            event.model_dump(),
            exclude_ws=None
        )


async def handle_init_rin(conversation_id: str, data: dict):
    """Initialize Rin client for conversation"""
    llm_config = data.get("llm_config", {})

    rin_client = get_or_create_rin_client(conversation_id, llm_config)
    await rin_client.start(conversation_id)
