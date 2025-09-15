#!/usr/bin/env python3
"""
Test strategy services with correct parameters
"""

import requests
import json

def debug_strategy_services_fixed():
    """Test strategy services with correct parameters"""
    
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
    
    print("🔍 Testing strategy services with correct parameters...")
    print(f"✅ Login successful")
    print(f"🆔 User ID: {user_id}")
    
    # Test strategy execution with corrected parameters
    print(f"\n1️⃣ Testing strategy execution with corrected parameters:")
    
    strategy_functions = [
        "risk_management",
        "portfolio_optimization", 
        "spot_momentum_strategy"
    ]
    
    for strategy_func in strategy_functions:
        print(f"\n   🎯 Testing {strategy_func}:")
        
        try:
            # Try without simulation_mode parameter
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
                print(f"      Success: {execute_result.get('success')}")
                print(f"      Function: {execute_result.get('function')}")
                
                # Check the actual response structure
                if 'result' in execute_result:
                    result = execute_result['result']
                    print(f"      Result type: {type(result)}")
                    
                    if isinstance(result, dict):
                        print(f"      Result keys: {list(result.keys())}")
                        
                        # Look for specific fields the scanners are expecting
                        if strategy_func == "risk_management":
                            # Check for hedge_recommendations or similar fields
                            for key in result.keys():
                                if 'hedge' in key.lower() or 'recommendation' in key.lower():
                                    print(f"      ✅ Found hedge-related field: {key}")
                                    print(f"         Value: {result[key]}")
                            
                            # Check for risk_management_analysis structure
                            if 'risk_management_analysis' in result:
                                analysis = result['risk_management_analysis']
                                print(f"      ✅ Found risk_management_analysis")
                                if isinstance(analysis, dict):
                                    print(f"         Analysis keys: {list(analysis.keys())}")
                                    if 'mitigation_strategies' in analysis:
                                        strategies = analysis['mitigation_strategies']
                                        print(f"         ✅ Found mitigation_strategies: {len(strategies) if isinstance(strategies, list) else 'Not a list'}")
                                        if isinstance(strategies, list) and strategies:
                                            print(f"         Sample strategy: {strategies[0]}")
                        
                        elif strategy_func == "portfolio_optimization":
                            # Check for rebalancing_recommendations or similar
                            for key in result.keys():
                                if 'rebalanc' in key.lower() or 'optimization' in key.lower():
                                    print(f"      ✅ Found rebalancing-related field: {key}")
                                    print(f"         Value: {result[key]}")
                        
                        elif strategy_func == "spot_momentum_strategy":
                            # Check for signals or momentum data
                            for key in result.keys():
                                if 'signal' in key.lower() or 'momentum' in key.lower():
                                    print(f"      ✅ Found momentum-related field: {key}")
                                    print(f"         Value: {result[key]}")
                    
                    # Show full response structure for analysis
                    print(f"      Full response structure:")
                    print(f"      {json.dumps(execute_result, indent=8)[:800]}...")
                
            elif execute_response.status_code == 422:
                error_data = execute_response.json()
                print(f"      Validation error details:")
                print(f"      {json.dumps(error_data, indent=8)}")
            else:
                print(f"      Error ({execute_response.status_code}): {execute_response.text[:300]}")
                
        except Exception as e:
            print(f"      Exception: {e}")
    
    # Test if we can call the trading strategies service methods directly through any other endpoint
    print(f"\n2️⃣ Testing alternative strategy endpoints:")
    
    # Check if there are any working strategy-related endpoints
    strategy_endpoints = [
        "/strategies/list",
        "/strategies/available", 
        "/strategies/marketplace",
        "/trading/strategies",
        "/trading/execute"
    ]
    
    for endpoint in strategy_endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=10)
            print(f"   GET {endpoint}: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    print(f"      Keys: {list(data.keys())}")
                elif isinstance(data, list):
                    print(f"      List length: {len(data)}")
                    if data:
                        print(f"      Sample item: {data[0]}")
        except Exception as e:
            print(f"   {endpoint}: Exception - {e}")

if __name__ == "__main__":
    debug_strategy_services_fixed()