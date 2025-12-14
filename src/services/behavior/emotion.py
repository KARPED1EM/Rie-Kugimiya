from typing import Dict
from src.core.models.behavior import EmotionState


class EmotionFetcher:
    INTENSITY_ORDER = ["low", "medium", "high", "extreme"]
    NAME_TO_STATE = {
        "neutral": EmotionState.NEUTRAL,
        "happy": EmotionState.HAPPY,
        "excited": EmotionState.EXCITED,
        "sad": EmotionState.SAD,
        "angry": EmotionState.ANGRY,
        "mad": EmotionState.ANGRY,
        "anxious": EmotionState.ANXIOUS,
        "nervous": EmotionState.ANXIOUS,
        "confused": EmotionState.CONFUSED,
        "shy": EmotionState.CONFUSED,
        "embarrassed": EmotionState.ANXIOUS,
        "surprised": EmotionState.EXCITED,
        "playful": EmotionState.HAPPY,
        "affectionate": EmotionState.HAPPY,
        "tired": EmotionState.SAD,
        "bored": EmotionState.SAD,
        "serious": EmotionState.NEUTRAL,
        "caring": EmotionState.HAPPY,
    }

    @staticmethod
    def fetch(
        emotion_map: Dict[str, str] | None = None, fallback_text: str | None = None
    ) -> EmotionState:
        if not emotion_map:
            return EmotionState.NEUTRAL

        normalized = EmotionFetcher._normalize_map(emotion_map)
        if not normalized:
            return EmotionState.NEUTRAL

        top_emotion, _ = max(
            normalized.items(),
            key=lambda item: EmotionFetcher._intensity_rank(item[1]),
        )
        return EmotionFetcher.NAME_TO_STATE.get(top_emotion, EmotionState.NEUTRAL)

    @staticmethod
    def normalize_map(emotion_map: Dict[str, str] | None) -> Dict[str, str]:
        if not emotion_map:
            return {}
        return EmotionFetcher._normalize_map(emotion_map)

    @staticmethod
    def _normalize_map(emotion_map: Dict[str, str]) -> Dict[str, str]:
        cleaned: Dict[str, str] = {}
        for raw_key, raw_value in emotion_map.items():
            key = str(raw_key).strip().lower()
            value = str(raw_value).strip().lower()
            if not key:
                continue
            if value not in EmotionFetcher.INTENSITY_ORDER:
                continue
            cleaned[key] = value
        return cleaned

    @staticmethod
    def _intensity_rank(intensity: str) -> int:
        try:
            return EmotionFetcher.INTENSITY_ORDER.index(intensity)
        except ValueError:
            return 0
