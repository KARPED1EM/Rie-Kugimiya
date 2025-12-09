#!/usr/bin/env python
"""Test message service"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import tempfile
from datetime import datetime
from src.message_server.service import MessageService
from src.message_server.models import Message, MessageType, TypingState


async def test_save_and_get_messages():
    print("Testing save and get messages...")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    service = MessageService(db_path)

    message = Message(
        id="msg-1",
        conversation_id="conv-1",
        sender_id="user",
        type=MessageType.TEXT,
        content="Hello",
        timestamp=datetime.now().timestamp(),
        metadata={}
    )

    await service.save_message(message)
    messages = await service.get_messages("conv-1")

    assert len(messages) == 1
    assert messages[0].content == "Hello"

    os.unlink(db_path)
    print("✓ Save and get messages successful")


async def test_typing_states():
    print("Testing typing states...")
    service = MessageService()

    typing_state = TypingState(
        user_id="rin",
        conversation_id="conv-1",
        is_typing=True,
        timestamp=datetime.now().timestamp()
    )

    await service.set_typing_state(typing_state)

    states = await service.get_typing_states("conv-1")
    assert len(states) == 1
    assert states[0].user_id == "rin"
    assert states[0].is_typing is True

    typing_state.is_typing = False
    await service.set_typing_state(typing_state)

    states_after = await service.get_typing_states("conv-1")
    assert len(states_after) == 0

    print("✓ Typing states test successful")


async def test_clear_user_typing_state():
    print("Testing clear user typing state...")
    service = MessageService()

    typing_state = TypingState(
        user_id="rin",
        conversation_id="conv-1",
        is_typing=True,
        timestamp=datetime.now().timestamp()
    )

    await service.set_typing_state(typing_state)

    states_before = await service.get_typing_states("conv-1")
    assert len(states_before) == 1

    await service.clear_user_typing_state("rin", "conv-1")

    states_after = await service.get_typing_states("conv-1")
    assert len(states_after) == 0

    print("✓ Clear user typing state successful")


async def test_create_events():
    print("Testing create events...")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    service = MessageService(db_path)

    message = Message(
        id="msg-1",
        conversation_id="conv-1",
        sender_id="user",
        type=MessageType.TEXT,
        content="Test",
        timestamp=datetime.now().timestamp(),
        metadata={"emotion": "happy"}
    )

    message_event = service.create_message_event(message)
    assert message_event.type == "message"
    assert message_event.data["content"] == "Test"
    assert message_event.data["metadata"]["emotion"] == "happy"

    typing_state = TypingState(
        user_id="rin",
        conversation_id="conv-1",
        is_typing=True,
        timestamp=datetime.now().timestamp()
    )

    typing_event = service.create_typing_event(typing_state)
    assert typing_event.type == "typing"
    assert typing_event.data["is_typing"] is True

    clear_event = service.create_clear_event("conv-1")
    assert clear_event.type == "clear"

    messages = [message]
    history_event = service.create_history_event(messages)
    assert history_event.type == "history"
    assert len(history_event.data["messages"]) == 1

    os.unlink(db_path)
    print("✓ Create events test successful")


async def test_incremental_sync():
    print("Testing incremental sync...")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    service = MessageService(db_path)

    base_timestamp = datetime.now().timestamp()

    for i in range(5):
        message = Message(
            id=f"msg-{i}",
            conversation_id="conv-1",
            sender_id="user",
            type=MessageType.TEXT,
            content=f"Message {i}",
            timestamp=base_timestamp + i,
            metadata={}
        )
        await service.save_message(message)

    all_messages = await service.get_messages("conv-1")
    assert len(all_messages) == 5

    new_messages = await service.get_messages("conv-1", after_timestamp=base_timestamp + 2)
    assert len(new_messages) == 2
    assert new_messages[0].id == "msg-3"
    assert new_messages[1].id == "msg-4"

    os.unlink(db_path)
    print("✓ Incremental sync test successful")


async def test_recall_message_event():
    """测试新的撤回机制：撤回创建一个recall_event消息"""
    print("Testing recall message event mechanism...")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    service = MessageService(db_path)

    # 1. 创建原始消息
    original_message = Message(
        id="msg-original",
        conversation_id="conv-1",
        sender_id="rin",
        type=MessageType.TEXT,
        content="This will be recalled",
        timestamp=100.0,
        metadata={}
    )
    await service.save_message(original_message)

    # 2. 撤回消息
    recall_event = await service.recall_message("msg-original", "conv-1", recalled_by="rin")

    # 3. 验证撤回事件被创建
    assert recall_event is not None, "Recall event should be created"
    assert recall_event.type == MessageType.RECALL_EVENT, "Should be recall_event type"
    assert recall_event.sender_id == "system", "Should be sent by system"
    assert recall_event.metadata["target_message_id"] == "msg-original"
    assert recall_event.metadata["recalled_by"] == "rin"
    assert recall_event.metadata["original_sender"] == "rin"
    assert recall_event.timestamp > 100.0, "Recall event should have new timestamp"

    # 4. 验证原消息仍然存在且未修改
    original_still_exists = service.db.get_message_by_id("msg-original")
    assert original_still_exists is not None, "Original message should still exist"
    assert original_still_exists.type == MessageType.TEXT, "Original message type unchanged"
    assert original_still_exists.content == "This will be recalled", "Original content unchanged"

    # 5. 验证增量同步能获取到撤回事件
    messages_after = await service.get_messages("conv-1", after_timestamp=100.0)
    assert len(messages_after) == 1, "Should have 1 message (the recall event)"
    assert messages_after[0].type == MessageType.RECALL_EVENT

    # 6. 验证撤回不存在的消息返回None
    recall_nonexistent = await service.recall_message("non-existent", "conv-1", recalled_by="user")
    assert recall_nonexistent is None, "Recalling non-existent message should return None"

    os.unlink(db_path)
    print("✓ Recall message event mechanism test successful")


async def run_all_tests():
    print("=" * 50)
    print("Running Message Service Tests")
    print("=" * 50)

    await test_save_and_get_messages()
    await test_typing_states()
    await test_clear_user_typing_state()
    await test_create_events()
    await test_incremental_sync()
    await test_recall_message_event()

    print("\n" + "=" * 50)
    print("✅ All message service tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
