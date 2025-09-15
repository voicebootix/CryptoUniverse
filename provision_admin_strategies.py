#!/usr/bin/env python3
"""
Provision Admin User Strategies

Manually provision the 3 free strategies for the admin user
using the same logic as the onboarding system.
"""

import requests
import json

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def provision_strategies():
    """Provision strategies for admin user."""
    
    print("🚀 PROVISIONING ADMIN STRATEGIES")
    print("=" * 60)
    
    # Login
    session = requests.Session()
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    
    response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return False
    
    token = response.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    print("✅ Authenticated successfully")
    
    # The 3 free strategies that should be provisioned
    free_strategies = [
        {
            "strategy_id": "ai_risk_management",
            "name": "AI Risk Management"
        },
        {
            "strategy_id": "ai_portfolio_optimization", 
            "name": "AI Portfolio Optimization"
        },
        {
            "strategy_id": "ai_spot_momentum_strategy",
            "name": "AI Spot Momentum Trading"
        }
    ]
    
    print(f"\n📦 Provisioning {len(free_strategies)} free strategies...")
    
    # Try different approaches to provision strategies
    
    # Approach 1: Try strategy marketplace endpoints
    marketplace_endpoints = [
        "/strategies/purchase",
        "/strategies/activate", 
        "/strategies/subscribe",
        "/marketplace/purchase"
    ]
    
    for endpoint in marketplace_endpoints:
        print(f"\n🔍 Testing endpoint: {endpoint}")
        
        for strategy in free_strategies:
            try:
                payload = {
                    "strategy_id": strategy["strategy_id"],
                    "subscription_type": "permanent",
                    "cost": 0
                }
                
                response = session.post(f"{BASE_URL}{endpoint}", json=payload)
                print(f"   {strategy['name']}: Status {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"      Success: {data.get('success', False)}")
                    if data.get('success'):
                        print(f"      ✅ {strategy['name']} provisioned!")
                elif response.status_code == 405:
                    print(f"      Method not allowed")
                else:
                    print(f"      Error: {response.text[:100]}")
                    
            except Exception as e:
                print(f"   Exception: {e}")
    
    # Approach 2: Try onboarding endpoint if it exists
    print(f"\n🔍 Testing onboarding endpoints...")
    
    onboarding_endpoints = [
        "/user/onboard",
        "/onboarding/complete",
        "/auth/onboard",
        "/strategies/onboard"
    ]
    
    for endpoint in onboarding_endpoints:
        try:
            response = session.post(f"{BASE_URL}{endpoint}", json={})
            print(f"   {endpoint}: Status {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"      Success: {data.get('success', False)}")
                print(f"      Message: {data.get('message', 'No message')}")
                
        except Exception as e:
            print(f"   {endpoint}: Exception {e}")
    
    # Test if strategies are now available
    print(f"\n🔍 Testing opportunity discovery after provisioning attempts...")
    
    payload = {
        "message": "Find me investment opportunities",
        "mode": "analysis"
    }
    
    response = session.post(f"{BASE_URL}/chat/message", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        metadata = data.get("metadata", {})
        opportunities_count = metadata.get("opportunities_count", 0)
        
        print(f"✅ Chat response received")
        print(f"   Opportunities found: {opportunities_count}")
        print(f"   Service used: {metadata.get('service_used', 'Unknown')}")
        
        if opportunities_count > 0:
            print(f"   🎉 SUCCESS! Strategies are now working!")
        else:
            print(f"   ⚠️ Still no opportunities - strategies may not be provisioned")
    
    return True

if __name__ == "__main__":
    provision_strategies()