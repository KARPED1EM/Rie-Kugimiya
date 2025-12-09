"""
Behavior Coordinator

Produces a one-shot playback sequence that mimics messaging apps such as WeChat.
"""
from typing import List
import uuid

from .models import BehaviorConfig, EmotionState, PlaybackAction
from .segmenter import SmartSegmenter
from .emotion import EmotionDetector
from .typo import TypoInjector
from .pause import PausePredictor


class BehaviorCoordinator:
    """
    Coordinates segmentation, typo injection, and recall behaviors to create the
    final playback timeline consumed by the frontend.
    """

    def __init__(self, config: BehaviorConfig = None):
        self.config = config or BehaviorConfig()

        self.segmenter = SmartSegmenter(
            max_length=self.config.max_segment_length,
        )
        self.emotion_detector = EmotionDetector()
        self.typo_injector = TypoInjector()
        self.pause_predictor = PausePredictor()

    def process_message(self, text: str, emotion_map: dict | None = None) -> List[PlaybackAction]:
        """
        Convert text into a playback sequence of send/pause/recall actions.
        """
        cleaned_input = text.strip()
        if not cleaned_input:
            return []

        emotion = self._detect_emotion(cleaned_input, emotion_map)
        segments = self._segment_and_clean(cleaned_input)
        total_segments = len(segments)

        actions: List[PlaybackAction] = []
        for index, segment_text in enumerate(segments):
            actions.extend(
                self._build_actions_for_segment(
                    segment_text=segment_text,
                    segment_index=index,
                    total_segments=total_segments,
                    emotion=emotion,
                )
            )

        return actions

    def update_config(self, config: BehaviorConfig):
        """Update behavior configuration at runtime."""
        self.config = config

    def get_emotion(self, text: str, emotion_map: dict | None = None) -> EmotionState:
        """Expose emotion detection for API metadata."""
        return self._detect_emotion(text, emotion_map)

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #
    def _segment_and_clean(self, text: str) -> List[str]:
        """Segment text and clean up trailing punctuation from each segment"""
        segments = [text]
        if self.config.enable_segmentation:
            try:
                segments = self.segmenter.segment(text)
            except Exception as exc:
                print(f"[behavior] segmentation failed, fallback to raw text: {exc}")
                segments = [text]

        cleaned = [self._trim_trailing_punctuation(seg) for seg in segments]
        cleaned = [seg for seg in cleaned if seg]

        if not cleaned:
            fallback = self._trim_trailing_punctuation(text)
            return [fallback] if fallback else []

        return cleaned

    def _build_actions_for_segment(
        self,
        segment_text: str,
        segment_index: int,
        total_segments: int,
        emotion: EmotionState,
    ) -> List[PlaybackAction]:
        actions: List[PlaybackAction] = []
        base_metadata = {
            "segment_index": segment_index,
            "total_segments": total_segments,
            "emotion": emotion.value,
        }

        # Typo injection (if enabled)
        has_typo, typo_text = False, None
        if self.config.enable_typo:
            emotion_multiplier = self.config.emotion_typo_multiplier.get(emotion, 1.0)
            typo_rate = self.config.base_typo_rate * emotion_multiplier
            (
                has_typo,
                typo_variant,
                _,
                _,
            ) = self.typo_injector.inject_typo(segment_text, typo_rate=typo_rate)
            if has_typo and typo_variant:
                typo_text = typo_variant

        send_text = typo_text or segment_text
        send_action = PlaybackAction(
            type="send",
            text=send_text,
            message_id=self._generate_message_id(),
            metadata={
                **base_metadata,
                "has_typo": bool(typo_text),
            },
        )
        actions.append(send_action)

        if has_typo and typo_text and self.config.enable_recall:
            if self.typo_injector.should_recall_typo(self.config.typo_recall_rate):
                actions.extend(
                    self._build_recall_sequence(
                        typo_action=send_action,
                        corrected_text=segment_text,
                        emotion=emotion,
                        base_metadata=base_metadata,
                    )
                )

        # Interval after this segment (unless it's the last one)
        if segment_index < total_segments - 1:
            interval = self.pause_predictor.segment_interval(
                emotion=emotion,
                min_duration=self.config.min_pause_duration,
                max_duration=self.config.max_pause_duration,
            )
            if interval > 0:
                actions.append(
                    PlaybackAction(
                        type="pause",
                        duration=interval,
                        metadata={
                            "reason": "segment_interval",
                            "from_segment": segment_index,
                            "emotion": emotion.value,
                        },
                    )
                )

        return actions

    def _build_recall_sequence(
        self,
        typo_action: PlaybackAction,
        corrected_text: str,
        emotion: EmotionState,
        base_metadata: dict,
    ) -> List[PlaybackAction]:
        recall_actions: List[PlaybackAction] = []

        if self.config.recall_delay > 0:
            recall_actions.append(
                PlaybackAction(
                    type="pause",
                    duration=self.config.recall_delay,
                    metadata={"reason": "typo_recall_delay"},
                )
            )

        recall_actions.append(
            PlaybackAction(
                type="recall",
                target_id=typo_action.message_id,
                metadata={"reason": "typo_recall"},
            )
        )

        if self.config.retype_delay > 0:
            recall_actions.append(
                PlaybackAction(
                    type="pause",
                    duration=self.config.retype_delay,
                    metadata={"reason": "typo_retype_wait"},
                )
            )

        correction_action = PlaybackAction(
            type="send",
            text=corrected_text,
            message_id=self._generate_message_id(),
            metadata={**base_metadata, "is_correction": True, "emotion": emotion.value},
        )
        recall_actions.append(correction_action)
        return recall_actions

    def _detect_emotion(self, text: str, emotion_map: dict | None = None) -> EmotionState:
        if not self.config.enable_emotion_detection:
            return EmotionState.NEUTRAL
        return self.emotion_detector.detect(emotion_map=emotion_map, fallback_text=text)

    @staticmethod
    def _trim_trailing_punctuation(text: str) -> str:
        """Remove trailing commas and periods from text"""
        trimmed = text.strip()
        while trimmed and trimmed[-1] in {",", "，", ".", "。"}:
            trimmed = trimmed[:-1].rstrip()
        return trimmed

    @staticmethod
    def _generate_message_id() -> str:
        return uuid.uuid4().hex
