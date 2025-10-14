#!/usr/bin/env python3
"""
Individual Strategy Testing - Test each strategy scanner one by one
to see if they're actually working or failing at runtime.
"""

import asyncio
import json
import sys
import traceback
from datetime import datetime
from typing import Dict, List, Any

# Add the app directory to the path
sys.path.append('/workspace')

from app.services.user_opportunity_discovery import UserOpportunityDiscoveryService, UserOpportunityProfile
from app.services.dynamic_asset_filter import enterprise_asset_filter

async def test_individual_strategy(strategy_name: str, scanner_method, discovered_assets: Dict, user_profile: UserOpportunityProfile, scan_id: str):
    """Test a single strategy scanner and return detailed results."""
    
    print(f"\n{'='*60}")
    print(f"🧪 TESTING: {strategy_name}")
    print(f"{'='*60}")
    
    # Mock portfolio result with some strategies
    portfolio_result = {
        "success": True,
        "active_strategies": [
            {"strategy_id": "ai_portfolio_optimization", "name": "AI Portfolio Optimization"},
            {"strategy_id": "ai_risk_management", "name": "AI Risk Management"},
            {"strategy_id": "ai_spot_momentum_strategy", "name": "AI Spot Momentum"},
            {"strategy_id": "ai_funding_arbitrage", "name": "AI Funding Arbitrage"},
            {"strategy_id": "ai_statistical_arbitrage", "name": "AI Statistical Arbitrage"},
            {"strategy_id": "ai_pairs_trading", "name": "AI Pairs Trading"},
            {"strategy_id": "ai_spot_mean_reversion", "name": "AI Spot Mean Reversion"},
            {"strategy_id": "ai_spot_breakout_strategy", "name": "AI Spot Breakout"},
            {"strategy_id": "ai_scalping_strategy", "name": "AI Scalping"},
            {"strategy_id": "ai_market_making", "name": "AI Market Making"},
            {"strategy_id": "ai_futures_trade", "name": "AI Futures Trading"},
            {"strategy_id": "ai_options_trade", "name": "AI Options Trading"},
            {"strategy_id": "ai_hedge_position", "name": "AI Hedge Position"},
            {"strategy_id": "ai_complex_strategy", "name": "AI Complex Strategy"}
        ]
    }
    
    try:
        print(f"📞 Calling {strategy_name} scanner...")
        start_time = datetime.now()
        
        # Call the strategy scanner
        opportunities = await scanner_method(
            discovered_assets=discovered_assets,
            user_profile=user_profile,
            scan_id=scan_id,
            portfolio_result=portfolio_result
        )
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        print(f"⏱️  Execution time: {execution_time:.2f} seconds")
        print(f"📊 Opportunities found: {len(opportunities)}")
        
        if opportunities:
            print(f"✅ SUCCESS: {strategy_name} generated {len(opportunities)} opportunities")
            
            # Show first opportunity details
            first_opp = opportunities[0]
            print(f"   📈 First opportunity:")
            print(f"      Symbol: {first_opp.symbol}")
            print(f"      Type: {first_opp.opportunity_type}")
            print(f"      Profit Potential: ${first_opp.profit_potential_usd}")
            print(f"      Confidence: {first_opp.confidence_score}%")
            print(f"      Risk Level: {first_opp.risk_level}")
            
            return {
                "strategy": strategy_name,
                "status": "SUCCESS",
                "opportunities_count": len(opportunities),
                "execution_time": execution_time,
                "error": None,
                "sample_opportunity": {
                    "symbol": first_opp.symbol,
                    "type": first_opp.opportunity_type,
                    "profit": first_opp.profit_potential_usd,
                    "confidence": first_opp.confidence_score
                }
            }
        else:
            print(f"⚠️  WARNING: {strategy_name} returned 0 opportunities")
            return {
                "strategy": strategy_name,
                "status": "NO_OPPORTUNITIES",
                "opportunities_count": 0,
                "execution_time": execution_time,
                "error": "No opportunities generated",
                "sample_opportunity": None
            }
            
    except Exception as e:
        print(f"❌ ERROR: {strategy_name} failed with exception")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {str(e)}")
        print(f"   Traceback:")
        traceback.print_exc()
        
        return {
            "strategy": strategy_name,
            "status": "ERROR",
            "opportunities_count": 0,
            "execution_time": 0,
            "error": f"{type(e).__name__}: {str(e)}",
            "sample_opportunity": None
        }

async def test_all_strategies():
    """Test all strategy scanners individually."""
    
    print("🚀 INDIVIDUAL STRATEGY TESTING")
    print("Testing each strategy scanner to see if they work at runtime")
    
    # Initialize the service
    service = UserOpportunityDiscoveryService()
    await service.async_init()
    
    # Create test user profile
    user_profile = UserOpportunityProfile(
        user_id="test-user-123",
        active_strategy_count=14,
        total_monthly_strategy_cost=0,
        user_tier="enterprise",
        max_asset_tier="tier_professional",
        opportunity_scan_limit=100,
        last_scan_time=None,
        strategy_fingerprint="test"
    )
    
    # Get discovered assets
    print("\n📡 Getting discovered assets...")
    discovered_assets = await enterprise_asset_filter.discover_all_assets_with_volume_filtering(
        min_tier="tier_retail",
        force_refresh=False
    )
    
    if not discovered_assets or sum(len(assets) for assets in discovered_assets.values()) == 0:
        print("❌ No assets discovered - cannot test strategies")
        return
    
    total_assets = sum(len(assets) for assets in discovered_assets.values())
    print(f"✅ Discovered {total_assets} assets across {len(discovered_assets)} exchanges")
    
    scan_id = f"test_scan_{int(datetime.now().timestamp())}"
    
    # Test each strategy
    strategy_tests = [
        ("Portfolio Optimization", service._scan_portfolio_optimization_opportunities),
        ("Risk Management", service._scan_risk_management_opportunities),
        ("Spot Momentum", service._scan_spot_momentum_opportunities),
        ("Spot Mean Reversion", service._scan_spot_mean_reversion_opportunities),
        ("Spot Breakout", service._scan_spot_breakout_opportunities),
        ("Scalping", service._scan_scalping_opportunities),
        ("Pairs Trading", service._scan_pairs_trading_opportunities),
        ("Statistical Arbitrage", service._scan_statistical_arbitrage_opportunities),
        ("Market Making", service._scan_market_making_opportunities),
        ("Futures Trading", service._scan_futures_trading_opportunities),
        ("Options Trading", service._scan_options_trading_opportunities),
        ("Funding Arbitrage", service._scan_funding_arbitrage_opportunities),
        ("Hedge Position", service._scan_hedge_opportunities),
        ("Complex Strategy", service._scan_complex_strategy_opportunities)
    ]
    
    results = []
    
    for strategy_name, scanner_method in strategy_tests:
        result = await test_individual_strategy(
            strategy_name, scanner_method, discovered_assets, user_profile, scan_id
        )
        results.append(result)
    
    # Summary
    print(f"\n{'='*80}")
    print("📊 STRATEGY TESTING SUMMARY")
    print(f"{'='*80}")
    
    successful = [r for r in results if r["status"] == "SUCCESS"]
    no_opportunities = [r for r in results if r["status"] == "NO_OPPORTUNITIES"]
    errors = [r for r in results if r["status"] == "ERROR"]
    
    print(f"✅ Successful strategies: {len(successful)}/{len(results)}")
    print(f"⚠️  No opportunities: {len(no_opportunities)}/{len(results)}")
    print(f"❌ Error strategies: {len(errors)}/{len(results)}")
    
    if successful:
        print(f"\n✅ WORKING STRATEGIES:")
        for result in successful:
            print(f"   - {result['strategy']}: {result['opportunities_count']} opportunities ({result['execution_time']:.2f}s)")
    
    if no_opportunities:
        print(f"\n⚠️  NO OPPORTUNITIES (but no errors):")
        for result in no_opportunities:
            print(f"   - {result['strategy']}: {result['error']}")
    
    if errors:
        print(f"\n❌ FAILING STRATEGIES:")
        for result in errors:
            print(f"   - {result['strategy']}: {result['error']}")
    
    # Save detailed results
    with open(f'/workspace/strategy_test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to strategy_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

if __name__ == "__main__":
    asyncio.run(test_all_strategies())