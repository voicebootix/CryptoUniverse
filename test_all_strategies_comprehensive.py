#!/usr/bin/env python3
"""
Comprehensive Test of All 14 Strategies
"""

import requests
import json
import asyncio
import time
import os

def test_all_strategies():
    """Test all 14 strategies comprehensively."""
    print("🔍 COMPREHENSIVE STRATEGY TESTING")
    print("=" * 50)
    
    # Get credentials from environment variables
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    api_base_url = os.getenv("API_BASE_URL", "https://cryptouniverse.onrender.com")
    
    if not admin_email or not admin_password:
        raise ValueError("Missing required environment variables: ADMIN_EMAIL and ADMIN_PASSWORD must be set")
    
    # Login
    login_data = {"email": admin_email, "password": admin_password}
    login_url = f"{api_base_url.rstrip('/')}/api/v1/auth/login"
    
    try:
        response = requests.post(login_url, json=login_data, timeout=30)
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error during login: {e}")
        return
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return
    
    token = response.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    print("✅ Authentication successful")
    
    # Test all 14 strategies
    strategies_to_test = [
        ("risk_management", "AI Risk Management"),
        ("portfolio_optimization", "AI Portfolio Optimization"),
        ("spot_momentum_strategy", "AI Spot Momentum"),
        ("spot_mean_reversion", "AI Spot Mean Reversion"),
        ("spot_breakout_strategy", "AI Spot Breakout"),
        ("scalping_strategy", "AI Scalping"),
        ("pairs_trading", "AI Pairs Trading"),
        ("statistical_arbitrage", "AI Statistical Arbitrage"),
        ("market_making", "AI Market Making"),
        ("futures_trade", "AI Futures Trading"),
        ("options_trade", "AI Options Trading"),
        ("funding_arbitrage", "AI Funding Arbitrage"),
        ("hedge_position", "AI Hedge Position"),
        ("complex_strategy", "AI Complex Strategy")
    ]
    
    results = {}
    
    for function_name, display_name in strategies_to_test:
        print(f"\n🧪 Testing {display_name}...")
        
        # Test parameters
        test_params = {
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "leverage": 1.0,
            "risk_percentage": 0.02
        }
        
        # Add specific parameters for certain strategies
        if function_name == "pairs_trading":
            test_params.update({
                "symbol1": "BTC",
                "symbol2": "ETH",
                "correlation_threshold": 0.7
            })
        elif function_name == "options_trade":
            test_params.update({
                "strategy_type": "call_option",
                "expiry_date": "2025-12-31"
            })
        elif function_name == "futures_trade":
            test_params.update({
                "symbol": "BTCUSDT",
                "leverage": 2.0
            })
        
        # Execute strategy
        strategy_data = {
            "function": function_name,
            "parameters": test_params,
            "user_id": "admin_user_id"
        }
        
        start_time = time.time()
        
        try:
            response = requests.post(
                "https://cryptouniverse.onrender.com/api/v1/strategies/execute",
                json=strategy_data,
                headers=headers,
                timeout=30
            )
            
            execution_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                success = result.get("success", False)
                error = result.get("error", "")
                
                if success:
                    print(f"   ✅ SUCCESS ({execution_time:.1f}s)")
                    results[function_name] = {
                        "status": "SUCCESS",
                        "execution_time": execution_time,
                        "result": result
                    }
                else:
                    print(f"   ❌ FAILED ({execution_time:.1f}s): {error}")
                    results[function_name] = {
                        "status": "FAILED",
                        "execution_time": execution_time,
                        "error": error
                    }
            else:
                print(f"   ❌ HTTP {response.status_code} ({execution_time:.1f}s)")
                results[function_name] = {
                    "status": "HTTP_ERROR",
                    "execution_time": execution_time,
                    "error": f"HTTP {response.status_code}"
                }
                
        except requests.exceptions.Timeout:
            execution_time = time.time() - start_time
            print(f"   ⏰ TIMEOUT ({execution_time:.1f}s)")
            results[function_name] = {
                "status": "TIMEOUT",
                "execution_time": execution_time,
                "error": "Request timeout"
            }
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"   💥 EXCEPTION ({execution_time:.1f}s): {str(e)}")
            results[function_name] = {
                "status": "EXCEPTION",
                "execution_time": execution_time,
                "error": str(e)
            }
    
    # Summary
    print(f"\n📊 COMPREHENSIVE TEST RESULTS")
    print("=" * 50)
    
    success_count = sum(1 for r in results.values() if r["status"] == "SUCCESS")
    failed_count = sum(1 for r in results.values() if r["status"] in ["FAILED", "HTTP_ERROR", "TIMEOUT", "EXCEPTION"])
    
    print(f"✅ SUCCESS: {success_count}/14 strategies")
    print(f"❌ FAILED: {failed_count}/14 strategies")
    
    # Detailed results
    print(f"\n📋 DETAILED RESULTS:")
    for function_name, result in results.items():
        status = result["status"]
        exec_time = result["execution_time"]
        error = result.get("error", "")
        
        if status == "SUCCESS":
            print(f"   ✅ {function_name}: {exec_time:.1f}s")
        else:
            print(f"   ❌ {function_name}: {status} ({exec_time:.1f}s) - {error}")
    
    # Save results
    with open('comprehensive_strategy_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: comprehensive_strategy_test_results.json")
    
    return results

if __name__ == "__main__":
    test_all_strategies()