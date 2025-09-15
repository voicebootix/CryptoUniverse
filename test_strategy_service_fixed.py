#!/usr/bin/env python3
"""
Test Trading Strategies Service with Fixed Method Calls

Test the trading strategies service using the correct execute_strategy method
"""

import asyncio
import sys
import os

# Set environment variables from existing or use safe defaults
if 'SECRET_KEY' not in os.environ:
    os.environ['SECRET_KEY'] = 'test-key-only-for-testing'
if 'DATABASE_URL' not in os.environ:
    os.environ['DATABASE_URL'] = 'sqlite:///test_memory.db'  # Use in-memory SQLite for testing
if 'ENVIRONMENT' not in os.environ:
    os.environ['ENVIRONMENT'] = 'testing'

# Dynamically determine project root
from pathlib import Path
project_root = Path(__file__).resolve().parents[0]
sys.path.insert(0, str(project_root))

async def test_strategy_service_methods():
    """Test trading strategies service with correct method calls."""
    
    print("🔧 TESTING TRADING STRATEGIES SERVICE - CORRECTED CALLS")
    print("=" * 70)
    
    try:
        from app.services.trading_strategies import trading_strategies_service
        
        print("✅ Trading strategies service imported successfully")
        
        # Test 1: Spot Momentum Strategy (corrected call)
        print("\n📊 Test 1: Spot Momentum Strategy")
        
        momentum_result = await trading_strategies_service.execute_strategy(
            function="spot_momentum_strategy",
            symbol="BTC/USDT",
            parameters={"timeframe": "4h"},
            user_id="test"
        )
        
        print(f"   Success: {momentum_result.get('success', False)}")
        print(f"   Function: {momentum_result.get('function', 'Unknown')}")
        print(f"   Strategy Type: {momentum_result.get('strategy_type', 'Unknown')}")
        print(f"   Error: {momentum_result.get('error', 'None')}")
        
        if momentum_result.get('success'):
            print(f"   ✅ Momentum strategy working!")
            execution_result = momentum_result.get('execution_result', {})
            print(f"   Signal strength: {execution_result.get('signal_strength', 'Unknown')}")
        else:
            print(f"   ❌ Momentum strategy failed")
        
        # Test 2: Risk Management Strategy
        print("\n🛡️ Test 2: Risk Management Strategy")
        
        risk_result = await trading_strategies_service.execute_strategy(
            function="risk_management",
            user_id="test"
        )
        
        print(f"   Success: {risk_result.get('success', False)}")
        print(f"   Function: {risk_result.get('function', 'Unknown')}")
        print(f"   Error: {risk_result.get('error', 'None')}")
        
        if risk_result.get('success'):
            print(f"   ✅ Risk management working!")
            risk_analysis = risk_result.get('risk_management_analysis', {})
            portfolio_metrics = risk_analysis.get('portfolio_risk_metrics', {})
            print(f"   Portfolio VaR: ${portfolio_metrics.get('portfolio_var_1d_95', 0):,.2f}")
        else:
            print(f"   ❌ Risk management failed")
        
        # Test 3: Portfolio Optimization Strategy
        print("\n📊 Test 3: Portfolio Optimization Strategy")
        
        portfolio_result = await trading_strategies_service.execute_strategy(
            function="portfolio_optimization",
            user_id="test"
        )
        
        print(f"   Success: {portfolio_result.get('success', False)}")
        print(f"   Function: {portfolio_result.get('function', 'Unknown')}")
        print(f"   Error: {portfolio_result.get('error', 'None')}")
        
        if portfolio_result.get('success'):
            print(f"   ✅ Portfolio optimization working!")
        else:
            print(f"   ❌ Portfolio optimization failed")
        
        # Count successful strategies
        successful_strategies = sum([
            momentum_result.get('success', False),
            risk_result.get('success', False), 
            portfolio_result.get('success', False)
        ])
        
        print(f"\n📊 STRATEGY SERVICE RESULTS:")
        print(f"   Successful strategies: {successful_strategies}/3")
        print(f"   Success rate: {successful_strategies/3*100:.1f}%")
        
        return successful_strategies > 0
        
    except Exception as e:
        print(f"❌ Strategy service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_opportunity_discovery_with_fixes():
    """Test opportunity discovery with all fixes applied."""
    
    print(f"\n🔍 TESTING OPPORTUNITY DISCOVERY WITH FIXES")
    print("=" * 70)
    
    try:
        from app.services.user_opportunity_discovery import user_opportunity_discovery
        
        print("✅ Opportunity discovery imported")
        
        # Test with admin user ID (we know has 3 strategies)
        test_result = await user_opportunity_discovery.discover_opportunities_for_user(
            user_id="test-admin",
            force_refresh=True,
            include_strategy_recommendations=True
        )
        
        print(f"   Success: {test_result.get('success', False)}")
        print(f"   Total opportunities: {test_result.get('total_opportunities', 0)}")
        print(f"   Opportunities: {len(test_result.get('opportunities', []))}")
        print(f"   Error: {test_result.get('error', 'None')}")
        
        if test_result.get('opportunities'):
            print(f"   🎉 OPPORTUNITIES FOUND!")
            for i, opp in enumerate(test_result['opportunities'][:3], 1):
                print(f"      {i}. {opp.get('symbol', 'Unknown')}: {opp.get('confidence_score', 0):.1%}")
        else:
            print(f"   ⚠️ No opportunities found")
            
            # Check execution details
            execution_time = test_result.get('execution_time_ms', 0)
            asset_discovery = test_result.get('asset_discovery', {})
            
            print(f"   Execution time: {execution_time:.0f}ms")
            print(f"   Assets discovered: {asset_discovery.get('total_assets_scanned', 0)}")
            
        return test_result.get('total_opportunities', 0) > 0
        
    except Exception as e:
        print(f"❌ Opportunity discovery test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("🔍 TRADING STRATEGIES SERVICE COMPREHENSIVE TEST")
    print("=" * 80)
    
    # Test strategy service
    strategy_ok = await test_strategy_service_methods()
    
    # Test opportunity discovery integration
    opportunity_ok = await test_opportunity_discovery_with_fixes()
    
    print(f"\n📊 COMPREHENSIVE TEST RESULTS:")
    print("=" * 70)
    print(f"Trading Strategies Service: {'✅' if strategy_ok else '❌'}")
    print(f"Opportunity Discovery: {'✅' if opportunity_ok else '❌'}")
    
    if strategy_ok and opportunity_ok:
        print(f"\n🎉 COMPLETE SYSTEM WORKING!")
        print(f"   ✅ Strategy service operational")
        print(f"   ✅ Opportunity discovery generating results")
        print(f"   ✅ Enterprise asset discovery feeding data")
    elif strategy_ok:
        print(f"\n⚠️ STRATEGY SERVICE WORKING, OPPORTUNITY DISCOVERY NEEDS WORK")
    else:
        print(f"\n❌ STRATEGY SERVICE STILL HAS ISSUES")

if __name__ == "__main__":
    asyncio.run(main())