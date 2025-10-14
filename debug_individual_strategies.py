#!/usr/bin/env python3
"""
Debug Individual Strategies - Detailed Error Analysis
"""

import requests
import json
import asyncio
import time

def debug_individual_strategies():
    """Debug each failing strategy individually with detailed error analysis."""
    print("🔍 DEBUGGING INDIVIDUAL STRATEGIES")
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
    
    # Test each failing strategy individually with detailed parameters
    failing_strategies = [
        {
            "name": "Portfolio Optimization",
            "function": "portfolio_optimization",
            "params": {
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "leverage": 1.0,
                "risk_percentage": 0.02
            }
        },
        {
            "name": "Spot Mean Reversion", 
            "function": "spot_mean_reversion",
            "params": {
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "leverage": 1.0,
                "risk_percentage": 0.02
            }
        },
        {
            "name": "Spot Breakout",
            "function": "spot_breakout_strategy", 
            "params": {
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "leverage": 1.0,
                "risk_percentage": 0.02
            }
        },
        {
            "name": "Pairs Trading",
            "function": "pairs_trading",
            "params": {
                "symbol1": "BTC",
                "symbol2": "ETH", 
                "correlation_threshold": 0.7,
                "timeframe": "1h"
            }
        },
        {
            "name": "Futures Trading",
            "function": "futures_trade",
            "params": {
                "symbol": "BTCUSDT",
                "strategy_type": "long_futures",
                "leverage": 2.0,
                "timeframe": "1h"
            }
        },
        {
            "name": "Options Trading",
            "function": "options_trade", 
            "params": {
                "symbol": "BTCUSDT",
                "strategy_type": "call_option",
                "expiry_days": 30,
                "strike_multiplier": 1.05
            }
        }
    ]
    
    results = {}
    
    for strategy in failing_strategies:
        print(f"\n🧪 DEBUGGING {strategy['name']}...")
        
        # Test with different parameter formats
        test_cases = [
            {
                "name": "Standard Parameters",
                "params": strategy["params"]
            },
            {
                "name": "Minimal Parameters", 
                "params": {"symbol": "BTCUSDT"}
            },
            {
                "name": "Extended Parameters",
                "params": {
                    **strategy["params"],
                    "user_id": "admin_user_id",
                    "strategy_id": "test_strategy_id"
                }
            }
        ]
        
        strategy_results = {}
        
        for test_case in test_cases:
            print(f"   📋 Testing {test_case['name']}...")
            
            strategy_data = {
                "function": strategy["function"],
                "parameters": test_case["params"],
                "user_id": "admin_user_id"
            }
            
            start_time = time.time()
            
            try:
                response = requests.post(
                    "https://cryptouniverse.onrender.com/api/v1/strategies/execute",
                    json=strategy_data,
                    headers=headers,
                    timeout=15
                )
                
                execution_time = time.time() - start_time
                
                print(f"      Status: {response.status_code} ({execution_time:.1f}s)")
                
                if response.status_code == 200:
                    result = response.json()
                    success = result.get("success", False)
                    error = result.get("error", "")
                    
                    if success:
                        print(f"      ✅ SUCCESS: {strategy['name']}")
                        strategy_results[test_case["name"]] = {
                            "status": "SUCCESS",
                            "execution_time": execution_time,
                            "result": result
                        }
                    else:
                        print(f"      ❌ FAILED: {error}")
                        strategy_results[test_case["name"]] = {
                            "status": "FAILED",
                            "execution_time": execution_time,
                            "error": error
                        }
                else:
                    print(f"      ❌ HTTP {response.status_code}")
                    try:
                        error_detail = response.json()
                        print(f"      Error Detail: {error_detail}")
                    except:
                        print(f"      Raw Response: {response.text[:200]}")
                    
                    strategy_results[test_case["name"]] = {
                        "status": f"HTTP_{response.status_code}",
                        "execution_time": execution_time,
                        "error": response.text[:200]
                    }
                    
            except requests.exceptions.Timeout:
                execution_time = time.time() - start_time
                print(f"      ⏰ TIMEOUT ({execution_time:.1f}s)")
                strategy_results[test_case["name"]] = {
                    "status": "TIMEOUT",
                    "execution_time": execution_time,
                    "error": "Request timeout"
                }
            except Exception as e:
                execution_time = time.time() - start_time
                print(f"      💥 EXCEPTION ({execution_time:.1f}s): {str(e)}")
                strategy_results[test_case["name"]] = {
                    "status": "EXCEPTION",
                    "execution_time": execution_time,
                    "error": str(e)
                }
        
        results[strategy["name"]] = strategy_results
    
    # Summary
    print(f"\n📊 DETAILED DEBUG RESULTS")
    print("=" * 50)
    
    for strategy_name, strategy_results in results.items():
        print(f"\n🔍 {strategy_name}:")
        for test_name, result in strategy_results.items():
            status = result["status"]
            exec_time = result["execution_time"]
            error = result.get("error", "")
            
            if status == "SUCCESS":
                print(f"   ✅ {test_name}: {execution_time:.1f}s")
            else:
                print(f"   ❌ {test_name}: {status} ({execution_time:.1f}s) - {error[:100]}")
    
    # Save detailed results
    with open('detailed_strategy_debug_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: detailed_strategy_debug_results.json")
    
    return results

if __name__ == "__main__":
    debug_individual_strategies()