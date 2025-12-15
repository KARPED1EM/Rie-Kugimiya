"""Centralized default values - Single Source of Truth for all defaults"""


class BehaviorDefaults:
    """Default values for behavior configuration - SINGLE SOURCE OF TRUTH"""
    
    # Timeline behavior defaults
    TIMELINE_HESITATION_PROBABILITY = 0.15
    TIMELINE_HESITATION_CYCLES_MIN = 1
    TIMELINE_HESITATION_CYCLES_MAX = 3
    TIMELINE_TYPING_SPEED_MIN = 30
    TIMELINE_TYPING_SPEED_MAX = 60
    TIMELINE_THINKING_DELAY_MIN = 0.5
    TIMELINE_THINKING_DELAY_MAX = 2.0
    TIMELINE_READING_SPEED = 8.0
    TIMELINE_PAUSE_PROBABILITY = 0.3
    TIMELINE_PAUSE_CYCLES_MIN = 1
    TIMELINE_PAUSE_CYCLES_MAX = 2
    
    # Segmenter defaults
    SEGMENTER_ENABLE = True
    SEGMENTER_MAX_LENGTH = 50
    SEGMENTER_MAX_SEGMENTS = 20  # From coordinator.py
    
    # Typo defaults
    TYPO_ENABLE = True
    TYPO_BASE_RATE = 0.05
    TYPO_RECALL_RATE = 0.75
    TYPO_CHAR_ACCEPT_RATE = 0.25  # From typo.py TypoInjector.CHAR_TYPO_ACCEPT_RATE
    TYPO_WORD_ACCEPT_THRESHOLD = 0.35  # From typo.py
    TYPO_CHAR_ACCEPT_THRESHOLD = 0.55  # From typo.py
    
    # Recall defaults
    RECALL_ENABLE = True
    RECALL_MIN_INTERVAL = 5.0
    RECALL_MAX_INTERVAL = 30.0
    RECALL_PROBABILITY = 0.1
    
    # Pause defaults  
    PAUSE_ENABLE = True
    PAUSE_MIN_DURATION = 0.5
    PAUSE_MAX_DURATION = 3.0
    PAUSE_PROBABILITY = 0.2
    
    # Sticker defaults
    STICKER_ENABLE = True
    STICKER_MIN_INTERVAL = 10.0
    STICKER_PROBABILITY = 0.3
    STICKER_CONFIDENCE_POSITIVE = 0.7  # From sticker.py StickerSelector.CONFIDENCE_THRESHOLDS
    STICKER_CONFIDENCE_NEUTRAL = 0.8
    STICKER_CONFIDENCE_NEGATIVE = 0.9
    STICKER_CONFIDENCE_DEFAULT = 0.8
    
    # Emotion detection defaults
    EMOTION_DETECTION_ENABLE = True


class MessageDefaults:
    """Default values for message service"""
    
    # Time message interval (in seconds)
    TIME_MESSAGE_INTERVAL = 300  # From message_service.py


class CharacterDefaults:
    """Default values for character configuration"""
    
    # Default character settings
    IS_BUILTIN = False
    STICKER_PACKS = []  # Empty list by default
    
    # Apply all behavior defaults to character
    TIMELINE_HESITATION_PROBABILITY = BehaviorDefaults.TIMELINE_HESITATION_PROBABILITY
    TIMELINE_HESITATION_CYCLES_MIN = BehaviorDefaults.TIMELINE_HESITATION_CYCLES_MIN
    TIMELINE_HESITATION_CYCLES_MAX = BehaviorDefaults.TIMELINE_HESITATION_CYCLES_MAX
    TIMELINE_TYPING_SPEED_MIN = BehaviorDefaults.TIMELINE_TYPING_SPEED_MIN
    TIMELINE_TYPING_SPEED_MAX = BehaviorDefaults.TIMELINE_TYPING_SPEED_MAX
    TIMELINE_THINKING_DELAY_MIN = BehaviorDefaults.TIMELINE_THINKING_DELAY_MIN
    TIMELINE_THINKING_DELAY_MAX = BehaviorDefaults.TIMELINE_THINKING_DELAY_MAX
    TIMELINE_READING_SPEED = BehaviorDefaults.TIMELINE_READING_SPEED
    TIMELINE_PAUSE_PROBABILITY = BehaviorDefaults.TIMELINE_PAUSE_PROBABILITY
    TIMELINE_PAUSE_CYCLES_MIN = BehaviorDefaults.TIMELINE_PAUSE_CYCLES_MIN
    TIMELINE_PAUSE_CYCLES_MAX = BehaviorDefaults.TIMELINE_PAUSE_CYCLES_MAX
    
    SEGMENTER_ENABLE = BehaviorDefaults.SEGMENTER_ENABLE
    SEGMENTER_MAX_LENGTH = BehaviorDefaults.SEGMENTER_MAX_LENGTH
    
    TYPO_ENABLE = BehaviorDefaults.TYPO_ENABLE
    TYPO_BASE_RATE = BehaviorDefaults.TYPO_BASE_RATE
    TYPO_RECALL_RATE = BehaviorDefaults.TYPO_RECALL_RATE
    
    RECALL_ENABLE = BehaviorDefaults.RECALL_ENABLE
    RECALL_MIN_INTERVAL = BehaviorDefaults.RECALL_MIN_INTERVAL
    RECALL_MAX_INTERVAL = BehaviorDefaults.RECALL_MAX_INTERVAL
    RECALL_PROBABILITY = BehaviorDefaults.RECALL_PROBABILITY
    
    PAUSE_ENABLE = BehaviorDefaults.PAUSE_ENABLE
    PAUSE_MIN_DURATION = BehaviorDefaults.PAUSE_MIN_DURATION
    PAUSE_MAX_DURATION = BehaviorDefaults.PAUSE_MAX_DURATION
    PAUSE_PROBABILITY = BehaviorDefaults.PAUSE_PROBABILITY
    
    STICKER_ENABLE = BehaviorDefaults.STICKER_ENABLE
    STICKER_MIN_INTERVAL = BehaviorDefaults.STICKER_MIN_INTERVAL
    STICKER_PROBABILITY = BehaviorDefaults.STICKER_PROBABILITY
    
    EMOTION_DETECTION_ENABLE = BehaviorDefaults.EMOTION_DETECTION_ENABLE
