"""Tests for tool call functionality."""

import json
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from src.services.session.session_client import SessionClient
from src.core.models.message import Message, MessageType
from src.core.models.character import Character
from src.api.schemas import LLMConfig
from src.services.llm.llm_client import LLMStructuredResponse


@pytest.fixture
def mock_message_service():
    """Create a mock message service."""
    service = AsyncMock()
    service.message_repo = AsyncMock()
    service.message_repo.create = AsyncMock()
    service.get_messages = AsyncMock(return_value=[])
    service.get_latest_emotion_state = AsyncMock(return_value=None)
    service.set_emotion_state = AsyncMock()
    service.set_typing_state = AsyncMock()
    return service


@pytest.fixture
def mock_ws_manager():
    """Create a mock websocket manager."""
    manager = AsyncMock()
    manager.send_to_conversation = AsyncMock()
    manager.send_toast = AsyncMock()
    return manager


@pytest.fixture
def test_character():
    """Create a test character."""
    return Character(
        id="test-char",
        name="Test Character",
        persona="A test character",
        greeting="Hello",
        sticker_send_probability=0.0,
        typo_base_rate=0.0,
        recall_base_rate=0.0,
    )


@pytest.fixture
def llm_config():
    """Create test LLM config."""
    return LLMConfig(
        api_key="test-key",
        base_url="http://test.com",
        model="test-model",
        protocol="completions",
        max_tokens=1000,
        persona="Test persona",
        character_name="Test",
        user_nickname="User",
    )


class TestToolCalls:
    """Tests for tool call functionality."""

    @pytest.mark.asyncio
    async def test_image_message_uses_uid_not_description(
        self, mock_message_service, mock_ws_manager, test_character, llm_config
    ):
        """Test that image messages use UID instead of description in LLM history."""
        client = SessionClient(
            mock_message_service, mock_ws_manager, llm_config, test_character
        )

        # Create an image message
        image_msg = Message(
            id="img-123",
            session_id="session-1",
            sender_id="user",
            type=MessageType.IMAGE,
            content="stickers/rin/buxinren/01.webp",
            metadata={},
            is_recalled=False,
            is_read=False,
            timestamp=datetime.now(timezone.utc).timestamp(),
        )

        # Test the conversion
        result = client._user_message_to_text(image_msg)
        
        # Should use message ID, not description
        assert result == "[image](img-123)"
        assert "rin自拍的表情包" not in result  # Description should not be included

    @pytest.mark.asyncio
    async def test_get_image_description_tool_call(
        self, mock_message_service, mock_ws_manager, test_character, llm_config
    ):
        """Test that get_image_description tool call retrieves description correctly."""
        client = SessionClient(
            mock_message_service, mock_ws_manager, llm_config, test_character
        )

        # Create message history with an image
        image_msg = Message(
            id="img-456",
            session_id="session-1",
            sender_id="user",
            type=MessageType.IMAGE,
            content="stickers/rin/buxinren/01.webp",
            metadata={},
            is_recalled=False,
            is_read=False,
            timestamp=datetime.now(timezone.utc).timestamp(),
        )

        history = [image_msg]

        # Simulate tool call
        tool_calls = [
            {
                "name": "get_image_description",
                "arguments": {"image_id": "img-456"},
            }
        ]

        # Execute tool calls
        await client._handle_tool_calls("session-1", tool_calls, history)

        # Verify that a SYSTEM_TOOL message was created
        mock_message_service.message_repo.create.assert_called_once()
        created_msg = mock_message_service.message_repo.create.call_args[0][0]
        
        assert created_msg.type == MessageType.SYSTEM_TOOL
        assert created_msg.sender_id == "system"
        assert created_msg.session_id == "session-1"
        assert "img-456" in created_msg.content
        assert "工具调用结果" in created_msg.content
        assert created_msg.metadata["tool_name"] == "get_image_description"
        assert created_msg.metadata["image_id"] == "img-456"

    @pytest.mark.asyncio
    async def test_get_image_description_with_actual_description(
        self, mock_message_service, mock_ws_manager, test_character, llm_config
    ):
        """Test that tool call returns actual image description when available."""
        client = SessionClient(
            mock_message_service, mock_ws_manager, llm_config, test_character
        )

        # Create message history with an image that has a description in image_alter.json
        image_msg = Message(
            id="img-789",
            session_id="session-1",
            sender_id="user",
            type=MessageType.IMAGE,
            content="stickers/rin/buxinren/01.webp",
            metadata={},
            is_recalled=False,
            is_read=False,
            timestamp=datetime.now(timezone.utc).timestamp(),
        )

        history = [image_msg]

        tool_calls = [
            {
                "name": "get_image_description",
                "arguments": {"image_id": "img-789"},
            }
        ]

        await client._handle_tool_calls("session-1", tool_calls, history)

        created_msg = mock_message_service.message_repo.create.call_args[0][0]
        
        # Should contain the actual description from image_alter.json
        assert "rin自拍的表情包" in created_msg.content

    @pytest.mark.asyncio
    async def test_get_image_description_image_not_found(
        self, mock_message_service, mock_ws_manager, test_character, llm_config
    ):
        """Test that tool call handles missing image gracefully."""
        client = SessionClient(
            mock_message_service, mock_ws_manager, llm_config, test_character
        )

        history = []  # No messages

        tool_calls = [
            {
                "name": "get_image_description",
                "arguments": {"image_id": "nonexistent-img"},
            }
        ]

        await client._handle_tool_calls("session-1", tool_calls, history)

        created_msg = mock_message_service.message_repo.create.call_args[0][0]
        
        assert "未找到图片" in created_msg.content
        assert "nonexistent-img" in created_msg.content

    @pytest.mark.asyncio
    async def test_system_tool_message_included_in_llm_history(
        self, mock_message_service, mock_ws_manager, test_character, llm_config
    ):
        """Test that SYSTEM_TOOL messages are included in LLM history."""
        client = SessionClient(
            mock_message_service, mock_ws_manager, llm_config, test_character
        )

        # Create a SYSTEM_TOOL message
        tool_msg = Message(
            id="tool-123",
            session_id="session-1",
            sender_id="system",
            type=MessageType.SYSTEM_TOOL,
            content="工具调用结果：图片 img-123 的描述为：测试图片",
            metadata={"tool_name": "get_image_description", "image_id": "img-123"},
            is_recalled=False,
            is_read=False,
            timestamp=datetime.now(timezone.utc).timestamp(),
        )

        history = [tool_msg]

        # Build LLM history
        llm_history = client._build_llm_history(history)

        # Find the tool message in the history
        tool_messages = [msg for msg in llm_history if "工具调用结果" in msg.content]
        assert len(tool_messages) == 1
        assert tool_messages[0].role == "system"
        assert "图片 img-123 的描述为：测试图片" in tool_messages[0].content

    def test_llm_response_with_tool_calls(self):
        """Test that LLMStructuredResponse correctly handles tool_calls field."""
        response = LLMStructuredResponse(
            reply="",
            emotion_map={"neutral": "low"},
            raw_text='{"reply": "", "emotion": {"neutral": "low"}, "tool_calls": [{"name": "get_image_description", "arguments": {"image_id": "img-123"}}]}',
            is_invalid_json=False,
            is_empty_content=False,
            tool_calls=[
                {
                    "name": "get_image_description",
                    "arguments": {"image_id": "img-123"},
                }
            ],
        )

        assert len(response.tool_calls) == 1
        assert response.tool_calls[0]["name"] == "get_image_description"
        assert response.tool_calls[0]["arguments"]["image_id"] == "img-123"

    def test_llm_response_empty_content_with_tool_calls(self):
        """Test that empty content is allowed when there are tool calls."""
        # With tool calls, empty content should be allowed
        response = LLMStructuredResponse(
            reply="",
            emotion_map={},
            raw_text="{}",
            is_invalid_json=False,
            is_empty_content=False,  # Should be False because tool_calls exist
            tool_calls=[{"name": "test"}],
        )

        assert not response.is_empty_content
        assert len(response.tool_calls) == 1
