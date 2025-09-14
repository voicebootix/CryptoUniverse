#!/usr/bin/env python3
"""
Debug the user profile building step specifically
"""

import requests
import json

def debug_user_profile_building():
    """Debug what happens in the user profile building step"""
    
    base_url = "https://cryptouniverse.onrender.com/api/v1"
    
    # Login
    login_data = {
        "email": "admin@cryptouniverse.com", 
        "password": "AdminPass123!"
    }
    
    response = requests.post(f"{base_url}/auth/login", json=login_data, timeout=30)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return
    
    token = response.json().get("access_token")
    user_id = response.json().get("user_id")
    headers = {"Authorization": f"Bearer {token}"}
    
    print("🔍 Debugging user profile building step...")
    print(f"✅ Login successful")
    print(f"🆔 User ID: {user_id}")
    
    # First, confirm the direct strategy call works
    print(f"\n1️⃣ Confirming direct strategy call:")
    portfolio_response = requests.get(f"{base_url}/strategies/my-portfolio", headers=headers, timeout=30)
    if portfolio_response.status_code == 200:
        portfolio_data = portfolio_response.json()
        print(f"   ✅ Direct call: Success={portfolio_data.get('success')}, Strategies={portfolio_data.get('total_strategies', 0)}")
    else:
        print(f"   ❌ Direct call failed: {portfolio_response.status_code}")
        return
    
    # Now test opportunity discovery with detailed logging
    print(f"\n2️⃣ Testing opportunity discovery with force_refresh=True:")
    discover_data = {
        "force_refresh": True,
        "include_strategy_recommendations": True
    }
    
    discover_response = requests.post(f"{base_url}/opportunities/discover", 
                                    headers=headers, 
                                    json=discover_data,
                                    timeout=120)
    
    if discover_response.status_code == 200:
        discover_result = discover_response.json()
        print(f"   Success: {discover_result.get('success')}")
        print(f"   Error: {discover_result.get('error', 'None')}")
        
        # Check user profile details
        user_profile = discover_result.get('user_profile', {})
        print(f"\n   📊 User Profile Details:")
        print(f"      Active strategy count: {user_profile.get('active_strategy_count', 'Not provided')}")
        print(f"      User tier: {user_profile.get('user_tier', 'Not provided')}")
        print(f"      Max asset tier: {user_profile.get('max_asset_tier', 'Not provided')}")
        print(f"      Scan limit: {user_profile.get('opportunity_scan_limit', 'Not provided')}")
        print(f"      Monthly cost: {user_profile.get('total_monthly_strategy_cost', 'Not provided')}")
        
        # Check asset discovery details
        asset_discovery = discover_result.get('asset_discovery', {})
        print(f"\n   🔍 Asset Discovery Details:")
        print(f"      Success: {asset_discovery.get('success', 'Not provided')}")
        print(f"      Error: {asset_discovery.get('error', 'None')}")
        print(f"      Total assets: {asset_discovery.get('total_assets', 'Not provided')}")
        print(f"      Execution time: {asset_discovery.get('execution_time_ms', 'Not provided')}ms")
        
        # Check strategy performance details
        strategy_performance = discover_result.get('strategy_performance', {})
        print(f"\n   ⚙️ Strategy Performance Details:")
        if strategy_performance:
            for strategy_id, perf in strategy_performance.items():
                print(f"      {strategy_id}:")
                print(f"         Opportunities found: {perf.get('opportunities_found', 'Not provided')}")
                print(f"         Success: {perf.get('success', 'Not provided')}")
                print(f"         Error: {perf.get('error', 'None')}")
        else:
            print(f"      No strategy performance data")
        
        # Check if we can see the scan ID and execution details
        print(f"\n   🔬 Execution Details:")
        print(f"      Scan ID: {discover_result.get('scan_id', 'Not provided')}")
        print(f"      Execution time: {discover_result.get('execution_time_ms', 'Not provided')}ms")
        print(f"      Last updated: {discover_result.get('last_updated', 'Not provided')}")
        
    else:
        print(f"   ❌ Opportunity discovery failed: {discover_response.status_code}")
        print(f"   Error: {discover_response.text}")
    
    # Test with force_refresh=False to see if caching affects it
    print(f"\n3️⃣ Testing with force_refresh=False (cached):")
    discover_data_cached = {
        "force_refresh": False,
        "include_strategy_recommendations": True
    }
    
    discover_response_cached = requests.post(f"{base_url}/opportunities/discover", 
                                           headers=headers, 
                                           json=discover_data_cached,
                                           timeout=60)
    
    if discover_response_cached.status_code == 200:
        discover_result_cached = discover_response_cached.json()
        user_profile_cached = discover_result_cached.get('user_profile', {})
        print(f"   Cached - Active strategies: {user_profile_cached.get('active_strategy_count', 'Not provided')}")
        print(f"   Cached - Success: {discover_result_cached.get('success')}")
        print(f"   Cached - Error: {discover_result_cached.get('error', 'None')}")
    else:
        print(f"   ❌ Cached call failed: {discover_response_cached.status_code}")

if __name__ == "__main__":
    debug_user_profile_building()