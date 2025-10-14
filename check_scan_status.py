#!/usr/bin/env python3
"""
Check Opportunity Scan Status
"""

import asyncio
import aiohttp
import json
import time


async def check_scan_status():
    """Check the status of the opportunity scan."""
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
        
        # Check scan status
        scan_id = "scan_7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af_1760445006"
        print(f"\n🔍 Checking scan status for: {scan_id}")
        
        try:
            async with session.get(
                f"{base_url}/api/v1/opportunities/status/{scan_id}",
                headers=headers
            ) as response:
                print(f"Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Scan status retrieved")
                    print(f"Scan Status: {data.get('status')}")
                    print(f"Message: {data.get('message')}")
                    print(f"Total Opportunities: {data.get('total_opportunities', 0)}")
                    print(f"Strategies Completed: {data.get('metadata', {}).get('strategies_completed', 0)}")
                    print(f"Total Strategies: {data.get('metadata', {}).get('total_strategies', 0)}")
                    print(f"Progress: {data.get('metadata', {}).get('progress_percentage', 0)}%")
                else:
                    text = await response.text()
                    print(f"❌ Status check failed: {response.status}")
                    print(f"Response: {text[:500]}...")
        except Exception as e:
            print(f"❌ Status check error: {e}")
        
        # Check results
        print(f"\n📊 Checking scan results...")
        try:
            async with session.get(
                f"{base_url}/api/v1/opportunities/results/{scan_id}",
                headers=headers
            ) as response:
                print(f"Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Results retrieved")
                    print(f"Success: {data.get('success')}")
                    print(f"Total Opportunities: {data.get('total_opportunities', 0)}")
                    print(f"Scan State: {data.get('scan_state', 'unknown')}")
                    
                    if data.get('opportunities'):
                        print(f"Opportunities found: {len(data['opportunities'])}")
                        for i, opp in enumerate(data['opportunities'][:5]):  # Show first 5
                            print(f"  {i+1}. {opp.get('strategy_name', 'Unknown')} - {opp.get('confidence', 0)}% confidence")
                            print(f"     Symbol: {opp.get('symbol', 'N/A')}")
                            print(f"     Action: {opp.get('action', 'N/A')}")
                    else:
                        print("No opportunities found")
                else:
                    text = await response.text()
                    print(f"❌ Results check failed: {response.status}")
                    print(f"Response: {text[:500]}...")
        except Exception as e:
            print(f"❌ Results check error: {e}")


if __name__ == "__main__":
    asyncio.run(check_scan_status())