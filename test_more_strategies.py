#!/usr/bin/env python3
import requests
import json

def test_more_strategies():
    # Login
    login_data = {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}
    response = requests.post("https://cryptouniverse.onrender.com/api/v1/auth/login", json=login_data, timeout=30)
    
    if response.status_code != 200:
        print(f"Login failed: {response.status_code}")
        return
    
    token = response.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    print("✅ Login successful")
    
    # Test more strategies
    strategies_to_test = [
        ("Spot Mean Reversion", "spot_mean_reversion", {"timeframe": "1h", "lookback": 40}),
        ("Spot Breakout", "spot_breakout_strategy", {"timeframe": "4h", "sensitivity": 2.0}),
        ("Pairs Trading", "pairs_trading", {"symbol1": "BTC/USDT", "symbol2": "ETH/USDT", "lookback": 100}),
        ("Statistical Arbitrage", "statistical_arbitrage", {"universe": ["BTC/USDT", "ETH/USDT"], "lookback": 50}),
        ("Market Making", "market_making", {"symbol": "BTC/USDT", "spread_bps": 10, "size": 0.1}),
        ("Futures Trading", "futures_trade", {"symbol": "BTCUSDT", "side": "long", "leverage": 2}),
        ("Options Trading", "options_trade", {"symbol": "BTC/USDT", "option_type": "call", "strike": 45000}),
        ("Funding Arbitrage", "funding_arbitrage", {"symbol": "BTC/USDT", "exchanges": ["binance", "okx"]}),
        ("Complex Strategy", "complex_strategy", {"strategy_type": "butterfly", "symbol": "BTC/USDT"})
    ]
    
    results = {}
    
    for name, function, params in strategies_to_test:
        print(f"\n🔍 Testing {name}...")
        
        payload = {
            "function": function,
            "symbol": "BTC/USDT", 
            "parameters": params,
            "simulation_mode": True
        }
        
        try:
            response = requests.post(
                "https://cryptouniverse.onrender.com/api/v1/strategies/execute",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                success = data.get('success', False)
                error = data.get('error')
                exec_result = data.get('execution_result', {})
                
                print(f"   Success: {success}")
                print(f"   Error: {error}")
                
                if success and isinstance(exec_result, dict):
                    print(f"   Result keys: {list(exec_result.keys())}")
                elif success and isinstance(exec_result, list):
                    print(f"   Result length: {len(exec_result)}")
                elif not success:
                    print(f"   Failure reason: {error}")
                
                results[name] = {
                    "success": success,
                    "error": error,
                    "result_type": str(type(exec_result)),
                    "result_keys": list(exec_result.keys()) if isinstance(exec_result, dict) else None,
                    "result_length": len(exec_result) if isinstance(exec_result, list) else None
                }
            else:
                print(f"   HTTP Error: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                results[name] = {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"   Exception: {e}")
            results[name] = {"success": False, "error": str(e)}
    
    # Summary
    print(f"\n📊 SUMMARY:")
    working = [name for name, result in results.items() if result.get("success")]
    failing = [name for name, result in results.items() if not result.get("success")]
    
    print(f"✅ Working: {len(working)}/9 - {working}")
    print(f"❌ Failing: {len(failing)}/9 - {failing}")
    
    # Save results
    with open('more_strategy_test_evidence.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to more_strategy_test_evidence.json")

if __name__ == "__main__":
    test_more_strategies()