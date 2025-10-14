#!/usr/bin/env python3
"""
Specific Response Testing for Deployed Server
Tests specific chat responses and opportunity scan status
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime


async def test_specific_responses():
    """Test specific chat responses and opportunity scan status."""
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
        
        # Test 1: Get strategies access
        print("\n💬 Testing: 'What strategies do I have access to?'")
        async with session.post(
            f"{base_url}/api/v1/chat/message",
            json={"message": "What strategies do I have access to?", "session_id": f"test_{int(time.time())}"},
            headers=headers
        ) as response:
            data = await response.json()
            print(f"Status: {response.status}")
            print(f"Response: {data.get('content', 'No content')[:500]}...")
            print(f"Intent: {data.get('intent')}")
            print(f"Confidence: {data.get('confidence')}")
        
        # Test 2: Check opportunity scan status
        print("\n🔍 Checking opportunity scan status...")
        scan_id = "scan_7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af_1760444811"
        async with session.get(
            f"{base_url}/api/v1/opportunities/status/{scan_id}",
            headers=headers
        ) as response:
            data = await response.json()
            print(f"Status: {response.status}")
            print(f"Scan Status: {data.get('status')}")
            print(f"Message: {data.get('message')}")
            print(f"Total Opportunities: {data.get('total_opportunities', 0)}")
            print(f"Strategies Completed: {data.get('metadata', {}).get('strategies_completed', 0)}")
            print(f"Total Strategies: {data.get('metadata', {}).get('total_strategies', 0)}")
        
        # Test 3: Get opportunity results
        print("\n📊 Checking opportunity results...")
        async with session.get(
            f"{base_url}/api/v1/opportunities/results/{scan_id}",
            headers=headers
        ) as response:
            data = await response.json()
            print(f"Status: {response.status}")
            print(f"Success: {data.get('success')}")
            print(f"Total Opportunities: {data.get('total_opportunities', 0)}")
            if data.get('opportunities'):
                print(f"Opportunities found: {len(data['opportunities'])}")
                for i, opp in enumerate(data['opportunities'][:3]):  # Show first 3
                    print(f"  {i+1}. {opp.get('strategy_name', 'Unknown')} - {opp.get('confidence', 0)}% confidence")
            else:
                print("No opportunities found")
        
        # Test 4: Test portfolio endpoint with shorter timeout
        print("\n📈 Testing portfolio endpoint...")
        try:
            async with asyncio.wait_for(
                session.get(f"{base_url}/api/v1/unified-strategies/portfolio", headers=headers),
                timeout=30.0
            ) as response:
                data = await response.json()
                print(f"Status: {response.status}")
                print(f"Success: {data.get('success')}")
                if data.get('strategies'):
                    print(f"Strategies found: {len(data['strategies'])}")
                else:
                    print("No strategies data")
        except asyncio.TimeoutError:
            print("Portfolio endpoint timed out after 30s")
        
        # Test 5: Test marketplace endpoint
        print("\n🏪 Testing marketplace endpoint...")
        try:
            async with asyncio.wait_for(
                session.get(f"{base_url}/api/v1/strategies/marketplace", headers=headers),
                timeout=30.0
            ) as response:
                data = await response.json()
                print(f"Status: {response.status}")
                print(f"Success: {data.get('success')}")
                if data.get('strategies'):
                    print(f"Marketplace strategies: {len(data['strategies'])}")
                else:
                    print("No marketplace data")
        except asyncio.TimeoutError:
            print("Marketplace endpoint timed out after 30s")


if __name__ == "__main__":
    asyncio.run(test_specific_responses())