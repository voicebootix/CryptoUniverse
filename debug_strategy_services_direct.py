#!/usr/bin/env python3
"""
Test the actual strategy services directly to see what they return
"""

import requests
import json

def debug_strategy_services_direct():
    """Test the actual strategy services to see their response structure"""
    
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
    
    print("🔍 Testing strategy services directly...")
    print(f"✅ Login successful")
    print(f"🆔 User ID: {user_id}")
    
    # Test strategy execution endpoints to see what's available
    print(f"\n1️⃣ Testing strategy execution endpoints:")
    
    strategy_functions = [
        "risk_management",
        "portfolio_optimization", 
        "spot_momentum_strategy"
    ]
    
    for strategy_func in strategy_functions:
        print(f"\n   🎯 Testing {strategy_func}:")
        
        try:
            # Try POST to /strategies/execute
            execute_data = {
                "function": strategy_func,
                "symbol": "BTC/USDT",
                "parameters": {},
                "simulation_mode": True
            }
            
            execute_response = requests.post(f"{base_url}/strategies/execute", 
                                           headers=headers, 
                                           json=execute_data,
                                           timeout=60)
            
            print(f"      Status: {execute_response.status_code}")
            
            if execute_response.status_code == 200:
                execute_result = execute_response.json()
                print(f"      Success: {execute_result.get('success')}")
                print(f"      Function: {execute_result.get('function')}")
                
                # Check the actual response structure
                if 'result' in execute_result:
                    result = execute_result['result']
                    print(f"      Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
                    
                    # Look for specific fields the scanners are expecting
                    if strategy_func == "risk_management":
                        if 'hedge_recommendations' in result:
                            hedge_recs = result['hedge_recommendations']
                            print(f"      ✅ hedge_recommendations found: {len(hedge_recs) if isinstance(hedge_recs, list) else 'Not a list'}")
                        else:
                            print(f"      ❌ hedge_recommendations NOT found")
                            print(f"      Available fields: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
                    
                    elif strategy_func == "portfolio_optimization":
                        if 'rebalancing_recommendations' in result:
                            rebal_recs = result['rebalancing_recommendations']
                            print(f"      ✅ rebalancing_recommendations found: {len(rebal_recs) if isinstance(rebal_recs, list) else 'Not a list'}")
                        else:
                            print(f"      ❌ rebalancing_recommendations NOT found")
                            print(f"      Available fields: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
                    
                    elif strategy_func == "spot_momentum_strategy":
                        if 'signals' in result:
                            signals = result['signals']
                            print(f"      ✅ signals found: {signals if isinstance(signals, dict) else 'Not a dict'}")
                        else:
                            print(f"      ❌ signals NOT found")
                            print(f"      Available fields: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
                
                # Show a sample of the actual response structure
                print(f"      Sample response structure:")
                print(f"      {json.dumps(execute_result, indent=8)[:500]}...")
                
            elif execute_response.status_code == 422:
                # Validation error - might give us clues about expected parameters
                error_data = execute_response.json()
                print(f"      Validation error: {error_data}")
            else:
                print(f"      Error: {execute_response.text[:200]}")
                
        except Exception as e:
            print(f"      Exception: {e}")
    
    # Test if there are direct strategy endpoints
    print(f"\n2️⃣ Testing direct strategy endpoints:")
    
    direct_endpoints = [
        "/strategies/risk-management",
        "/strategies/portfolio-optimization",
        "/strategies/momentum",
        "/trading/risk-management",
        "/trading/portfolio-optimization",
        "/trading/momentum"
    ]
    
    for endpoint in direct_endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=10)
            print(f"   {endpoint}: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"      Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        except Exception as e:
            print(f"   {endpoint}: Exception - {e}")
    
    # Test with POST for direct strategy endpoints
    print(f"\n3️⃣ Testing POST to direct strategy endpoints:")
    
    for endpoint in direct_endpoints:
        try:
            post_data = {"user_id": user_id, "analysis_type": "comprehensive"}
            response = requests.post(f"{base_url}{endpoint}", 
                                   headers=headers, 
                                   json=post_data,
                                   timeout=10)
            print(f"   {endpoint}: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"      Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        except Exception as e:
            print(f"   {endpoint}: Exception - {e}")

if __name__ == "__main__":
    debug_strategy_services_direct()