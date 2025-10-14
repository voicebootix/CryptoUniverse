#!/usr/bin/env python3
"""
Fix Strategy Execution and Test Opportunity Discovery
"""

import asyncio
import aiohttp
import json
import time


async def test_fixed_strategy_execution():
    """Test strategy execution with correct parameters."""
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
        
        # Test strategy execution with correct parameters
        print("\n🧪 Testing strategy execution with correct parameters...")
        
        # Test spot momentum strategy
        print(f"\n🔍 Testing spot_momentum_strategy...")
        try:
            async with session.post(
                f"{base_url}/api/v1/strategies/execute",
                json={
                    "function": "spot_momentum_strategy",
                    "symbols": ["BTC/USDT", "ETH/USDT"],
                    "parameters": {
                        "risk_tolerance": "moderate",
                        "investment_amount": 1000,
                        "timeframe": "1h",
                        "lookback_periods": 20
                    }
                },
                headers=headers
            ) as response:
                print(f"Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ spot_momentum_strategy executed successfully")
                    print(f"Success: {data.get('success')}")
                    if data.get('result'):
                        result = data['result']
                        print(f"Confidence: {result.get('confidence', 0)}%")
                        print(f"Action: {result.get('action', 'N/A')}")
                        print(f"Symbol: {result.get('symbol', 'N/A')}")
                        print(f"Entry Price: {result.get('entry_price', 'N/A')}")
                        print(f"Target Price: {result.get('target_price', 'N/A')}")
                else:
                    text = await response.text()
                    print(f"❌ spot_momentum_strategy failed: {response.status}")
                    print(f"Error: {text[:500]}...")
        except Exception as e:
            print(f"❌ spot_momentum_strategy error: {e}")
        
        # Test portfolio optimization strategy
        print(f"\n🔍 Testing portfolio_optimization_strategy...")
        try:
            async with session.post(
                f"{base_url}/api/v1/strategies/execute",
                json={
                    "function": "portfolio_optimization_strategy",
                    "symbols": ["BTC/USDT", "ETH/USDT", "BNB/USDT"],
                    "parameters": {
                        "risk_tolerance": "moderate",
                        "investment_amount": 5000,
                        "rebalance_frequency": "weekly",
                        "max_position_size": 0.3
                    }
                },
                headers=headers
            ) as response:
                print(f"Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ portfolio_optimization_strategy executed successfully")
                    print(f"Success: {data.get('success')}")
                    if data.get('result'):
                        result = data['result']
                        print(f"Confidence: {result.get('confidence', 0)}%")
                        print(f"Action: {result.get('action', 'N/A')}")
                        print(f"Optimization: {result.get('optimization', 'N/A')}")
                else:
                    text = await response.text()
                    print(f"❌ portfolio_optimization_strategy failed: {response.status}")
                    print(f"Error: {text[:500]}...")
        except Exception as e:
            print(f"❌ portfolio_optimization_strategy error: {e}")
        
        # Test opportunity discovery with a fresh scan
        print(f"\n🚀 Testing opportunity discovery with fresh scan...")
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
                    
                    scan_id = data.get('scan_id')
                    
                    # Wait longer and check more frequently
                    print(f"\n⏳ Extended monitoring (waiting up to 3 minutes)...")
                    for i in range(30):  # Check 30 times
                        await asyncio.sleep(6)  # Wait 6 seconds between checks
                        
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
                                    
                                    # Show detailed metadata
                                    metadata = status_data.get('metadata', {})
                                    if metadata:
                                        print(f"  Strategies Completed: {metadata.get('strategies_completed', 0)}")
                                        print(f"  Total Strategies: {metadata.get('total_strategies', 0)}")
                                        print(f"  Message: {metadata.get('message', 'N/A')}")
                                    
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
                                                    print(f"🎉 OPPORTUNITIES FOUND: {len(results_data['opportunities'])}")
                                                    for j, opp in enumerate(results_data['opportunities'][:10]):
                                                        print(f"  {j+1}. {opp.get('strategy_name', 'Unknown')}")
                                                        print(f"     Symbol: {opp.get('symbol', 'N/A')}")
                                                        print(f"     Action: {opp.get('action', 'N/A')}")
                                                        print(f"     Confidence: {opp.get('confidence', 0)}%")
                                                        print(f"     Entry Price: {opp.get('entry_price', 'N/A')}")
                                                        print(f"     Target Price: {opp.get('target_price', 'N/A')}")
                                                        print(f"     Stop Loss: {opp.get('stop_loss', 'N/A')}")
                                                        print(f"     Risk Level: {opp.get('risk_level', 'N/A')}")
                                                        print(f"     Timeframe: {opp.get('timeframe', 'N/A')}")
                                                else:
                                                    print("❌ No opportunities found")
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
    asyncio.run(test_fixed_strategy_execution())