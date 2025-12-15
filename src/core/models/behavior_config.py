"""
Behavior configuration models - separated from Character for SRP compliance

These models ARE the single source of truth for all behavior defaults.
No separate defaults.py file needed - defaults are defined directly in model fields.
Infrastructure layer (database) does NOT define defaults - only domain models do.
"""
from pydantic import BaseModel


class TimelineConfig(BaseModel):
    """Timeline behavior configuration - SINGLE SOURCE OF TRUTH for timeline defaults"""
    # Hesitation behavior
    hesitation_probability: float = 0.15
    hesitation_cycles_min: int = 1
    hesitation_cycles_max: int = 3
    hesitation_duration_min: int = 1500
    hesitation_duration_max: int = 5000
    hesitation_gap_min: int = 500
    hesitation_gap_max: int = 2000
    
    # Typing lead time
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
    
    # Entry delay
    entry_delay_min: int = 200
    entry_delay_max: int = 2000
    
    # Initial delay
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


class SegmenterConfig(BaseModel):
    """Text segmentation configuration - SINGLE SOURCE OF TRUTH for segmenter defaults"""
    enable: bool = True
    max_length: int = 50


class TypoConfig(BaseModel):
    """Typo injection configuration - SINGLE SOURCE OF TRUTH for typo defaults"""
    enable: bool = True
    base_rate: float = 0.05
    recall_rate: float = 0.75


class RecallConfig(BaseModel):
    """Message recall configuration - SINGLE SOURCE OF TRUTH for recall defaults"""
    enable: bool = True
    delay: float = 2.0
    retype_delay: float = 2.5


class PauseConfig(BaseModel):
    """Pause behavior configuration - SINGLE SOURCE OF TRUTH for pause defaults"""
    min_duration: float = 0.8
    max_duration: float = 6.0


class StickerConfig(BaseModel):
    """Sticker sending configuration - SINGLE SOURCE OF TRUTH for sticker defaults"""
    send_probability: float = 0.4
    confidence_threshold_positive: float = 0.6
    confidence_threshold_neutral: float = 0.7
    confidence_threshold_negative: float = 0.8


class BehaviorConfig(BaseModel):
    """Complete behavior configuration - aggregates all behavior modules"""
    timeline: TimelineConfig = TimelineConfig()
    segmenter: SegmenterConfig = SegmenterConfig()
    typo: TypoConfig = TypoConfig()
    recall: RecallConfig = RecallConfig()
    pause: PauseConfig = PauseConfig()
    sticker: StickerConfig = StickerConfig()
