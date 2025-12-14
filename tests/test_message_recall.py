"""
Tests for message recall functionality.

This test verifies that:
1. SYSTEM_RECALL messages properly mark target messages as recalled
2. The LLM history includes recalled messages with system notifications
"""

import pytest
from datetime import datetime, timezone
from src.core.models.message import Message, MessageType
from src.services.session.session_client import SessionClient
from src.api.schemas import LLMConfig, ChatMessage
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
        """Create a SessionClient with mocked dependencies."""
        mock_service = MockMessageService()
        mock_service.set_messages(messages)
        
        # Minimal LLM config for testing
        llm_config = LLMConfig(
            llm_protocol="openai",
            llm_api_key="test",
            llm_base_url="http://test",
            llm_model="test",
            user_nickname="TestUser"
        )
        
        # Minimal character config for testing
        character = Character(
            id="char1",
            name="TestChar",
            avatar="",
            persona="test persona",
            is_builtin=False,
            hesitation_probability=0.0,
            hesitation_cycles_min=1,
            hesitation_cycles_max=2,
            hesitation_duration_min=100,
            hesitation_duration_max=200,
            hesitation_gap_min=50,
            hesitation_gap_max=100,
            typing_lead_time_threshold_1=10,
            typing_lead_time_1=500,
            typing_lead_time_threshold_2=20,
            typing_lead_time_2=1000,
            typing_lead_time_threshold_3=30,
            typing_lead_time_3=1500,
            typing_lead_time_threshold_4=40,
            typing_lead_time_4=2000,
            typing_lead_time_threshold_5=50,
            typing_lead_time_5=2500,
            typing_lead_time_default=3000,
            entry_delay_min=100,
            entry_delay_max=500,
            initial_delay_weight_1=0.5,
            initial_delay_range_1_min=200,
            initial_delay_range_1_max=400,
            initial_delay_weight_2=0.3,
            initial_delay_range_2_min=500,
            initial_delay_range_2_max=800,
            initial_delay_weight_3=0.2,
            initial_delay_range_3_min=1000,
            initial_delay_range_3_max=1500,
            initial_delay_range_4_min=2000,
            initial_delay_range_4_max=3000,
            enable_segmentation=False,
            enable_typo=False,
            enable_recall=True,
            enable_emotion_detection=False,
            max_segment_length=50,
            min_pause_duration=200,
            max_pause_duration=500,
            base_typo_rate=0.0,
            typo_recall_rate=0.0,
            recall_delay=1000,
            retype_delay=500,
            emoticon_packs=[]
        )
        
        client = SessionClient(
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
