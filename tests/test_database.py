#!/usr/bin/env python
"""Test database operations"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import tempfile
from datetime import datetime
from src.message_server.database import MessageDatabase
from src.message_server.models import Message, MessageType


def test_database_initialization():
    print("Testing database initialization...")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    MessageDatabase(db_path)
    assert os.path.exists(db_path)
    os.unlink(db_path)
    print("✓ Database initialization successful")


def test_save_message():
    print("Testing save message...")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    db = MessageDatabase(db_path)

    message = Message(
        id="test-msg-1",
        conversation_id="conv-1",
        sender_id="user",
        type=MessageType.TEXT,
        content="Test message",
        timestamp=datetime.now().timestamp(),
        metadata={"test": True}
    )

    success = db.save_message(message)
    assert success, "Failed to save message"

    os.unlink(db_path)
    print("✓ Save message successful")


def test_get_messages():
    print("Testing get messages...")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    db = MessageDatabase(db_path)

    for i in range(5):
        message = Message(
            id=f"msg-{i}",
            conversation_id="conv-1",
            sender_id="user" if i % 2 == 0 else "rin",
            type=MessageType.TEXT,
            content=f"Message {i}",
            timestamp=datetime.now().timestamp() + i,
            metadata={}
        )
        db.save_message(message)

    messages = db.get_messages("conv-1")
    assert len(messages) == 5, f"Expected 5 messages, got {len(messages)}"

    assert messages[0].id == "msg-0"
    assert messages[4].id == "msg-4"

    os.unlink(db_path)
    print("✓ Get messages successful")


def test_get_messages_with_limit():
    print("Testing get messages with limit...")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    db = MessageDatabase(db_path)

    for i in range(10):
        message = Message(
            id=f"msg-{i}",
            conversation_id="conv-1",
            sender_id="user",
            type=MessageType.TEXT,
            content=f"Message {i}",
            timestamp=datetime.now().timestamp() + i,
            metadata={}
        )
        db.save_message(message)

    messages = db.get_messages("conv-1", limit=3)
    assert len(messages) == 3, f"Expected 3 messages, got {len(messages)}"

    os.unlink(db_path)
    print("✓ Get messages with limit successful")


def test_get_messages_after_timestamp():
    print("Testing get messages after timestamp...")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    db = MessageDatabase(db_path)

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
        db.save_message(message)

    messages = db.get_messages("conv-1", after_timestamp=base_timestamp + 2)
    assert len(messages) == 2, f"Expected 2 messages, got {len(messages)}"
    assert messages[0].id == "msg-3"
    assert messages[1].id == "msg-4"

    os.unlink(db_path)
    print("✓ Get messages after timestamp successful")



def test_clear_conversation():
    print("Testing clear conversation...")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    db = MessageDatabase(db_path)

    for i in range(5):
        message = Message(
            id=f"msg-{i}",
            conversation_id="conv-1",
            sender_id="user",
            type=MessageType.TEXT,
            content=f"Message {i}",
            timestamp=datetime.now().timestamp() + i,
            metadata={}
        )
        db.save_message(message)

    messages_before = db.get_messages("conv-1")
    assert len(messages_before) == 5

    success = db.clear_conversation("conv-1")
    assert success, "Failed to clear conversation"

    messages_after = db.get_messages("conv-1")
    assert len(messages_after) == 0, "Conversation not cleared"

    os.unlink(db_path)
    print("✓ Clear conversation successful")


def test_multiple_conversations():
    print("Testing multiple conversations...")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    db = MessageDatabase(db_path)

    for conv_id in ["conv-1", "conv-2", "conv-3"]:
        for i in range(3):
            message = Message(
                id=f"{conv_id}-msg-{i}",
                conversation_id=conv_id,
                sender_id="user",
                type=MessageType.TEXT,
                content=f"Message {i}",
                timestamp=datetime.now().timestamp() + i,
                metadata={}
            )
            db.save_message(message)

    messages_conv1 = db.get_messages("conv-1")
    messages_conv2 = db.get_messages("conv-2")
    messages_conv3 = db.get_messages("conv-3")

    assert len(messages_conv1) == 3
    assert len(messages_conv2) == 3
    assert len(messages_conv3) == 3

    db.clear_conversation("conv-2")
    messages_conv2_after = db.get_messages("conv-2")
    assert len(messages_conv2_after) == 0

    messages_conv1_after = db.get_messages("conv-1")
    assert len(messages_conv1_after) == 3

    os.unlink(db_path)
    print("✓ Multiple conversations test successful")


def run_all_tests():
    print("=" * 50)
    print("Running Database Tests")
    print("=" * 50)

    test_database_initialization()
    test_save_message()
    test_get_messages()
    test_get_messages_with_limit()
    test_get_messages_after_timestamp()
    test_clear_conversation()
    test_multiple_conversations()

    print("\n" + "=" * 50)
    print("✅ All database tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    run_all_tests()
