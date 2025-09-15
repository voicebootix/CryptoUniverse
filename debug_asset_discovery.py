#!/usr/bin/env python3
"""
Debug the asset discovery service directly to see what it returns
"""

import requests
import json

def debug_asset_discovery():
    """Debug the asset discovery service to see what's failing"""
    
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
    
    print("🔍 Debugging asset discovery service...")
    print(f"✅ Login successful")
    print(f"🆔 User ID: {user_id}")
    
    # First, let's see what user tier the user profile would have
    print(f"\n1️⃣ Checking what user tier would be assigned:")
    portfolio_response = requests.get(f"{base_url}/strategies/my-portfolio", headers=headers, timeout=30)
    if portfolio_response.status_code == 200:
        portfolio_data = portfolio_response.json()
        strategy_count = portfolio_data.get('total_strategies', 0)
        monthly_cost = portfolio_data.get('total_monthly_cost', 0)
        
        print(f"   Strategy count: {strategy_count}")
        print(f"   Monthly cost: ${monthly_cost}")
        
        # Determine user tier based on the logic from _build_user_opportunity_profile
        if strategy_count >= 10 and monthly_cost >= 300:
            user_tier = "enterprise"
        elif strategy_count >= 5 and monthly_cost >= 100:
            user_tier = "pro"
        else:
            user_tier = "basic"
        
        print(f"   Calculated user tier: {user_tier}")
        
        # Determine max_asset_tier based on tier_configs (from the code)
        tier_configs = {
            "basic": {"max_asset_tier": "tier_retail", "scan_limit": 10},
            "pro": {"max_asset_tier": "tier_professional", "scan_limit": 50},
            "enterprise": {"max_asset_tier": "tier_institutional", "scan_limit": 200}
        }
        
        max_asset_tier = tier_configs[user_tier]["max_asset_tier"]
        print(f"   Max asset tier: {max_asset_tier}")
    else:
        print(f"   ❌ Portfolio check failed: {portfolio_response.status_code}")
        return
    
    # Check if there are any asset discovery endpoints we can test directly
    print(f"\n2️⃣ Testing potential asset discovery endpoints:")
    
    # Try various possible asset discovery endpoints
    asset_endpoints = [
        "/market/assets",
        "/market/discover-assets", 
        "/trading/assets",
        "/exchanges/assets",
        "/opportunities/assets",
        "/admin/assets"
    ]
    
    for endpoint in asset_endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=10)
            print(f"   {endpoint}: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    print(f"      Keys: {list(data.keys())}")
                    if 'assets' in data:
                        assets = data['assets']
                        print(f"      Assets count: {len(assets) if isinstance(assets, list) else 'Not a list'}")
                elif isinstance(data, list):
                    print(f"      List length: {len(data)}")
            elif response.status_code != 404 and response.status_code != 405:
                print(f"      Error: {response.text[:100]}")
        except Exception as e:
            print(f"   {endpoint}: Exception - {e}")
    
    # Test market data endpoints that might be used by asset discovery
    print(f"\n3️⃣ Testing market data endpoints that asset discovery might use:")
    
    market_endpoints = [
        "/market/overview",
        "/market/prices", 
        "/market/tickers",
        "/exchanges/binance/assets",
        "/exchanges/kraken/assets",
        "/exchanges/kucoin/assets"
    ]
    
    for endpoint in market_endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=10)
            print(f"   {endpoint}: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    success = data.get('success', 'No success field')
                    print(f"      Success: {success}")
                    if 'data' in data:
                        data_content = data['data']
                        if isinstance(data_content, dict):
                            print(f"      Data keys: {list(data_content.keys())}")
                        elif isinstance(data_content, list):
                            print(f"      Data count: {len(data_content)}")
                    if 'error' in data:
                        print(f"      Error: {data['error']}")
        except Exception as e:
            print(f"   {endpoint}: Exception - {e}")
    
    # Test if we can call the opportunity discovery with debug info
    print(f"\n4️⃣ Testing opportunity discovery with minimal request to see detailed error:")
    
    try:
        # Try with minimal parameters to see if we get more detailed error info
        discover_data = {
            "force_refresh": True,
            "include_strategy_recommendations": False
        }
        
        discover_response = requests.post(f"{base_url}/opportunities/discover", 
                                        headers=headers, 
                                        json=discover_data,
                                        timeout=30)
        
        print(f"   Status: {discover_response.status_code}")
        
        if discover_response.status_code == 200:
            discover_result = discover_response.json()
            print(f"   Success: {discover_result.get('success')}")
            print(f"   Error: {discover_result.get('error')}")
            print(f"   Scan ID: {discover_result.get('scan_id')}")
            print(f"   Execution time: {discover_result.get('execution_time_ms', 0)}ms")
            
            # Check if there's any additional error information
            if 'error_type' in discover_result:
                print(f"   Error type: {discover_result['error_type']}")
            
            if 'fallback_used' in discover_result:
                print(f"   Fallback used: {discover_result['fallback_used']}")
                
        else:
            print(f"   HTTP Error: {discover_response.text}")
            
    except Exception as e:
        print(f"   Exception: {e}")
    
    print(f"\n📊 ANALYSIS:")
    print(f"Based on the results above, we can determine:")
    print(f"1. What user tier is calculated: {user_tier}")
    print(f"2. What max_asset_tier is used: {max_asset_tier}")
    print(f"3. Whether any asset discovery endpoints exist")
    print(f"4. Whether market data endpoints are working")
    print(f"5. What specific error the asset discovery is encountering")

if __name__ == "__main__":
    debug_asset_discovery()