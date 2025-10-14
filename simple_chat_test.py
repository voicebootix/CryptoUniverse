#!/usr/bin/env python3
"""
Simple Chat Test with Error Handling
"""

import asyncio
import aiohttp
import json
import time


async def simple_chat_test():
    """Simple chat test with proper error handling."""
    base_url = "https://cryptouniverse.onrender.com"
    
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=60),
        headers={"Content-Type": "application/json"}
    ) as session:
        
        print("🔐 Authenticating...")
        # Authenticate
        try:
            async with session.post(
                f"{base_url}/api/v1/auth/login",
                json={"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}
            ) as response:
                if response.status == 200:
                    auth_data = await response.json()
                    token = auth_data.get("access_token")
                    print(f"✅ Authentication successful")
                else:
                    print(f"❌ Auth failed: {response.status}")
                    print(f"Response: {await response.text()}")
                    return
        except Exception as e:
            print(f"❌ Auth error: {e}")
            return
        
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        # Test chat with error handling
        print("\n💬 Testing chat endpoint...")
        try:
            async with session.post(
                f"{base_url}/api/v1/chat/message",
                json={"message": "Hello, what strategies do I have access to?", "session_id": f"test_{int(time.time())}"},
                headers=headers
            ) as response:
                print(f"Status: {response.status}")
                print(f"Content-Type: {response.headers.get('content-type')}")
                
                if response.status == 200:
                    try:
                        data = await response.json()
                        print(f"✅ Chat response successful")
                        print(f"Content: {data.get('content', 'No content')[:300]}...")
                        print(f"Intent: {data.get('intent')}")
                        print(f"Confidence: {data.get('confidence')}")
                    except Exception as e:
                        print(f"❌ JSON decode error: {e}")
                        text = await response.text()
                        print(f"Raw response: {text[:500]}...")
                else:
                    text = await response.text()
                    print(f"❌ Chat failed: {response.status}")
                    print(f"Response: {text[:500]}...")
        except Exception as e:
            print(f"❌ Chat request error: {e}")
        
        # Test opportunity discovery
        print("\n🔍 Testing opportunity discovery...")
        try:
            async with session.post(
                f"{base_url}/api/v1/opportunities/discover",
                json={
                    "risk_tolerance": "moderate",
                    "investment_objectives": ["growth", "balanced"],
                    "time_horizon": "medium_term",
                    "investment_amount": 5000,
                    "constraints": ["no_leverage"]
                },
                headers=headers
            ) as response:
                print(f"Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Opportunity discovery successful")
                    print(f"Scan ID: {data.get('scan_id')}")
                    print(f"Status: {data.get('status')}")
                    print(f"Message: {data.get('message')}")
                else:
                    text = await response.text()
                    print(f"❌ Opportunity discovery failed: {response.status}")
                    print(f"Response: {text[:500]}...")
        except Exception as e:
            print(f"❌ Opportunity discovery error: {e}")


if __name__ == "__main__":
    asyncio.run(simple_chat_test())