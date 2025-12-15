from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone
import random
import uuid
from src.core.models.message import (
    Message,
    MessageType,
    ALLOWED_SYSTEM_MESSAGE_TYPES,
)
from src.core.interfaces.repositories import IMessageRepository
from src.core.utils.logger import (
    unified_logger,
    broadcast_log_if_needed,
    LogCategory,
)

# Time message interval in seconds - SINGLE SOURCE OF TRUTH
TIME_MESSAGE_INTERVAL = 300


class MessageService:
    def __init__(self, message_repo: IMessageRepository):
        self.message_repo = message_repo

    async def _ensure_system_invariants(
        self, session_id: str, sender_id: str, message_type: MessageType
    ):
        is_system_sender = sender_id == "system"
        is_system_type = message_type in ALLOWED_SYSTEM_MESSAGE_TYPES
        if is_system_sender != is_system_type:
            log_entry = unified_logger.error(
                "Invalid system message invariant",
                category=LogCategory.MESSAGE,
                metadata={
                    "session_id": session_id,
                    "sender_id": sender_id,
                    "message_type": message_type.value,
                },
            )
            await broadcast_log_if_needed(log_entry)
            raise ValueError(
                "Only System Role may send System-xx messages, "
                "and System Role messages must be System-xx types."
            )

    async def send_message(
        self,
        session_id: str,
        sender_id: str,
        message_type: MessageType,
        content: str,
        metadata: Dict = None,
        message_id: Optional[str] = None,
    ) -> Message:
        messages = await self.send_message_with_time(
            session_id=session_id,
            sender_id=sender_id,
            message_type=message_type,
            content=content,
            metadata=metadata,
            message_id=message_id,
        )
        return messages[-1]

    async def send_message_with_time(
        self,
        session_id: str,
        sender_id: str,
        message_type: MessageType,
        content: str,
        metadata: Dict = None,
        message_id: Optional[str] = None,
    ) -> List[Message]:
        """
        Send a message and, if needed, insert a system-time message before it.
        Returns ordered list: [time_msg?, message].
        """
        metadata = metadata or {}
        timestamp = datetime.now(timezone.utc).timestamp()

        await self._ensure_system_invariants(session_id, sender_id, message_type)

        time_msg = await self._insert_time_message_if_needed(session_id, timestamp)

        if message_id is None:
            message_id = f"msg-{uuid.uuid4().hex[:12]}"
        else:
            message_id = str(message_id).strip() or f"msg-{uuid.uuid4().hex[:12]}"
        message = Message(
            id=message_id,
            session_id=session_id,
            sender_id=sender_id,
            type=message_type,
            content=content,
            metadata=metadata,
            is_recalled=False,
            is_read=False,
            timestamp=timestamp,
        )

        await self.message_repo.create(message)
        await self.set_typing_state(session_id, sender_id, False)

        return [m for m in [time_msg, message] if m is not None]

    async def recall_message(
        self, session_id: str, message_id: str, timestamp: float, recalled_by: str
    ) -> Optional[Message]:
        original = await self.message_repo.get_by_id(message_id)
        if not original:
            log_entry = unified_logger.warning(
                f"Message {message_id} not found for recall",
                category=LogCategory.MESSAGE,
            )
            await broadcast_log_if_needed(log_entry)
            return None

        if abs(original.timestamp - timestamp) > 0.001:
            log_entry = unified_logger.warning(
                f"Timestamp mismatch for message {message_id}",
                category=LogCategory.MESSAGE,
            )
            await broadcast_log_if_needed(log_entry)
            return None

        await self.message_repo.update_recalled_status(message_id, True)

        recall_id = f"recall-{uuid.uuid4().hex[:12]}"
        recall_message = Message(
            id=recall_id,
            session_id=session_id,
            sender_id="system",
            type=MessageType.SYSTEM_RECALL,
            content="",
            metadata={
                "target_message_id": message_id,
                "target_timestamp": timestamp,
                "recalled_by": recalled_by,
            },
            is_recalled=False,
            is_read=False,
            timestamp=datetime.now(timezone.utc).timestamp(),
        )

        await self.message_repo.create(recall_message)
        return recall_message

    async def create_session(
        self, session_id: str, assistant_name: str, user_nickname: Optional[str] = None
    ) -> bool:
        try:
            local_now = datetime.now().astimezone()
            base_time = local_now - timedelta(days=1)
            base_time = base_time.replace(
                hour=random.randint(8, 22),
                minute=random.randint(0, 59),
                second=random.randint(0, 59),
                microsecond=0,
            )
            base_timestamp = base_time.timestamp()

            time_msg = Message(
                id=f"time-{uuid.uuid4().hex[:12]}",
                session_id=session_id,
                sender_id="system",
                type=MessageType.SYSTEM_TIME,
                content="",
                metadata={},
                is_recalled=False,
                is_read=False,
                timestamp=base_timestamp,
            )
            await self.message_repo.create(time_msg)

            hint_msg = Message(
                id=f"hint-{uuid.uuid4().hex[:12]}",
                session_id=session_id,
                sender_id="system",
                type=MessageType.SYSTEM_HINT,
                content=f"你已添加了{assistant_name}，现在可以开始聊天了。",
                metadata={},
                is_recalled=False,
                is_read=True,
                timestamp=base_timestamp + 1,
            )
            await self.message_repo.create(hint_msg)

            user_nickname = user_nickname or "用户"
            greeting_msg = Message(
                id=f"greeting-{uuid.uuid4().hex[:12]}",
                session_id=session_id,
                sender_id="user",
                type=MessageType.TEXT,
                content=f"我是{user_nickname}",
                metadata={},
                is_recalled=False,
                is_read=True,
                timestamp=base_timestamp + 2,
            )
            await self.message_repo.create(greeting_msg)

            greeting_msg = Message(
                id=f"greeting-{uuid.uuid4().hex[:12]}",
                session_id=session_id,
                sender_id="assistant",
                type=MessageType.TEXT,
                content=f"我是{assistant_name}",
                metadata={},
                is_recalled=False,
                is_read=True,
                timestamp=base_timestamp + 3,
            )
            await self.message_repo.create(greeting_msg)

            hint_msg = Message(
                id=f"hint-{uuid.uuid4().hex[:12]}",
                session_id=session_id,
                sender_id="system",
                type=MessageType.SYSTEM_HINT,
                content="以上是打招呼的消息",
                metadata={},
                is_recalled=False,
                is_read=True,
                timestamp=base_timestamp + 4,
            )
            await self.message_repo.create(hint_msg)

            return True
        except Exception as e:
            log_entry = unified_logger.error(
                f"Error creating session: {e}",
                category=LogCategory.MESSAGE,
                metadata={"exc_info": True},
            )
            await broadcast_log_if_needed(log_entry)
            return False

    async def delete_session(self, session_id: str) -> bool:
        return await self.message_repo.delete_by_session(session_id)

    async def get_message(self, message_id: str) -> Optional[Message]:
        return await self.message_repo.get_by_id(message_id)

    async def get_messages(
        self, session_id: str, after_timestamp: Optional[float] = None
    ) -> List[Message]:
        return await self.message_repo.get_by_session(session_id, after_timestamp)

    async def mark_read_until(self, session_id: str, until_timestamp: float) -> float:
        """
        Mark all non-recalled messages with timestamp <= until_timestamp as read.
        Returns the new last-read timestamp.
        """
        if until_timestamp <= 0:
            return await self.message_repo.get_last_read_timestamp(session_id)

        await self.message_repo.update_read_status_until(
            session_id=session_id, until_timestamp=until_timestamp, is_read=True
        )
        return await self.message_repo.get_last_read_timestamp(session_id)

    async def set_typing_state(
        self, session_id: str, user_id: str, is_typing: bool
    ) -> Message:
        typing_id = f"typing-{uuid.uuid4().hex[:12]}"
        typing_msg = Message(
            id=typing_id,
            session_id=session_id,
            sender_id="system",
            type=MessageType.SYSTEM_TYPING,
            content="",
            metadata={"user_id": user_id, "is_typing": is_typing},
            is_recalled=False,
            is_read=False,
            timestamp=datetime.now(timezone.utc).timestamp(),
        )

        await self.message_repo.create(typing_msg)
        await self._cleanup_old_state_messages(session_id, MessageType.SYSTEM_TYPING)

        return typing_msg

    async def set_emotion_state(
        self, session_id: str, emotion_map: Dict[str, str]
    ) -> Message:
        emotion_id = f"emotion-{uuid.uuid4().hex[:12]}"
        emotion_msg = Message(
            id=emotion_id,
            session_id=session_id,
            sender_id="system",
            type=MessageType.SYSTEM_EMOTION,
            content="",
            metadata=emotion_map,
            is_recalled=False,
            is_read=False,
            timestamp=datetime.now(timezone.utc).timestamp(),
        )

        await self.message_repo.create(emotion_msg)
        await self._cleanup_old_state_messages(session_id, MessageType.SYSTEM_EMOTION)

        return emotion_msg

    async def get_latest_emotion_state(
        self, session_id: str
    ) -> Optional[Dict[str, str]]:
        messages = await self.message_repo.get_by_session(session_id)
        for msg in reversed(messages):
            if msg.type == MessageType.SYSTEM_EMOTION:
                return msg.metadata
        return None

    async def get_latest_typing_state(self, session_id: str, user_id: str) -> bool:
        messages = await self.message_repo.get_by_session(session_id)
        for msg in reversed(messages):
            if (
                msg.type == MessageType.SYSTEM_TYPING
                and msg.metadata.get("user_id") == user_id
            ):
                return msg.metadata.get("is_typing", False)
        return False

    async def is_session_blocked(self, session_id: str) -> bool:
        """
        Check if a session is in blocked state.
        A session is blocked if there's any SYSTEM_BLOCKED message in history.
        """
        messages = await self.message_repo.get_by_session(session_id)
        for msg in messages:
            if msg.type == MessageType.SYSTEM_BLOCKED:
                return True
        return False

    async def _insert_time_message_if_needed(
        self, session_id: str, reference_timestamp: float
    ) -> Optional[Message]:
        messages = await self.message_repo.get_by_session(session_id)
        if not messages:
            return None

        last_message = messages[-1]
        time_gap = reference_timestamp - last_message.timestamp

        if time_gap > TIME_MESSAGE_INTERVAL:
            time_id = f"time-{uuid.uuid4().hex[:12]}"
            time_msg = Message(
                id=time_id,
                session_id=session_id,
                sender_id="system",
                type=MessageType.SYSTEM_TIME,
                content="",
                metadata={},
                is_recalled=False,
                is_read=False,
                # Slightly earlier to ensure ordering before the real message.
                timestamp=reference_timestamp - 0.001,
            )

            await self.message_repo.create(time_msg)
            return time_msg

        return None

    async def _cleanup_old_state_messages(
        self, session_id: str, message_type: MessageType
    ):
        messages = await self.message_repo.get_by_session(session_id)

        state_messages = [msg for msg in messages if msg.type == message_type]

        if len(state_messages) <= 1:
            return

        state_messages.sort(key=lambda m: m.timestamp)

        for old_msg in state_messages[:-1]:
            await self.message_repo.update_recalled_status(old_msg.id, True)
