#!/usr/bin/env python3
"""
Debug available strategies to understand the structure
"""

import requests
import json

def debug_available_strategies():
    """Debug available strategies endpoint"""
    
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
    
    print("🔍 Debugging available strategies...")
    print(f"✅ Login successful")
    print(f"🆔 User ID: {user_id}")
    
    # Test available strategies endpoint
    print(f"\n1️⃣ Testing /strategies/available:")
    try:
        response = requests.get(f"{base_url}/strategies/available", headers=headers, timeout=30)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Success: {data.get('success')}")
            print(f"   Total count: {data.get('total_count')}")
            
            strategies = data.get('available_strategies', [])
            print(f"   Available strategies: {len(strategies)}")
            
            # Look for our 3 strategies
            target_strategies = ['risk_management', 'portfolio_optimization', 'spot_momentum_strategy']
            
            for strategy_name in target_strategies:
                found = False
                for strategy in strategies:
                    if strategy_name in strategy.get('name', '').lower() or strategy_name in strategy.get('category', '').lower():
                        print(f"   ✅ Found {strategy_name}:")
                        print(f"      Name: {strategy.get('name')}")
                        print(f"      Category: {strategy.get('category')}")
                        print(f"      Description: {strategy.get('description', '')[:100]}...")
                        found = True
                        break
                
                if not found:
                    print(f"   ❌ {strategy_name} not found in available strategies")
            
            # Show all available strategies
            print(f"\n   📋 All available strategies:")
            for i, strategy in enumerate(strategies):
                print(f"      {i+1}. {strategy.get('name')} ({strategy.get('category')})")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Test marketplace endpoint
    print(f"\n2️⃣ Testing /strategies/marketplace:")
    try:
        response = requests.get(f"{base_url}/strategies/marketplace", headers=headers, timeout=30)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Success: {data.get('success')}")
            print(f"   Total strategies: {data.get('total_count')}")
            print(f"   AI strategies: {data.get('ai_strategies_count')}")
            
            strategies = data.get('strategies', [])
            
            # Look for our 3 strategies in marketplace
            target_strategies = ['risk_management', 'portfolio_optimization', 'spot_momentum_strategy']
            
            for strategy_name in target_strategies:
                found = False
                for strategy in strategies:
                    if strategy_name in strategy.get('name', '').lower():
                        print(f"   ✅ Found {strategy_name} in marketplace:")
                        print(f"      Name: {strategy.get('name')}")
                        print(f"      Cost: ${strategy.get('credit_cost_monthly', 0)}/month")
                        print(f"      Is AI: {strategy.get('is_ai_strategy', False)}")
                        found = True
                        break
                
                if not found:
                    print(f"   ❌ {strategy_name} not found in marketplace")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Try to execute a simple strategy to see the actual response structure
    print(f"\n3️⃣ Testing strategy execution with minimal parameters:")
    
    # Try different parameter combinations
    test_cases = [
        {"function": "risk_management"},
        {"function": "risk_management", "symbol": "BTC"},
        {"function": "risk_management", "parameters": {"analysis_type": "comprehensive"}},
        {"function": "portfolio_optimization"},
        {"function": "spot_momentum_strategy"}
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n   Test case {i+1}: {test_case}")
        try:
            response = requests.post(f"{base_url}/strategies/execute", 
                                   headers=headers, 
                                   json=test_case,
                                   timeout=30)
            
            print(f"      Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"      Success: {result.get('success')}")
                
                if 'result' in result:
                    strategy_result = result['result']
                    print(f"      Result keys: {list(strategy_result.keys()) if isinstance(strategy_result, dict) else 'Not a dict'}")
                    
                    # Show sample of actual response
                    print(f"      Sample response:")
                    print(f"      {json.dumps(result, indent=10)[:400]}...")
                    break  # Stop on first success
            else:
                error_text = response.text[:200]
                print(f"      Error: {error_text}")
                
        except Exception as e:
            print(f"      Exception: {e}")

if __name__ == "__main__":
    debug_available_strategies()