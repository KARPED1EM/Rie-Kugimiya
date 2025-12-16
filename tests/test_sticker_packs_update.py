"""Test that sticker_packs can be updated via behavior_params"""
from src.core.models.character import Character
from src.api.http_routes import _normalize_string_list


def test_sticker_packs_in_behavior_params():
    """
    Test that sticker_packs sent in behavior_params is properly handled.
    This simulates the backend logic for updating a character.
    """
    # Create a character without sticker_packs
    character = Character(
        id="test-char",
        name="Test Character",
        avatar="",
        persona="Test persona",
        sticker_packs=[],
    )
    
    # Verify initial state
    assert character.sticker_packs == []
    
    # Simulate the behavior_params processing logic from http_routes.py
    behavior_params = {
        "sticker_packs": ["general", "rin"],
        "timeline_hesitation_probability": 0.3,  # A normal nested field
        "sticker_send_probability": 0.5,  # Another sticker field
    }
    
    for key, value in behavior_params.items():
        # Handle sticker_packs as a special case (top-level Character field)
        if key == "sticker_packs":
            character.sticker_packs = _normalize_string_list(value)
        # Handle nested behavior config fields
        elif "_" in key:
            parts = key.split("_", 1)
            module_name = parts[0]
            field_name = parts[1]
            
            # Check if this is a valid module in BehaviorConfig
            if hasattr(character.behavior, module_name):
                module_config = getattr(character.behavior, module_name)
                if hasattr(module_config, field_name):
                    setattr(module_config, field_name, value)
    
    # Verify sticker_packs was updated
    assert character.sticker_packs == ["general", "rin"]
    
    # Verify other fields were also updated correctly
    assert character.behavior.timeline.hesitation_probability == 0.3
    assert character.behavior.sticker.send_probability == 0.5
    
    print("✓ test_sticker_packs_in_behavior_params passed")


def test_normalize_string_list():
    """Test the _normalize_string_list helper function"""
    # Test with valid list
    result = _normalize_string_list(["general", "rin", "abai"])
    assert result == ["general", "rin", "abai"]
    
    # Test with duplicates
    result = _normalize_string_list(["general", "rin", "general"])
    assert result == ["general", "rin"]
    
    # Test with empty strings
    result = _normalize_string_list(["general", "", "rin", "  ", "abai"])
    assert result == ["general", "rin", "abai"]
    
    # Test with None
    result = _normalize_string_list(None)
    assert result == []
    
    # Test with empty list
    result = _normalize_string_list([])
    assert result == []
    
    print("✓ test_normalize_string_list passed")


if __name__ == "__main__":
    test_normalize_string_list()
    test_sticker_packs_in_behavior_params()
    print("\nAll tests passed! ✓")
