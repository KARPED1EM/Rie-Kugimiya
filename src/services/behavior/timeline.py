import random
from typing import List
from src.core.models.behavior import PlaybackAction
from src.core.models.character import Character


class TimelineBuilder:
    def __init__(self, character: Character):
        self.character = character

    def build_timeline(self, actions: List[PlaybackAction]) -> List[PlaybackAction]:
        timeline = []
        current_time = 0.0

        hesitation_sequence = self._generate_hesitation_sequence()
        for hesitation_action in hesitation_sequence:
            hesitation_action.timestamp = current_time
            timeline.append(hesitation_action)
            current_time += hesitation_action.duration

        initial_delay = self._sample_initial_delay()
        if initial_delay > 0:
            timeline.append(
                PlaybackAction(
                    type="wait",
                    duration=initial_delay,
                    timestamp=current_time,
                    metadata={"reason": "initial_delay"},
                )
            )
            current_time += initial_delay

        typing_active = False
        for i, action in enumerate(actions):
            if action.type == "send":
                text_length = len(action.text or "")
                typing_lead_time = self._calculate_typing_lead_time(text_length)

                if not typing_active:
                    entry_delay = random.uniform(
                        self.character.timeline_entry_delay_min / 1000,
                        self.character.timeline_entry_delay_max / 1000,
                    )
                    if entry_delay > 0:
                        timeline.append(
                            PlaybackAction(
                                type="wait",
                                duration=entry_delay,
                                timestamp=current_time,
                                metadata={"reason": "typing_entry_delay"},
                            )
                        )
                        current_time += entry_delay

                    timeline.append(
                        PlaybackAction(
                            type="typing_start",
                            timestamp=current_time,
                            metadata={"text_length": text_length},
                        )
                    )
                    typing_active = True

                if typing_lead_time > 0:
                    timeline.append(
                        PlaybackAction(
                            type="wait",
                            duration=typing_lead_time,
                            timestamp=current_time,
                            metadata={"reason": "typing_lead_time"},
                        )
                    )
                    current_time += typing_lead_time

                send_action = action.model_copy()
                send_action.timestamp = current_time
                timeline.append(send_action)

                next_is_send = i + 1 < len(actions) and actions[i + 1].type == "send"
                keep_typing = text_length > 100 and next_is_send

                if not keep_typing and typing_active:
                    timeline.append(
                        PlaybackAction(
                            type="typing_end", timestamp=current_time, metadata={}
                        )
                    )
                    typing_active = False

            elif action.type == "pause":
                if action.duration > 0:
                    timeline.append(
                        PlaybackAction(
                            type="wait",
                            duration=action.duration,
                            timestamp=current_time,
                            metadata=action.metadata,
                        )
                    )
                    current_time += action.duration

            elif action.type == "recall":
                if typing_active:
                    timeline.append(
                        PlaybackAction(
                            type="typing_end", timestamp=current_time, metadata={}
                        )
                    )
                    typing_active = False

                recall_action = action.model_copy()
                recall_action.timestamp = current_time
                timeline.append(recall_action)

            elif action.type == "image":
                if typing_active:
                    timeline.append(
                        PlaybackAction(
                            type="typing_end", timestamp=current_time, metadata={}
                        )
                    )
                    typing_active = False

                image_action = action.model_copy()
                image_action.timestamp = current_time
                timeline.append(image_action)

        if typing_active:
            timeline.append(
                PlaybackAction(type="typing_end", timestamp=current_time, metadata={})
            )

        return timeline

    def _generate_hesitation_sequence(self) -> List[PlaybackAction]:
        if random.random() > self.character.timeline_hesitation_probability:
            return []

        cycles = random.randint(
            self.character.timeline_hesitation_cycles_min, self.character.timeline_hesitation_cycles_max
        )

        sequence = []
        for i in range(cycles):
            typing_duration = (
                random.randint(
                    self.character.timeline_hesitation_duration_min,
                    self.character.timeline_hesitation_duration_max,
                )
                / 1000
            )
            sequence.append(
                PlaybackAction(
                    type="typing_start",
                    duration=0,
                    metadata={"reason": "hesitation", "cycle": i + 1},
                )
            )
            sequence.append(
                PlaybackAction(
                    type="wait",
                    duration=typing_duration,
                    metadata={"reason": "hesitation_typing"},
                )
            )
            sequence.append(
                PlaybackAction(
                    type="typing_end",
                    duration=0,
                    metadata={"reason": "hesitation"},
                )
            )

            if i < cycles - 1:
                gap_duration = (
                    random.randint(
                        self.character.timeline_hesitation_gap_min,
                        self.character.timeline_hesitation_gap_max,
                    )
                    / 1000
                )
                sequence.append(
                    PlaybackAction(
                        type="wait",
                        duration=gap_duration,
                        metadata={"reason": "hesitation_gap"},
                    )
                )

        return sequence

    def _sample_initial_delay(self) -> float:
        r = random.random()
        if r < self.character.timeline_initial_delay_weight_1:
            return random.uniform(
                self.character.timeline_initial_delay_range_1_min,
                self.character.timeline_initial_delay_range_1_max,
            )
        elif r < self.character.timeline_initial_delay_weight_2:
            return random.uniform(
                self.character.timeline_initial_delay_range_2_min,
                self.character.timeline_initial_delay_range_2_max,
            )
        elif r < self.character.timeline_initial_delay_weight_3:
            return random.uniform(
                self.character.timeline_initial_delay_range_3_min,
                self.character.timeline_initial_delay_range_3_max,
            )
        else:
            return random.uniform(
                self.character.timeline_initial_delay_range_4_min,
                self.character.timeline_initial_delay_range_4_max,
            )

    def _calculate_typing_lead_time(self, text_length: int) -> float:
        if text_length <= self.character.timeline_typing_lead_time_threshold_1:
            return self.character.timeline_typing_lead_time_1 / 1000
        elif text_length <= self.character.timeline_typing_lead_time_threshold_2:
            return self.character.timeline_typing_lead_time_2 / 1000
        elif text_length <= self.character.timeline_typing_lead_time_threshold_3:
            return self.character.timeline_typing_lead_time_3 / 1000
        elif text_length <= self.character.timeline_typing_lead_time_threshold_4:
            return self.character.timeline_typing_lead_time_4 / 1000
        elif text_length <= self.character.timeline_typing_lead_time_threshold_5:
            return self.character.timeline_typing_lead_time_5 / 1000
        else:
            return self.character.timeline_typing_lead_time_default / 1000

