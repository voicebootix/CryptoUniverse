#!/usr/bin/env python3
"""
Debug Redis to see what's actually in the user_strategies key
"""

import requests
import json

def debug_redis_strategies():
    """Debug what's actually in Redis for user strategies"""
    
    base_url = "https://cryptouniverse.onrender.com/api/v1"
    
    # Login to get user ID
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
    
    print("🔍 Debugging Redis strategies and user data...")
    
    # Try to get user info from different endpoints
    print("\n1️⃣ Checking user info from login response:")
    user_data = response.json()
    print(f"   Login response keys: {list(user_data.keys())}")
    
    if 'user' in user_data:
        user_info = user_data['user']
        user_id = user_info.get('id')
        print(f"   User ID: {user_id}")
        print(f"   Email: {user_info.get('email')}")
        print(f"   Created: {user_info.get('created_at')}")
        print(f"   Role: {user_info.get('role')}")
    else:
        print(f"   No 'user' key in login response")
        user_id = None
    
    # Try to call strategy portfolio endpoint directly
    print(f"\n2️⃣ Testing strategy portfolio endpoint directly:")
    try:
        portfolio_response = requests.get(f"{base_url}/strategies/portfolio", headers=headers, timeout=30)
        print(f"   Status: {portfolio_response.status_code}")
        
        if portfolio_response.status_code == 200:
            portfolio_data = portfolio_response.json()
            print(f"   Success: {portfolio_data.get('success')}")
            print(f"   Active strategies: {portfolio_data.get('total_strategies', 0)}")
            print(f"   Strategies: {portfolio_data.get('active_strategies', [])}")
        else:
            print(f"   Error: {portfolio_response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Try to call onboarding status endpoint
    print(f"\n3️⃣ Testing onboarding status:")
    try:
        onboarding_response = requests.get(f"{base_url}/auth/onboarding-status", headers=headers, timeout=30)
        print(f"   Status: {onboarding_response.status_code}")
        
        if onboarding_response.status_code == 200:
            onboarding_data = onboarding_response.json()
            print(f"   Onboarded: {onboarding_data.get('onboarded')}")
            print(f"   Needs onboarding: {onboarding_data.get('needs_onboarding')}")
            print(f"   Has credit account: {onboarding_data.get('has_credit_account')}")
            print(f"   Active strategies: {onboarding_data.get('active_strategies')}")
        else:
            print(f"   Error: {onboarding_response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Try to trigger onboarding manually
    print(f"\n4️⃣ Testing manual onboarding trigger:")
    try:
        onboard_response = requests.post(f"{base_url}/auth/onboard", headers=headers, timeout=60)
        print(f"   Status: {onboard_response.status_code}")
        
        if onboard_response.status_code == 200:
            onboard_data = onboard_response.json()
            print(f"   Success: {onboard_data.get('success')}")
            print(f"   Message: {onboard_data.get('message', '')}")
            
            if 'provisioned_strategies' in onboard_data:
                strategies = onboard_data['provisioned_strategies']
                print(f"   Provisioned {len(strategies)} strategies:")
                for strategy in strategies:
                    print(f"      - {strategy.get('name')} ({strategy.get('strategy_id')})")
        else:
            print(f"   Error: {onboard_response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Test opportunity discovery again after potential onboarding
    print(f"\n5️⃣ Testing opportunity discovery after onboarding:")
    message_data = {
        "message": "Find me trading opportunities",
        "mode": "trading"
    }
    
    chat_response = requests.post(f"{base_url}/chat/message", 
                                 json=message_data, 
                                 headers=headers, 
                                 timeout=120)
    
    if chat_response.status_code == 200:
        chat_data = chat_response.json()
        metadata = chat_data.get('metadata', {})
        opportunities = metadata.get('opportunities', [])
        
        print(f"   Opportunities found: {len(opportunities)}")
        
        if opportunities:
            print(f"   ✅ SUCCESS! Found opportunities after onboarding")
            for i, opp in enumerate(opportunities[:3]):
                print(f"      {i+1}. {opp.get('symbol', 'Unknown')}: {opp.get('confidence', 0)}% confidence")
        else:
            print(f"   ❌ Still no opportunities found")
    else:
        print(f"   Chat error: {chat_response.status_code}")

if __name__ == "__main__":
    debug_redis_strategies()