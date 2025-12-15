# Core domain schemas (used across layers)
from pydantic import BaseModel, Field
from typing import Literal, Optional


class LLMConfig(BaseModel):
    """LLM configuration - core domain model"""
    # Protocol-based configuration (replaces provider-based)
    protocol: Optional[Literal["completions", "responses", "messages"]] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)  # Optional, don't send if empty
    max_tokens: int = 1000  # Required, default 1000
    persona: Optional[str] = None  # Will be populated from config defaults
    character_name: Optional[str] = None  # Display only, not used in prompts
    user_nickname: Optional[str] = None  # User's WeChat nickname


class ChatMessage(BaseModel):
    """Chat message - core domain model"""
    role: Literal["user", "assistant", "system"]
    content: str
