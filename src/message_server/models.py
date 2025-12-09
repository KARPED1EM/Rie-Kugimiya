from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class MessageType(str, Enum):
    TEXT = "text"
    RECALL_EVENT = "recall_event"  # 撤回事件（新消息）
    SYSTEM = "system"


class Message(BaseModel):
    id: str
    conversation_id: str
    sender_id: str
    type: MessageType = MessageType.TEXT
    content: str
    timestamp: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class TypingState(BaseModel):
    user_id: str
    conversation_id: str
    is_typing: bool
    timestamp: float


class WSMessage(BaseModel):
    type: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[float] = None

    def model_dump(self, **kwargs):
        result = super().model_dump(**kwargs)
        if result.get('timestamp') is None:
            result['timestamp'] = datetime.now().timestamp()
        return result
