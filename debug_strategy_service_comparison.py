#!/usr/bin/env python3
"""
Compare the strategy service responses between direct API and opportunity discovery
"""

import requests
import json
import time

def debug_strategy_service_comparison():
    """Compare strategy service responses"""
    
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
    
    print("🔍 Comparing strategy service responses...")
    print(f"✅ Login successful")
    print(f"🆔 User ID: {user_id}")
    
    # Test 1: Direct strategy portfolio call
    print(f"\n1️⃣ Direct call to /strategies/my-portfolio:")
    try:
        start_time = time.time()
        portfolio_response = requests.get(f"{base_url}/strategies/my-portfolio", headers=headers, timeout=30)
        response_time = time.time() - start_time
        
        print(f"   Status: {portfolio_response.status_code}")
        print(f"   Response time: {response_time:.3f}s")
        
        if portfolio_response.status_code == 200:
            portfolio_data = portfolio_response.json()
            print(f"   Success: {portfolio_data.get('success')}")
            print(f"   Total strategies: {portfolio_data.get('total_strategies', 0)}")
            print(f"   Monthly cost: ${portfolio_data.get('total_monthly_cost', 0)}")
            print(f"   Active strategies: {len(portfolio_data.get('active_strategies', []))}")
            
            if 'error' in portfolio_data:
                print(f"   Error: {portfolio_data['error']}")
        else:
            print(f"   Error: {portfolio_response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Small delay
    time.sleep(1)
    
    # Test 2: Opportunity discovery call (which internally calls the same service)
    print(f"\n2️⃣ Call via /opportunities/discover (which calls same service internally):")
    try:
        start_time = time.time()
        discover_data = {
            "force_refresh": True,
            "include_strategy_recommendations": True
        }
        
        discover_response = requests.post(f"{base_url}/opportunities/discover", 
                                        headers=headers, 
                                        json=discover_data,
                                        timeout=120)
        response_time = time.time() - start_time
        
        print(f"   Status: {discover_response.status_code}")
        print(f"   Response time: {response_time:.3f}s")
        
        if discover_response.status_code == 200:
            discover_result = discover_response.json()
            print(f"   Success: {discover_result.get('success')}")
            print(f"   Total opportunities: {discover_result.get('total_opportunities', 0)}")
            
            # Check user profile (which is built from strategy service)
            user_profile = discover_result.get('user_profile', {})
            print(f"   User profile active strategies: {user_profile.get('active_strategy_count', 0)}")
            print(f"   User tier: {user_profile.get('user_tier', 'Unknown')}")
            
            # Check if there's an error
            if 'error' in discover_result:
                print(f"   Error: {discover_result['error']}")
            
            # Check asset discovery status
            asset_discovery = discover_result.get('asset_discovery', {})
            print(f"   Asset discovery success: {asset_discovery.get('success', False)}")
            if 'error' in asset_discovery:
                print(f"   Asset discovery error: {asset_discovery['error']}")
        else:
            print(f"   Error: {discover_response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Test 3: Call them back-to-back rapidly to check for timing issues
    print(f"\n3️⃣ Rapid back-to-back calls to check for timing issues:")
    
    for i in range(3):
        print(f"   Round {i+1}:")
        
        # Direct call
        try:
            portfolio_response = requests.get(f"{base_url}/strategies/my-portfolio", headers=headers, timeout=10)
            if portfolio_response.status_code == 200:
                portfolio_data = portfolio_response.json()
                direct_strategies = portfolio_data.get('total_strategies', 0)
                direct_success = portfolio_data.get('success')
                print(f"      Direct: {direct_success}, {direct_strategies} strategies")
            else:
                print(f"      Direct: HTTP {portfolio_response.status_code}")
        except Exception as e:
            print(f"      Direct: Exception {e}")
        
        # Small delay
        time.sleep(0.5)
        
        # Opportunity discovery call
        try:
            discover_data = {"force_refresh": False, "include_strategy_recommendations": False}
            discover_response = requests.post(f"{base_url}/opportunities/discover", 
                                            headers=headers, 
                                            json=discover_data,
                                            timeout=30)
            if discover_response.status_code == 200:
                discover_result = discover_response.json()
                user_profile = discover_result.get('user_profile', {})
                discover_strategies = user_profile.get('active_strategy_count', 0)
                discover_success = discover_result.get('success')
                print(f"      Discover: {discover_success}, {discover_strategies} strategies")
            else:
                print(f"      Discover: HTTP {discover_response.status_code}")
        except Exception as e:
            print(f"      Discover: Exception {e}")
        
        time.sleep(1)
    
    print(f"\n📊 ANALYSIS:")
    print(f"If direct calls show 3 strategies but discover calls show 0,")
    print(f"then there's an issue in the opportunity discovery service's")
    print(f"call to the strategy marketplace service.")

if __name__ == "__main__":
    debug_strategy_service_comparison()