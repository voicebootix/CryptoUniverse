#!/usr/bin/env python3
"""
Admin Testing Solution

Simple approach: Test strategies directly via execute endpoint
without needing to purchase them first.
"""

import requests
import json
import time

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def test_all_strategies_directly():
    """Test all 25 strategies directly via execute endpoint."""
    
    print("🔧 ADMIN STRATEGY TESTING - DIRECT EXECUTION")
    print("=" * 70)
    
    # Login
    session = requests.Session()
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    
    response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    token = response.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    print("✅ Authenticated successfully")
    
    # All 25 strategy functions to test
    all_strategy_functions = [
        # Derivatives (12)
        {"function": "futures_trade", "params": {"strategy_type": "long_futures", "leverage": 3}},
        {"function": "options_trade", "params": {"strategy_type": "call_option", "strike_price": 50000}},
        {"function": "perpetual_trade", "params": {"leverage": 5}},
        {"function": "leverage_position", "params": {"leverage": 3, "position_size": 1000}},
        {"function": "complex_strategy", "params": {"strategy_type": "iron_condor"}},
        {"function": "margin_status", "params": {}},
        {"function": "funding_arbitrage", "params": {"symbols": "BTC,ETH"}},
        {"function": "basis_trade", "params": {}},
        {"function": "options_chain", "params": {"expiry_date": "2024-12-27"}},
        {"function": "calculate_greeks", "params": {"strike_price": 50000, "volatility": 0.8}},
        {"function": "liquidation_price", "params": {"leverage": 5, "entry_price": 50000}},
        {"function": "hedge_position", "params": {"hedge_ratio": 0.5}},
        
        # Spot (3)
        {"function": "spot_momentum_strategy", "params": {"timeframe": "4h"}},
        {"function": "spot_mean_reversion", "params": {"timeframe": "1h"}},
        {"function": "spot_breakout_strategy", "params": {"timeframe": "1h"}},
        
        # Algorithmic (6)
        {"function": "algorithmic_trading", "params": {"strategy_type": "momentum"}},
        {"function": "pairs_trading", "params": {"pair_symbols": "BTC-ETH"}},
        {"function": "statistical_arbitrage", "params": {"universe": "BTC,ETH,SOL"}},
        {"function": "market_making", "params": {"spread_percentage": 0.1}},
        {"function": "scalping_strategy", "params": {"timeframe": "1m"}},
        {"function": "swing_trading", "params": {"timeframe": "1d", "holding_period": 7}},
        
        # Risk & Portfolio (4)
        {"function": "position_management", "params": {"action": "analyze"}},
        {"function": "risk_management", "params": {"analysis_type": "comprehensive"}},
        {"function": "portfolio_optimization", "params": {"rebalance_frequency": "weekly"}},
        {"function": "strategy_performance", "params": {"analysis_period": "30d"}}
    ]
    
    print(f"📊 Testing {len(all_strategy_functions)} strategy functions...")
    
    results = []
    
    for i, strategy_test in enumerate(all_strategy_functions, 1):
        function = strategy_test["function"]
        params = strategy_test["params"]
        
        print(f"\n{i:2d}. Testing: {function}")
        
        payload = {
            "function": function,
            "symbol": "BTC/USDT",
            "parameters": params,
            "simulation_mode": True
        }
        
        try:
            start_time = time.time()
            response = session.post(f"{BASE_URL}/strategies/execute", json=payload)
            execution_time = time.time() - start_time
            
            print(f"     Status: {response.status_code}")
            print(f"     Time: {execution_time:.2f}s")
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                
                if success:
                    execution_result = data.get("execution_result", {})
                    function_name = execution_result.get("function", "unknown")
                    
                    print(f"     ✅ SUCCESS - Function: {function_name}")
                    
                    # Check for real data indicators
                    real_data_indicators = 0
                    if execution_result.get("real_data_sources"):
                        real_data_indicators += 1
                    if any(key for key in execution_result.keys() if "real" in str(key).lower()):
                        real_data_indicators += 1
                    
                    print(f"     📊 Real data indicators: {real_data_indicators}")
                    
                    results.append({
                        "function": function,
                        "success": True,
                        "execution_time": execution_time,
                        "real_data_indicators": real_data_indicators
                    })
                else:
                    error = data.get("error", "Unknown")
                    print(f"     ❌ Execution failed: {error}")
                    
                    results.append({
                        "function": function,
                        "success": False,
                        "error": error
                    })
            else:
                print(f"     ❌ HTTP Error: {response.status_code}")
                error_text = response.text[:100] if response.text else "Unknown"
                
                results.append({
                    "function": function,
                    "success": False,
                    "error": f"HTTP {response.status_code}: {error_text}"
                })
                
        except Exception as e:
            print(f"     ❌ Exception: {e}")
            
            results.append({
                "function": function,
                "success": False,
                "error": str(e)
            })
        
        # Rate limiting
        time.sleep(0.5)
    
    # Final summary
    successful = len([r for r in results if r.get("success", False)])
    with_real_data = len([r for r in results if r.get("success", False) and r.get("real_data_indicators", 0) > 0])
    
    print(f"\n🎯 COMPREHENSIVE TESTING RESULTS")
    print("=" * 70)
    print(f"Total functions tested: {len(results)}")
    print(f"Successful executions: {successful}")
    print(f"Functions with real data: {with_real_data}")
    print(f"Success rate: {successful/len(results)*100:.1f}%")
    print(f"Real data rate: {with_real_data/successful*100:.1f}%" if successful > 0 else "N/A")
    
    # Show working strategies
    print(f"\n✅ WORKING STRATEGIES:")
    working_strategies = [r for r in results if r.get("success", False)]
    for result in working_strategies:
        indicators = result.get("real_data_indicators", 0)
        data_quality = "🎉 REAL DATA" if indicators > 0 else "⚠️ Basic"
        print(f"   - {result['function']}: {data_quality}")
    
    # Show failed strategies
    failed_strategies = [r for r in results if not r.get("success", False)]
    if failed_strategies:
        print(f"\n❌ FAILED STRATEGIES ({len(failed_strategies)}):")
        for result in failed_strategies[:5]:  # Show first 5
            print(f"   - {result['function']}: {result.get('error', 'Unknown')[:50]}")
    
    return results

if __name__ == "__main__":
    test_all_strategies_directly()