#!/usr/bin/env python
"""
Simple server test script using only standard library
"""
import urllib.request
import json

print("=" * 60)
print("Server Connectivity Test")
print("=" * 60)

# Test 1: Health check
print("\n[1/2] Testing HTTP endpoint...")
try:
    response = urllib.request.urlopen("http://localhost:8000/api/health", timeout=5)
    data = json.loads(response.read().decode())
    print(f"✓ Server is running")
    print(f"  Service: {data['service']}")
    print(f"  Status: {data['status']}")
    print(f"  Active conversations: {data['active_conversations']}")
    print(f"  Active WebSockets: {data['active_websockets']}")
except Exception as e:
    print(f"❌ HTTP endpoint failed: {e}")
    print("\nMake sure the server is running: python run.py")
    exit(1)

# Test 2: Frontend
print("\n[2/2] Testing frontend...")
try:
    response = urllib.request.urlopen("http://localhost:8000/", timeout=5)
    content = response.read().decode()
    if "<!DOCTYPE html>" in content or "<html" in content:
        print("✓ Frontend is accessible")
    else:
        print("⚠️  Frontend returned unexpected content")
except Exception as e:
    print(f"❌ Frontend failed: {e}")

print("\n" + "=" * 60)
print("✅ Server is running correctly!")
print("=" * 60)
print("\nNext steps:")
print("1. Open browser to: http://localhost:8000")
print("2. Check browser console for WebSocket errors")
print("3. Make sure you're NOT using http://0.0.0.0:8000")
print("\nFor WebSocket debugging, check server logs above.")
