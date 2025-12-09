"""
Interval Prediction Module

Generates random-but-bounded intervals between playback actions.
"""
import random
from .models import EmotionState


class PausePredictor:
    """Generate intervals to space out playback actions."""

    def __init__(self):
        # Emotion-based speed multipliers for pause duration
        self.emotion_speed_multipliers = {
            EmotionState.NEUTRAL: 1.0,
            EmotionState.HAPPY: 0.9,
            EmotionState.EXCITED: 0.8,
            EmotionState.SAD: 1.2,
            EmotionState.ANGRY: 0.9,
            EmotionState.ANXIOUS: 1.1,
            EmotionState.CONFUSED: 1.1,
        }

    def segment_interval(
        self,
        emotion: EmotionState = EmotionState.NEUTRAL,
        min_duration: float = 0.4,
        max_duration: float = 2.5,
        text_length: int = 0,
    ) -> float:
        """
        Produce a random interval between two outgoing messages.

        Args:
            emotion: Current emotion state
            min_duration: Minimum pause duration in seconds
            max_duration: Maximum pause duration in seconds

        Returns:
            Interval duration in seconds
        """
        if max_duration < min_duration:
            min_duration, max_duration = max_duration, min_duration

        variance = random.uniform(0.8, 1.2)
        base = random.uniform(max(0.0, min_duration), max_duration) * variance
        multiplier = self.emotion_speed_multipliers.get(emotion, 1.0)
        interval = base * multiplier

        length_bonus = min(max(text_length, 0) * 0.035, 5.0)
        interval += length_bonus

        # Clamp to non-negative range
        return round(max(0.0, interval), 3)
