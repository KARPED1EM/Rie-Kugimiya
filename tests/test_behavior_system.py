#!/usr/bin/env python
"""Test behavior system"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.behavior.coordinator import BehaviorCoordinator
from src.behavior.models import BehaviorConfig, EmotionState
from src.behavior.segmenter import SmartSegmenter
from src.behavior.emotion import EmotionDetector
from src.behavior.typo import TypoInjector
from src.behavior.pause import PausePredictor
from src.behavior.timeline import TimelineBuilder


def test_behavior_coordinator():
    print("Testing behavior coordinator...")

    coordinator = BehaviorCoordinator(BehaviorConfig())

    text = "你好！我是Rin。今天天气真不错。"
    timeline = coordinator.process_message(text)

    assert len(timeline) > 0, "Timeline should not be empty"

    action_types = set(action.type for action in timeline)
    assert "send" in action_types, "Should have send actions"

    send_actions = [a for a in timeline if a.type == "send"]
    assert len(send_actions) > 0, "Should have at least one send action"

    for action in timeline:
        assert hasattr(action, 'timestamp'), "All actions should have timestamp"
        assert action.timestamp >= 0, "Timestamp should be non-negative"

    for i in range(len(timeline) - 1):
        assert timeline[i].timestamp <= timeline[i + 1].timestamp, "Timeline should be sorted by timestamp"

    print("✓ Behavior coordinator test successful")


def test_smart_segmenter():
    print("Testing smart segmenter...")

    segmenter = SmartSegmenter(max_length=50)

    text = "这是第一句。这是第二句。这是第三句。"
    segments = segmenter.segment(text)

    assert len(segments) > 0, "Should produce segments"
    assert all(isinstance(s, str) for s in segments), "All segments should be strings"

    print("✓ Smart segmenter test successful")


def test_emotion_detector():
    print("Testing emotion detector...")

    detector = EmotionDetector()

    emotion_map_happy = {"happy": "high"}
    emotion = detector.detect(emotion_map=emotion_map_happy)
    assert emotion == EmotionState.HAPPY, "Should detect happy emotion"

    emotion_map_sad = {"sad": "medium"}
    emotion = detector.detect(emotion_map=emotion_map_sad)
    assert emotion == EmotionState.SAD, "Should detect sad emotion"

    emotion_neutral = detector.detect(emotion_map=None, fallback_text="Hello")
    assert emotion_neutral == EmotionState.NEUTRAL, "Should default to neutral"

    print("✓ Emotion detector test successful")


def test_typo_injector():
    print("Testing typo injector...")

    injector = TypoInjector()

    text = "你好，我的名字是Rin，这是我们的对话"

    has_typo_count = 0
    for _ in range(100):
        has_typo, typo_text, _, _ = injector.inject_typo(text, typo_rate=1.0)
        if has_typo:
            has_typo_count += 1

    assert has_typo_count > 0, f"Should generate typos with 100% rate (got {has_typo_count}/100)"

    recall_count = 0
    for _ in range(100):
        should_recall = injector.should_recall_typo(recall_rate=0.5)
        if should_recall:
            recall_count += 1

    assert recall_count > 0, "Should sometimes recall"
    assert recall_count < 100, "Should not always recall"

    print("✓ Typo injector test successful")


def test_pause_predictor():
    print("Testing pause predictor...")

    predictor = PausePredictor()

    duration_neutral = predictor.segment_interval(
        emotion=EmotionState.NEUTRAL,
        min_duration=0.5,
        max_duration=2.0
    )
    assert 0.5 <= duration_neutral <= 2.0, "Duration should be within range"

    duration_excited = predictor.segment_interval(
        emotion=EmotionState.EXCITED,
        min_duration=0.5,
        max_duration=2.0
    )
    assert 0.5 <= duration_excited <= 2.0, "Duration should be within range"

    print("✓ Pause predictor test successful")


def test_timeline_builder():
    print("Testing timeline builder...")

    builder = TimelineBuilder()

    from src.behavior.models import PlaybackAction

    actions = [
        PlaybackAction(type="send", text="Hello", duration=0, message_id="msg-1"),
        PlaybackAction(type="pause", duration=1.0),
        PlaybackAction(type="send", text="World", duration=0, message_id="msg-2"),
    ]

    timeline = builder.build_timeline(actions)

    assert len(timeline) > len(actions), "Timeline should have more actions (typing states, etc.)"

    action_types = [a.type for a in timeline]
    assert "wait" in action_types or "typing_start" in action_types, "Should have timing actions"

    send_actions = [a for a in timeline if a.type == "send"]
    assert len(send_actions) == 2, "Should preserve send actions"

    for i in range(len(timeline) - 1):
        assert timeline[i].timestamp <= timeline[i + 1].timestamp, "Timeline should be sorted"

    print("✓ Timeline builder test successful")


def test_behavior_with_emotion():
    print("Testing behavior with emotion...")

    coordinator = BehaviorCoordinator(BehaviorConfig())

    emotion_maps = {
        "neutral": {"neutral": "medium"},
        "happy": {"happy": "high"},
        "sad": {"sad": "medium"},
        "excited": {"excited": "high"},
    }

    for emotion_name, emotion_map in emotion_maps.items():
        timeline = coordinator.process_message("测试消息", emotion_map=emotion_map)
        assert len(timeline) > 0, f"Should generate timeline for {emotion_name}"

    print("✓ Behavior with emotion test successful")


def test_behavior_with_typo_and_recall():
    print("Testing behavior with typo and recall...")

    config = BehaviorConfig(
        enable_typo=True,
        enable_recall=True,
        base_typo_rate=1.0,
        typo_recall_rate=1.0
    )

    coordinator = BehaviorCoordinator(config)

    found_recall = False
    for _ in range(10):
        timeline = coordinator.process_message("这是一个测试消息")
        action_types = [a.type for a in timeline]

        if "recall" in action_types:
            found_recall = True
            break

    print(f"  Found recall action: {found_recall}")
    print("✓ Behavior with typo and recall test completed")


def test_timeline_timestamps():
    print("Testing timeline timestamps...")

    coordinator = BehaviorCoordinator(BehaviorConfig())
    timeline = coordinator.process_message("测试消息")

    assert timeline[0].timestamp == 0 or timeline[0].timestamp >= 0, "First action should start at or after 0"

    for i in range(len(timeline) - 1):
        current = timeline[i]
        next_action = timeline[i + 1]

        assert next_action.timestamp >= current.timestamp, "Timestamps should be non-decreasing"

        if current.type == "wait":
            expected_next_time = current.timestamp + current.duration
            assert abs(next_action.timestamp - expected_next_time) < 0.01, "Wait duration should advance timestamp"

    print("✓ Timeline timestamps test successful")


def run_all_tests():
    print("=" * 50)
    print("Running Behavior System Tests")
    print("=" * 50)

    test_behavior_coordinator()
    test_smart_segmenter()
    test_emotion_detector()
    test_typo_injector()
    test_pause_predictor()
    test_timeline_builder()
    test_behavior_with_emotion()
    test_behavior_with_typo_and_recall()
    test_timeline_timestamps()

    print("\n" + "=" * 50)
    print("✅ All behavior system tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    run_all_tests()
