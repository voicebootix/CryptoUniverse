#!/usr/bin/env python3
"""
Test Codex Branch - Check what's working and what needs fixing
"""

import requests
import json
import time

def test_codex_branch():
    """Test the current codex branch to see what's working."""
    print("🔍 TESTING CODEX BRANCH - CURRENT STATUS")
    print("=" * 50)
    
    # Login
    login_data = {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}
    response = requests.post("https://cryptouniverse.onrender.com/api/v1/auth/login", json=login_data, timeout=30)
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return
    
    token = response.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    print("✅ Authentication successful")
    
    # Test the 8 strategies that were failing
    strategies = [
        {
            "name": "Portfolio Optimization",
            "function": "portfolio_optimization",
            "parameters": {"rebalance_frequency": "weekly", "risk_target": "balanced"}
        },
        {
            "name": "Spot Momentum",
            "function": "spot_momentum_strategy",
            "parameters": {"timeframe": "1h", "lookback": 50}
        },
        {
            "name": "Spot Mean Reversion",
            "function": "spot_mean_reversion",
            "parameters": {"timeframe": "1h", "lookback": 40}
        },
        {
            "name": "Spot Breakout",
            "function": "spot_breakout_strategy",
            "parameters": {"timeframe": "4h", "sensitivity": 2.0}
        },
        {
            "name": "Pairs Trading",
            "function": "pairs_trading",
            "parameters": {"symbol1": "BTC/USDT", "symbol2": "ETH/USDT", "lookback": 100}
        },
        {
            "name": "Statistical Arbitrage",
            "function": "statistical_arbitrage",
            "parameters": {"universe": ["BTC/USDT", "ETH/USDT", "SOL/USDT"], "lookback": 50}
        },
        {
            "name": "Futures Trading",
            "function": "futures_trade",
            "parameters": {"symbol": "BTCUSDT", "side": "long", "leverage": 2}
        },
        {
            "name": "Options Trading",
            "function": "options_trade",
            "parameters": {"symbol": "BTC/USDT", "option_type": "call", "strike": 45000}
        }
    ]
    
    results = {}
    working_count = 0
    
    for strategy in strategies:
        print(f"\n🔍 Testing {strategy['name']}...")
        
        payload = {
            "function": strategy["function"],
            "symbol": "BTC/USDT",
            "parameters": strategy["parameters"],
            "simulation_mode": True
        }
        
        start_time = time.time()
        
        try:
            response = requests.post(
                "https://cryptouniverse.onrender.com/api/v1/strategies/execute",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            execution_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                success = data.get('success', False)
                error = data.get('error')
                
                if success:
                    print(f"✅ {strategy['name']} - SUCCESS ({execution_time:.1f}s)")
                    working_count += 1
                    results[strategy['name']] = "SUCCESS"
                else:
                    print(f"⚠️  {strategy['name']} - PARTIAL ({execution_time:.1f}s) - {error}")
                    results[strategy['name']] = "PARTIAL"
            else:
                print(f"❌ {strategy['name']} - FAILED ({execution_time:.1f}s) - HTTP {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                results[strategy['name']] = "FAILED"
                
        except requests.exceptions.Timeout:
            print(f"⏰ {strategy['name']} - TIMEOUT (30s)")
            results[strategy['name']] = "TIMEOUT"
        except Exception as e:
            print(f"💥 {strategy['name']} - ERROR - {str(e)}")
            results[strategy['name']] = "ERROR"
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 CODEX BRANCH STATUS")
    print(f"{'='*50}")
    
    success_rate = (working_count / len(strategies)) * 100
    print(f"✅ Success Rate: {success_rate:.1f}% ({working_count}/{len(strategies)})")
    
    if success_rate >= 75:
        print("🎉 EXCELLENT: Codex branch is working well!")
    elif success_rate >= 50:
        print("✅ GOOD: Codex branch has some working strategies!")
    elif success_rate >= 25:
        print("⚠️  PARTIAL: Codex branch needs improvements!")
    else:
        print("❌ ISSUES: Codex branch needs significant fixes!")
    
    # Save results
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"codex_branch_status_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {filename}")
    
    return results

if __name__ == "__main__":
    test_codex_branch()