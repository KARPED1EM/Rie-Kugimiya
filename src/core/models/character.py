from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from src.core.models.behavior_config import BehaviorConfig


class Character(BaseModel):
    """
    Character model - core character information only (SRP compliant)
    
    This model IS the single source of truth for character defaults.
    All default values are defined in the nested BehaviorConfig model.
    No separate config classes needed - models define structure AND defaults.
    """
    id: str
    name: str
    avatar: str
    persona: str
    is_builtin: bool = False
    sticker_packs: List[str] = Field(default_factory=list)
    
    # Behavior configuration - aggregated from separate config classes
    behavior: BehaviorConfig = Field(default_factory=BehaviorConfig)
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Backward compatibility properties - deprecated, use behavior.* instead
    @property
    def timeline_hesitation_probability(self) -> float:
        return self.behavior.timeline.hesitation_probability
    
    @property
    def timeline_hesitation_cycles_min(self) -> int:
        return self.behavior.timeline.hesitation_cycles_min
    
    @property
    def timeline_hesitation_cycles_max(self) -> int:
        return self.behavior.timeline.hesitation_cycles_max
    
    @property
    def timeline_hesitation_duration_min(self) -> int:
        return self.behavior.timeline.hesitation_duration_min
    
    @property
    def timeline_hesitation_duration_max(self) -> int:
        return self.behavior.timeline.hesitation_duration_max
    
    @property
    def timeline_hesitation_gap_min(self) -> int:
        return self.behavior.timeline.hesitation_gap_min
    
    @property
    def timeline_hesitation_gap_max(self) -> int:
        return self.behavior.timeline.hesitation_gap_max
    
    @property
    def timeline_typing_lead_time_threshold_1(self) -> int:
        return self.behavior.timeline.typing_lead_time_threshold_1
    
    @property
    def timeline_typing_lead_time_1(self) -> int:
        return self.behavior.timeline.typing_lead_time_1
    
    @property
    def timeline_typing_lead_time_threshold_2(self) -> int:
        return self.behavior.timeline.typing_lead_time_threshold_2
    
    @property
    def timeline_typing_lead_time_2(self) -> int:
        return self.behavior.timeline.typing_lead_time_2
    
    @property
    def timeline_typing_lead_time_threshold_3(self) -> int:
        return self.behavior.timeline.typing_lead_time_threshold_3
    
    @property
    def timeline_typing_lead_time_3(self) -> int:
        return self.behavior.timeline.typing_lead_time_3
    
    @property
    def timeline_typing_lead_time_threshold_4(self) -> int:
        return self.behavior.timeline.typing_lead_time_threshold_4
    
    @property
    def timeline_typing_lead_time_4(self) -> int:
        return self.behavior.timeline.typing_lead_time_4
    
    @property
    def timeline_typing_lead_time_threshold_5(self) -> int:
        return self.behavior.timeline.typing_lead_time_threshold_5
    
    @property
    def timeline_typing_lead_time_5(self) -> int:
        return self.behavior.timeline.typing_lead_time_5
    
    @property
    def timeline_typing_lead_time_default(self) -> int:
        return self.behavior.timeline.typing_lead_time_default
    
    @property
    def timeline_entry_delay_min(self) -> int:
        return self.behavior.timeline.entry_delay_min
    
    @property
    def timeline_entry_delay_max(self) -> int:
        return self.behavior.timeline.entry_delay_max
    
    @property
    def timeline_initial_delay_weight_1(self) -> float:
        return self.behavior.timeline.initial_delay_weight_1
    
    @property
    def timeline_initial_delay_range_1_min(self) -> int:
        return self.behavior.timeline.initial_delay_range_1_min
    
    @property
    def timeline_initial_delay_range_1_max(self) -> int:
        return self.behavior.timeline.initial_delay_range_1_max
    
    @property
    def timeline_initial_delay_weight_2(self) -> float:
        return self.behavior.timeline.initial_delay_weight_2
    
    @property
    def timeline_initial_delay_range_2_min(self) -> int:
        return self.behavior.timeline.initial_delay_range_2_min
    
    @property
    def timeline_initial_delay_range_2_max(self) -> int:
        return self.behavior.timeline.initial_delay_range_2_max
    
    @property
    def timeline_initial_delay_weight_3(self) -> float:
        return self.behavior.timeline.initial_delay_weight_3
    
    @property
    def timeline_initial_delay_range_3_min(self) -> int:
        return self.behavior.timeline.initial_delay_range_3_min
    
    @property
    def timeline_initial_delay_range_3_max(self) -> int:
        return self.behavior.timeline.initial_delay_range_3_max
    
    @property
    def timeline_initial_delay_range_4_min(self) -> int:
        return self.behavior.timeline.initial_delay_range_4_min
    
    @property
    def timeline_initial_delay_range_4_max(self) -> int:
        return self.behavior.timeline.initial_delay_range_4_max
    
    @property
    def segmenter_enable(self) -> bool:
        return self.behavior.segmenter.enable
    
    @property
    def segmenter_max_length(self) -> int:
        return self.behavior.segmenter.max_length
    
    @property
    def typo_enable(self) -> bool:
        return self.behavior.typo.enable
    
    @property
    def typo_base_rate(self) -> float:
        return self.behavior.typo.base_rate
    
    @property
    def typo_recall_rate(self) -> float:
        return self.behavior.typo.recall_rate
    
    @property
    def recall_enable(self) -> bool:
        return self.behavior.recall.enable
    
    @property
    def recall_delay(self) -> float:
        return self.behavior.recall.delay
    
    @property
    def recall_retype_delay(self) -> float:
        return self.behavior.recall.retype_delay
    
    @property
    def pause_min_duration(self) -> float:
        return self.behavior.pause.min_duration
    
    @property
    def pause_max_duration(self) -> float:
        return self.behavior.pause.max_duration
    
    @property
    def sticker_send_probability(self) -> float:
        return self.behavior.sticker.send_probability
    
    @property
    def sticker_confidence_threshold_positive(self) -> float:
        return self.behavior.sticker.confidence_threshold_positive
    
    @property
    def sticker_confidence_threshold_neutral(self) -> float:
        return self.behavior.sticker.confidence_threshold_neutral
    
    @property
    def sticker_confidence_threshold_negative(self) -> float:
        return self.behavior.sticker.confidence_threshold_negative
