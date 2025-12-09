#!/usr/bin/env python
"""Test configuration system"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import (
    app_config,
    character_config,
    llm_defaults,
    behavior_defaults,
    typing_state_defaults,
    ui_defaults,
    websocket_config,
    database_config
)


def test_app_config():
    print("Testing app config...")
    assert app_config.app_name == "Yuzuriha Rin Virtual Chat"
    assert isinstance(app_config.debug, bool)
    assert isinstance(app_config.cors_origins, list)
    print("✓ App config valid")


def test_character_config():
    print("Testing character config...")
    assert character_config.default_name == "Rin"
    assert isinstance(character_config.default_persona, str)
    assert len(character_config.default_persona) > 0
    print("✓ Character config valid")


def test_llm_defaults():
    print("Testing LLM defaults...")
    assert llm_defaults.provider in ["openai", "anthropic", "deepseek", "custom"]
    assert llm_defaults.model_openai == "gpt-3.5-turbo"
    assert llm_defaults.model_anthropic == "claude-3-5-sonnet-20241022"
    assert llm_defaults.model_deepseek == "deepseek-chat"
    print("✓ LLM defaults valid")


def test_behavior_defaults():
    print("Testing behavior defaults...")
    assert isinstance(behavior_defaults.enable_segmentation, bool)
    assert isinstance(behavior_defaults.enable_typo, bool)
    assert isinstance(behavior_defaults.enable_recall, bool)

    assert behavior_defaults.max_segment_length > 0
    assert 0 <= behavior_defaults.min_pause_duration <= behavior_defaults.max_pause_duration
    assert 0 <= behavior_defaults.base_typo_rate <= 1
    assert 0 <= behavior_defaults.typo_recall_rate <= 1

    assert isinstance(behavior_defaults.emotion_typo_multiplier, dict)
    assert "neutral" in behavior_defaults.emotion_typo_multiplier
    print("✓ Behavior defaults valid")


def test_typing_state_defaults():
    print("Testing typing state defaults...")
    assert 0 <= typing_state_defaults.hesitation_probability <= 1
    assert typing_state_defaults.hesitation_cycles_min <= typing_state_defaults.hesitation_cycles_max
    assert typing_state_defaults.hesitation_duration_min < typing_state_defaults.hesitation_duration_max

    assert typing_state_defaults.typing_lead_time_threshold_1 < typing_state_defaults.typing_lead_time_threshold_2
    assert typing_state_defaults.typing_lead_time_1 < typing_state_defaults.typing_lead_time_2

    assert typing_state_defaults.initial_delay_weight_1 < typing_state_defaults.initial_delay_weight_2 < typing_state_defaults.initial_delay_weight_3 < 1
    print("✓ Typing state defaults valid")


def test_ui_defaults():
    print("Testing UI defaults...")
    assert ui_defaults.avatar_user_path.startswith("/static")
    assert ui_defaults.avatar_assistant_path.startswith("/static")

    assert isinstance(ui_defaults.emotion_palette, dict)
    assert "neutral" in ui_defaults.emotion_palette
    assert "happy" in ui_defaults.emotion_palette

    assert isinstance(ui_defaults.intensity_weights, dict)
    assert "low" in ui_defaults.intensity_weights
    assert "high" in ui_defaults.intensity_weights

    assert ui_defaults.base_accent_color.startswith("#")
    print("✓ UI defaults valid")


def test_websocket_config():
    print("Testing WebSocket config...")
    assert isinstance(websocket_config.host, str)
    assert isinstance(websocket_config.port, int)
    assert 1024 <= websocket_config.port <= 65535
    assert websocket_config.ping_interval > 0
    assert websocket_config.ping_timeout > 0
    print("✓ WebSocket config valid")


def test_database_config():
    print("Testing database config...")
    assert isinstance(database_config.path, str)
    assert database_config.path.endswith(".db")
    print("✓ Database config valid")


def run_all_tests():
    print("=" * 50)
    print("Running Configuration Tests")
    print("=" * 50)

    test_app_config()
    test_character_config()
    test_llm_defaults()
    test_behavior_defaults()
    test_typing_state_defaults()
    test_ui_defaults()
    test_websocket_config()
    test_database_config()

    print("\n" + "=" * 50)
    print("✅ All configuration tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    run_all_tests()
