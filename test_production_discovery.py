#!/usr/bin/env python3
"""
Test Production Discovery

Test if the production system is using our fixed discovery
"""

import asyncio
import sys
import os

# Set environment to match production
os.environ['SECRET_KEY'] = 'production-test-key'
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost/test'
os.environ['ENVIRONMENT'] = 'production'

sys.path.append('/workspace')

async def test_production_discovery():
    """Test if production system uses our fixes."""
    
    print("🔍 TESTING PRODUCTION DISCOVERY SYSTEM")
    print("=" * 60)
    
    try:
        # Test enterprise asset filter directly
        from app.services.dynamic_asset_filter import enterprise_asset_filter
        
        print("✅ Enterprise asset filter imported")
        
        # Force a fresh discovery
        print("\n📊 Testing fresh asset discovery...")
        
        discovered_assets = await enterprise_asset_filter.discover_all_assets_with_volume_filtering(
            min_tier="tier_retail",
            force_refresh=True
        )
        
        total_assets = sum(len(assets) for assets in discovered_assets.values())
        print(f"   Total assets discovered: {total_assets}")
        
        if total_assets > 0:
            print(f"   🎉 Enterprise discovery working!")
            
            # Show breakdown
            for tier, assets in discovered_assets.items():
                if assets:
                    print(f"   {tier}: {len(assets)} assets")
                    for asset in assets[:2]:
                        print(f"      {asset.symbol} ({asset.exchange}): ${asset.volume_24h_usd:,.0f}")
        else:
            print(f"   ❌ Still no assets discovered")
        
        return total_assets > 0
        
    except Exception as e:
        print(f"❌ Production discovery test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_chat_integration():
    """Test if chat system uses the fixed discovery."""
    
    print(f"\n🔍 TESTING CHAT INTEGRATION")
    print("=" * 60)
    
    try:
        from app.services.chat_service_adapters_fixed import ChatServiceAdaptersFixed
        
        adapter = ChatServiceAdaptersFixed()
        print("✅ Chat adapter imported")
        
        # Test market overview with our SMART_ADAPTIVE fix
        print("\n📊 Testing market overview with SMART_ADAPTIVE...")
        
        market_overview = await adapter.get_market_overview()
        
        print(f"   Success: {market_overview.get('success', 'No success field')}")
        print(f"   Sentiment: {market_overview.get('sentiment', 'Unknown')}")
        print(f"   Available symbols: {len(market_overview.get('available_symbols', []))}")
        print(f"   Market cap: ${market_overview.get('total_market_cap', 0):,}")
        print(f"   Error: {market_overview.get('error', 'None')}")
        
        if len(market_overview.get('available_symbols', [])) > 0:
            print(f"   🎉 Real market data detected!")
            return True
        else:
            print(f"   ⚠️ Still no real data")
            return False
            
    except Exception as e:
        print(f"❌ Chat integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("🔍 PRODUCTION SYSTEM VERIFICATION")
    print("=" * 80)
    
    discovery_ok = await test_production_discovery()
    chat_ok = await test_chat_integration()
    
    print(f"\n📊 VERIFICATION RESULTS:")
    print("=" * 60)
    print(f"Enterprise Discovery: {'✅' if discovery_ok else '❌'}")
    print(f"Chat Integration: {'✅' if chat_ok else '❌'}")
    
    if discovery_ok and chat_ok:
        print(f"\n🎉 PRODUCTION SYSTEM FULLY FIXED!")
    elif discovery_ok:
        print(f"\n⚠️ DISCOVERY WORKING, CHAT INTEGRATION ISSUE")
    else:
        print(f"\n❌ DISCOVERY SYSTEM STILL HAS ISSUES")

if __name__ == "__main__":
    asyncio.run(main())