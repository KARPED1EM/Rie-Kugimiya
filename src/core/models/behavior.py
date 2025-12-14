"""
Behavior system models and constants.
"""
from pydantic import BaseModel, Field
from typing import Any, Dict, Literal, Optional
from enum import Enum


class EmotionState(str, Enum):
    """Emotion states for character behavior."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    EXCITED = "excited"
    SAD = "sad"
    ANGRY = "angry"
    ANXIOUS = "anxious"
    CONFUSED = "confused"


# Emotion multipliers for typo rate (how much emotion affects typing errors)
EMOTION_TYPO_MULTIPLIERS = {
    EmotionState.NEUTRAL: 1.0,
    EmotionState.HAPPY: 1.2,
    EmotionState.EXCITED: 2.0,
    EmotionState.SAD: 0.5,
    EmotionState.ANGRY: 2.3,
    EmotionState.ANXIOUS: 1.3,
    EmotionState.CONFUSED: 0.3,
}

# Emotion multipliers for pause duration (how much emotion affects pauses between segments)
EMOTION_PAUSE_MULTIPLIERS = {
    EmotionState.NEUTRAL: 1.0,
    EmotionState.HAPPY: 0.9,
    EmotionState.EXCITED: 0.8,
    EmotionState.SAD: 1.4,
    EmotionState.ANGRY: 0.7,
    EmotionState.ANXIOUS: 1.1,
    EmotionState.CONFUSED: 1.3,
}


class MessageSegment(BaseModel):
    """A segment of a message for behavior processing."""
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PlaybackAction(BaseModel):
    """An action in the message playback timeline."""
    type: Literal["send", "pause", "recall", "typing_start", "typing_end", "wait", "image"]
    text: Optional[str] = None
    timestamp: float = Field(default=0.0, ge=0.0)
    duration: float = Field(default=0.0, ge=0.0)
    message_id: Optional[str] = None
    target_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
