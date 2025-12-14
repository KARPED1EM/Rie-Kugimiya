from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class Character(BaseModel):
    id: str
    name: str
    avatar: str
    persona: str
    is_builtin: bool = False

    # Timeline module - hesitation behavior
    timeline_hesitation_probability: float = 0.15
    timeline_hesitation_cycles_min: int = 1
    timeline_hesitation_cycles_max: int = 2
    timeline_hesitation_duration_min: int = 1500
    timeline_hesitation_duration_max: int = 5000
    timeline_hesitation_gap_min: int = 500
    timeline_hesitation_gap_max: int = 2000

    # Timeline module - typing lead time
    timeline_typing_lead_time_threshold_1: int = 6
    timeline_typing_lead_time_1: int = 1200
    timeline_typing_lead_time_threshold_2: int = 15
    timeline_typing_lead_time_2: int = 2000
    timeline_typing_lead_time_threshold_3: int = 28
    timeline_typing_lead_time_3: int = 3800
    timeline_typing_lead_time_threshold_4: int = 34
    timeline_typing_lead_time_4: int = 6000
    timeline_typing_lead_time_threshold_5: int = 50
    timeline_typing_lead_time_5: int = 8800
    timeline_typing_lead_time_default: int = 2500

    # Timeline module - entry delay
    timeline_entry_delay_min: int = 200
    timeline_entry_delay_max: int = 2000

    # Timeline module - initial delay
    timeline_initial_delay_weight_1: float = 0.45
    timeline_initial_delay_range_1_min: int = 3
    timeline_initial_delay_range_1_max: int = 4
    timeline_initial_delay_weight_2: float = 0.75
    timeline_initial_delay_range_2_min: int = 4
    timeline_initial_delay_range_2_max: int = 6
    timeline_initial_delay_weight_3: float = 0.93
    timeline_initial_delay_range_3_min: int = 6
    timeline_initial_delay_range_3_max: int = 7
    timeline_initial_delay_range_4_min: int = 8
    timeline_initial_delay_range_4_max: int = 9

    # Segmenter module
    segmenter_enable: bool = True
    segmenter_max_length: int = 50

    # Typo module
    typo_enable: bool = True
    typo_base_rate: float = 0.05
    typo_recall_rate: float = 0.75

    # Recall module
    recall_enable: bool = True
    recall_delay: float = 2.0
    recall_retype_delay: float = 2.5

    # Pause module
    pause_min_duration: float = 0.8
    pause_max_duration: float = 6.0

    # Sticker module
    sticker_packs: List[str] = Field(default_factory=list)
    sticker_send_probability: float = 0.4
    sticker_confidence_threshold_positive: float = 0.6
    sticker_confidence_threshold_neutral: float = 0.7
    sticker_confidence_threshold_negative: float = 0.8

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
