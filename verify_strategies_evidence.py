#!/usr/bin/env python3
"""
Evidence-Based Strategy Verification

Test each of the 14 strategies individually to get factual evidence
of what's working, what's failing, and why.
"""

import requests
import json
import time
from datetime import datetime

def test_individual_strategy(strategy_name, function_name, parameters, headers):
    """Test a single strategy and return detailed results."""
    print(f"\n🔍 Testing {strategy_name}...")
    
    payload = {
        "function": function_name,
        "symbol": "BTC/USDT",
        "parameters": parameters,
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
            execution_result = data.get('execution_result', {})
            
            print(f"   Status Code: {response.status_code}")
            print(f"   Success: {success}")
            print(f"   Execution Time: {execution_time:.1f}s")
            print(f"   Error: {error}")
            
            if success and execution_result:
                # Check what kind of data we got
                if isinstance(execution_result, dict):
                    print(f"   Result Keys: {list(execution_result.keys())}")
                    if 'opportunities' in execution_result:
                        opps = execution_result['opportunities']
                        print(f"   Opportunities Found: {len(opps) if isinstance(opps, list) else 'N/A'}")
                    if 'signals' in execution_result:
                        signals = execution_result['signals']
                        print(f"   Signals Found: {len(signals) if isinstance(signals, list) else 'N/A'}")
                    if 'recommendations' in execution_result:
                        recs = execution_result['recommendations']
                        print(f"   Recommendations: {len(recs) if isinstance(recs, list) else 'N/A'}")
                elif isinstance(execution_result, list):
                    print(f"   Result List Length: {len(execution_result)}")
                else:
                    print(f"   Result Type: {type(execution_result)}")
                    print(f"   Result Value: {str(execution_result)[:200]}...")
            
            return {
                "status": "success" if success else "failed",
                "execution_time": execution_time,
                "success": success,
                "error": error,
                "execution_result": execution_result,
                "raw_response": data
            }
        else:
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return {
                "status": "http_error",
                "execution_time": execution_time,
                "success": False,
                "error": f"HTTP {response.status_code}",
                "execution_result": None,
                "raw_response": response.text
            }
            
    except requests.exceptions.Timeout:
        print(f"   TIMEOUT after 60s")
        return {
            "status": "timeout",
            "execution_time": 60.0,
            "success": False,
            "error": "Request timeout",
            "execution_result": None,
            "raw_response": None
        }
    except Exception as e:
        print(f"   ERROR: {str(e)}")
        return {
            "status": "error",
            "execution_time": time.time() - start_time,
            "success": False,
            "error": str(e),
            "execution_result": None,
            "raw_response": None
        }

def main():
    """Test all 14 strategies with evidence."""
    print("🚀 EVIDENCE-BASED STRATEGY VERIFICATION")
    print("=" * 60)
    
    # Get authentication
    login_data = {
        "email": "admin@cryptouniverse.com",
        "password": "AdminPass123!"
    }
    
    try:
        response = requests.post("https://cryptouniverse.onrender.com/api/v1/auth/login", json=login_data, timeout=30)
        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code}")
            return
        
        token = response.json().get('access_token')
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        print("✅ Authentication successful")
        
    except Exception as e:
        print(f"❌ Login error: {e}")
        return
    
    # Define all 14 strategies with their exact parameters
    strategies = [
        {
            "name": "Risk Management",
            "function": "risk_management",
            "parameters": {
                "analysis_type": "comprehensive",
                "symbols": ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
            }
        },
        {
            "name": "Portfolio Optimization", 
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
            "name": "Scalping",
            "function": "scalping_strategy",
            "parameters": {"timeframe": "5m", "profit_target": 0.5}
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
            "name": "Market Making",
            "function": "market_making",
            "parameters": {"symbol": "BTC/USDT", "spread_bps": 10, "size": 0.1}
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
        },
        {
            "name": "Funding Arbitrage",
            "function": "funding_arbitrage",
            "parameters": {"symbol": "BTC/USDT", "exchanges": ["binance", "okx"]}
        },
        {
            "name": "Hedge Position",
            "function": "hedge_position",
            "parameters": {"symbol": "BTC/USDT", "hedge_ratio": 0.5}
        },
        {
            "name": "Complex Strategy",
            "function": "complex_strategy",
            "parameters": {"strategy_type": "butterfly", "symbol": "BTC/USDT"}
        }
    ]
    
    # Test each strategy
    results = {}
    for strategy in strategies:
        result = test_individual_strategy(
            strategy["name"],
            strategy["function"], 
            strategy["parameters"],
            headers
        )
        results[strategy["name"]] = result
    
    # Generate evidence-based report
    print("\n" + "=" * 60)
    print("📊 EVIDENCE-BASED RESULTS")
    print("=" * 60)
    
    working = []
    partial = []
    failing = []
    
    for name, result in results.items():
        status = result["status"]
        success = result["success"]
        exec_time = result["execution_time"]
        error = result["error"]
        
        if status == "success" and success:
            working.append(f"{name} ({exec_time:.1f}s)")
        elif status == "success" and not success:
            partial.append(f"{name} ({exec_time:.1f}s) - {error}")
        else:
            failing.append(f"{name} ({exec_time:.1f}s) - {error}")
    
    print(f"\n✅ WORKING STRATEGIES ({len(working)}/14):")
    for item in working:
        print(f"   - {item}")
    
    print(f"\n⚠️  PARTIAL/FAILED STRATEGIES ({len(partial)}/14):")
    for item in partial:
        print(f"   - {item}")
    
    print(f"\n❌ FAILING STRATEGIES ({len(failing)}/14):")
    for item in failing:
        print(f"   - {item}")
    
    # Save detailed evidence
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"strategy_evidence_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Detailed evidence saved to: {filename}")
    
    # Calculate actual working percentage
    working_count = len(working)
    total_count = len(strategies)
    working_percentage = (working_count / total_count) * 100
    
    print(f"\n📈 ACTUAL WORKING PERCENTAGE: {working_percentage:.1f}% ({working_count}/{total_count})")
    
    if working_percentage < 50:
        print("🚨 CRITICAL: System is not production-ready")
    elif working_percentage < 80:
        print("⚠️  WARNING: System needs significant improvements")
    else:
        print("✅ GOOD: System is mostly functional")

if __name__ == "__main__":
    main()