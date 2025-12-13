from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class Character(BaseModel):
    id: str
    name: str
    avatar: str
    persona: str
    is_builtin: bool = False

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

    enable_segmentation: bool = True
    enable_typo: bool = True
    enable_recall: bool = True
    enable_emotion_detection: bool = True

    max_segment_length: int = 50
    min_pause_duration: float = 0.8
    max_pause_duration: float = 6.0

    base_typo_rate: float = 0.05
    typo_recall_rate: float = 0.75
    recall_delay: float = 2.0
    retype_delay: float = 2.5

    sticker_packs: List[str] = Field(default_factory=list)
    sticker_send_probability: float = 0.4
    sticker_confidence_threshold_positive: float = 0.6
    sticker_confidence_threshold_neutral: float = 0.7
    sticker_confidence_threshold_negative: float = 0.8

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
