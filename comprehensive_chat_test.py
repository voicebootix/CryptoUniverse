#!/usr/bin/env python3
"""
Comprehensive Chat Response Testing
"""

import asyncio
import aiohttp
import json
import time


async def comprehensive_chat_test():
    """Test various chat responses to get comprehensive evidence."""
    base_url = "https://cryptouniverse.onrender.com"
    
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=60),
        headers={"Content-Type": "application/json"}
    ) as session:
        
        print("🔐 Authenticating...")
        # Authenticate
        async with session.post(
            f"{base_url}/api/v1/auth/login",
            json={"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}
        ) as response:
            auth_data = await response.json()
            token = auth_data.get("access_token")
            print(f"✅ Authentication successful")
        
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        # Test various chat messages
        test_messages = [
            "Hello, what strategies do I have access to?",
            "Find the best opportunities now",
            "Show my portfolio performance",
            "What's my credit balance?",
            "What are the best trading opportunities today?"
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n💬 Test {i}: '{message}'")
            try:
                async with session.post(
                    f"{base_url}/api/v1/chat/message",
                    json={"message": message, "session_id": f"test_{int(time.time())}_{i}"},
                    headers=headers
                ) as response:
                    print(f"Status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Response successful")
                        print(f"Content: {data.get('content', 'No content')[:400]}...")
                        print(f"Intent: {data.get('intent')}")
                        print(f"Confidence: {data.get('confidence')}")
                        
                        # Check if opportunities context is present
                        if 'opportunities' in data.get('context', {}):
                            opp_data = data['context']['opportunities']
                            print(f"Opportunities Context:")
                            print(f"  Success: {opp_data.get('success')}")
                            print(f"  Total: {opp_data.get('total_opportunities', 0)}")
                            print(f"  Scan State: {opp_data.get('scan_state', 'unknown')}")
                    else:
                        text = await response.text()
                        print(f"❌ Failed: {response.status}")
                        print(f"Response: {text[:300]}...")
            except Exception as e:
                print(f"❌ Error: {e}")
            
            # Wait between requests
            await asyncio.sleep(2)
        
        # Test health endpoint
        print(f"\n🏥 Testing health endpoint...")
        try:
            async with session.get(f"{base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Health check passed")
                    print(f"Status: {data.get('status')}")
                    print(f"Services: {list(data.get('services', {}).keys())}")
                else:
                    print(f"❌ Health check failed: {response.status}")
        except Exception as e:
            print(f"❌ Health check error: {e}")


if __name__ == "__main__":
    asyncio.run(comprehensive_chat_test())