import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

from ..api.llm_client import LLMClient
from ..behavior.coordinator import BehaviorCoordinator
from ..behavior.models import BehaviorConfig, PlaybackAction
from ..message_server.service import MessageService
from ..message_server.models import Message, MessageType, TypingState
from ..config import character_config


class RinClient:
    """
    Rin as an independent client that connects to message service
    """

    def __init__(
        self,
        message_service: MessageService,
        ws_manager: Any,
        llm_config: dict,
        behavior_config: Optional[BehaviorConfig] = None
    ):
        self.message_service = message_service
        self.ws_manager = ws_manager
        self.llm_client = LLMClient(llm_config)
        self.coordinator = BehaviorCoordinator(behavior_config or BehaviorConfig())
        self.user_id = "rin"
        self.character_name = character_config.default_name
        self._running = False
        self._tasks = []

    async def start(self, conversation_id: str):
        """Start Rin client for a conversation"""
        self._running = True
        self.conversation_id = conversation_id

    async def stop(self):
        """Stop Rin client"""
        self._running = False
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()
        await self.llm_client.close()

    async def process_user_message(self, user_message: Message):
        """Process user message and generate response"""
        if not self._running:
            return

        history = await self.message_service.get_messages(user_message.conversation_id)

        conversation_history = []
        for msg in history:
            if msg.type == MessageType.TEXT:
                role = "assistant" if msg.sender_id == self.user_id else "user"
                conversation_history.append({
                    "role": role,
                    "content": msg.content
                })

        llm_response = await self.llm_client.chat(
            conversation_history,
            character_name=self.character_name
        )

        timeline = self.coordinator.process_message(
            llm_response.reply,
            emotion_map=llm_response.emotion_map
        )

        task = asyncio.create_task(
            self._execute_timeline(timeline, user_message.conversation_id)
        )
        self._tasks.append(task)

    async def _execute_timeline(self, timeline: list[PlaybackAction], conversation_id: str):
        """Execute timeline with proper timing"""
        start_time = datetime.now().timestamp()

        for action in timeline:
            if not self._running:
                break

            scheduled_time = start_time + action.timestamp
            current_time = datetime.now().timestamp()
            wait_time = max(0, scheduled_time - current_time)

            if wait_time > 0:
                await asyncio.sleep(wait_time)

            if action.type == "typing_start":
                await self._send_typing_state(conversation_id, True)

            elif action.type == "typing_end":
                await self._send_typing_state(conversation_id, False)

            elif action.type == "send":
                await self._send_typing_state(conversation_id, False)
                await self._send_message(
                    conversation_id,
                    action.text,
                    action.message_id,
                    action.metadata
                )

            elif action.type == "recall":
                await self._send_typing_state(conversation_id, False)
                await self._recall_message(conversation_id, action.target_id)

            elif action.type == "wait":
                pass

    async def _send_typing_state(self, conversation_id: str, is_typing: bool):
        """Send typing state to message service"""
        typing_state = TypingState(
            user_id=self.user_id,
            conversation_id=conversation_id,
            is_typing=is_typing,
            timestamp=datetime.now().timestamp()
        )
        await self.message_service.set_typing_state(typing_state)

        event = self.message_service.create_typing_event(typing_state)
        await self.ws_manager.send_to_conversation(conversation_id, event.model_dump())

    async def _send_message(
        self,
        conversation_id: str,
        content: str,
        message_id: str,
        metadata: Dict[str, Any]
    ):
        """Send message to message service"""
        message = Message(
            id=message_id,
            conversation_id=conversation_id,
            sender_id=self.user_id,
            type=MessageType.TEXT,
            content=content,
            timestamp=datetime.now().timestamp(),
            metadata=metadata
        )
        await self.message_service.save_message(message)

        event = self.message_service.create_message_event(message)
        await self.ws_manager.send_to_conversation(conversation_id, event.model_dump())

    async def _recall_message(self, conversation_id: str, message_id: str):
        """Recall a message"""
        recall_event = await self.message_service.recall_message(
            message_id,
            conversation_id,
            recalled_by=self.user_id
        )

        if recall_event:
            event = self.message_service.create_message_event(recall_event)
            await self.ws_manager.send_to_conversation(conversation_id, event.model_dump())
