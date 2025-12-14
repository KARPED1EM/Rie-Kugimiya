import random
from src.core.models.behavior import EmotionState


class PausePredictor:
    @staticmethod
    def segment_interval(
        emotion: EmotionState,
        emotion_multipliers: dict,
        min_duration: float,
        max_duration: float,
        text_length: int = 0,
    ) -> float:
        if max_duration < min_duration:
            min_duration, max_duration = max_duration, min_duration

        variance = random.uniform(0.8, 1.2)
        base = random.uniform(max(0.0, min_duration), max_duration) * variance
        multiplier = emotion_multipliers.get(emotion, 1.0)
        interval = base * multiplier

        length_bonus = min(max(text_length, 0) * 0.075, 6.0)
        interval += length_bonus

        return round(max(0.0, interval), 3)
