#!/usr/bin/env python3
"""
Simple WebSocket client to test CryptoUniverse chat WebSocket functionality
"""

import asyncio
import json
import websockets
from websockets.exceptions import ConnectionClosed

async def test_websocket():
    """Test the WebSocket chat endpoint"""
    
    # WebSocket URL and session ID
    session_id = "test_session_123"
    ws_url = f"wss://cryptouniverse.onrender.com/api/v1/chat/ws/{session_id}"
    
    # Authentication token (updated)
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3YTFlZThjZC1iZmM5LTRlNGUtODViMi02OWM4ZTkxMDU0YWYiLCJlbWFpbCI6ImFkbWluQGNyeXB0b3VuaXZlcnNlLmNvbSIsInJvbGUiOiJhZG1pbiIsInRlbmFudF9pZCI6IiIsImV4cCI6MTc1NzYxNjM2NywiaWF0IjoxNzU3NTg3NTY3LCJqdGkiOiJkNjQ1NjVkYzA1ZDM5YTU4MWRjZTk1OGFkZjlmOGQwNyIsInR5cGUiOiJhY2Nlc3MifQ.jHvphAjB9ezYP5_BawSz2hKZjCXTDhWvtmkyjabt5rk"
    
    try:
        print(f"Connecting to WebSocket: {ws_url}")
        
        # Connect with bearer authentication via subprotocols
        subprotocols = ["bearer", token, "json"]
        
        async with websockets.connect(
            ws_url, 
            subprotocols=subprotocols
        ) as websocket:
            
            print("[OK] WebSocket connected successfully!")
            print(f"Selected subprotocol: {websocket.subprotocol}")
            
            # Wait for connection confirmation
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                response_data = json.loads(response)
                print(f"[RECV] Connection message: {response_data}")
            except asyncio.TimeoutError:
                print("[TIMEOUT] No initial connection message received")
            
            # Send a test chat message
            test_message = {
                "type": "chat_message",
                "message": "Hello, can you give me a quick market update?",
                "timestamp": "2025-09-11T10:25:00Z"
            }
            
            print(f"[SEND] Sending message: {test_message}")
            await websocket.send(json.dumps(test_message))
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=30)
                response_data = json.loads(response)
                print(f"[RECV] Chat response: {response_data}")
                
                if response_data.get("type") == "chat_response":
                    print(f"[OK] Chat content: {response_data.get('content', 'No content')}")
                    print(f"[INFO] Intent: {response_data.get('intent', 'Unknown')}")
                    print(f"[INFO] Confidence: {response_data.get('confidence', 0)}")
                
            except asyncio.TimeoutError:
                print("[TIMEOUT] No response received within 30 seconds")
            
            # Send ping message
            ping_message = {
                "type": "ping",
                "timestamp": "2025-09-11T10:25:10Z"
            }
            
            print(f"[SEND] Sending ping: {ping_message}")
            await websocket.send(json.dumps(ping_message))
            
            # Wait for pong
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                response_data = json.loads(response)
                # Handle Unicode characters safely for Windows console
                response_str = str(response_data).encode('ascii', 'replace').decode('ascii')
                print(f"[RECV] Pong response: {response_str}")
                
            except asyncio.TimeoutError:
                print("[TIMEOUT] No pong response received")
            
            print("[OK] WebSocket test completed successfully!")
            
    except ConnectionClosed as e:
        print(f"[ERROR] WebSocket connection closed: {e}")
    except Exception as e:
        print(f"[ERROR] WebSocket test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Install websockets if not available
    try:
        import websockets
    except ImportError:
        print("Installing websockets package...")
        import subprocess
        subprocess.check_call(["pip", "install", "websockets"])
        import websockets
    
    # Run the test
    asyncio.run(test_websocket())