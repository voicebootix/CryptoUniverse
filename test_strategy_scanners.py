#!/usr/bin/env python3
"""
Test Strategy Scanners

Test the individual strategy scanners to see why they're not finding opportunities
"""

import asyncio
import sys
import os

# Set environment variables
os.environ['SECRET_KEY'] = 'test-key'
os.environ['DATABASE_URL'] = 'sqlite:///test.db'
os.environ['ENVIRONMENT'] = 'development'

sys.path.append('/workspace')

async def test_trading_strategies_service():
    """Test the trading strategies service directly."""
    
    print("🔧 TESTING TRADING STRATEGIES SERVICE")
    print("=" * 60)
    
    try:
        from app.services.trading_strategies import trading_strategies_service
        
        print("✅ Trading strategies service imported")
        
        # Test spot momentum strategy using execute_strategy method
        print("\n📊 Testing spot_momentum_strategy...")

        from app.models.strategy import StrategyParameters

        # Create StrategyParameters instance
        params = StrategyParameters(
            symbol="BTC/USDT",
            timeframe="4h"
        )

        result = await trading_strategies_service.execute_strategy(
            function="spot_momentum_strategy",
            symbol="BTC/USDT",
            parameters={"timeframe": "4h"},
            user_id="test",
            simulation_mode=True
        )
        
        print(f"   Success: {result.get('success', False)}")
        print(f"   Function: {result.get('function', 'Unknown')}")
        print(f"   Signal: {result.get('signal', {})}")
        print(f"   Error: {result.get('error', 'None')}")
        
        if result.get('signal'):
            signal = result['signal']
            print(f"   Signal strength: {signal.get('strength', 0)}")
            print(f"   Signal confidence: {signal.get('confidence', 0)}")
            print(f"   Signal direction: {signal.get('direction', 'Unknown')}")
        
        return result.get('success', False)
        
    except Exception as e:
        print(f"❌ Trading strategies test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_opportunity_scanner_directly():
    """Test opportunity scanner methods directly."""
    
    print(f"\n🔍 TESTING OPPORTUNITY SCANNER DIRECTLY")
    print("=" * 60)
    
    try:
        from app.services.user_opportunity_discovery import user_opportunity_discovery
        
        print("✅ Opportunity discovery service imported")
        
        # Create mock discovered assets with attribute access
        import types

        def dict_to_obj(d):
            return types.SimpleNamespace(**d)

        mock_discovered_assets = {
            "tier_professional": [
                dict_to_obj({"symbol": "AVNT", "volume_24h_usd": 21066658, "price_usd": 0.9939}),
                dict_to_obj({"symbol": "AVAX", "volume_24h_usd": 18964275, "price_usd": 29.7090}),
                dict_to_obj({"symbol": "PUMP", "volume_24h_usd": 15097252, "price_usd": 0.0081})
            ],
            "tier_retail": [
                dict_to_obj({"symbol": "HIFI", "volume_24h_usd": 9330189, "price_usd": 0.4055}),
                dict_to_obj({"symbol": "PEPE", "volume_24h_usd": 8244452, "price_usd": 0.000018}),
                dict_to_obj({"symbol": "LINK", "volume_24h_usd": 10424439, "price_usd": 24.27})
            ]
        }
        
        # Create mock user profile
        from app.services.user_opportunity_discovery import UserOpportunityProfile
        user_profile = UserOpportunityProfile(
            user_id="test",
            active_strategy_count=3,
            total_monthly_strategy_cost=0,
            user_tier="basic",
            max_asset_tier="tier_retail",
            opportunity_scan_limit=50,
            last_scan_time=None
        )
        
        # Test spot momentum scanner
        print("\n📊 Testing _scan_spot_momentum_opportunities...")
        
        momentum_opportunities = await user_opportunity_discovery._scan_spot_momentum_opportunities(
            discovered_assets=mock_discovered_assets,
            user_profile=user_profile,
            scan_id="test_scan"
        )
        
        print(f"   Momentum opportunities found: {len(momentum_opportunities)}")
        
        for opp in momentum_opportunities[:3]:
            print(f"      {opp.symbol}: {opp.confidence_score:.1%} confidence, ${opp.profit_potential_usd:.2f} potential")
        
        return len(momentum_opportunities) > 0
        
    except Exception as e:
        print(f"❌ Opportunity scanner test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_get_top_symbols_method():
    """Test the _get_top_symbols_by_volume method."""
    
    print(f"\n🔍 TESTING _get_top_symbols_by_volume")
    print("=" * 60)
    
    try:
        from app.services.user_opportunity_discovery import user_opportunity_discovery
        
        # Mock discovered assets with attribute access
        import types

        def dict_to_obj(d):
            return types.SimpleNamespace(**d)

        mock_discovered_assets = {
            "tier_professional": [
                dict_to_obj({"symbol": "AVNT", "volume_24h_usd": 21066658}),
                dict_to_obj({"symbol": "AVAX", "volume_24h_usd": 18964275})
            ],
            "tier_retail": [
                dict_to_obj({"symbol": "HIFI", "volume_24h_usd": 9330189}),
                dict_to_obj({"symbol": "LINK", "volume_24h_usd": 10424439})
            ]
        }
        
        # Test the method
        top_symbols = user_opportunity_discovery._get_top_symbols_by_volume(
            discovered_assets=mock_discovered_assets,
            limit=10
        )
        
        print(f"   Top symbols extracted: {len(top_symbols)}")
        print(f"   Symbols: {top_symbols}")
        
        return len(top_symbols) > 0
        
    except Exception as e:
        print(f"❌ Get top symbols test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("🔍 STRATEGY SCANNER ANALYSIS")
    print("=" * 80)
    
    # Test components
    trading_ok = await test_trading_strategies_service()
    scanner_ok = await test_opportunity_scanner_directly()
    symbols_ok = await test_get_top_symbols_method()
    
    print(f"\n📊 ANALYSIS RESULTS:")
    print("=" * 60)
    print(f"Trading Strategies Service: {'✅' if trading_ok else '❌'}")
    print(f"Opportunity Scanner: {'✅' if scanner_ok else '❌'}")
    print(f"Symbol Extraction: {'✅' if symbols_ok else '❌'}")
    
    if all([trading_ok, scanner_ok, symbols_ok]):
        print(f"\n🎉 ALL COMPONENTS WORKING!")
    else:
        print(f"\n⚠️ SOME COMPONENTS NEED FIXES")

if __name__ == "__main__":
    asyncio.run(main())