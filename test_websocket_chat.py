#!/usr/bin/env python3
"""
WebSocket Chat Test Script

Tests the WebSocket chat functionality with authentication.
"""

import asyncio
import json
import websockets
import sys
from datetime import datetime

# Configuration
WEBSOCKET_URL = "wss://cryptouniverse.onrender.com/api/v1/chat/ws"
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3YTFlZThjZC1iZmM5LTRlNGUtODViMi02OWM4ZTkxMDU0YWYiLCJlbWFpbCI6ImFkbWluQGNyeXB0b3VuaXZlcnNlLmNvbSIsInJvbGUiOiJhZG1pbiIsInRlbmFudF9pZCI6IiIsImV4cCI6MTc1NzQ0NTEwMywiaWF0IjoxNzU3NDE3MTAzLCJqdGkiOiJhMTYyNzAxZjdkODRlMTAyMzJmYzc2ZGU1MGE4NzcyMzUiLCJ0eXBlIjoiYWNjZXNzIn0.B2CErhzWDlW5px-m24MZeTaPHIsgRPBZ8EO99pL2ZfU"
SESSION_ID = "test-session-123"

async def test_websocket_chat():
    """Test WebSocket chat functionality."""
    
    # WebSocket URL with session ID
    ws_url = f"{WEBSOCKET_URL}/{SESSION_ID}"
    
    # Use bearer token authentication via subprotocols
    subprotocols = ["bearer", ACCESS_TOKEN, "json"]
    
    print(f"🔗 Connecting to: {ws_url}")
    print(f"🔑 Using authentication subprotocols")
    
    try:
        async with websockets.connect(
            ws_url,
            subprotocols=subprotocols,
            ping_interval=30,
            ping_timeout=10
        ) as websocket:
            
            print("✅ WebSocket connected successfully!")
            print(f"📡 Selected subprotocol: {websocket.subprotocol}")
            
            # Listen for initial connection message
            try:
                initial_message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📨 Initial message: {initial_message}")
            except asyncio.TimeoutError:
                print("⚠️ No initial message received")
            
            # Send a test chat message
            test_message = {
                "type": "chat_message",
                "message": "Hello! Can you tell me the current Bitcoin price?",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            print(f"📤 Sending test message: {test_message['message']}")
            await websocket.send(json.dumps(test_message))
            
            # Wait for response
            print("⏳ Waiting for AI response...")
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                response_data = json.loads(response)
                print(f"📨 AI Response: {json.dumps(response_data, indent=2)}")
            except asyncio.TimeoutError:
                print("⚠️ No response received within 15 seconds")
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse response: {e}")
                print(f"Raw response: {response}")
            
            # Send a ping to test connection
            ping_message = {
                "type": "ping",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            print("📤 Sending ping...")
            await websocket.send(json.dumps(ping_message))
            
            # Wait for pong
            try:
                pong_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                pong_data = json.loads(pong_response)
                print(f"📨 Pong response: {json.dumps(pong_data, indent=2)}")
            except asyncio.TimeoutError:
                print("⚠️ No pong response received")
            
            # Keep connection alive for a bit to test stability
            print("⏳ Keeping connection alive for 10 seconds...")
            await asyncio.sleep(10)
            
            print("✅ WebSocket test completed successfully!")
            
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ WebSocket connection closed: {e}")
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ WebSocket connection failed with status: {e}")
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_websocket_without_auth():
    """Test WebSocket without authentication (should still work as guest)."""
    
    ws_url = f"{WEBSOCKET_URL}/guest-session"
    
    print(f"\n🔗 Testing without authentication...")
    print(f"🔗 Connecting to: {ws_url}")
    
    try:
        async with websockets.connect(
            ws_url,
            ping_interval=30,
            ping_timeout=10
        ) as websocket:
            
            print("✅ Guest WebSocket connected!")
            
            # Send a simple message
            test_message = {
                "type": "chat_message", 
                "message": "Hello as guest user!",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await websocket.send(json.dumps(test_message))
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                print(f"📨 Guest Response: {json.dumps(response_data, indent=2)}")
            except asyncio.TimeoutError:
                print("⚠️ No guest response received")
            
            print("✅ Guest WebSocket test completed!")
            
    except Exception as e:
        print(f"❌ Guest WebSocket test failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting WebSocket Chat Tests")
    print("=" * 50)
    
    # Test with authentication
    asyncio.run(test_websocket_chat())
    
    # Test without authentication  
    asyncio.run(test_websocket_without_auth())
    
    print("\n🎉 All WebSocket tests completed!")