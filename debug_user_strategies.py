#!/usr/bin/env python3
"""
Debug user strategies to see what's actually happening with the 3 free strategies
"""

import requests
import json

def debug_user_strategies():
    """Debug the user's strategy portfolio and onboarding status"""
    
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
    headers = {"Authorization": f"Bearer {token}"}
    
    print("🔍 Debugging user strategies and onboarding...")
    
    # Check user profile
    print("\n1️⃣ Checking user profile:")
    profile_response = requests.get(f"{base_url}/auth/me", headers=headers, timeout=30)
    if profile_response.status_code == 200:
        profile_data = profile_response.json()
        user_id = profile_data.get('id')
        print(f"   ✅ User ID: {user_id}")
        print(f"   📧 Email: {profile_data.get('email')}")
        print(f"   👤 Role: {profile_data.get('role')}")
    else:
        print(f"   ❌ Profile check failed: {profile_response.status_code}")
        return
    
    # Check strategy marketplace/portfolio
    print("\n2️⃣ Checking strategy portfolio:")
    try:
        portfolio_response = requests.get(f"{base_url}/strategies/portfolio", headers=headers, timeout=30)
        print(f"   📡 Portfolio endpoint status: {portfolio_response.status_code}")
        
        if portfolio_response.status_code == 200:
            portfolio_data = portfolio_response.json()
            print(f"   ✅ Portfolio response: {portfolio_data.get('success')}")
            
            active_strategies = portfolio_data.get('active_strategies', [])
            print(f"   📊 Active strategies count: {len(active_strategies)}")
            
            if active_strategies:
                print(f"   📋 Active strategies:")
                for i, strategy in enumerate(active_strategies):
                    print(f"      {i+1}. {strategy.get('name', 'Unknown')} - {strategy.get('status', 'Unknown')}")
            else:
                print(f"   ❌ No active strategies found")
        else:
            print(f"   ❌ Portfolio check failed: {portfolio_response.text}")
    except Exception as e:
        print(f"   💥 Portfolio check exception: {e}")
    
    # Check onboarding status
    print("\n3️⃣ Checking onboarding status:")
    try:
        onboarding_response = requests.get(f"{base_url}/auth/onboarding-status", headers=headers, timeout=30)
        print(f"   📡 Onboarding endpoint status: {onboarding_response.status_code}")
        
        if onboarding_response.status_code == 200:
            onboarding_data = onboarding_response.json()
            print(f"   ✅ Onboarding response: {onboarding_data}")
        else:
            print(f"   ❌ Onboarding check failed: {onboarding_response.text}")
    except Exception as e:
        print(f"   💥 Onboarding check exception: {e}")
    
    # Check available strategies in marketplace
    print("\n4️⃣ Checking marketplace strategies:")
    try:
        marketplace_response = requests.get(f"{base_url}/strategies/marketplace", headers=headers, timeout=30)
        print(f"   📡 Marketplace endpoint status: {marketplace_response.status_code}")
        
        if marketplace_response.status_code == 200:
            marketplace_data = marketplace_response.json()
            print(f"   ✅ Marketplace response: {marketplace_data.get('success')}")
            
            strategies = marketplace_data.get('strategies', [])
            print(f"   📊 Available strategies count: {len(strategies)}")
            
            free_strategies = [s for s in strategies if s.get('price', 0) == 0 or s.get('is_free', False)]
            print(f"   🆓 Free strategies count: {len(free_strategies)}")
            
            if free_strategies:
                print(f"   📋 Free strategies:")
                for i, strategy in enumerate(free_strategies[:5]):
                    print(f"      {i+1}. {strategy.get('name', 'Unknown')} - ${strategy.get('price', 0)}")
        else:
            print(f"   ❌ Marketplace check failed: {marketplace_response.text}")
    except Exception as e:
        print(f"   💥 Marketplace check exception: {e}")
    
    # Try to trigger onboarding manually
    print("\n5️⃣ Trying to trigger onboarding:")
    try:
        onboard_response = requests.post(f"{base_url}/auth/onboard", headers=headers, timeout=30)
        print(f"   📡 Onboard trigger status: {onboard_response.status_code}")
        
        if onboard_response.status_code == 200:
            onboard_data = onboard_response.json()
            print(f"   ✅ Onboard response: {onboard_data}")
        else:
            print(f"   ❌ Onboard trigger failed: {onboard_response.text}")
    except Exception as e:
        print(f"   💥 Onboard trigger exception: {e}")

if __name__ == "__main__":
    debug_user_strategies()