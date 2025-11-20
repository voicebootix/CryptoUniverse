#!/usr/bin/env python3
"""
Test admin user recognition and portfolio access
"""

import requests
import json

def test_admin_user_debug():
    """Test admin user recognition and portfolio access"""
    
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
        return
    
    token = response.json().get("access_token")
    user_id = response.json().get("user_id")
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"✅ Login successful")
    print(f"🆔 User ID: {user_id}")
    print(f"🔑 Token: {token[:20]}...")
    
    # Test different portfolio endpoints
    print("\n📊 Testing different portfolio endpoints...")
    
    endpoints = [
        {"path": "/strategies/my-portfolio", "name": "My Portfolio"},
        {"path": "/strategies/marketplace", "name": "Marketplace"},
        {"path": "/strategies/available", "name": "Available Strategies"},
    ]
    
    for endpoint in endpoints:
        print(f"\n🔍 Testing: {endpoint['name']}")
        try:
            response = requests.get(f"{base_url}{endpoint['path']}", headers=headers, timeout=30)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Success: {data.get('success')}")
                
                if 'active_strategies' in data:
                    strategies = data.get('active_strategies', [])
                    print(f"   Active strategies: {len(strategies)}")
                    if strategies:
                        print(f"   Strategy names: {[s.get('name') for s in strategies[:3]]}")
                
                if 'strategies' in data:
                    strategies = data.get('strategies', [])
                    print(f"   Total strategies: {len(strategies)}")
                    if strategies:
                        print(f"   Strategy names: {[s.get('name') for s in strategies[:3]]}")
            else:
                print(f"   Error: {response.text[:100]}")
        except Exception as e:
            print(f"   Exception: {e}")
    
    # Test opportunity discovery with different parameters
    print("\n🔍 Testing opportunity discovery with different parameters...")
    
    test_params = [
        {"force_refresh": True, "include_strategy_recommendations": True},
        {"force_refresh": False, "include_strategy_recommendations": False},
        {"max_opportunities": 5},
        {"debug": True},
    ]
    
    for i, params in enumerate(test_params, 1):
        print(f"\n   Test {i}: {params}")
        try:
            response = requests.post(f"{base_url}/opportunities/discover", 
                                   headers=headers, 
                                   json=params,
                                   timeout=60)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Success: {data.get('success')}")
                print(f"   Total opportunities: {data.get('total_opportunities', 0)}")
                print(f"   Active strategies: {data.get('user_profile', {}).get('active_strategies', 0)}")
                print(f"   Assets scanned: {data.get('asset_discovery', {}).get('total_assets_scanned', 0)}")
            else:
                print(f"   Error: {response.text[:100]}")
        except Exception as e:
            print(f"   Exception: {e}")

if __name__ == "__main__":
    test_admin_user_debug()