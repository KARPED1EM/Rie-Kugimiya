from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    SYSTEM_RECALL = "system-recall"
    SYSTEM_TIME = "system-time"
    SYSTEM_HINT = "system-hint"
    SYSTEM_EMOTION = "system-emotion"
    SYSTEM_TYPING = "system-typing"
    SYSTEM_TOOL = "system-tool"


# System Role messages that are allowed to enter the session stream.
ALLOWED_SYSTEM_MESSAGE_TYPES = {
    MessageType.SYSTEM_RECALL,
    MessageType.SYSTEM_TIME,
    MessageType.SYSTEM_HINT,
    MessageType.SYSTEM_EMOTION,
    MessageType.SYSTEM_TYPING,
    MessageType.SYSTEM_TOOL,
}


class Message(BaseModel):
    id: str
    session_id: str
    sender_id: str
    type: MessageType = MessageType.TEXT
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_recalled: bool = False
    is_read: bool = False
    timestamp: float

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
