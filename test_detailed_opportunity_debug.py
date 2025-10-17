#!/usr/bin/env python3
"""
Detailed test to debug opportunity discovery issues
"""

import requests
import json
import time

def test_detailed_opportunity_debug():
    """Test opportunity discovery with detailed debugging"""
    
    base_url = "https://cryptouniverse.onrender.com/api/v1"
    
    # Login
    print("🔐 Logging in...")
    login_data = {
        "email": "admin@cryptouniverse.com", 
        "password": "AdminPass123!"
    }
    
    response = requests.post(f"{base_url}/auth/login", json=login_data, timeout=30)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        print(f"Response: {response.text}")
        return
    
    token = response.json().get("access_token")
    user_id = response.json().get("user_id")
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"✅ Login successful - User ID: {user_id}")
    
    # Test user profile first
    print("\n👤 Testing user profile...")
    try:
        profile_response = requests.get(f"{base_url}/user/profile", headers=headers, timeout=30)
        print(f"Profile status: {profile_response.status_code}")
        if profile_response.status_code == 200:
            profile_data = profile_response.json()
            print(f"Profile data: {json.dumps(profile_data, indent=2)}")
        else:
            print(f"Profile error: {profile_response.text}")
    except Exception as e:
        print(f"Profile exception: {e}")
    
    # Test strategies access
    print("\n🎯 Testing strategies access...")
    try:
        strategies_response = requests.get(f"{base_url}/strategies/user-access", headers=headers, timeout=30)
        print(f"Strategies status: {strategies_response.status_code}")
        if strategies_response.status_code == 200:
            strategies_data = strategies_response.json()
            print(f"Strategies count: {len(strategies_data.get('strategies', []))}")
            print(f"Strategies: {[s.get('name') for s in strategies_data.get('strategies', [])[:5]]}")
        else:
            print(f"Strategies error: {strategies_response.text}")
    except Exception as e:
        print(f"Strategies exception: {e}")
    
    # Test opportunity discovery with detailed response
    print("\n🔍 Testing opportunity discovery with detailed debugging...")
    try:
        discover_data = {
            "force_refresh": True,
            "include_strategy_recommendations": True,
            "max_opportunities": 5,
            "debug": True
        }
        
        print("Sending request...")
        start_time = time.time()
        discover_response = requests.post(f"{base_url}/opportunities/discover", 
                                        headers=headers, 
                                        json=discover_data,
                                        timeout=180)
        end_time = time.time()
        
        print(f"Response time: {end_time - start_time:.2f}s")
        print(f"Status: {discover_response.status_code}")
        
        if discover_response.status_code == 200:
            discover_result = discover_response.json()
            print(f"\n📊 DISCOVERY RESULT:")
            print(f"Success: {discover_result.get('success')}")
            print(f"Total opportunities: {discover_result.get('total_opportunities', 0)}")
            print(f"Execution time: {discover_result.get('execution_time_ms', 0):.2f}ms")
            
            # Check user profile in response
            user_profile = discover_result.get('user_profile', {})
            print(f"\n👤 USER PROFILE:")
            print(f"Active strategies: {user_profile.get('active_strategies', 0)}")
            print(f"User tier: {user_profile.get('user_tier', 'Unknown')}")
            print(f"Monthly cost: ${user_profile.get('monthly_strategy_cost', 0)}")
            
            # Check asset discovery
            asset_discovery = discover_result.get('asset_discovery', {})
            print(f"\n🎯 ASSET DISCOVERY:")
            print(f"Total assets scanned: {asset_discovery.get('total_assets_scanned', 0)}")
            print(f"Asset tiers: {asset_discovery.get('asset_tiers', [])}")
            print(f"Max tier accessed: {asset_discovery.get('max_tier_accessed', 'Unknown')}")
            
            # Check opportunities
            opportunities = discover_result.get('opportunities', [])
            print(f"\n💎 OPPORTUNITIES:")
            print(f"Found: {len(opportunities)}")
            for i, opp in enumerate(opportunities[:3]):
                print(f"  {i+1}. {opp.get('symbol')} - {opp.get('strategy_name')}")
                print(f"     Profit: ${opp.get('profit_potential_usd', 0):.2f}")
                print(f"     Confidence: {opp.get('confidence_score', 0):.1f}%")
            
            # Check for errors
            if discover_result.get('error'):
                print(f"\n❌ ERROR: {discover_result['error']}")
            
            # Check debug info
            debug_info = discover_result.get('debug_info', {})
            if debug_info:
                print(f"\n🐛 DEBUG INFO:")
                for key, value in debug_info.items():
                    print(f"  {key}: {value}")
                    
        else:
            print(f"❌ Error: {discover_response.status_code}")
            print(f"Response: {discover_response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_detailed_opportunity_debug()