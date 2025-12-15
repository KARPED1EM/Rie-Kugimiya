"""Tests for tool service."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from src.services.tools.tool_service import ToolService
from src.services.messaging.message_service import MessageService
from src.core.models.message import Message, MessageType


class TestToolService:
    """Tests for ToolService class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_message_service = MagicMock(spec=MessageService)
        self.tool_service = ToolService(self.mock_message_service)

    @pytest.mark.asyncio
    async def test_get_avatar_descriptions(self):
        """Test getting avatar descriptions."""
        result = await self.tool_service.get_avatar_descriptions(
            character_avatar="data/avatars/character.png",
            user_avatar="data/avatars/user.png"
        )
        
        assert "character_avatar_description" in result
        assert "user_avatar_description" in result

    @pytest.mark.asyncio
    async def test_get_image_description_success(self):
        """Test getting image description successfully."""
        image_id = "msg-image-1"
        session_id = "test-session"
        current_time = datetime.now(timezone.utc).timestamp()
        
        image_message = Message(
            id=image_id,
            session_id=session_id,
            sender_id="user",
            type=MessageType.IMAGE,
            content="data/images/test.png",
            metadata={},
            is_recalled=False,
            is_read=False,
            timestamp=current_time
        )
        
        self.mock_message_service.get_message = AsyncMock(return_value=image_message)
        
        result = await self.tool_service.get_image_description(image_id)
        
        assert "image_id" in result
        assert result["image_id"] == image_id
        assert "description" in result

    @pytest.mark.asyncio
    async def test_get_image_description_not_found(self):
        """Test getting image description for non-existent message."""
        image_id = "msg-nonexistent"
        
        self.mock_message_service.get_message = AsyncMock(return_value=None)
        
        result = await self.tool_service.get_image_description(image_id)
        
        assert "error" in result
        assert "不存在" in result["error"]
        assert result["image_id"] == image_id

    @pytest.mark.asyncio
    async def test_get_image_description_wrong_type(self):
        """Test getting image description for non-image message."""
        message_id = "msg-text-1"
        session_id = "test-session"
        current_time = datetime.now(timezone.utc).timestamp()
        
        text_message = Message(
            id=message_id,
            session_id=session_id,
            sender_id="user",
            type=MessageType.TEXT,
            content="This is a text message",
            metadata={},
            is_recalled=False,
            is_read=False,
            timestamp=current_time
        )
        
        self.mock_message_service.get_message = AsyncMock(return_value=text_message)
        
        result = await self.tool_service.get_image_description(message_id)
        
        assert "error" in result
        assert "不是图片类型" in result["error"]
        assert result["image_id"] == message_id

    @pytest.mark.asyncio
    async def test_get_recallable_messages(self):
        """Test getting recallable messages within 2 minutes."""
        session_id = "test-session"
        current_time = datetime.now(timezone.utc).timestamp()
        
        # Create test messages
        messages = [
            Message(
                id="msg-1",
                session_id=session_id,
                sender_id="assistant",
                type=MessageType.TEXT,
                content="Recent message",
                metadata={},
                is_recalled=False,
                is_read=False,
                timestamp=current_time - 60  # 1 minute ago
            ),
            Message(
                id="msg-2",
                session_id=session_id,
                sender_id="assistant",
                type=MessageType.TEXT,
                content="Old message",
                metadata={},
                is_recalled=False,
                is_read=False,
                timestamp=current_time - 300  # 5 minutes ago
            ),
            Message(
                id="msg-3",
                session_id=session_id,
                sender_id="user",
                type=MessageType.TEXT,
                content="User message",
                metadata={},
                is_recalled=False,
                is_read=False,
                timestamp=current_time - 30  # 30 seconds ago
            ),
        ]
        
        self.mock_message_service.get_messages = AsyncMock(return_value=messages)
        
        result = await self.tool_service.get_recallable_messages(session_id)
        
        assert "recallable_messages" in result
        # Should only include msg-1 (recent assistant message)
        assert len(result["recallable_messages"]) == 1
        assert result["recallable_messages"][0]["id"] == "msg-1"

    @pytest.mark.asyncio
    async def test_recall_message_by_id_success(self):
        """Test successfully recalling a message."""
        session_id = "test-session"
        message_id = "msg-1"
        current_time = datetime.now(timezone.utc).timestamp()
        
        message = Message(
            id=message_id,
            session_id=session_id,
            sender_id="assistant",
            type=MessageType.TEXT,
            content="Test message",
            metadata={},
            is_recalled=False,
            is_read=False,
            timestamp=current_time - 60  # 1 minute ago
        )
        
        recall_message = Message(
            id="recall-1",
            session_id=session_id,
            sender_id="system",
            type=MessageType.SYSTEM_RECALL,
            content="",
            metadata={"target_message_id": message_id},
            is_recalled=False,
            is_read=False,
            timestamp=current_time
        )
        
        self.mock_message_service.get_message = AsyncMock(return_value=message)
        self.mock_message_service.recall_message = AsyncMock(return_value=recall_message)
        
        result = await self.tool_service.recall_message_by_id(session_id, message_id)
        
        assert result["success"] is True
        assert result["recalled_message_id"] == message_id

    @pytest.mark.asyncio
    async def test_recall_message_by_id_too_old(self):
        """Test recalling a message that's too old (>2 minutes)."""
        session_id = "test-session"
        message_id = "msg-1"
        current_time = datetime.now(timezone.utc).timestamp()
        
        TWO_MINUTES_IN_SECONDS = 120
        
        message = Message(
            id=message_id,
            session_id=session_id,
            sender_id="assistant",
            type=MessageType.TEXT,
            content="Old message",
            metadata={},
            is_recalled=False,
            is_read=False,
            timestamp=current_time - (TWO_MINUTES_IN_SECONDS + 20)  # 2min 20sec ago
        )
        
        self.mock_message_service.get_message = AsyncMock(return_value=message)
        
        result = await self.tool_service.recall_message_by_id(session_id, message_id)
        
        assert result["success"] is False
        assert "older than 2 minutes" in result["error"]

    @pytest.mark.asyncio
    async def test_block_user(self):
        """Test blocking a user."""
        session_id = "test-session"
        current_time = datetime.now(timezone.utc).timestamp()
        
        blocked_message = Message(
            id="blocked-1",
            session_id=session_id,
            sender_id="system",
            type=MessageType.SYSTEM_BLOCKED,
            content="",
            metadata={},
            is_recalled=False,
            is_read=False,
            timestamp=current_time
        )
        
        self.mock_message_service.send_message = AsyncMock(return_value=blocked_message)
        
        result = await self.tool_service.block_user(session_id)
        
        assert result["success"] is True
        assert result["blocked"] is True
        assert "blocked_message_id" in result

    @pytest.mark.asyncio
    async def test_execute_tool_unknown(self):
        """Test executing an unknown tool."""
        result = await self.tool_service.execute_tool(
            tool_name="unknown_tool",
            tool_args={},
            session_id="test-session",
            character_avatar="",
            user_avatar=""
        )
        
        assert "error" in result
        assert "Unknown tool" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_get_image_description(self):
        """Test executing get_image_description tool."""
        image_id = "msg-image-1"
        session_id = "test-session"
        current_time = datetime.now(timezone.utc).timestamp()
        
        image_message = Message(
            id=image_id,
            session_id=session_id,
            sender_id="user",
            type=MessageType.IMAGE,
            content="data/images/test.png",
            metadata={},
            is_recalled=False,
            is_read=False,
            timestamp=current_time
        )
        
        self.mock_message_service.get_message = AsyncMock(return_value=image_message)
        
        result = await self.tool_service.execute_tool(
            tool_name="get_image_description",
            tool_args={"image_id": image_id},
            session_id=session_id,
            character_avatar="",
            user_avatar=""
        )
        
        assert "image_id" in result
        assert result["image_id"] == image_id
        assert "description" in result

    @pytest.mark.asyncio
    async def test_execute_tool_get_image_description_missing_arg(self):
        """Test executing get_image_description tool without required argument."""
        result = await self.tool_service.execute_tool(
            tool_name="get_image_description",
            tool_args={},
            session_id="test-session",
            character_avatar="",
            user_avatar=""
        )
        
        assert "error" in result
        assert "image_id is required" in result["error"]
