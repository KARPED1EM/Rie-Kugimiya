#!/usr/bin/env python
"""Test WebSocket manager"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
from src.message_server.websocket import WebSocketManager


class MockWebSocket:
    def __init__(self, name):
        self.name = name
        self.messages = []
        self.closed = False

    async def accept(self):
        pass

    async def send_json(self, data):
        if not self.closed:
            self.messages.append(data)
        else:
            raise Exception("WebSocket is closed")

    def close(self):
        self.closed = True


async def test_connect_and_disconnect():
    print("Testing connect and disconnect...")

    manager = WebSocketManager()
    ws = MockWebSocket("test-ws")

    await manager.connect(ws, "conv-1", "user-1")

    assert "conv-1" in manager.active_connections
    assert ws in manager.active_connections["conv-1"]
    assert manager.get_user_id(ws) == "user-1"

    manager.disconnect(ws, "conv-1")

    assert "conv-1" not in manager.active_connections
    assert ws not in manager.user_websockets

    print("✓ Connect and disconnect test successful")


async def test_multiple_connections():
    print("Testing multiple connections...")

    manager = WebSocketManager()
    ws1 = MockWebSocket("ws-1")
    ws2 = MockWebSocket("ws-2")
    ws3 = MockWebSocket("ws-3")

    await manager.connect(ws1, "conv-1", "user-1")
    await manager.connect(ws2, "conv-1", "user-2")
    await manager.connect(ws3, "conv-2", "user-3")

    assert len(manager.active_connections["conv-1"]) == 2
    assert len(manager.active_connections["conv-2"]) == 1

    assert manager.get_connection_count("conv-1") == 2
    assert manager.get_connection_count("conv-2") == 1

    print("✓ Multiple connections test successful")


async def test_send_to_conversation():
    print("Testing send to conversation...")

    manager = WebSocketManager()
    ws1 = MockWebSocket("ws-1")
    ws2 = MockWebSocket("ws-2")

    await manager.connect(ws1, "conv-1", "user-1")
    await manager.connect(ws2, "conv-1", "user-2")

    message = {"type": "test", "data": "hello"}
    await manager.send_to_conversation("conv-1", message)

    assert len(ws1.messages) == 1
    assert len(ws2.messages) == 1
    assert ws1.messages[0]["type"] == "test"
    assert ws2.messages[0]["data"] == "hello"

    print("✓ Send to conversation test successful")


async def test_send_to_conversation_with_exclusion():
    print("Testing send to conversation with exclusion...")

    manager = WebSocketManager()
    ws1 = MockWebSocket("ws-1")
    ws2 = MockWebSocket("ws-2")

    await manager.connect(ws1, "conv-1", "user-1")
    await manager.connect(ws2, "conv-1", "user-2")

    message = {"type": "test", "data": "hello"}
    await manager.send_to_conversation("conv-1", message, exclude_ws=ws1)

    assert len(ws1.messages) == 0, "ws1 should not receive message"
    assert len(ws2.messages) == 1, "ws2 should receive message"

    print("✓ Send to conversation with exclusion test successful")


async def test_send_to_websocket():
    print("Testing send to websocket...")

    manager = WebSocketManager()
    ws = MockWebSocket("test-ws")

    await manager.connect(ws, "conv-1", "user-1")

    message = {"type": "direct", "data": "message"}
    await manager.send_to_websocket(ws, message)

    assert len(ws.messages) == 1
    assert ws.messages[0]["type"] == "direct"

    print("✓ Send to websocket test successful")


async def test_get_conversation_connections():
    print("Testing get conversation connections...")

    manager = WebSocketManager()
    ws1 = MockWebSocket("ws-1")
    ws2 = MockWebSocket("ws-2")

    await manager.connect(ws1, "conv-1", "user-1")
    await manager.connect(ws2, "conv-1", "user-2")

    connections = manager.get_conversation_connections("conv-1")

    assert len(connections) == 2
    assert ws1 in connections
    assert ws2 in connections

    print("✓ Get conversation connections test successful")


async def test_disconnect_cleans_up():
    print("Testing disconnect cleans up...")

    manager = WebSocketManager()
    ws1 = MockWebSocket("ws-1")
    ws2 = MockWebSocket("ws-2")

    await manager.connect(ws1, "conv-1", "user-1")
    await manager.connect(ws2, "conv-1", "user-2")

    manager.disconnect(ws1, "conv-1")

    assert len(manager.active_connections["conv-1"]) == 1
    assert ws1 not in manager.active_connections["conv-1"]
    assert ws2 in manager.active_connections["conv-1"]

    manager.disconnect(ws2, "conv-1")

    assert "conv-1" not in manager.active_connections

    print("✓ Disconnect cleans up test successful")


async def test_failed_send_removes_connection():
    print("Testing failed send removes connection...")

    manager = WebSocketManager()
    ws1 = MockWebSocket("ws-1")
    ws2 = MockWebSocket("ws-2")

    await manager.connect(ws1, "conv-1", "user-1")
    await manager.connect(ws2, "conv-1", "user-2")

    ws1.close()

    message = {"type": "test", "data": "hello"}
    await manager.send_to_conversation("conv-1", message)

    assert ws1 not in manager.active_connections.get("conv-1", set())
    assert ws2 in manager.active_connections["conv-1"]
    assert len(ws2.messages) == 1

    print("✓ Failed send removes connection test successful")


async def run_all_tests():
    print("=" * 50)
    print("Running WebSocket Manager Tests")
    print("=" * 50)

    await test_connect_and_disconnect()
    await test_multiple_connections()
    await test_send_to_conversation()
    await test_send_to_conversation_with_exclusion()
    await test_send_to_websocket()
    await test_get_conversation_connections()
    await test_disconnect_cleans_up()
    await test_failed_send_removes_connection()

    print("\n" + "=" * 50)
    print("✅ All WebSocket manager tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
