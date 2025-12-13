from typing import List
import uuid
import random

from src.services.behavior.models import (
    BehaviorConfig,
    EmotionState,
    PlaybackAction,
    TimelineConfig,
)
from src.services.behavior.segmenter import SmartSegmenter
from src.services.behavior.emotion import EmotionFetcher
from src.services.behavior.typo import TypoInjector
from src.services.behavior.pause import PausePredictor
from src.services.behavior.timeline import TimelineBuilder
from src.services.behavior.sticker import StickerSelector
from src.infrastructure.utils.logger import unified_logger, LogCategory


class BehaviorCoordinator:
    def __init__(
        self, config: BehaviorConfig = None, timeline_config: TimelineConfig = None
    ):
        self.config = config or BehaviorConfig()
        self.segmenter = SmartSegmenter(max_length=self.config.max_segment_length)
        self.typo_injector = TypoInjector()
        self.timeline_builder = TimelineBuilder(timeline_config)
        self.sticker_packs = []
        self.sticker_send_probability = 0.4
        self.sticker_confidence_threshold_positive = 0.6
        self.sticker_confidence_threshold_neutral = 0.7
        self.sticker_confidence_threshold_negative = 0.8
        self.pending_log_entries = []

    def set_sticker_packs(self, packs: List[str]):
        self.sticker_packs = packs or []

    def set_sticker_config(
        self,
        send_probability: float = 0.4,
        threshold_positive: float = 0.6,
        threshold_neutral: float = 0.7,
        threshold_negative: float = 0.8,
    ):
        self.sticker_send_probability = send_probability
        self.sticker_confidence_threshold_positive = threshold_positive
        self.sticker_confidence_threshold_neutral = threshold_neutral
        self.sticker_confidence_threshold_negative = threshold_negative

    def get_and_clear_log_entries(self) -> List:
        entries = self.pending_log_entries
        self.pending_log_entries = []
        return entries

    def process_message(
        self, text: str, emotion_map: dict | None = None
    ) -> List[PlaybackAction]:
        cleaned_input = text.strip()
        if not cleaned_input:
            return []

        normalized_emotion_map = EmotionFetcher.normalize_map(emotion_map)
        emotion = self._fetch_emotion(cleaned_input, normalized_emotion_map)
        segments = self._segment_and_clean(cleaned_input)
        total_segments = len(segments)

        # Safety check: prevent excessive segments (likely due to malformed input)
        MAX_SEGMENTS = 20
        if total_segments > MAX_SEGMENTS:
            unified_logger.error(
                f"Excessive segments detected ({total_segments}), truncating to {MAX_SEGMENTS}. "
                f"Input preview: {cleaned_input[:200]}...",
                category=LogCategory.BEHAVIOR,
            )
            segments = segments[:MAX_SEGMENTS]
            total_segments = len(segments)

        actions: List[PlaybackAction] = []
        for index, segment_text in enumerate(segments):
            actions.extend(
                self._build_actions_for_segment(
                    segment_text=segment_text,
                    segment_index=index,
                    total_segments=total_segments,
                    emotion=emotion,
                    emotion_map=normalized_emotion_map,
                )
            )

        should_send, sticker_path, log_entry = StickerSelector.select_sticker(
            cleaned_input,
            self.sticker_packs,
            normalized_emotion_map,
            self.sticker_send_probability,
            self.sticker_confidence_threshold_positive,
            self.sticker_confidence_threshold_neutral,
            self.sticker_confidence_threshold_negative,
        )
        
        if log_entry:
            self.pending_log_entries.append(log_entry)

        if should_send and sticker_path:
            actions = self._insert_sticker_action(actions, sticker_path)

        timeline = self.timeline_builder.build_timeline(actions)
        return timeline

    def update_config(self, config: BehaviorConfig):
        self.config = config
        self.segmenter = SmartSegmenter(max_length=config.max_segment_length)

    def get_emotion(self, text: str, emotion_map: dict | None = None) -> EmotionState:
        normalized_map = EmotionFetcher.normalize_map(emotion_map)
        return self._fetch_emotion(text, normalized_map)

    def _segment_and_clean(self, text: str) -> List[str]:
        segments = [text]
        if self.config.enable_segmentation:
            try:
                segments = self.segmenter.segment(text)
            except Exception as exc:
                unified_logger.warning(
                    f"Segmentation failed, fallback to raw text: {exc}",
                    category=LogCategory.BEHAVIOR,
                )
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
        emotion_map: dict | None = None,
    ) -> List[PlaybackAction]:
        actions: List[PlaybackAction] = []
        base_metadata = {
            "segment_index": segment_index,
            "total_segments": total_segments,
            "emotion": emotion.value,
            "emotion_map": emotion_map or {},
        }

        has_typo, typo_text = False, None
        if self.config.enable_typo:
            emotion_multiplier = self.config.emotion_typo_multiplier.get(emotion, 1.0)
            typo_rate = self.config.base_typo_rate * emotion_multiplier
            (has_typo, typo_variant, _, _) = self.typo_injector.inject_typo(
                segment_text, typo_rate=typo_rate
            )
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
            if TypoInjector.should_recall_typo(self.config.typo_recall_rate):
                actions.extend(
                    self._build_recall_sequence(
                        typo_action=send_action,
                        corrected_text=segment_text,
                        emotion=emotion,
                        base_metadata=base_metadata,
                    )
                )

        if segment_index < total_segments - 1:
            interval = PausePredictor.segment_interval(
                emotion=emotion,
                emotion_multipliers=self.config.emotion_pause_multiplier,
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
            metadata={
                **base_metadata,
                "is_correction": True,
                "correction_for": typo_action.message_id,
                "emotion": emotion.value,
            },
        )
        recall_actions.append(correction_action)
        return recall_actions

    def _fetch_emotion(
        self, text: str, emotion_map: dict | None = None
    ) -> EmotionState:
        if not self.config.enable_emotion_fetch:
            return EmotionState.NEUTRAL
        return EmotionFetcher.fetch(emotion_map=emotion_map, fallback_text=text)

    def _insert_sticker_action(
        self, actions: List[PlaybackAction], sticker_path: str
    ) -> List[PlaybackAction]:
        send_actions = [i for i, a in enumerate(actions) if a.type == "send"]
        if not send_actions:
            return actions

        insert_idx = random.choice(send_actions)
        insert_after = random.choice([True, False])

        if insert_after:
            insert_idx += 1

        wait_duration = random.uniform(1.0, 5.0)
        wait_action = PlaybackAction(
            type="pause",
            duration=wait_duration,
            metadata={"reason": "sticker_delay"},
        )

        sticker_action = PlaybackAction(
            type="image",
            text=sticker_path,
            message_id=self._generate_message_id(),
            metadata={"is_sticker": True},
        )

        new_actions = actions[:insert_idx]
        new_actions.append(wait_action)
        new_actions.append(sticker_action)
        new_actions.extend(actions[insert_idx:])

        return new_actions

    @staticmethod
    def _trim_trailing_punctuation(text: str) -> str:
        if not text:
            return text

        trimmed = text.rstrip()
        punctuations = {",", "，", "。"}
        i = len(trimmed) - 1

        count = 0
        while i >= 0 and trimmed[i] in punctuations:
            count += 1
            i -= 1

        if count == 1:
            return trimmed[: i + 1].rstrip()
        return text

    @staticmethod
    def _generate_message_id() -> str:
        return uuid.uuid4().hex
