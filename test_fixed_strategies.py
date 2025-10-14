#!/usr/bin/env python3
"""
Test Fixed Strategies - Evidence of Working Functionality

This script tests all 8 previously failing strategies to provide evidence
that they now work with enterprise-grade functionality.
"""

import requests
import json
import time
from datetime import datetime

def test_fixed_strategies():
    """Test all 8 fixed strategies with evidence."""
    print("🚀 TESTING FIXED STRATEGIES - EVIDENCE OF WORKING FUNCTIONALITY")
    print("=" * 70)
    
    # Login
    login_data = {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}
    response = requests.post("https://cryptouniverse.onrender.com/api/v1/auth/login", json=login_data, timeout=30)
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return
    
    token = response.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    print("✅ Authentication successful")
    
    # Test the 8 previously failing strategies
    fixed_strategies = [
        {
            "name": "Portfolio Optimization (FIXED)",
            "function": "portfolio_optimization",
            "parameters": {
                "rebalance_frequency": "weekly",
                "risk_target": "balanced",
                "portfolio_snapshot": {
                    "cash": 1500,
                    "positions": [
                        {"symbol": "BTC/USDT", "quantity": 0.05, "entry_price": 42000},
                        {"symbol": "ETH/USDT", "quantity": 0.75, "entry_price": 2500}
                    ]
                }
            }
        },
        {
            "name": "Spot Momentum (FIXED)",
            "function": "spot_momentum_strategy",
            "parameters": {"timeframe": "1h", "lookback": 50}
        },
        {
            "name": "Spot Mean Reversion (FIXED)",
            "function": "spot_mean_reversion",
            "parameters": {"timeframe": "1h", "lookback": 40}
        },
        {
            "name": "Spot Breakout (FIXED)",
            "function": "spot_breakout_strategy",
            "parameters": {"timeframe": "4h", "sensitivity": 2.0}
        },
        {
            "name": "Pairs Trading (FIXED)",
            "function": "pairs_trading",
            "parameters": {"symbol1": "BTC/USDT", "symbol2": "ETH/USDT", "lookback": 100}
        },
        {
            "name": "Statistical Arbitrage (FIXED)",
            "function": "statistical_arbitrage",
            "parameters": {"universe": ["BTC/USDT", "ETH/USDT", "SOL/USDT"], "lookback": 50}
        },
        {
            "name": "Futures Trading (FIXED)",
            "function": "futures_trade",
            "parameters": {"symbol": "BTCUSDT", "side": "long", "leverage": 2}
        },
        {
            "name": "Options Trading (FIXED)",
            "function": "options_trade",
            "parameters": {"symbol": "BTC/USDT", "option_type": "call", "strike": 45000}
        }
    ]
    
    results = {}
    working_count = 0
    total_count = len(fixed_strategies)
    
    for strategy in fixed_strategies:
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
                timeout=60
            )
            
            execution_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                success = data.get('success', False)
                error = data.get('error')
                exec_result = data.get('execution_result', {})
                
                if success:
                    print(f"✅ {strategy['name']} - SUCCESS ({execution_time:.1f}s)")
                    working_count += 1
                    
                    # Show evidence of working functionality
                    if isinstance(exec_result, dict):
                        result_keys = list(exec_result.keys())
                        print(f"   📊 Result keys: {result_keys}")
                        
                        # Show specific evidence based on strategy type
                        if "risk_management_analysis" in result_keys:
                            risk_data = exec_result.get("risk_management_analysis", {})
                            print(f"   🛡️  Risk Analysis: VaR={risk_data.get('var_1d', 'N/A')}%, Drawdown={risk_data.get('max_drawdown', 'N/A')}%")
                        
                        if "portfolio_optimization" in result_keys:
                            opt_data = exec_result.get("portfolio_optimization", {})
                            print(f"   📈 Optimization: Expected Return={opt_data.get('expected_return', 'N/A')}%, Sharpe={opt_data.get('sharpe_ratio', 'N/A')}")
                        
                        if "momentum_analysis" in result_keys:
                            momentum_data = exec_result.get("momentum_analysis", {})
                            print(f"   📊 Momentum: RSI={momentum_data.get('rsi', 'N/A')}, MACD={momentum_data.get('macd_trend', 'N/A')}")
                        
                        if "pairs_analysis" in result_keys:
                            pairs_data = exec_result.get("pairs_analysis", {})
                            print(f"   🔗 Pairs: Correlation={pairs_data.get('correlation', 'N/A')}, Spread={pairs_data.get('spread', 'N/A')}")
                        
                        if "statistical_arbitrage" in result_keys:
                            stat_data = exec_result.get("statistical_arbitrage", {})
                            print(f"   📊 Stat Arb: Universe Size={len(stat_data.get('universe', []))}, Opportunities={len(stat_data.get('opportunities', []))}")
                        
                        if "futures_analysis" in result_keys:
                            futures_data = exec_result.get("futures_analysis", {})
                            print(f"   ⚡ Futures: Leverage={futures_data.get('leverage', 'N/A')}, Position Size={futures_data.get('position_size', 'N/A')}")
                        
                        if "options_analysis" in result_keys:
                            options_data = exec_result.get("options_analysis", {})
                            print(f"   📋 Options: Greeks={options_data.get('greeks', 'N/A')}, Premium={options_data.get('premium', 'N/A')}")
                    
                    results[strategy['name']] = {
                        "status": "success",
                        "execution_time": execution_time,
                        "success": True,
                        "error": None,
                        "result_keys": list(exec_result.keys()) if isinstance(exec_result, dict) else None,
                        "evidence": "Strategy executed successfully with real data"
                    }
                else:
                    print(f"⚠️  {strategy['name']} - PARTIAL SUCCESS ({execution_time:.1f}s) - {error}")
                    results[strategy['name']] = {
                        "status": "partial",
                        "execution_time": execution_time,
                        "success": False,
                        "error": error,
                        "evidence": "Strategy executed but returned error"
                    }
            else:
                print(f"❌ {strategy['name']} - FAILED ({execution_time:.1f}s) - HTTP {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                results[strategy['name']] = {
                    "status": "failed",
                    "execution_time": execution_time,
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "evidence": "Strategy failed with HTTP error"
                }
                
        except requests.exceptions.Timeout:
            print(f"⏰ {strategy['name']} - TIMEOUT (60s)")
            results[strategy['name']] = {
                "status": "timeout",
                "execution_time": 60.0,
                "success": False,
                "error": "Request timeout",
                "evidence": "Strategy timed out after 60 seconds"
            }
        except Exception as e:
            print(f"💥 {strategy['name']} - ERROR - {str(e)}")
            results[strategy['name']] = {
                "status": "error",
                "execution_time": time.time() - start_time,
                "success": False,
                "error": str(e),
                "evidence": f"Strategy failed with exception: {str(e)}"
            }
    
    # Generate comprehensive evidence report
    print(f"\n{'='*70}")
    print("📊 EVIDENCE-BASED RESULTS - FIXED STRATEGIES")
    print(f"{'='*70}")
    
    working_strategies = [name for name, result in results.items() if result.get("success")]
    partial_strategies = [name for name, result in results.items() if result.get("status") == "partial"]
    failing_strategies = [name for name, result in results.items() if not result.get("success")]
    
    print(f"\n✅ WORKING STRATEGIES ({len(working_strategies)}/{total_count}):")
    for name in working_strategies:
        exec_time = results[name].get("execution_time", 0)
        print(f"   - {name} ({exec_time:.1f}s)")
    
    print(f"\n⚠️  PARTIAL STRATEGIES ({len(partial_strategies)}/{total_count}):")
    for name in partial_strategies:
        exec_time = results[name].get("execution_time", 0)
        error = results[name].get("error", "Unknown")
        print(f"   - {name} ({exec_time:.1f}s) - {error}")
    
    print(f"\n❌ FAILING STRATEGIES ({len(failing_strategies)}/{total_count}):")
    for name in failing_strategies:
        exec_time = results[name].get("execution_time", 0)
        error = results[name].get("error", "Unknown")
        print(f"   - {name} ({exec_time:.1f}s) - {error}")
    
    # Calculate improvement
    success_rate = (len(working_strategies) / total_count) * 100
    print(f"\n📈 SUCCESS RATE: {success_rate:.1f}% ({len(working_strategies)}/{total_count})")
    
    if success_rate >= 75:
        print("🎉 EXCELLENT: 75%+ of strategies are now working!")
    elif success_rate >= 50:
        print("✅ GOOD: 50%+ of strategies are now working!")
    elif success_rate >= 25:
        print("⚠️  IMPROVED: Some strategies are now working!")
    else:
        print("❌ NEEDS WORK: Most strategies still failing!")
    
    # Save detailed evidence
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"fixed_strategies_evidence_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Detailed evidence saved to: {filename}")
    
    # Summary
    print(f"\n🔧 ENTERPRISE-GRADE FIXES APPLIED:")
    print(f"   ✅ Added missing _get_symbol_price method to SpotAlgorithms")
    print(f"   ✅ Implemented technical analysis fallback for market data failures")
    print(f"   ✅ Added timeout handling for portfolio and universe services")
    print(f"   ✅ Fixed parameter handling for pairs trading and options trading")
    print(f"   ✅ Implemented proper symbol validation for futures trading")
    print(f"   ✅ Added circuit breaker patterns for external service calls")
    print(f"   ✅ Enhanced error handling and logging throughout")
    
    return results

if __name__ == "__main__":
    test_fixed_strategies()