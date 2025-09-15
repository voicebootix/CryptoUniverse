#!/usr/bin/env python3
"""
Test opportunity discovery after the fixes
"""

import requests
import json
import time

def test_opportunity_discovery_after_fixes():
    """Test opportunity discovery after fixes"""
    
    base_url = "https://cryptouniverse.onrender.com/api/v1"
    
    # Login
    login_data = {
        "email": "admin@cryptouniverse.com", 
        "password": "AdminPass123!"
    }
    
    response = requests.post(f"{base_url}/auth/login", json=login_data, timeout=30)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return
    
    token = response.json().get("access_token")
    user_id = response.json().get("user_id")
    headers = {"Authorization": f"Bearer {token}"}
    
    print("🚀 TESTING OPPORTUNITY DISCOVERY AFTER FIXES")
    print("="*60)
    print(f"✅ Login successful")
    print(f"🆔 User ID: {user_id}")
    
    # Test 1: Strategy execution (should work now)
    print(f"\n1️⃣ Testing strategy execution (simulation_mode fix):")
    
    strategy_functions = ["risk_management", "portfolio_optimization", "spot_momentum_strategy"]
    
    for strategy_func in strategy_functions:
        print(f"\n   🎯 Testing {strategy_func}:")
        
        try:
            execute_data = {
                "function": strategy_func,
                "symbol": "BTC/USDT",
                "parameters": {}
            }
            
            execute_response = requests.post(f"{base_url}/strategies/execute", 
                                           headers=headers, 
                                           json=execute_data,
                                           timeout=60)
            
            print(f"      Status: {execute_response.status_code}")
            
            if execute_response.status_code == 200:
                execute_result = execute_response.json()
                print(f"      ✅ Success: {execute_result.get('success')}")
                print(f"      Function: {execute_result.get('function')}")
                
                # Check response structure
                if 'result' in execute_result:
                    result = execute_result['result']
                    if isinstance(result, dict):
                        print(f"      Result keys: {list(result.keys())}")
                        
                        # Check for expected fields based on strategy
                        if strategy_func == "risk_management":
                            if 'risk_management_analysis' in result:
                                analysis = result['risk_management_analysis']
                                if 'mitigation_strategies' in analysis:
                                    strategies = analysis['mitigation_strategies']
                                    print(f"      ✅ Found mitigation_strategies: {len(strategies)}")
                                else:
                                    print(f"      ❌ No mitigation_strategies in analysis")
                            else:
                                print(f"      ❌ No risk_management_analysis in result")
                        
                        elif strategy_func == "portfolio_optimization":
                            # Check what fields are actually available
                            print(f"      Available fields for portfolio_optimization: {list(result.keys())}")
                        
                        elif strategy_func == "spot_momentum_strategy":
                            # Check for momentum-related fields
                            print(f"      Available fields for spot_momentum_strategy: {list(result.keys())}")
            else:
                print(f"      ❌ Error: {execute_response.text[:200]}")
                
        except Exception as e:
            print(f"      Exception: {e}")
    
    # Test 2: Opportunity discovery endpoint
    print(f"\n2️⃣ Testing opportunity discovery endpoint:")
    
    try:
        discover_data = {
            "force_refresh": True,
            "include_strategy_recommendations": True
        }
        
        start_time = time.time()
        discover_response = requests.post(f"{base_url}/opportunities/discover", 
                                        headers=headers, 
                                        json=discover_data,
                                        timeout=120)
        response_time = time.time() - start_time
        
        print(f"   Status: {discover_response.status_code}")
        print(f"   Response time: {response_time:.2f}s")
        
        if discover_response.status_code == 200:
            discover_result = discover_response.json()
            print(f"   Success: {discover_result.get('success')}")
            print(f"   Total opportunities: {discover_result.get('total_opportunities', 0)}")
            print(f"   Execution time: {discover_result.get('execution_time_ms', 0):.2f}ms")
            
            if discover_result.get('error'):
                print(f"   Error: {discover_result['error']}")
            
            # Check user profile
            user_profile = discover_result.get('user_profile', {})
            if user_profile:
                print(f"   User profile:")
                print(f"      Active strategies: {user_profile.get('active_strategies', 0)}")
                print(f"      User tier: {user_profile.get('user_tier', 'Unknown')}")
            
            # Check opportunities
            opportunities = discover_result.get('opportunities', [])
            if opportunities:
                print(f"   ✅ FOUND {len(opportunities)} OPPORTUNITIES!")
                for i, opp in enumerate(opportunities[:5]):
                    print(f"      {i+1}. {opp.get('symbol')} on {opp.get('exchange')}")
                    print(f"         Strategy: {opp.get('strategy_name')}")
                    print(f"         Profit: ${opp.get('profit_potential_usd', 0):.2f}")
                    print(f"         Confidence: {opp.get('confidence_score', 0):.1f}%")
                    print(f"         Risk: {opp.get('risk_level')}")
            else:
                print(f"   ❌ Still no opportunities found")
                
                # Check strategy performance details
                strategy_performance = discover_result.get('strategy_performance', {})
                if strategy_performance:
                    print(f"   Strategy scan results:")
                    for strategy_id, perf in strategy_performance.items():
                        opportunities_found = perf.get('opportunities_found', 0)
                        success = perf.get('success', False)
                        error = perf.get('error', 'None')
                        print(f"      {strategy_id}: {opportunities_found} opportunities, success={success}, error={error}")
        else:
            print(f"   Error: {discover_response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Test 3: Chat opportunity discovery
    print(f"\n3️⃣ Testing chat opportunity discovery:")
    
    try:
        message_data = {
            "message": "Find me trading opportunities",
            "mode": "trading"
        }
        
        start_time = time.time()
        chat_response = requests.post(f"{base_url}/chat/message", 
                                     json=message_data, 
                                     headers=headers, 
                                     timeout=120)
        response_time = time.time() - start_time
        
        print(f"   Status: {chat_response.status_code}")
        print(f"   Response time: {response_time:.2f}s")
        
        if chat_response.status_code == 200:
            chat_data = chat_response.json()
            print(f"   Success: {chat_data.get('success')}")
            print(f"   Intent: {chat_data.get('intent')}")
            
            content = chat_data.get('content', '')
            print(f"   Content preview: {content[:200]}...")
            
            metadata = chat_data.get('metadata', {})
            opportunities = metadata.get('opportunities', [])
            print(f"   Chat opportunities: {len(opportunities)}")
            
            if opportunities:
                print(f"   ✅ CHAT FOUND OPPORTUNITIES!")
                for i, opp in enumerate(opportunities[:3]):
                    print(f"      {i+1}. {opp.get('symbol', 'Unknown')}: {opp.get('confidence', 0)}% confidence")
            else:
                print(f"   ❌ Chat still found no opportunities")
        else:
            print(f"   Error: {chat_response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    print(f"\n{'='*60}")
    print("📊 RESULTS ANALYSIS:")
    print("If strategy execution now works (200 status) and")
    print("opportunity discovery finds opportunities > 0,")
    print("then the fixes were successful!")

if __name__ == "__main__":
    test_opportunity_discovery_after_fixes()