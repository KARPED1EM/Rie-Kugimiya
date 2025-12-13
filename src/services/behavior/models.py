from pydantic import BaseModel, Field
from typing import Any, Dict, Literal, Optional
from enum import Enum


class EmotionState(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    EXCITED = "excited"
    SAD = "sad"
    ANGRY = "angry"
    ANXIOUS = "anxious"
    CONFUSED = "confused"


class MessageSegment(BaseModel):
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PlaybackAction(BaseModel):
    type: Literal["send", "pause", "recall", "typing_start", "typing_end", "wait", "image"]
    text: Optional[str] = None
    timestamp: float = Field(default=0.0, ge=0.0)
    duration: float = Field(default=0.0, ge=0.0)
    message_id: Optional[str] = None
    target_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BehaviorConfig(BaseModel):
    enable_segmentation: bool = True
    max_segment_length: int = 50
    min_pause_duration: float = 0.8
    max_pause_duration: float = 6.0

    enable_typo: bool = True
    base_typo_rate: float = 0.05
    emotion_typo_multiplier: dict = Field(
        default_factory=lambda: {
            EmotionState.NEUTRAL: 1.0,
            EmotionState.HAPPY: 1.2,
            EmotionState.EXCITED: 2.0,
            EmotionState.SAD: 0.5,
            EmotionState.ANGRY: 2.3,
            EmotionState.ANXIOUS: 1.3,
            EmotionState.CONFUSED: 0.3,
        }
    )

    enable_recall: bool = True
    typo_recall_rate: float = 0.75
    recall_delay: float = 2.0
    retype_delay: float = 2.5

    enable_emotion_fetch: bool = True

    emotion_pause_multiplier: dict = Field(
        default_factory=lambda: {
            EmotionState.NEUTRAL: 1.0,
            EmotionState.HAPPY: 0.9,
            EmotionState.EXCITED: 0.8,
            EmotionState.SAD: 1.4,
            EmotionState.ANGRY: 0.7,
            EmotionState.ANXIOUS: 1.1,
            EmotionState.CONFUSED: 1.3,
        }
    )


class TimelineConfig(BaseModel):
    hesitation_probability: float = 0.15
    hesitation_cycles_min: int = 1
    hesitation_cycles_max: int = 2
    hesitation_duration_min: int = 1500
    hesitation_duration_max: int = 5000
    hesitation_gap_min: int = 500
    hesitation_gap_max: int = 2000

    typing_lead_time_threshold_1: int = 6
    typing_lead_time_1: int = 1200
    typing_lead_time_threshold_2: int = 15
    typing_lead_time_2: int = 2000
    typing_lead_time_threshold_3: int = 28
    typing_lead_time_3: int = 3800
    typing_lead_time_threshold_4: int = 34
    typing_lead_time_4: int = 6000
    typing_lead_time_threshold_5: int = 50
    typing_lead_time_5: int = 8800
    typing_lead_time_default: int = 2500

    entry_delay_min: int = 200
    entry_delay_max: int = 2000

    initial_delay_weight_1: float = 0.45
    initial_delay_range_1_min: int = 3
    initial_delay_range_1_max: int = 4
    initial_delay_weight_2: float = 0.75
    initial_delay_range_2_min: int = 4
    initial_delay_range_2_max: int = 6
    initial_delay_weight_3: float = 0.93
    initial_delay_range_3_min: int = 6
    initial_delay_range_3_max: int = 7
    initial_delay_range_4_min: int = 8
    initial_delay_range_4_max: int = 9
