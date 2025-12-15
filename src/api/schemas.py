# Pydantic schemas for API layer
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

# Import core domain schemas
from src.core.schemas import LLMConfig, ChatMessage


class BehaviorSettings(BaseModel):
    """Settings for message behavior engine"""

    enable_segmentation: Optional[bool] = None
    enable_typo: Optional[bool] = None
    enable_recall: Optional[bool] = None
    enable_emotion_detection: Optional[bool] = None
    max_segment_length: Optional[int] = Field(default=None, gt=0)
    min_pause_duration: Optional[float] = Field(default=None, ge=0.0)
    max_pause_duration: Optional[float] = Field(default=None, ge=0.0)
    base_typo_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    typo_recall_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ChatRequest(BaseModel):
    llm_config: LLMConfig
    messages: List[ChatMessage]
    character_name: Optional[str] = None
    conversation_id: Optional[str] = None
    behavior_settings: Optional[BehaviorSettings] = None


class MessageAction(BaseModel):
    """
    A single playback action (send, recall, pause)
    """

    type: Literal["send", "recall", "pause"]
    text: Optional[str] = None  # Text content for 'send' actions
    duration: Optional[float] = Field(
        default=None, ge=0.0, description="Duration in seconds for this action"
    )
    message_id: Optional[str] = Field(
        default=None, description="Unique id for send actions"
    )
    target_id: Optional[str] = Field(
        default=None, description="Target message id for recall actions"
    )
    metadata: Optional[dict] = Field(
        default=None, description="Additional metadata (e.g., emotion, has_typo)"
    )


class ChatResponse(BaseModel):
    actions: List[MessageAction]
    raw_response: str
    metadata: Optional[dict] = Field(
        default=None, description="Response metadata (e.g., detected emotion)"
    )
