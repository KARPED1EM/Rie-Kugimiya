# Pydantic schemas for API
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class LLMConfig(BaseModel):
    provider: Literal["openai", "anthropic", "deepseek", "custom"] = "openai"
    api_key: str
    base_url: Optional[str] = None
    model: str = "gpt-3.5-turbo"
    persona: str = "You are a helpful assistant."  # Character personality and behavior

class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

class BehaviorSettings(BaseModel):
    """Settings for message behavior engine"""
    enable_segmentation: bool = True
    enable_typo: bool = True
    enable_recall: bool = True
    enable_emotion_detection: bool = True
    max_segment_length: int = Field(default=60, gt=0)
    min_pause_duration: float = Field(default=0.4, ge=0.0)
    max_pause_duration: float = Field(default=2.5, ge=0.0)
    base_typo_rate: float = Field(default=0.08, ge=0.0, le=1.0)
    typo_recall_rate: float = Field(default=0.4, ge=0.0, le=1.0)

class ChatRequest(BaseModel):
    llm_config: LLMConfig
    messages: List[ChatMessage]
    character_name: str = "Rin"
    conversation_id: str = "default"
    behavior_settings: Optional[BehaviorSettings] = None

class MessageAction(BaseModel):
    """
    A single playback action (send, recall, pause)
    """
    type: Literal["send", "recall", "pause"]
    text: Optional[str] = None  # Text content for 'send' actions
    duration: float = Field(default=0.0, ge=0.0, description="Duration in seconds for this action")
    message_id: Optional[str] = Field(default=None, description="Unique id for send actions")
    target_id: Optional[str] = Field(default=None, description="Target message id for recall actions")
    metadata: Optional[dict] = Field(default=None, description="Additional metadata (e.g., emotion, has_typo)")

class ChatResponse(BaseModel):
    actions: List[MessageAction]
    raw_response: str
    metadata: Optional[dict] = Field(default=None, description="Response metadata (e.g., detected emotion)")
