#!/usr/bin/env python3
import requests
import json

def test_strategies():
    # Login
    login_data = {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}
    response = requests.post("https://cryptouniverse.onrender.com/api/v1/auth/login", json=login_data, timeout=30)
    
    if response.status_code != 200:
        print(f"Login failed: {response.status_code}")
        return
    
    token = response.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    print("✅ Login successful")
    
    # Test a few key strategies
    strategies_to_test = [
        ("Risk Management", "risk_management", {"analysis_type": "comprehensive", "symbols": ["BTC/USDT"]}),
        ("Portfolio Optimization", "portfolio_optimization", {"rebalance_frequency": "weekly", "risk_target": "balanced"}),
        ("Spot Momentum", "spot_momentum_strategy", {"timeframe": "1h", "lookback": 50}),
        ("Scalping", "scalping_strategy", {"timeframe": "5m", "profit_target": 0.5}),
        ("Hedge Position", "hedge_position", {"symbol": "BTC/USDT", "hedge_ratio": 0.5})
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
                print(f"   Result type: {type(exec_result)}")
                
                if isinstance(exec_result, dict):
                    print(f"   Result keys: {list(exec_result.keys())}")
                elif isinstance(exec_result, list):
                    print(f"   Result length: {len(exec_result)}")
                else:
                    print(f"   Result value: {str(exec_result)[:100]}...")
                
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
    
    print(f"✅ Working: {len(working)}/5 - {working}")
    print(f"❌ Failing: {len(failing)}/5 - {failing}")
    
    # Save results
    with open('strategy_test_evidence.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to strategy_test_evidence.json")

if __name__ == "__main__":
    test_strategies()