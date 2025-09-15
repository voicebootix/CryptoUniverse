#!/usr/bin/env python3
"""
Final Complete System Test

Test the complete system after all implementations
"""

import requests
import json

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def test_complete_system():
    """Test the complete system with all fixes."""
    
    print("🚀 FINAL COMPLETE SYSTEM TEST")
    print("=" * 80)
    
    # Login
    session = requests.Session()
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    
    response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return
    
    token = response.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    print("✅ Authenticated successfully")
    
    # Test 1: Marketplace with all strategies
    print(f"\n📊 TEST 1: MARKETPLACE WITH ALL STRATEGIES")
    print("=" * 60)
    
    response = session.get(f"{BASE_URL}/strategies/marketplace")
    
    if response.status_code == 200:
        data = response.json()
        strategies = data.get("strategies", [])
        
        print(f"✅ Marketplace loaded successfully")
        print(f"   Total strategies: {len(strategies)}")
        print(f"   AI strategies: {data.get('ai_strategies_count', 0)}")
        
        # Check for new strategies
        strategy_ids = [s.get("strategy_id", "") for s in strategies]
        new_strategies = [id for id in strategy_ids if any(new_func in id for new_func in ["funding", "greeks", "swing", "leverage", "margin", "options_chain", "basis", "liquidation", "hedge", "performance"])]
        
        print(f"   New strategies detected: {len(new_strategies)}")
        for strategy_id in new_strategies[:5]:
            print(f"      - {strategy_id}")
        
        # Check backtest data quality
        unique_backtests = set()
        for strategy in strategies:
            backtest = strategy.get("backtest_results", {})
            total_return = backtest.get("total_return", 0)
            win_rate = backtest.get("win_rate", 0)
            sharpe = backtest.get("sharpe_ratio", 0)
            
            backtest_signature = f"{total_return}-{win_rate}-{sharpe}"
            unique_backtests.add(backtest_signature)
        
        print(f"   Unique backtest profiles: {len(unique_backtests)}")
        if len(unique_backtests) > 1:
            print(f"   🎉 REAL BACKTESTING WORKING! (No more identical 156.7% returns)")
        else:
            print(f"   ⚠️ Still identical backtest data")
    
    else:
        print(f"❌ Marketplace failed: {response.status_code}")
    
    # Test 2: Strategy execution with new functions
    print(f"\n🔧 TEST 2: NEW STRATEGY EXECUTION")
    print("=" * 60)
    
    # Test a few key new functions
    test_functions = ["funding_arbitrage", "swing_trading", "calculate_greeks"]
    
    for function in test_functions:
        print(f"\n🎯 Testing: {function}")
        
        payload = {
            "function": function,
            "symbol": "BTC/USDT",
            "parameters": {}
        }
        
        try:
            response = session.post(f"{BASE_URL}/strategies/execute", json=payload)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                print(f"   Success: {success}")
                
                if success:
                    execution_result = data.get("execution_result", {})
                    function_name = execution_result.get("function", "unknown")
                    print(f"   ✅ {function} working! Function: {function_name}")
                else:
                    error = data.get("error", "Unknown")
                    print(f"   ❌ Execution failed: {error}")
            else:
                print(f"   ❌ HTTP Error: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    # Test 3: Chat system with enhanced discovery
    print(f"\n💬 TEST 3: CHAT SYSTEM WITH ENHANCED DISCOVERY")
    print("=" * 60)
    
    payload = {
        "message": "Find me investment opportunities using all available strategies",
        "mode": "analysis"
    }
    
    try:
        response = session.post(f"{BASE_URL}/chat/message", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            metadata = data.get("metadata", {})
            
            print(f"✅ Chat response received")
            print(f"   Intent: {data.get('intent')}")
            print(f"   Opportunities: {metadata.get('opportunities_count', 0)}")
            print(f"   Service: {metadata.get('service_used', 'Unknown')}")
            
            if metadata.get('opportunities_count', 0) > 0:
                print(f"   🎉 OPPORTUNITIES FOUND WITH ENHANCED SYSTEM!")
            else:
                print(f"   ⚠️ Still no opportunities - may need production restart")
        else:
            print(f"❌ Chat failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Chat test failed: {e}")

if __name__ == "__main__":
    test_complete_system()