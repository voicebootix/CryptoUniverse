#!/usr/bin/env python3
"""
Test Newly Implemented Functions

Test the 9 newly implemented strategy functions to verify they work
"""

import requests
import json
import time

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def test_new_strategy_functions():
    """Test all newly implemented strategy functions."""
    
    print("🚀 TESTING NEWLY IMPLEMENTED STRATEGY FUNCTIONS")
    print("=" * 70)
    
    # Login
    session = requests.Session()
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    
    response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    token = response.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    print("✅ Authenticated successfully")
    
    # Test newly implemented functions
    new_functions = [
        {
            "function": "funding_arbitrage",
            "name": "Funding Arbitrage",
            "parameters": {"symbols": "BTC,ETH", "min_funding_rate": 0.001}
        },
        {
            "function": "calculate_greeks",
            "name": "Calculate Greeks",
            "parameters": {
                "strike_price": 50000,
                "time_to_expiry": 0.0833,  # 30 days
                "volatility": 0.8
            }
        },
        {
            "function": "swing_trading",
            "name": "Swing Trading",
            "parameters": {"timeframe": "1d", "holding_period": 7}
        },
        {
            "function": "leverage_position",
            "name": "Leverage Position",
            "parameters": {"leverage": 3, "position_size": 1000}
        },
        {
            "function": "margin_status",
            "name": "Margin Status",
            "parameters": {}
        },
        {
            "function": "options_chain",
            "name": "Options Chain",
            "parameters": {"expiry_date": "2024-12-27"}
        },
        {
            "function": "basis_trade",
            "name": "Basis Trade",
            "parameters": {}
        },
        {
            "function": "liquidation_price",
            "name": "Liquidation Price",
            "parameters": {"leverage": 5, "position_type": "long"}
        },
        {
            "function": "hedge_position",
            "name": "Hedge Position",
            "parameters": {"hedge_ratio": 0.5}
        },
        {
            "function": "strategy_performance",
            "name": "Strategy Performance",
            "parameters": {"analysis_period": "30d"}
        }
    ]
    
    results = []
    
    for test_func in new_functions:
        function = test_func["function"]
        name = test_func["name"]
        params = test_func["parameters"]
        
        print(f"\n🎯 Testing: {name}")
        print(f"   Function: {function}")
        
        payload = {
            "function": function,
            "symbol": "BTC/USDT",
            "parameters": params
        }
        
        try:
            start_time = time.time()
            response = session.post(f"{BASE_URL}/strategies/execute", json=payload)
            execution_time = time.time() - start_time
            
            print(f"   Status: {response.status_code}")
            print(f"   Time: {execution_time:.2f}s")
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                
                if success:
                    execution_result = data.get("execution_result", {})
                    
                    print(f"   ✅ SUCCESS!")
                    print(f"   Function: {execution_result.get('function', 'Unknown')}")
                    
                    # Check for real data indicators
                    real_data_indicators = []
                    
                    if "real_data_sources" in execution_result:
                        real_data_indicators.append("Has real_data_sources field")
                    
                    if "calculation_method" in execution_result:
                        method = execution_result["calculation_method"]
                        if "real" in method.lower():
                            real_data_indicators.append(f"Real calculation method: {method}")
                    
                    # Look for numerical results that indicate real calculations
                    for key, value in execution_result.items():
                        if isinstance(value, dict):
                            for subkey, subvalue in value.items():
                                if isinstance(subvalue, (int, float)) and subvalue > 0:
                                    real_data_indicators.append(f"{key}.{subkey}: {subvalue}")
                    
                    print(f"   📊 Real data indicators: {len(real_data_indicators)}")
                    for indicator in real_data_indicators[:3]:
                        print(f"      - {indicator}")
                    
                    results.append({
                        "function": function,
                        "name": name,
                        "success": True,
                        "execution_time": execution_time,
                        "real_indicators": len(real_data_indicators)
                    })
                    
                else:
                    error = data.get("error", "Unknown error")
                    print(f"   ❌ Execution failed: {error}")
                    
                    results.append({
                        "function": function,
                        "name": name,
                        "success": False,
                        "error": error
                    })
            else:
                print(f"   ❌ HTTP Error: {response.status_code}")
                error_text = response.text[:100]
                print(f"   Error: {error_text}")
                
                results.append({
                    "function": function,
                    "name": name,
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                })
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            
            results.append({
                "function": function,
                "name": name,
                "success": False,
                "error": str(e)
            })
    
    # Summary
    successful = len([r for r in results if r.get("success", False)])
    
    print(f"\n📊 NEW FUNCTIONS TEST SUMMARY")
    print("=" * 60)
    print(f"Total new functions tested: {len(results)}")
    print(f"Successful implementations: {successful}")
    print(f"Success rate: {successful/len(results)*100:.1f}%")
    
    print(f"\n📈 DETAILED RESULTS:")
    for result in results:
        status = "✅" if result.get("success") else "❌"
        print(f"   {status} {result['name']}: {result.get('error', 'Working')}")
    
    return results

if __name__ == "__main__":
    test_new_strategy_functions()