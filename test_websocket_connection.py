#!/usr/bin/env python
"""
WebSocket connection test script
Run this to verify the server is working correctly
"""
import asyncio
import websockets
import json
import sys

async def test_websocket():
    uri = "ws://localhost:8000/api/ws/test-conversation?user_id=test"

    print("=" * 60)
    print("WebSocket Connection Test")
    print("=" * 60)
    print(f"\nConnecting to: {uri}")

    try:
        async with websockets.connect(uri) as websocket:
            print("✓ WebSocket connected successfully!")

            # Receive history message
            history = await websocket.recv()
            history_data = json.loads(history)
            print(f"✓ Received history: {history_data['type']}")

            # Send a test message
            test_message = {
                "type": "message",
                "id": "test-msg-1",
                "content": "Hello from test script"
            }
            print(f"\nSending test message...")
            await websocket.send(json.dumps(test_message))
            print("✓ Message sent successfully")

            # Receive echo
            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            response_data = json.loads(response)
            print(f"✓ Received response: {response_data['type']}")

            print("\n" + "=" * 60)
            print("✅ All tests passed! WebSocket is working correctly.")
            print("=" * 60)

    except websockets.exceptions.WebSocketException as e:
        print(f"\n❌ WebSocket connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure the server is running (python run.py)")
        print("2. Check if port 8000 is accessible")
        print("3. Verify no firewall is blocking the connection")
        sys.exit(1)

    except asyncio.TimeoutError:
        print(f"\n❌ Timeout waiting for server response")
        print("\nThe connection was established but the server didn't respond.")
        print("This might indicate an issue with the server-side code.")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_websocket())
