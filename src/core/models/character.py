from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Any, Dict
from datetime import datetime
from src.core.models.behavior import BehaviorConfig


class Character(BaseModel):
    """
    Character model - core character information only (SRP compliant)
    
    This model IS the single source of truth for character defaults.
    All default values are defined in the nested BehaviorConfig model.
    No separate config classes needed - models define structure AND defaults.
    
    Accepts both nested (behavior.timeline.field) and flattened (timeline_field) formats
    for backward compatibility with database and API layers.
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
    
    @model_validator(mode='before')
    @classmethod
    def map_flattened_fields(cls, data: Any) -> Any:
        """
        Transform flattened behavior fields (e.g., timeline_hesitation_probability)
        into nested structure (behavior.timeline.hesitation_probability).
        
        This enables backward compatibility with the database layer and API
        that use flattened field names.
        """
        if not isinstance(data, dict):
            return data
        
        # Extract existing behavior dict if present
        behavior_dict = {}
        if 'behavior' in data:
            existing_behavior = data['behavior']
            if isinstance(existing_behavior, BehaviorConfig):
                # Convert BehaviorConfig instance to dict
                behavior_dict = existing_behavior.model_dump()
            elif isinstance(existing_behavior, dict):
                behavior_dict = existing_behavior.copy()
        
        # Cache valid module names for performance
        valid_modules = set(BehaviorConfig.model_fields.keys())
        
        # Extract flattened fields and group by module
        modules: Dict[str, Dict[str, Any]] = {}
        remaining_data = {}
        
        for key, value in data.items():
            if '_' in key:
                # Split into module and field name
                parts = key.split('_', 1)
                module_name = parts[0]
                field_name = parts[1]
                
                # Check if this is a valid behavior module
                if module_name in valid_modules:
                    if module_name not in modules:
                        modules[module_name] = {}
                    modules[module_name][field_name] = value
                else:
                    # Not a behavior field, keep in remaining data
                    remaining_data[key] = value
            else:
                # No underscore, not a flattened field
                remaining_data[key] = value
        
        # Merge extracted modules into behavior dict
        for module_name, module_fields in modules.items():
            if module_name not in behavior_dict:
                # Create new module dict with extracted fields
                behavior_dict[module_name] = module_fields
            elif isinstance(behavior_dict[module_name], dict):
                # Merge new fields with existing dict
                behavior_dict[module_name].update(module_fields)
            else:
                # Module is an instantiated object - preserve existing values
                # This edge case handles mixed nested/flattened input
                existing_data = behavior_dict[module_name].model_dump() if hasattr(behavior_dict[module_name], 'model_dump') else {}
                behavior_dict[module_name] = {**existing_data, **module_fields}
        
        # Add behavior dict to remaining data
        if behavior_dict or modules:
            remaining_data['behavior'] = behavior_dict
        
        return remaining_data
    
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
    
    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """
        Override model_dump to include flattened behavior fields for backward compatibility.
        
        This ensures the frontend receives both the nested 'behavior' structure and
        flattened fields (e.g., timeline_hesitation_probability) that it expects.
        """
        # Get base model dump
        data = super().model_dump(**kwargs)
        
        # Add flattened fields from behavior modules
        if 'behavior' in data and isinstance(data['behavior'], dict):
            for module_name, module_data in data['behavior'].items():
                if isinstance(module_data, dict):
                    for field_name, field_value in module_data.items():
                        flat_key = f"{module_name}_{field_name}"
                        data[flat_key] = field_value
        
        return data
