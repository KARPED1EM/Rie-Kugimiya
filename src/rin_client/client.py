import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from ..api.llm_client import LLMClient
from ..api.schemas import LLMConfig, ChatMessage
from ..behavior.coordinator import BehaviorCoordinator
from ..behavior.models import BehaviorConfig, PlaybackAction
from ..message_server.service import MessageService
from ..message_server.models import Message, MessageType, TypingState
from ..config import character_config
from ..utils.logger import unified_logger, LogCategory, broadcast_log_if_needed

logger = logging.getLogger(__name__)


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
        # Convert dict to LLMConfig if needed
        if isinstance(llm_config, dict):
            try:
                llm_config = LLMConfig(**llm_config)
            except Exception as e:
                logger.error(f"Failed to create LLMConfig: {e}")
                raise ValueError(f"Invalid LLM configuration: {e}")
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

        try:
            history = await self.message_service.get_messages(user_message.conversation_id)

            conversation_history = []
            for msg in history:
                if msg.type == MessageType.TEXT:
                    role = "assistant" if msg.sender_id == self.user_id else "user"
                    conversation_history.append(
                        ChatMessage(role=role, content=msg.content)
                    )

            llm_response = await self.llm_client.chat(
                conversation_history,
                character_name=self.character_name
            )

            # Log emotion data
            if llm_response.emotion_map:
                log_entry = unified_logger.emotion(
                    emotion_map=llm_response.emotion_map,
                    context=f"User message: {user_message.content[:50]}..."
                )
                await broadcast_log_if_needed(log_entry)

            timeline = self.coordinator.process_message(
                llm_response.reply,
                emotion_map=llm_response.emotion_map
            )

            # Log behavior sequence with full details
            behavior_summary = []
            for action in timeline:
                detail_parts = [f"{action.type}", f"@{action.timestamp:.2f}s"]

                # Add specific details based on action type
                if action.type == "send":
                    text_preview = action.text[:30] + "..." if len(action.text) > 30 else action.text
                    detail_parts.append(f"text='{text_preview}'")
                    if action.metadata and action.metadata.get('emotion'):
                        detail_parts.append(f"emotion={action.metadata['emotion']}")
                elif action.type == "recall":
                    detail_parts.append(f"target={action.target_id}")
                elif action.type in ["typing_start", "typing_end"]:
                    pass  # No extra details needed
                elif action.type == "wait":
                    pass  # Duration already shown in timestamp

                behavior_summary.append(" ".join(detail_parts))

            log_entry = unified_logger.behavior(
                action="Generated timeline",
                details={
                    "actions": behavior_summary,
                    "total_actions": len(timeline),
                    "reply": llm_response.reply
                }
            )
            await broadcast_log_if_needed(log_entry)

            task = asyncio.create_task(
                self._execute_timeline(timeline, user_message.conversation_id)
            )
            self._tasks.append(task)

        except Exception as e:
            logger.error(f"Error processing user message: {e}", exc_info=True)
            # Send error message to user
            error_message = Message(
                id=f"error-{datetime.now().timestamp()}",
                conversation_id=user_message.conversation_id,
                sender_id=self.user_id,
                type=MessageType.TEXT,
                content="抱歉，我现在有点懵...稍后再试试吧 >_<",
                timestamp=datetime.now().timestamp(),
                metadata={"error": True}
            )
            await self.message_service.save_message(error_message)
            event = self.message_service.create_message_event(error_message)
            await self.ws_manager.send_to_conversation(
                user_message.conversation_id,
                event.model_dump()
            )

    async def _execute_timeline(self, timeline: List[PlaybackAction], conversation_id: str):
        """Execute timeline with proper timing"""
        start_time = datetime.now().timestamp()

        log_entry = unified_logger.info(
            f"Starting timeline execution with {len(timeline)} actions",
            category=LogCategory.BEHAVIOR
        )
        await broadcast_log_if_needed(log_entry)

        for i, action in enumerate(timeline):
            if not self._running:
                break

            scheduled_time = start_time + action.timestamp
            current_time = datetime.now().timestamp()
            wait_time = max(0, scheduled_time - current_time)

            if wait_time > 0:
                await asyncio.sleep(wait_time)

            # Log action execution
            action_desc = f"[{i+1}/{len(timeline)}] Executing: {action.type}"
            if action.type == "send":
                text_preview = action.text[:20] + "..." if len(action.text) > 20 else action.text
                action_desc += f" '{text_preview}'"
            elif action.type == "recall":
                action_desc += f" (target={action.target_id})"

            log_entry = unified_logger.debug(
                action_desc,
                category=LogCategory.BEHAVIOR,
                metadata={
                    "action_index": i + 1,
                    "total_actions": len(timeline),
                    "elapsed_time": f"{current_time - start_time:.2f}s"
                }
            )
            await broadcast_log_if_needed(log_entry)

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

        log_entry = unified_logger.info(
            "Timeline execution completed",
            category=LogCategory.BEHAVIOR,
            metadata={"total_time": f"{datetime.now().timestamp() - start_time:.2f}s"}
        )
        await broadcast_log_if_needed(log_entry)

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

        # Log the message being sent
        log_entry = unified_logger.debug(
            f"Sent message to frontend: '{content[:30]}...' (id={message_id})",
            category=LogCategory.WEBSOCKET,
            metadata={
                "message_id": message_id,
                "content": content,
                "emotion": metadata.get("emotion"),
                "emotion_map": metadata.get("emotion_map")
            }
        )
        await broadcast_log_if_needed(log_entry)

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

            # Log the recall action
            log_entry = unified_logger.debug(
                f"Recalled message (id={message_id})",
                category=LogCategory.WEBSOCKET,
                metadata={"message_id": message_id, "action": "recall"}
            )
            await broadcast_log_if_needed(log_entry)
