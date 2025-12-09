from typing import Dict, List, Optional
from datetime import datetime
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

    async def recall_message(self, message_id: str, conversation_id: str) -> bool:
        return self.db.recall_message(message_id, conversation_id)

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

    def create_recall_event(self, message_id: str, conversation_id: str) -> WSMessage:
        return WSMessage(
            type="recall",
            data={
                "message_id": message_id,
                "conversation_id": conversation_id
            },
            timestamp=datetime.now().timestamp()
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
