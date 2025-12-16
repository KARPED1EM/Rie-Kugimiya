"""
Tests for message recall functionality.

This test verifies that:
1. SYSTEM_RECALL messages properly mark target messages as recalled
2. The LLM history includes recalled messages with system notifications
"""

import pytest
from datetime import datetime, timezone
from src.core.models.message import Message, MessageType
from src.services.session.session_service import SessionService
from src.core.schemas import LLMConfig, ChatMessage
from src.core.models.character import Character


class MockMessageService:
    """Mock message service for testing."""
    
    def __init__(self):
        self.messages = []
    
    async def get_messages(self, session_id):
        return self.messages
    
    def set_messages(self, messages):
        self.messages = messages


class TestMessageRecall:
    """Test message recall handling."""
    
    def create_session_client(self, messages):
        """Create a SessionService with mocked dependencies."""
        mock_service = MockMessageService()
        mock_service.set_messages(messages)
        
        # Minimal LLM config for testing
        llm_config = LLMConfig(
            protocol="completions",
            api_key="test",
            base_url="http://test",
            model="test",
            user_nickname="TestUser"
        )
        
        # Minimal character config for testing
        behavior_config = {
            "segmenter": {"enable": False, "max_length": 50},
            "typo": {"enable": False, "base_rate": 0.0, "recall_rate": 0.0},
            "recall": {"enable": True, "delay": 1.0, "retype_delay": 0.5},
            "pause": {"min_duration": 0.2, "max_duration": 0.5},
        }

        character = Character(
            id="char1",
            name="TestChar",
            avatar="",
            persona="test persona",
            sticker_packs=[],
            behavior=behavior_config,
        )
        
        client = SessionService(
            message_service=mock_service,
            ws_manager=None,
            llm_config=llm_config,
            character=character
        )
        
        return client
    
    def test_recalled_message_in_llm_history(self):
        """Test that recalled messages appear in LLM history with system notification."""
        
        timestamp_base = datetime.now(timezone.utc).timestamp()
        
        messages = [
            # User message that will be recalled
            Message(
                id="msg1",
                session_id="sess1",
                sender_id="user",
                type=MessageType.TEXT,
                content="This message will be recalled",
                metadata={},
                is_recalled=True,  # Already marked as recalled
                is_read=True,
                timestamp=timestamp_base + 1
            ),
            # SYSTEM_RECALL message (should be ignored in LLM history)
            Message(
                id="recall1",
                session_id="sess1",
                sender_id="system",
                type=MessageType.SYSTEM_RECALL,
                content="",
                metadata={
                    "target_message_id": "msg1",
                    "target_timestamp": timestamp_base + 1,
                    "recalled_by": "user"
                },
                is_recalled=False,
                is_read=False,
                timestamp=timestamp_base + 2
            ),
            # Another user message (not recalled)
            Message(
                id="msg2",
                session_id="sess1",
                sender_id="user",
                type=MessageType.TEXT,
                content="This message is normal",
                metadata={},
                is_recalled=False,
                is_read=True,
                timestamp=timestamp_base + 3
            ),
        ]
        
        client = self.create_session_client(messages)
        history = client._build_llm_history(messages)
        
        # Convert to list of dicts for easier assertion
        history_dicts = [{"role": msg.role, "content": msg.content} for msg in history]
        
        # Expected history:
        # 1. The recalled message (msg1)
        # 2. A system notification about the recall
        # 3. The normal message (msg2)
        # (SYSTEM_RECALL message should not appear)
        
        assert len(history_dicts) == 3
        assert history_dicts[0]["role"] == "user"
        assert history_dicts[0]["content"] == "This message will be recalled"
        
        assert history_dicts[1]["role"] == "system"
        assert "撤回" in history_dicts[1]["content"]
        assert "上一条消息" in history_dicts[1]["content"]
        
        assert history_dicts[2]["role"] == "user"
        assert history_dicts[2]["content"] == "This message is normal"
    
    def test_system_recall_not_in_llm_history(self):
        """Test that SYSTEM_RECALL messages are not included in LLM history."""
        
        timestamp_base = datetime.now(timezone.utc).timestamp()
        
        messages = [
            Message(
                id="msg1",
                session_id="sess1",
                sender_id="user",
                type=MessageType.TEXT,
                content="Normal message",
                metadata={},
                is_recalled=False,
                is_read=True,
                timestamp=timestamp_base + 1
            ),
            Message(
                id="recall1",
                session_id="sess1",
                sender_id="system",
                type=MessageType.SYSTEM_RECALL,
                content="",
                metadata={
                    "target_message_id": "msg1",
                    "target_timestamp": timestamp_base + 1,
                    "recalled_by": "user"
                },
                is_recalled=False,
                is_read=False,
                timestamp=timestamp_base + 2
            ),
        ]
        
        client = self.create_session_client(messages)
        history = client._build_llm_history(messages)
        
        # Should only contain the normal message, not the SYSTEM_RECALL
        assert len(history) == 1
        assert history[0].role == "user"
        assert history[0].content == "Normal message"
    
    def test_assistant_recalled_message_in_llm_history(self):
        """Test that recalled assistant messages also get system notification."""
        
        timestamp_base = datetime.now(timezone.utc).timestamp()
        
        messages = [
            Message(
                id="msg1",
                session_id="sess1",
                sender_id="assistant",
                type=MessageType.TEXT,
                content="Assistant message recalled",
                metadata={},
                is_recalled=True,
                is_read=True,
                timestamp=timestamp_base + 1
            ),
        ]
        
        client = self.create_session_client(messages)
        history = client._build_llm_history(messages)
        
        assert len(history) == 2
        assert history[0].role == "assistant"
        assert history[0].content == "Assistant message recalled"
        
        assert history[1].role == "system"
        assert "撤回" in history[1].content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
