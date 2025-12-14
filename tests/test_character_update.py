"""Test character configuration update functionality"""
from unittest.mock import Mock
from src.services.session.session_client import SessionClient
from src.core.models.character import Character
from src.api.schemas import LLMConfig


def test_session_client_update_character():
    """Test that SessionClient.update_character updates the character and coordinator"""
    # Create initial character
    initial_character = Character(
        id="test_char_1",
        name="Test Character",
        avatar="avatar.png",
        persona="Test persona",
        sticker_send_probability=0.4,
    )
    
    # Create mock dependencies
    message_service = Mock()
    ws_manager = Mock()
    llm_config = LLMConfig(
        provider="openai",
        api_key="test_key",
        model="gpt-3.5-turbo",
        base_url=None,
        persona="Test persona",
        character_name="Test Character",
        user_nickname=None,
    )
    
    # Create SessionClient
    session_client = SessionClient(
        message_service=message_service,
        ws_manager=ws_manager,
        llm_config=llm_config,
        character=initial_character,
    )
    
    # Verify initial state
    assert session_client.character.sticker_send_probability == 0.4
    assert session_client.coordinator.character.sticker_send_probability == 0.4
    
    # Create updated character with different probability
    updated_character = Character(
        id="test_char_1",
        name="Test Character",
        avatar="avatar.png",
        persona="Test persona",
        sticker_send_probability=0.01,  # Changed from 0.4
    )
    
    # Update the character
    session_client.update_character(updated_character)
    
    # Verify the update
    assert session_client.character.sticker_send_probability == 0.01
    assert session_client.coordinator.character.sticker_send_probability == 0.01
    
    # Verify they are the same object reference
    assert session_client.character is session_client.coordinator.character


if __name__ == "__main__":
    test_session_client_update_character()
    print("✓ test_session_client_update_character passed")
