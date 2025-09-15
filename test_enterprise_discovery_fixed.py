#!/usr/bin/env python3
"""
Test Enterprise Discovery System - After Fixes

Test the fixed enterprise asset discovery system to ensure it works properly
without hardcoded limitations.
"""

import asyncio
import sys
import os

# Set environment variables
os.environ['SECRET_KEY'] = 'test-key'
os.environ['DATABASE_URL'] = 'sqlite:///test.db' 
os.environ['ENVIRONMENT'] = 'development'

sys.path.append('/workspace')

async def test_fixed_enterprise_discovery():
    """Test the fixed enterprise discovery system."""
    
    print("🚀 TESTING FIXED ENTERPRISE DISCOVERY SYSTEM")
    print("=" * 80)
    
    try:
        from app.services.dynamic_asset_filter import enterprise_asset_filter
        
        print("✅ Enterprise asset filter imported")
        
        # Test the fixed discovery system
        print("\n🔍 Testing discover_all_assets_with_volume_filtering...")
        
        discovered_assets = await enterprise_asset_filter.discover_all_assets_with_volume_filtering(
            min_tier="tier_retail",  # $1M+ daily volume
            force_refresh=True
        )
        
        print(f"\n📊 DISCOVERY RESULTS:")
        print(f"   Total tiers: {len(discovered_assets)}")
        
        total_assets = 0
        for tier_name, assets in discovered_assets.items():
            asset_count = len(assets)
            total_assets += asset_count
            print(f"   {tier_name}: {asset_count} assets")
            
            # Show sample assets from each tier
            if assets:
                print(f"      Sample assets:")
                for asset in assets[:3]:
                    print(f"         {asset.symbol} ({asset.exchange}): ${asset.price_usd:.4f}, Vol: ${asset.volume_24h_usd:,.0f}")
        
        print(f"\n✅ TOTAL ASSETS DISCOVERED: {total_assets}")
        
        if total_assets > 0:
            print(f"🎉 SUCCESS! Enterprise discovery is working!")
            
            # Test get_top_assets
            print(f"\n🔍 Testing get_top_assets...")
            top_assets = await enterprise_asset_filter.get_top_assets(
                count=20,
                min_tier="tier_retail"
            )
            
            print(f"   Top 20 assets by volume:")
            for i, asset in enumerate(top_assets[:10], 1):
                print(f"      {i:2d}. {asset.symbol} ({asset.exchange}): ${asset.volume_24h_usd:,.0f}")
            
            return True
        else:
            print(f"❌ No assets discovered - system still not working")
            return False
            
    except Exception as e:
        print(f"❌ Enterprise discovery test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_chat_with_fixed_discovery():
    """Test chat system with fixed discovery."""
    
    print(f"\n🔍 TESTING CHAT WITH FIXED DISCOVERY")
    print("=" * 60)
    
    import requests
    
    # Configuration
    BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
    ADMIN_EMAIL = "admin@cryptouniverse.com"
    ADMIN_PASSWORD = "AdminPass123!"
    
    # Login
    session = requests.Session()
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    
    response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code != 200:
        print(f"❌ Login failed")
        return False
    
    token = response.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    print("✅ Authenticated successfully")
    
    # Test opportunity discovery after fixes
    print(f"\n🔍 Testing opportunity discovery with fixed system...")
    
    payload = {
        "message": "Find me the best investment opportunities using enterprise asset discovery",
        "mode": "analysis"
    }
    
    import time
    start_time = time.time()
    response = session.post(f"{BASE_URL}/chat/message", json=payload)
    response_time = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        metadata = data.get("metadata", {})
        
        print(f"✅ Chat Response:")
        print(f"   Intent: {data.get('intent')}")
        print(f"   Confidence: {data.get('confidence')}")
        print(f"   Response time: {response_time:.2f}s")
        print(f"   Opportunities found: {metadata.get('opportunities_count', 0)}")
        print(f"   Service used: {metadata.get('service_used', 'Unknown')}")
        
        # Check if we now have real opportunities
        if metadata.get('opportunities_count', 0) > 0:
            print(f"   🎉 SUCCESS! Opportunities discovered!")
            
            opportunities = metadata.get('opportunities', [])
            for i, opp in enumerate(opportunities[:3], 1):
                print(f"      {i}. {opp.get('symbol', 'Unknown')}: {opp.get('confidence', 0):.1f}% confidence")
            
            return True
        else:
            print(f"   ⚠️ Still no opportunities - checking why...")
            
            # Check AI analysis for clues
            ai_analysis = metadata.get('ai_analysis', {})
            if ai_analysis:
                opportunity_analysis = ai_analysis.get('opportunity_analysis', {})
                reasoning = opportunity_analysis.get('reasoning', '')
                print(f"   AI Reasoning: {reasoning[:200]}...")
            
            return False
    else:
        print(f"❌ Chat request failed: {response.status_code}")
        return False

async def main():
    print("🔍 ENTERPRISE DISCOVERY SYSTEM TEST")
    print("=" * 80)
    
    # Test the fixed discovery system
    discovery_ok = await test_fixed_enterprise_discovery()
    
    # Test chat integration
    chat_ok = await test_chat_with_fixed_discovery()
    
    print(f"\n📊 FINAL RESULTS:")
    print("=" * 60)
    print(f"Enterprise Discovery: {'✅' if discovery_ok else '❌'}")
    print(f"Chat Integration: {'✅' if chat_ok else '❌'}")
    
    if discovery_ok and chat_ok:
        print(f"\n🎉 ENTERPRISE SYSTEM FULLY OPERATIONAL!")
        print(f"   ✅ Dynamic asset discovery working")
        print(f"   ✅ Multi-exchange scanning operational")
        print(f"   ✅ Volume-based tier classification active")
        print(f"   ✅ Chat integration functional")
    elif discovery_ok:
        print(f"\n⚠️ DISCOVERY WORKING BUT CHAT INTEGRATION NEEDS WORK")
    else:
        print(f"\n❌ DISCOVERY SYSTEM STILL NEEDS FIXES")

if __name__ == "__main__":
    asyncio.run(main())