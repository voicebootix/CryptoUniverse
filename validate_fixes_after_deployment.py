#!/usr/bin/env python3
"""
Validate Fixes After Deployment

This script should be run AFTER the fixes are deployed to the live server
to validate that all 8 strategies are now working correctly.
"""

import requests
import json
import time
from datetime import datetime

def validate_fixes():
    """Validate that all fixes are working after deployment."""
    print("🚀 VALIDATING FIXES AFTER DEPLOYMENT")
    print("=" * 50)
    
    # Login
    login_data = {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}
    response = requests.post("https://cryptouniverse.onrender.com/api/v1/auth/login", json=login_data, timeout=30)
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return False
    
    token = response.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    print("✅ Authentication successful")
    
    # Test all 8 fixed strategies
    strategies = [
        {
            "name": "Portfolio Optimization",
            "function": "portfolio_optimization",
            "parameters": {"rebalance_frequency": "weekly", "risk_target": "balanced"},
            "expected_keys": ["portfolio_optimization", "recommendations", "strategy_results"]
        },
        {
            "name": "Spot Momentum",
            "function": "spot_momentum_strategy",
            "parameters": {"timeframe": "1h", "lookback": 50},
            "expected_keys": ["momentum_analysis", "trading_signals", "risk_metrics"]
        },
        {
            "name": "Spot Mean Reversion",
            "function": "spot_mean_reversion",
            "parameters": {"timeframe": "1h", "lookback": 40},
            "expected_keys": ["mean_reversion_analysis", "z_score", "trading_signals"]
        },
        {
            "name": "Spot Breakout",
            "function": "spot_breakout_strategy",
            "parameters": {"timeframe": "4h", "sensitivity": 2.0},
            "expected_keys": ["breakout_analysis", "support_resistance", "trading_signals"]
        },
        {
            "name": "Pairs Trading",
            "function": "pairs_trading",
            "parameters": {"symbol1": "BTC/USDT", "symbol2": "ETH/USDT", "lookback": 100},
            "expected_keys": ["pairs_analysis", "correlation", "trading_signals"]
        },
        {
            "name": "Statistical Arbitrage",
            "function": "statistical_arbitrage",
            "parameters": {"universe": ["BTC/USDT", "ETH/USDT", "SOL/USDT"], "lookback": 50},
            "expected_keys": ["statistical_arbitrage", "universe", "opportunities"]
        },
        {
            "name": "Futures Trading",
            "function": "futures_trade",
            "parameters": {"symbol": "BTCUSDT", "side": "long", "leverage": 2},
            "expected_keys": ["futures_analysis", "position_size", "leverage"]
        },
        {
            "name": "Options Trading",
            "function": "options_trade",
            "parameters": {"symbol": "BTC/USDT", "option_type": "call", "strike": 45000},
            "expected_keys": ["options_analysis", "greeks", "premium"]
        }
    ]
    
    results = {}
    success_count = 0
    
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
                exec_result = data.get('execution_result', {})
                
                if success and isinstance(exec_result, dict):
                    result_keys = list(exec_result.keys())
                    expected_keys = strategy["expected_keys"]
                    
                    # Check if we have the expected keys
                    has_expected_keys = any(key in result_keys for key in expected_keys)
                    
                    if has_expected_keys:
                        print(f"✅ {strategy['name']} - SUCCESS ({execution_time:.1f}s)")
                        print(f"   📊 Keys: {result_keys}")
                        success_count += 1
                        results[strategy['name']] = "SUCCESS"
                    else:
                        print(f"⚠️  {strategy['name']} - PARTIAL ({execution_time:.1f}s)")
                        print(f"   📊 Keys: {result_keys}")
                        print(f"   ⚠️  Expected: {expected_keys}")
                        results[strategy['name']] = "PARTIAL"
                else:
                    error = data.get('error', 'Unknown error')
                    print(f"❌ {strategy['name']} - FAILED ({execution_time:.1f}s) - {error}")
                    results[strategy['name']] = "FAILED"
            else:
                print(f"❌ {strategy['name']} - HTTP ERROR ({execution_time:.1f}s) - {response.status_code}")
                results[strategy['name']] = "HTTP_ERROR"
                
        except requests.exceptions.Timeout:
            print(f"⏰ {strategy['name']} - TIMEOUT (30s)")
            results[strategy['name']] = "TIMEOUT"
        except Exception as e:
            print(f"💥 {strategy['name']} - ERROR - {str(e)}")
            results[strategy['name']] = "ERROR"
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 VALIDATION RESULTS")
    print(f"{'='*50}")
    
    success_rate = (success_count / len(strategies)) * 100
    print(f"✅ Success Rate: {success_rate:.1f}% ({success_count}/{len(strategies)})")
    
    if success_rate >= 75:
        print("🎉 EXCELLENT: Fixes are working perfectly!")
    elif success_rate >= 50:
        print("✅ GOOD: Most fixes are working!")
    elif success_rate >= 25:
        print("⚠️  PARTIAL: Some fixes are working!")
    else:
        print("❌ ISSUES: Fixes may need adjustment!")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"validation_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {filename}")
    
    return success_rate >= 50

if __name__ == "__main__":
    validate_fixes()