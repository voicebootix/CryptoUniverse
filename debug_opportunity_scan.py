#!/usr/bin/env python3
"""
Debug Opportunity Scan - Get Real Results
"""

import asyncio
import aiohttp
import json
import time


async def debug_opportunity_scan():
    """Debug why opportunity scan is not providing real results."""
    base_url = "https://cryptouniverse.onrender.com"
    
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=120),
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
        
        # Check admin strategy access
        print("\n🔍 Checking admin strategy access...")
        try:
            async with session.get(
                f"{base_url}/api/v1/admin-strategy-access/admin-portfolio-status",
                headers=headers
            ) as response:
                print(f"Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Admin portfolio status retrieved")
                    print(f"Success: {data.get('success')}")
                    print(f"Total Strategies: {data.get('total_strategies', 0)}")
                    print(f"Active Strategies: {data.get('active_strategies', 0)}")
                    if data.get('strategies'):
                        print(f"Available Strategies:")
                        for i, strategy in enumerate(data['strategies'][:10]):  # Show first 10
                            print(f"  {i+1}. {strategy.get('name', 'Unknown')} - {strategy.get('status', 'Unknown')}")
                else:
                    text = await response.text()
                    print(f"❌ Admin portfolio check failed: {response.status}")
                    print(f"Response: {text[:500]}...")
        except Exception as e:
            print(f"❌ Admin portfolio check error: {e}")
        
        # Check marketplace strategies
        print("\n🏪 Checking marketplace strategies...")
        try:
            async with session.get(
                f"{base_url}/api/v1/strategies/marketplace",
                headers=headers
            ) as response:
                print(f"Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Marketplace strategies retrieved")
                    print(f"Success: {data.get('success')}")
                    if data.get('strategies'):
                        print(f"Marketplace Strategies: {len(data['strategies'])}")
                        for i, strategy in enumerate(data['strategies'][:10]):  # Show first 10
                            print(f"  {i+1}. {strategy.get('name', 'Unknown')} - {strategy.get('category', 'Unknown')}")
                else:
                    text = await response.text()
                    print(f"❌ Marketplace check failed: {response.status}")
                    print(f"Response: {text[:500]}...")
        except Exception as e:
            print(f"❌ Marketplace check error: {e}")
        
        # Initiate opportunity discovery
        print("\n🚀 Initiating opportunity discovery...")
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
                    print(f"✅ Opportunity discovery initiated")
                    print(f"Scan ID: {data.get('scan_id')}")
                    print(f"Status: {data.get('status')}")
                    print(f"Message: {data.get('message')}")
                    print(f"Estimated Completion: {data.get('estimated_completion_seconds')}s")
                    
                    scan_id = data.get('scan_id')
                    
                    # Wait and check status multiple times
                    print(f"\n⏳ Monitoring scan progress...")
                    for i in range(10):  # Check 10 times
                        await asyncio.sleep(5)  # Wait 5 seconds between checks
                        
                        try:
                            async with session.get(
                                f"{base_url}/api/v1/opportunities/status/{scan_id}",
                                headers=headers
                            ) as status_response:
                                if status_response.status == 200:
                                    status_data = await status_response.json()
                                    print(f"Check {i+1}: Status={status_data.get('status')}, "
                                          f"Opportunities={status_data.get('total_opportunities', 0)}, "
                                          f"Progress={status_data.get('metadata', {}).get('progress_percentage', 0)}%")
                                    
                                    # Check results if scan is complete
                                    if status_data.get('status') in ['completed', 'success']:
                                        print(f"\n📊 Checking final results...")
                                        async with session.get(
                                            f"{base_url}/api/v1/opportunities/results/{scan_id}",
                                            headers=headers
                                        ) as results_response:
                                            if results_response.status == 200:
                                                results_data = await results_response.json()
                                                print(f"✅ Results retrieved")
                                                print(f"Total Opportunities: {results_data.get('total_opportunities', 0)}")
                                                print(f"Scan State: {results_data.get('scan_state', 'unknown')}")
                                                
                                                if results_data.get('opportunities'):
                                                    print(f"Opportunities found: {len(results_data['opportunities'])}")
                                                    for j, opp in enumerate(results_data['opportunities'][:5]):
                                                        print(f"  {j+1}. {opp.get('strategy_name', 'Unknown')}")
                                                        print(f"     Symbol: {opp.get('symbol', 'N/A')}")
                                                        print(f"     Action: {opp.get('action', 'N/A')}")
                                                        print(f"     Confidence: {opp.get('confidence', 0)}%")
                                                        print(f"     Entry Price: {opp.get('entry_price', 'N/A')}")
                                                        print(f"     Target Price: {opp.get('target_price', 'N/A')}")
                                                else:
                                                    print("No opportunities found")
                                            else:
                                                print(f"❌ Results check failed: {results_response.status}")
                                        break
                                else:
                                    print(f"Check {i+1}: Status check failed: {status_response.status}")
                        except Exception as e:
                            print(f"Check {i+1}: Error: {e}")
                else:
                    text = await response.text()
                    print(f"❌ Opportunity discovery failed: {response.status}")
                    print(f"Response: {text[:500]}...")
        except Exception as e:
            print(f"❌ Opportunity discovery error: {e}")


if __name__ == "__main__":
    asyncio.run(debug_opportunity_scan())