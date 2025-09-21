#!/usr/bin/env python3
"""
Debug Marketplace Loading Issue
"""

import asyncio
import aiohttp
import json

async def test_marketplace_api():
    """Test the marketplace API endpoint"""

    # First login to get token
    login_url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    marketplace_url = "https://cryptouniverse.onrender.com/api/v1/strategies/marketplace"

    login_data = {
        "email": "admin@cryptouniverse.com",
        "password": "AdminPass123!"
    }

    try:
        async with aiohttp.ClientSession() as session:
            # Login first
            print("Logging in...")
            async with session.post(login_url, json=login_data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"Login failed: {response.status}")
                    print(f"Error: {error_text}")
                    return

                login_result = await response.json()
                token = login_result.get("access_token")
                print(f"Login successful, got token")

            # Test marketplace
            print("Testing marketplace endpoint...")
            headers = {"Authorization": f"Bearer {token}"}
            async with session.get(marketplace_url, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"Marketplace failed: {response.status}")
                    print(f"Error: {error_text}")
                    return

                marketplace_result = await response.json()
                strategies = marketplace_result.get("strategies", [])
                print(f"Marketplace success: {len(strategies)} strategies found")

                if strategies:
                    print(f"First strategy: {strategies[0].get('name', 'Unknown')}")
                else:
                    print("No strategies returned")
                    print(f"Full response: {json.dumps(marketplace_result, indent=2)}")

    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_marketplace_api())