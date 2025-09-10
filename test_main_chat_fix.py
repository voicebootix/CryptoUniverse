#!/usr/bin/env python3
"""
Test Main Chat Interface Fix
Verifies that both chat implementations work correctly.
"""

import requests
import json
import time

def test_chat_endpoints():
    """Test both chat implementations."""
    base_url = "https://cryptouniverse-backend.onrender.com"
    
    print("🧪 Testing Chat Endpoints...")
    print("=" * 50)
    
    # Test 1: Session Creation
    print("1. Testing Session Creation...")
    try:
        response = requests.post(f"{base_url}/api/v1/chat/session/new", 
                               json={}, 
                               timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                session_id = data.get('session_id')
                print(f"   ✅ Session created: {session_id}")
                
                # Test 2: Message Sending
                print("2. Testing Message Sending...")
                message_response = requests.post(f"{base_url}/api/v1/chat/message",
                                               json={
                                                   "message": "Hello, test message",
                                                   "session_id": session_id
                                               },
                                               timeout=30)
                
                if message_response.status_code == 200:
                    msg_data = message_response.json()
                    if msg_data.get('success'):
                        print(f"   ✅ Message sent successfully")
                        print(f"   📝 Response: {msg_data.get('content', '')[:100]}...")
                    else:
                        print(f"   ❌ Message failed: {msg_data}")
                else:
                    print(f"   ❌ Message request failed: {message_response.status_code}")
            else:
                print(f"   ❌ Session creation failed: {data}")
        else:
            print(f"   ❌ Session request failed: {response.status_code}")
    except Exception as e:
        print(f"   💥 Test failed: {str(e)}")
    
    print("\n🎯 EXPECTED RESULTS:")
    print("   • Both ChatWidget and ConversationalTradingInterface should work")
    print("   • Session creation should succeed")
    print("   • Message sending should get AI responses")
    print("   • No more 'AI is thinking...' infinite loading")

if __name__ == "__main__":
    test_chat_endpoints()