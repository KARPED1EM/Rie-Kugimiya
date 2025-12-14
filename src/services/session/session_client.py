import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Any
from src.services.llm.llm_client import LLMClient
from src.api.schemas import LLMConfig, ChatMessage
from src.services.behavior.coordinator import BehaviorCoordinator
from src.core.models.behavior import PlaybackAction
from src.services.messaging.message_service import MessageService
from src.core.models.message import Message, MessageType
from src.core.models.character import Character
from src.infrastructure.utils.logger import (
    unified_logger,
    broadcast_log_if_needed,
    LogCategory,
)

logger = logging.getLogger(__name__)


class SessionClient:
    def __init__(
        self,
        message_service: MessageService,
        ws_manager: Any,
        llm_config: LLMConfig,
        character: Character,
    ):
        self.message_service = message_service
        self.ws_manager = ws_manager
        self.llm_client = LLMClient(llm_config)
        self.character = character
        self.user_id = "assistant"

        self.coordinator = BehaviorCoordinator(character)
        self._running = False
        self._tasks = []
        self.session_id = None

    async def start(self, session_id: str):
        self._running = True
        self.session_id = session_id
        logger.info(f"SessionClient started for session {session_id}")

    async def stop(self):
        self._running = False

        # Cancel all pending tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        # Wait for all tasks to complete (with cancellation)
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks.clear()

        # Close the HTTP client
        await self.llm_client.close()
        logger.info("SessionClient stopped")

    def update_character(self, character: Character):
        """Update the character configuration for this SessionClient instance.
        
        This updates both the character reference and recreates the coordinator
        with the new character configuration.
        """
        self.character = character
        self.coordinator = BehaviorCoordinator(character)
        logger.info(f"Character configuration updated for session {self.session_id}")

    async def process_user_message(self, user_message: Message):
        if not self._running:
            return

        try:
            history = await self.message_service.get_messages(user_message.session_id)

            conversation_history = self._build_llm_history(history)

            llm_response = await self.llm_client.chat(conversation_history)

            # Handle invalid JSON or empty content - skip processing entirely
            if llm_response.is_invalid_json or llm_response.is_empty_content:
                reason = "invalid_json" if llm_response.is_invalid_json else "empty_content"
                message = (
                    "LLM 返回了非法 JSON，本次不处理"
                    if llm_response.is_invalid_json
                    else "LLM 返回了空内容，本次不处理"
                )
                
                log_entry = unified_logger.warning(
                    f"Skipping LLM response: {reason}",
                    category=LogCategory.LLM,
                    metadata={
                        "session_id": user_message.session_id,
                        "reason": reason,
                        "raw_text_preview": llm_response.raw_text[:200] if llm_response.raw_text else "",
                    },
                )
                await broadcast_log_if_needed(log_entry)
                
                # Send toast notification to frontend
                await self.ws_manager.send_toast(
                    user_message.session_id,
                    message,
                    level="warning",
                )
                return

            # Determine the emotion_map to use
            emotion_map_to_use = llm_response.emotion_map
            
            # If emotion_map is empty, reuse the last emotion state
            if not emotion_map_to_use:
                last_emotion = await self.message_service.get_latest_emotion_state(
                    user_message.session_id
                )
                if last_emotion:
                    emotion_map_to_use = last_emotion
                    log_entry = unified_logger.info(
                        "Reusing last emotion state (LLM returned no emotions)",
                        category=LogCategory.EMOTION,
                        metadata={
                            "session_id": user_message.session_id,
                            "last_emotion": last_emotion,
                        },
                    )
                    await broadcast_log_if_needed(log_entry)
                else:
                    # No previous emotion state exists, use neutral as absolute fallback
                    emotion_map_to_use = {"neutral": "low"}
                    log_entry = unified_logger.info(
                        "No emotion from LLM and no previous state, using neutral fallback",
                        category=LogCategory.EMOTION,
                        metadata={
                            "session_id": user_message.session_id,
                        },
                    )
                    await broadcast_log_if_needed(log_entry)

            # Only update emotion state if we have valid emotions from LLM
            if llm_response.emotion_map:
                log_entry = unified_logger.emotion(
                    emotion_map=llm_response.emotion_map,
                    context=f"User: {user_message.content[:50]}...",
                )
                await broadcast_log_if_needed(log_entry)

                emotion_msg = await self.message_service.set_emotion_state(
                    user_message.session_id, llm_response.emotion_map
                )
                await self._broadcast_message(emotion_msg)
                try:
                    conn_count = (
                        self.ws_manager.get_connection_count(user_message.session_id)
                        if hasattr(self.ws_manager, "get_connection_count")
                        else None
                    )
                    log_entry = unified_logger.info(
                        "Emotion state broadcasted",
                        category=LogCategory.EMOTION,
                        metadata={
                            "session_id": user_message.session_id,
                            "keys": list(llm_response.emotion_map.keys()),
                            "connections": conn_count,
                        },
                    )
                    await broadcast_log_if_needed(log_entry)
                except Exception:
                    pass

            # Use emotion_map_to_use for behavior processing (either new or reused)
            timeline = self.coordinator.process_message(
                llm_response.reply, emotion_map=emotion_map_to_use
            )

            sticker_log_entries = self.coordinator.get_and_clear_log_entries()
            for entry in sticker_log_entries:
                await broadcast_log_if_needed(entry)

            behavior_summary = []
            for action in timeline:
                parts = [f"{action.type}@{action.timestamp:.2f}s"]
                if action.type == "send":
                    preview = (
                        action.text[:30] + "..."
                        if len(action.text) > 30
                        else action.text
                    )
                    parts.append(f"'{preview}'")
                behavior_summary.append(" ".join(parts))

            log_entry = unified_logger.behavior(
                action="Timeline generated",
                details={
                    "actions": behavior_summary,
                    "total": len(timeline),
                    "reply": llm_response.reply,
                },
            )
            await broadcast_log_if_needed(log_entry)

            # Full timeline for debugging (rendered via log metadata).
            full_timeline = []
            for a in timeline:
                full_timeline.append(
                    {
                        "type": getattr(a, "type", None),
                        "timestamp": getattr(a, "timestamp", None),
                        "text": getattr(a, "text", None),
                        "target_id": getattr(a, "target_id", None),
                        "metadata": getattr(a, "metadata", None),
                    }
                )
            log_entry = unified_logger.behavior(
                action="Timeline full",
                details={"timeline": full_timeline},
            )
            await broadcast_log_if_needed(log_entry)

            task = asyncio.create_task(
                self._execute_timeline(timeline, user_message.session_id)
            )
            self._tasks.append(task)

        except Exception as e:
            logger.error(f"Error processing user message: {e}", exc_info=True)
            # Do not inject synthetic assistant messages on failure.
            # Notify frontend via toast and debug logs instead.
            await self.ws_manager.send_toast(
                user_message.session_id,
                "LLM 请求失败，请检查设置和日志。",
                level="error",
            )
            log_entry = unified_logger.error(
                "LLM request failed",
                category=LogCategory.LLM,
                metadata={"exc_info": True, "session_id": user_message.session_id},
            )
            await broadcast_log_if_needed(log_entry)

    async def _execute_timeline(self, timeline: List[PlaybackAction], session_id: str):
        start_time = datetime.now(timezone.utc).timestamp()
        sent_timestamps_by_id: dict[str, float] = {}
        recalled_target_ids: set[str] = set()

        log_entry = unified_logger.info(
            f"Executing timeline: {len(timeline)} actions",
            metadata={"session_id": session_id},
            category=LogCategory.BEHAVIOR,
        )
        await broadcast_log_if_needed(log_entry)

        for action in timeline:
            if not self._running:
                break

            scheduled_time = start_time + action.timestamp
            current_time = datetime.now(timezone.utc).timestamp()
            wait_time = max(0, scheduled_time - current_time)

            if wait_time > 0:
                await asyncio.sleep(wait_time)

            try:
                if action.type == "typing_start":
                    typing_msg = await self.message_service.set_typing_state(
                        session_id, self.user_id, True
                    )
                    await self._broadcast_message(typing_msg)

                elif action.type == "typing_end":
                    typing_msg = await self.message_service.set_typing_state(
                        session_id, self.user_id, False
                    )
                    await self._broadcast_message(typing_msg)

                elif action.type == "send":
                    if action.metadata and action.metadata.get("is_correction") is True:
                        correction_for = action.metadata.get("correction_for")
                        if correction_for and correction_for not in recalled_target_ids:
                            continue

                    messages = await self.message_service.send_message_with_time(
                        session_id=session_id,
                        sender_id=self.user_id,
                        message_type=MessageType.TEXT,
                        content=action.text,
                        metadata=action.metadata,
                        message_id=action.message_id,
                    )
                    for message in messages:
                        await self._broadcast_message(message)
                    if messages:
                        last_msg = messages[-1]
                        if last_msg and last_msg.id and last_msg.timestamp:
                            sent_timestamps_by_id[str(last_msg.id)] = float(
                                last_msg.timestamp
                            )

                elif action.type == "image":
                    sticker_url = f"/api/stickers/{action.text}"
                    messages = await self.message_service.send_message_with_time(
                        session_id=session_id,
                        sender_id=self.user_id,
                        message_type=MessageType.IMAGE,
                        content=sticker_url,
                        metadata=action.metadata,
                        message_id=action.message_id,
                    )
                    for message in messages:
                        await self._broadcast_message(message)
                    if messages:
                        last_msg = messages[-1]
                        if last_msg and last_msg.id and last_msg.timestamp:
                            sent_timestamps_by_id[str(last_msg.id)] = float(
                                last_msg.timestamp
                            )

                elif action.type == "recall":
                    if not action.target_id:
                        continue

                    target_id = str(action.target_id)
                    target_ts = None
                    if action.metadata:
                        target_ts = action.metadata.get("target_timestamp")
                    if not target_ts:
                        target_ts = sent_timestamps_by_id.get(target_id)
                    if not target_ts:
                        original = await self.message_service.get_message(target_id)
                        target_ts = original.timestamp if original else 0

                    recall_msg = await self.message_service.recall_message(
                        session_id=session_id,
                        message_id=target_id,
                        timestamp=float(target_ts or 0),
                        recalled_by=self.user_id,
                    )
                    if recall_msg:
                        recalled_target_ids.add(target_id)
                        await self._broadcast_message(recall_msg)

                elif action.type == "wait":
                    pass

            except Exception as e:
                logger.error(
                    f"Error executing action {action.type}: {e}", exc_info=True
                )

        log_entry = unified_logger.info(
            "Timeline execution completed",
            metadata={"session_id": session_id},
            category=LogCategory.BEHAVIOR,
        )
        await broadcast_log_if_needed(log_entry)

    async def _broadcast_message(self, message: Message):
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
        await self.ws_manager.send_to_conversation(message.session_id, event)

    def _build_llm_history(self, history: List[Message]) -> List[ChatMessage]:
        """
        Build the LLM input messages from DB history.

        Rules:
        - Filter out SYSTEM_TYPING messages.
        - Filter out recalled messages.
        - Keep all 3 roles' messages (system/user/assistant), except the greeting hijack:
          the initial 5 greeting messages (time + hints + "I am ...") are replaced with:
            1) the first system-time message
            2) a synthetic system-hint:
               "你已接受{user_nickname}的好友请求，现在可以开始聊天了。"
        """

        if not history:
            return []

        # Detect the initial greeting block (5 messages created by MessageService.create_session).
        greeting_block = False
        if len(history) >= 5:
            m0, m1, m2, m3, m4 = history[0], history[1], history[2], history[3], history[4]
            greeting_block = (
                m0.sender_id == "system"
                and m0.type == MessageType.SYSTEM_TIME
                and m1.sender_id == "system"
                and m1.type == MessageType.SYSTEM_HINT
                and m2.sender_id == "user"
                and m2.type == MessageType.TEXT
                and (m2.content or "").startswith("我是")
                and m3.sender_id == "assistant"
                and m3.type == MessageType.TEXT
                and (m3.content or "").startswith("我是")
                and m4.sender_id == "system"
                and m4.type == MessageType.SYSTEM_HINT
                and ("打招呼" in (m4.content or "") or "以上" in (m4.content or ""))
            )

        nickname = (self.llm_client.config.user_nickname or "").strip() or "用户"
        synthetic_hint = f"你已接受{nickname}的好友请求，现在可以开始聊天了。"

        out: List[ChatMessage] = []

        start_idx = 0
        if greeting_block:
            # Keep the first time message, then replace the remaining 4 greeting messages.
            time_msg = history[0]
            out.append(
                ChatMessage(
                    role="system",
                    content=self._format_system_time(time_msg.timestamp),
                )
            )
            out.append(ChatMessage(role="system", content=synthetic_hint))
            start_idx = 5

        for msg in history[start_idx:]:
            if msg.is_recalled:
                continue
            if msg.type == MessageType.SYSTEM_TYPING:
                continue

            role: str
            if msg.sender_id == "assistant":
                role = "assistant"
            elif msg.sender_id == "user":
                role = "user"
            else:
                role = "system"

            content = ""
            if role == "system":
                content = self._system_message_to_text(msg)
            else:
                content = self._user_message_to_text(msg)

            if content.strip():
                out.append(ChatMessage(role=role, content=content))

        return out

    def _format_system_time(self, timestamp: float) -> str:
        try:
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone()
            return f"时间：{dt.strftime('%Y-%m-%d %H:%M:%S')}"
        except Exception:
            return "时间："

    def _system_message_to_text(self, msg: Message) -> str:
        if msg.type == MessageType.SYSTEM_TIME:
            return self._format_system_time(msg.timestamp)
        if msg.type == MessageType.SYSTEM_HINT:
            return msg.content or ""
        if msg.type == MessageType.SYSTEM_RECALL:
            return "系统提示：对方撤回了一条消息。"
        if msg.type == MessageType.SYSTEM_EMOTION:
            meta = msg.metadata or {}
            parts = [f"{k}={v}" for k, v in meta.items()]
            return "Emotion state: " + (", ".join(parts) if parts else "neutral")
        # Fallback for other system messages.
        return msg.content or ""

    def _user_message_to_text(self, msg: Message) -> str:
        if msg.type == MessageType.TEXT:
            return msg.content or ""
        if msg.type == MessageType.IMAGE:
            return "[Image]"
        if msg.type == MessageType.VIDEO:
            return "[Video]"
        if msg.type == MessageType.AUDIO:
            return "[Audio]"
        return f"[Unsupported message type: {msg.type}]"
