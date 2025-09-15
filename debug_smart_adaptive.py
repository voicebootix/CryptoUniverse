#!/usr/bin/env python3
"""
Debug SMART_ADAPTIVE Parameter

Test why SMART_ADAPTIVE isn't triggering the dynamic asset discovery
"""

import asyncio
import aiohttp
import sys
import os

# Set environment variables
os.environ['SECRET_KEY'] = 'test-key'
os.environ['DATABASE_URL'] = 'sqlite:///test.db'
os.environ['ENVIRONMENT'] = 'development'

sys.path.append('/workspace')

async def test_smart_adaptive_flow():
    """Test the SMART_ADAPTIVE flow step by step."""
    
    print("🔍 DEBUGGING SMART_ADAPTIVE FLOW")
    print("=" * 60)
    
    try:
        # Test 1: Direct enterprise asset filter
        print("📊 Test 1: Direct Enterprise Asset Filter")
        
        from app.services.dynamic_asset_filter import enterprise_asset_filter
        
        print("✅ Enterprise asset filter imported")
        
        # Initialize
        await enterprise_asset_filter.async_init()
        print("✅ Asset filter initialized")
        
        # Test get_top_assets
        print("🔍 Testing get_top_assets...")
        top_assets = await enterprise_asset_filter.get_top_assets(
            count=10,
            min_tier="tier_retail"
        )
        
        print(f"   Top assets found: {len(top_assets)}")
        if top_assets:
            print("   Sample assets:")
            for asset in top_assets[:3]:
                print(f"      {asset.symbol}: ${asset.price_usd:.2f} (Vol: ${asset.volume_24h_usd:,.0f})")
        else:
            print("   ❌ No assets found")
        
        return len(top_assets) > 0
        
    except Exception as e:
        print(f"❌ Enterprise asset filter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_market_analysis_smart_adaptive():
    """Test market analysis with SMART_ADAPTIVE directly."""
    
    print(f"\n📊 Test 2: Market Analysis with SMART_ADAPTIVE")
    print("=" * 60)
    
    try:
        from app.services.market_analysis_core import MarketAnalysisService
        
        service = MarketAnalysisService()
        print("✅ Market analysis service imported")
        
        # Test with SMART_ADAPTIVE
        print("🔍 Testing realtime_price_tracking with SMART_ADAPTIVE...")
        
        result = await service.realtime_price_tracking(
            symbols="SMART_ADAPTIVE",
            exchanges="all",
            user_id="system"
        )
        
        print(f"   Success: {result.get('success', False)}")
        print(f"   Function: {result.get('function', 'Unknown')}")
        print(f"   Data count: {len(result.get('data', {}))}")
        print(f"   Error: {result.get('error', 'None')}")
        
        if result.get('data'):
            print("   Sample data:")
            for symbol, data in list(result.get('data', {}).items())[:3]:
                print(f"      {symbol}: {data}")
        
        return result.get('success', False)
        
    except Exception as e:
        print(f"❌ Market analysis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_complete_market_assessment():
    """Test complete market assessment."""
    
    print(f"\n📊 Test 3: Complete Market Assessment")
    print("=" * 60)
    
    try:
        from app.services.market_analysis_core import MarketAnalysisService
        
        service = MarketAnalysisService()
        
        # Test complete assessment
        result = await service.complete_market_assessment(
            symbols="SMART_ADAPTIVE",
            depth="comprehensive",
            user_id="system"
        )
        
        print(f"   Success: {result.get('success', False)}")
        print(f"   Components: {len(result.get('data', {}).get('assessment', {}))}")
        print(f"   Market Score: {result.get('data', {}).get('market_score', 'Unknown')}")
        print(f"   Error: {result.get('error', 'None')}")
        
        assessment = result.get('data', {}).get('assessment', {})
        if assessment:
            print("   Assessment components:")
            for component, data in assessment.items():
                has_data = data is not None and data != {}
                print(f"      {component}: {'✅' if has_data else '❌'}")
        
        return result.get('success', False)
        
    except Exception as e:
        print(f"❌ Complete assessment test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("🔍 SMART_ADAPTIVE DEBUG ANALYSIS")
    print("=" * 80)
    
    # Test all components
    asset_filter_ok = await test_smart_adaptive_flow()
    price_tracking_ok = await test_market_analysis_smart_adaptive()
    assessment_ok = await test_complete_market_assessment()
    
    print(f"\n📊 DEBUG SUMMARY:")
    print("=" * 60)
    print(f"Enterprise Asset Filter: {'✅' if asset_filter_ok else '❌'}")
    print(f"Price Tracking: {'✅' if price_tracking_ok else '❌'}")
    print(f"Complete Assessment: {'✅' if assessment_ok else '❌'}")
    
    if not any([asset_filter_ok, price_tracking_ok, assessment_ok]):
        print("\n⚠️ ALL COMPONENTS FAILING")
        print("Root cause likely: Missing dependencies or service initialization")
    elif asset_filter_ok and not price_tracking_ok:
        print("\n⚠️ ASSET FILTER WORKS BUT PRICE TRACKING FAILS")
        print("Root cause likely: Integration issue between services")
    else:
        print("\n✅ COMPONENTS WORKING - ISSUE MAY BE ELSEWHERE")

if __name__ == "__main__":
    asyncio.run(main())