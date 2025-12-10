#!/usr/bin/env python
"""Integration tests for the complete system"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import tempfile
from datetime import datetime

from src.message_server.service import MessageService
from src.message_server.websocket import WebSocketManager
from src.message_server.models import Message, MessageType, TypingState
from src.behavior.coordinator import BehaviorCoordinator
from src.behavior.models import BehaviorConfig
from src.config import behavior_defaults


class MockLLMResponse:
    def __init__(self, reply, emotion_map=None):
        self.reply = reply
        self.emotion_map = emotion_map or {}
        self.raw_text = reply


class MockLLMClient:
    async def chat(self, history, character_name="Rin"):
        return MockLLMResponse(
            "你好！我是Rin。很高兴见到你！",
            emotion_map={"happy": "medium"}
        )

    async def close(self):
        pass


async def test_complete_message_flow():
    print("Testing complete message flow...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    message_service = MessageService(db_path)

    user_message = Message(
        id="user-msg-1",
        conversation_id="conv-1",
        sender_id="user",
        type=MessageType.TEXT,
        content="Hello Rin!",
        timestamp=datetime.now().timestamp(),
        metadata={}
    )

    await message_service.save_message(user_message)

    messages = await message_service.get_messages("conv-1")
    assert len(messages) == 1
    assert messages[0].content == "Hello Rin!"

    rin_message = Message(
        id="rin-msg-1",
        conversation_id="conv-1",
        sender_id="rin",
        type=MessageType.TEXT,
        content="你好！",
        timestamp=datetime.now().timestamp(),
        metadata={"emotion": "happy"}
    )

    await message_service.save_message(rin_message)

    all_messages = await message_service.get_messages("conv-1")
    assert len(all_messages) == 2

    os.unlink(db_path)
    print("✓ Complete message flow test successful")


async def test_behavior_to_message_flow():
    print("Testing behavior to message flow...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    message_service = MessageService(db_path)

    coordinator = BehaviorCoordinator(BehaviorConfig())

    llm_response_text = "你好！我是Rin。今天天气真不错呢！"
    emotion_map = {"happy": "high"}

    timeline = coordinator.process_message(llm_response_text, emotion_map=emotion_map)

    assert len(timeline) > 0, "Should generate timeline"

    send_actions = [a for a in timeline if a.type == "send"]
    assert len(send_actions) > 0, "Should have send actions"

    for action in send_actions:
        message = Message(
            id=action.message_id,
            conversation_id="conv-1",
            sender_id="rin",
            type=MessageType.TEXT,
            content=action.text,
            timestamp=datetime.now().timestamp(),
            metadata=action.metadata
        )
        await message_service.save_message(message)

    saved_messages = await message_service.get_messages("conv-1")
    assert len(saved_messages) == len(send_actions)

    os.unlink(db_path)
    print("✓ Behavior to message flow test successful")


async def test_typing_state_flow():
    print("Testing typing state flow...")

    message_service = MessageService()

    typing_start = TypingState(
        user_id="rin",
        conversation_id="conv-1",
        is_typing=True,
        timestamp=datetime.now().timestamp()
    )

    await message_service.set_typing_state(typing_start)

    states = await message_service.get_typing_states("conv-1")
    assert len(states) == 1
    assert states[0].is_typing is True

    await asyncio.sleep(0.1)

    typing_end = TypingState(
        user_id="rin",
        conversation_id="conv-1",
        is_typing=False,
        timestamp=datetime.now().timestamp()
    )

    await message_service.set_typing_state(typing_end)

    states_after = await message_service.get_typing_states("conv-1")
    assert len(states_after) == 0

    print("✓ Typing state flow test successful")


async def test_recall_flow():
    """测试完整的撤回流程：发送带错别字的消息 -> 撤回 -> 发送修正消息"""
    print("Testing recall flow...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    message_service = MessageService(db_path)

    # 1. 发送带错别字的消息
    typo_message = Message(
        id="msg-typo",
        conversation_id="conv-1",
        sender_id="rin",
        type=MessageType.TEXT,
        content="你hao！",
        timestamp=100.0,
        metadata={"has_typo": True}
    )
    await message_service.save_message(typo_message)

    # 2. 撤回消息（生成recall_event）
    recall_event = await message_service.recall_message("msg-typo", "conv-1", recalled_by="rin")
    assert recall_event is not None, "Should create recall event"
    assert recall_event.type == MessageType.RECALL_EVENT, "Should be recall_event type"
    assert recall_event.metadata["target_message_id"] == "msg-typo"

    # 3. 发送修正后的消息
    corrected_message = Message(
        id="msg-corrected",
        conversation_id="conv-1",
        sender_id="rin",
        type=MessageType.TEXT,
        content="你好！",
        timestamp=recall_event.timestamp + 1.0,
        metadata={"is_correction": True}
    )
    await message_service.save_message(corrected_message)

    # 4. 验证数据库中的消息
    all_messages = await message_service.get_messages("conv-1")
    assert len(all_messages) == 3, "Should have 3 messages: typo + recall_event + corrected"

    # 原消息仍然存在且未修改
    typo_msg = next((m for m in all_messages if m.id == "msg-typo"), None)
    assert typo_msg is not None, "Original typo message should still exist"
    assert typo_msg.type == MessageType.TEXT, "Original message type unchanged"
    assert typo_msg.content == "你hao！", "Original content unchanged"

    # 撤回事件存在
    recall_msg = next((m for m in all_messages if m.type == MessageType.RECALL_EVENT), None)
    assert recall_msg is not None, "Recall event should exist"

    # 修正消息存在
    corrected_msg = next((m for m in all_messages if m.id == "msg-corrected"), None)
    assert corrected_msg is not None, "Corrected message should exist"

    # 5. 验证增量同步能获取到撤回事件和修正消息
    new_messages = await message_service.get_messages("conv-1", after_timestamp=100.0)
    assert len(new_messages) == 2, "Should get recall_event and corrected message"
    assert new_messages[0].type == MessageType.RECALL_EVENT
    assert new_messages[1].id == "msg-corrected"

    os.unlink(db_path)
    print("✓ Recall flow test successful")


async def test_incremental_sync_flow():
    print("Testing incremental sync flow...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    message_service = MessageService(db_path)

    base_timestamp = datetime.now().timestamp()

    for i in range(3):
        message = Message(
            id=f"msg-{i}",
            conversation_id="conv-1",
            sender_id="user",
            type=MessageType.TEXT,
            content=f"Message {i}",
            timestamp=base_timestamp + i,
            metadata={}
        )
        await message_service.save_message(message)

    last_sync_timestamp = base_timestamp + 1

    await asyncio.sleep(0.1)

    for i in range(3, 5):
        message = Message(
            id=f"msg-{i}",
            conversation_id="conv-1",
            sender_id="rin",
            type=MessageType.TEXT,
            content=f"Message {i}",
            timestamp=base_timestamp + i,
            metadata={}
        )
        await message_service.save_message(message)

    new_messages = await message_service.get_messages("conv-1", after_timestamp=last_sync_timestamp)

    assert len(new_messages) == 3, f"Should get 3 new messages, got {len(new_messages)}"
    assert new_messages[0].id == "msg-2"
    assert new_messages[1].id == "msg-3"
    assert new_messages[2].id == "msg-4"

    os.unlink(db_path)
    print("✓ Incremental sync flow test successful")


async def test_multi_conversation_isolation():
    print("Testing multi-conversation isolation...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    message_service = MessageService(db_path)

    for conv_id in ["conv-1", "conv-2"]:
        for i in range(3):
            message = Message(
                id=f"{conv_id}-msg-{i}",
                conversation_id=conv_id,
                sender_id="user",
                type=MessageType.TEXT,
                content=f"Message {i} in {conv_id}",
                timestamp=datetime.now().timestamp() + i,
                metadata={}
            )
            await message_service.save_message(message)

    conv1_messages = await message_service.get_messages("conv-1")
    conv2_messages = await message_service.get_messages("conv-2")

    assert len(conv1_messages) == 3
    assert len(conv2_messages) == 3

    assert all(m.conversation_id == "conv-1" for m in conv1_messages)
    assert all(m.conversation_id == "conv-2" for m in conv2_messages)

    await message_service.clear_conversation("conv-1")

    conv1_after = await message_service.get_messages("conv-1")
    conv2_after = await message_service.get_messages("conv-2")

    assert len(conv1_after) == 0
    assert len(conv2_after) == 3

    os.unlink(db_path)
    print("✓ Multi-conversation isolation test successful")


async def test_timeline_execution_simulation():
    print("Testing timeline execution simulation...")

    coordinator = BehaviorCoordinator(BehaviorConfig())

    timeline = coordinator.process_message("测试消息", emotion_map={"neutral": "medium"})

    assert len(timeline) > 0

    current_time = 0
    executed_actions = []

    for action in timeline:
        wait_time = action.timestamp - current_time

        assert wait_time >= 0, f"Timeline should not go backwards: {wait_time}"

        current_time = action.timestamp
        executed_actions.append(action)

    assert len(executed_actions) == len(timeline)

    send_actions = [a for a in executed_actions if a.type == "send"]
    assert len(send_actions) > 0, "Should have executed send actions"

    print("✓ Timeline execution simulation test successful")


async def run_all_tests():
    print("=" * 50)
    print("Running Integration Tests")
    print("=" * 50)

    await test_complete_message_flow()
    await test_behavior_to_message_flow()
    await test_typing_state_flow()
    await test_recall_flow()
    await test_incremental_sync_flow()
    await test_multi_conversation_isolation()
    await test_timeline_execution_simulation()

    print("\n" + "=" * 50)
    print("✅ All integration tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
