from typing import Dict, List, Optional
from datetime import datetime, timedelta
import random
import uuid
from .database import MessageDatabase
from .models import Message, MessageType, TypingState, WSMessage


class MessageService:
    def __init__(self, db_path: str = None):
        self.db = MessageDatabase(db_path)
        self.typing_states: Dict[str, TypingState] = {}

    async def save_message(self, message: Message) -> Message:
        self.db.save_message(message)
        return message

    async def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        after_timestamp: Optional[float] = None
    ) -> List[Message]:
        return self.db.get_messages(conversation_id, limit, after_timestamp)

    async def recall_message(
        self,
        message_id: str,
        conversation_id: str,
        recalled_by: str
    ) -> Optional[Message]:
        """
        撤回消息：创建一个新的recall_event消息

        Args:
            message_id: 要撤回的消息ID
            conversation_id: 会话ID
            recalled_by: 撤回者的用户ID

        Returns:
            新创建的recall_event消息，如果原消息不存在则返回None
        """
        # 验证原消息存在
        original_message = self.db.get_message_by_id(message_id)
        if not original_message:
            return None

        # 创建撤回事件消息
        import uuid
        recall_event = Message(
            id=f"recall-{uuid.uuid4().hex[:8]}",
            conversation_id=conversation_id,
            sender_id="system",
            type=MessageType.RECALL_EVENT,
            content="",
            timestamp=datetime.now().timestamp(),
            metadata={
                "target_message_id": message_id,
                "recalled_by": recalled_by,
                "original_sender": original_message.sender_id
            }
        )

        # 保存撤回事件
        self.db.save_message(recall_event)
        return recall_event

    async def clear_conversation(self, conversation_id: str) -> bool:
        return self.db.clear_conversation(conversation_id)

    async def set_typing_state(self, typing_state: TypingState):
        key = f"{typing_state.conversation_id}:{typing_state.user_id}"
        if typing_state.is_typing:
            self.typing_states[key] = typing_state
        else:
            self.typing_states.pop(key, None)

    async def get_typing_states(self, conversation_id: str) -> List[TypingState]:
        return [
            state for state in self.typing_states.values()
            if state.conversation_id == conversation_id and state.is_typing
        ]

    async def clear_user_typing_state(self, user_id: str, conversation_id: str):
        key = f"{conversation_id}:{user_id}"
        self.typing_states.pop(key, None)

    def create_message_event(self, message: Message) -> WSMessage:
        return WSMessage(
            type="message",
            data={
                "id": message.id,
                "conversation_id": message.conversation_id,
                "sender_id": message.sender_id,
                "type": message.type,
                "content": message.content,
                "timestamp": message.timestamp,
                "metadata": message.metadata
            },
            timestamp=message.timestamp
        )

    def create_typing_event(self, typing_state: TypingState) -> WSMessage:
        return WSMessage(
            type="typing",
            data={
                "user_id": typing_state.user_id,
                "conversation_id": typing_state.conversation_id,
                "is_typing": typing_state.is_typing
            },
            timestamp=typing_state.timestamp
        )

    def create_clear_event(self, conversation_id: str) -> WSMessage:
        return WSMessage(
            type="clear",
            data={
                "conversation_id": conversation_id
            },
            timestamp=datetime.now().timestamp()
        )

    def create_history_event(self, messages: List[Message]) -> WSMessage:
        return WSMessage(
            type="history",
            data={
                "messages": [
                    {
                        "id": msg.id,
                        "conversation_id": msg.conversation_id,
                        "sender_id": msg.sender_id,
                        "type": msg.type,
                        "content": msg.content,
                        "timestamp": msg.timestamp,
                        "metadata": msg.metadata
                    }
                    for msg in messages
                ]
            },
            timestamp=datetime.now().timestamp()
        )

    async def ensure_greeting_messages(
        self,
        conversation_id: str,
        assistant_name: str = "Rin",
        user_name: str = "鲨鲨"
    ) -> bool:
        """
        确保对话开头有打招呼消息。
        只在对话为空或没有打招呼标记时创建。

        Args:
            conversation_id: 会话ID
            assistant_name: 助手名称
            user_name: 用户名称

        Returns:
            是否创建了新的打招呼消息
        """
        # 获取所有消息
        messages = await self.get_messages(conversation_id)

        # 如果已经有消息，不再创建打招呼消息
        # 只在对话完全为空时创建打招呼消息
        if messages:
            return False  # 已经有消息，不需要创建打招呼

        # 生成昨天的随机时间戳（昨天的00:00到23:59之间）
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        # 设置为昨天的开始时间
        yesterday_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        # 随机选择昨天的某个时间点（8:00到22:00之间）
        random_hour = random.randint(8, 22)
        random_minute = random.randint(0, 59)
        random_second = random.randint(0, 59)
        base_time = yesterday_start.replace(
            hour=random_hour,
            minute=random_minute,
            second=random_second
        )
        base_timestamp = base_time.timestamp()

        # 创建4条打招呼消息（时间提示由前端自动生成）
        greeting_messages = []

        # 1. 添加好友提示（前端会自动在第一条消息前显示时间）
        add_friend_msg = Message(
            id=f"greeting-add-{uuid.uuid4().hex[:8]}",
            conversation_id=conversation_id,
            sender_id="system",
            type=MessageType.TEXT,
            content=f"你已添加了{assistant_name}，现在可以开始聊天了。",
            timestamp=base_timestamp,
            metadata={"is_greeting": True, "greeting_type": "add_friend"}
        )
        greeting_messages.append(add_friend_msg)

        # 2. 用户打招呼 (延后1秒)
        user_greeting = Message(
            id=f"greeting-user-{uuid.uuid4().hex[:8]}",
            conversation_id=conversation_id,
            sender_id="user",
            type=MessageType.TEXT,
            content=f"我是{user_name}",
            timestamp=base_timestamp + 1,
            metadata={"is_greeting": True, "greeting_type": "user_intro"}
        )
        greeting_messages.append(user_greeting)

        # 3. 助手打招呼 (延后2秒)
        assistant_greeting = Message(
            id=f"greeting-assistant-{uuid.uuid4().hex[:8]}",
            conversation_id=conversation_id,
            sender_id="rin",
            type=MessageType.TEXT,
            content=f"我是{assistant_name}",
            timestamp=base_timestamp + 2,
            metadata={"is_greeting": True, "greeting_type": "assistant_intro"}
        )
        greeting_messages.append(assistant_greeting)

        # 4. 结束提示 (延后3秒)
        end_msg = Message(
            id=f"greeting-end-{uuid.uuid4().hex[:8]}",
            conversation_id=conversation_id,
            sender_id="system",
            type=MessageType.TEXT,
            content="以上是打招呼的消息",
            timestamp=base_timestamp + 3,
            metadata={"is_greeting": True, "greeting_type": "end"}
        )
        greeting_messages.append(end_msg)

        # 保存所有打招呼消息到数据库
        for msg in greeting_messages:
            self.db.save_message(msg)

        return True
