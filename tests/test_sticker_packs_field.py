"""Test that sticker_packs field is correctly handled by Character model"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_character_sticker_packs_field():
    """
    Test that sticker_packs is not mistakenly treated as a flattened behavior field.
    
    The bug: sticker_packs was being split into module="sticker" and field="packs",
    and since BehaviorConfig has a "sticker" module, it was incorrectly treated as
    a behavior field instead of a top-level Character field.
    """
    from src.core.models.character import Character
    
    # Test 1: Create character with sticker_packs in constructor
    char1 = Character(
        id="test-1",
        name="Test",
        avatar="",
        persona="",
        sticker_packs=["rin", "general"]
    )
    
    assert char1.sticker_packs == ["rin", "general"], \
        f"Expected ['rin', 'general'], got {char1.sticker_packs}"
    
    # Test 2: Create character from dict (simulating database load)
    char_data = {
        "id": "test-2",
        "name": "Test2",
        "avatar": "",
        "persona": "",
        "sticker_packs": ["weirdo", "general"]
    }
    
    char2 = Character(**char_data)
    assert char2.sticker_packs == ["weirdo", "general"], \
        f"Expected ['weirdo', 'general'], got {char2.sticker_packs}"
    
    # Test 3: Verify model_dump includes sticker_packs
    dumped = char2.model_dump()
    assert "sticker_packs" in dumped, "sticker_packs should be in model_dump()"
    assert dumped["sticker_packs"] == ["weirdo", "general"], \
        f"Expected ['weirdo', 'general'] in dump, got {dumped.get('sticker_packs')}"
    
    # Test 4: Create character with mixed flattened and direct fields
    mixed_data = {
        "id": "test-3",
        "name": "Test3",
        "avatar": "",
        "persona": "",
        "sticker_packs": ["general"],
        "sticker_send_probability": 0.5,  # This IS a flattened behavior field
    }
    
    char3 = Character(**mixed_data)
    assert char3.sticker_packs == ["general"], \
        f"sticker_packs should be ['general'], got {char3.sticker_packs}"
    assert char3.behavior.sticker.send_probability == 0.5, \
        f"sticker.send_probability should be 0.5, got {char3.behavior.sticker.send_probability}"
    
    print("✓ All sticker_packs tests passed!")


if __name__ == "__main__":
    test_character_sticker_packs_field()
