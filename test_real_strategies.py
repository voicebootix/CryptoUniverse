#!/usr/bin/env python3
"""
Real Strategy Testing - Test actual strategy scanners with real trading service
to see what's really happening at runtime.
"""

import asyncio
import json
import sys
import traceback
from datetime import datetime
from typing import Dict, List, Any

# Add the app directory to the path
sys.path.append('/workspace')

async def test_real_strategies():
    """Test real strategy scanners with actual trading service calls."""
    
    print("🚀 REAL STRATEGY TESTING")
    print("Testing actual strategy scanners with real trading service calls")
    
    try:
        # Import the actual services
        from app.services.trading_strategies import trading_strategies_service
        
        print("✅ Successfully imported trading strategies service")
        
        # Test each strategy function individually
        strategy_tests = [
            ("portfolio_optimization", {"user_id": "test-user", "simulation_mode": True}),
            ("risk_management", {"user_id": "test-user", "simulation_mode": True}),
            ("spot_momentum_strategy", {"symbol": "BTC/USDT", "parameters": {"timeframe": "4h"}, "user_id": "test-user", "simulation_mode": True}),
            ("funding_arbitrage", {"parameters": {"symbols": "BTC,ETH", "exchanges": "all", "min_funding_rate": 0.005}, "user_id": "test-user", "simulation_mode": True}),
            ("statistical_arbitrage", {"strategy_type": "mean_reversion", "parameters": {"universe": "BTC,ETH,ADA"}, "user_id": "test-user"}),
            ("pairs_trading", {"strategy_type": "statistical_arbitrage", "parameters": {"pair_symbols": "BTC-ETH"}, "user_id": "test-user"}),
            ("spot_mean_reversion", {"symbol": "BTC/USDT", "parameters": {"timeframe": "1h"}, "user_id": "test-user"}),
            ("spot_breakout_strategy", {"symbol": "BTC/USDT", "parameters": {"timeframe": "1h"}, "user_id": "test-user"}),
            ("scalping_strategy", {"strategy_type": "momentum_scalp", "symbol": "BTC/USDT", "parameters": {"timeframe": "1m", "profit_target": 0.005, "stop_loss": 0.002}, "user_id": "test-user", "simulation_mode": True}),
            ("market_making", {"strategy_type": "dual_side", "symbol": "BTC/USDT", "parameters": {"spread_target": 0.002, "order_amount": 1000}, "user_id": "test-user", "simulation_mode": True}),
            ("futures_trade", {"strategy_type": "trend_following", "symbol": "BTC/USDT", "parameters": {"timeframe": "1h", "leverage": 10}, "user_id": "test-user", "simulation_mode": True}),
            ("options_trade", {"strategy_type": "iron_condor", "symbol": "BTC/USDT", "parameters": {"timeframe": "1d", "calculate_greeks": True}, "user_id": "test-user", "simulation_mode": True})
        ]
        
        results = []
        
        for strategy_name, params in strategy_tests:
            print(f"\n{'='*60}")
            print(f"🧪 TESTING: {strategy_name}")
            print(f"{'='*60}")
            
            try:
                print(f"📞 Calling trading_strategies_service.execute_strategy('{strategy_name}')...")
                start_time = datetime.now()
                
                # Call the actual trading strategy service
                result = await trading_strategies_service.execute_strategy(
                    function=strategy_name,
                    **params
                )
                
                end_time = datetime.now()
                execution_time = (end_time - start_time).total_seconds()
                
                print(f"⏱️  Execution time: {execution_time:.2f} seconds")
                print(f"📊 Success: {result.get('success', False)}")
                
                if result.get('success'):
                    print(f"✅ SUCCESS: {strategy_name} executed successfully")
                    
                    # Analyze the response structure
                    response_keys = list(result.keys())
                    print(f"   📋 Response keys: {response_keys}")
                    
                    # Look for opportunities or signals
                    opportunities_found = 0
                    signals_found = 0
                    
                    # Check for various opportunity/signal patterns
                    if 'opportunities' in result:
                        opportunities_found = len(result['opportunities'])
                    if 'signal' in result:
                        signals_found = 1
                    if 'signals' in result:
                        signals_found = len(result['signals'])
                    if 'trading_signals' in result:
                        signals_found = len(result['trading_signals'])
                    if 'breakout_signals' in result:
                        signals_found = len(result['breakout_signals'])
                    if 'rebalancing_recommendations' in result:
                        opportunities_found = len(result['rebalancing_recommendations'])
                    if 'mitigation_strategies' in result:
                        opportunities_found = len(result['mitigation_strategies'])
                    
                    print(f"   📈 Opportunities found: {opportunities_found}")
                    print(f"   📡 Signals found: {signals_found}")
                    
                    # Show sample data
                    if opportunities_found > 0 or signals_found > 0:
                        print(f"   📊 Sample data available")
                        if 'signal' in result:
                            signal_data = result['signal']
                            print(f"      Signal strength: {signal_data.get('strength', 'N/A')}")
                            print(f"      Signal action: {signal_data.get('action', 'N/A')}")
                    else:
                        print(f"   ⚠️  No opportunities or signals found in response")
                    
                    test_result = {
                        "strategy": strategy_name,
                        "status": "SUCCESS",
                        "execution_time": execution_time,
                        "success": True,
                        "opportunities_found": opportunities_found,
                        "signals_found": signals_found,
                        "response_keys": response_keys,
                        "error": None
                    }
                else:
                    error_msg = result.get('error', 'Unknown error')
                    print(f"❌ FAILED: {strategy_name} returned success=False")
                    print(f"   Error: {error_msg}")
                    
                    test_result = {
                        "strategy": strategy_name,
                        "status": "FAILED",
                        "execution_time": execution_time,
                        "success": False,
                        "opportunities_found": 0,
                        "signals_found": 0,
                        "response_keys": list(result.keys()),
                        "error": error_msg
                    }
                
                results.append(test_result)
                
            except Exception as e:
                print(f"❌ ERROR: {strategy_name} failed with exception")
                print(f"   Error type: {type(e).__name__}")
                print(f"   Error message: {str(e)}")
                print(f"   Traceback:")
                traceback.print_exc()
                
                test_result = {
                    "strategy": strategy_name,
                    "status": "ERROR",
                    "execution_time": 0,
                    "success": False,
                    "opportunities_found": 0,
                    "signals_found": 0,
                    "response_keys": [],
                    "error": f"{type(e).__name__}: {str(e)}"
                }
                results.append(test_result)
        
        # Summary
        print(f"\n{'='*80}")
        print("📊 REAL STRATEGY TESTING SUMMARY")
        print(f"{'='*80}")
        
        successful = [r for r in results if r["status"] == "SUCCESS"]
        failed = [r for r in results if r["status"] == "FAILED"]
        errors = [r for r in results if r["status"] == "ERROR"]
        
        print(f"✅ Successful strategies: {len(successful)}/{len(results)}")
        print(f"❌ Failed strategies: {len(failed)}/{len(results)}")
        print(f"💥 Error strategies: {len(errors)}/{len(results)}")
        
        if successful:
            print(f"\n✅ WORKING STRATEGIES:")
            for result in successful:
                print(f"   - {result['strategy']}: {result['opportunities_found']} opportunities, {result['signals_found']} signals ({result['execution_time']:.2f}s)")
        
        if failed:
            print(f"\n❌ FAILED STRATEGIES:")
            for result in failed:
                print(f"   - {result['strategy']}: {result['error']}")
        
        if errors:
            print(f"\n💥 ERROR STRATEGIES:")
            for result in errors:
                print(f"   - {result['strategy']}: {result['error']}")
        
        # Save detailed results
        with open(f'/workspace/real_strategy_test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to real_strategy_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        return results
        
    except Exception as e:
        print(f"💥 CRITICAL ERROR: Failed to import or initialize services")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {str(e)}")
        print(f"   Traceback:")
        traceback.print_exc()
        return []

if __name__ == "__main__":
    asyncio.run(test_real_strategies())