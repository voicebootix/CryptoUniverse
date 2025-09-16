#!/usr/bin/env python3
"""
Provision Admin Strategies - Using Correct Endpoint Format
"""

import requests
import json

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def provision_admin_strategies():
    """Provision strategies using the correct endpoint format."""
    
    print("🚀 PROVISIONING ADMIN STRATEGIES - CORRECT METHOD")
    print("=" * 70)
    
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
    
    # Check current portfolio
    print("\n📋 Checking current strategy portfolio...")
    response = session.get(f"{BASE_URL}/strategies/my-portfolio")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   Current strategies: {len(data.get('strategies', []))}")
        print(f"   Active strategies: {data.get('active_count', 0)}")
        print(f"   Total cost: ${data.get('total_monthly_cost', 0)}")
    else:
        print(f"   Portfolio check failed: {response.status_code}")
    
    # The 3 free strategies to provision
    free_strategies = [
        "ai_risk_management",
        "ai_portfolio_optimization", 
        "ai_spot_momentum_strategy"
    ]
    
    print(f"\n📦 Provisioning {len(free_strategies)} strategies...")
    
    success_count = 0
    
    for strategy_id in free_strategies:
        print(f"\n🎯 Provisioning: {strategy_id}")
        
        # Use the correct endpoint format found in the code
        # POST /strategies/purchase with query parameter
        try:
            # Method 1: Query parameter
            url = f"{BASE_URL}/strategies/purchase?strategy_id={strategy_id}&subscription_type=permanent"
            response = session.post(url)
            
            print(f"   Method 1 (query): Status {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print(f"   ✅ SUCCESS: {strategy_id} provisioned!")
                    success_count += 1
                    continue
                else:
                    print(f"   Error: {data.get('error', 'Unknown error')}")
            
            # Method 2: Try with JSON body
            payload = {
                "strategy_id": strategy_id,
                "subscription_type": "permanent"
            }
            
            response = session.post(f"{BASE_URL}/strategies/purchase", json=payload)
            print(f"   Method 2 (JSON): Status {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print(f"   ✅ SUCCESS: {strategy_id} provisioned!")
                    success_count += 1
                else:
                    print(f"   Error: {data.get('error', 'Unknown error')}")
            else:
                print(f"   Error: {response.text[:100]}")
                
        except Exception as e:
            print(f"   Exception: {e}")
    
    print(f"\n📊 PROVISIONING RESULTS:")
    print(f"   Strategies provisioned: {success_count}/{len(free_strategies)}")
    
    # Check portfolio again
    print(f"\n📋 Checking updated strategy portfolio...")
    response = session.get(f"{BASE_URL}/strategies/my-portfolio")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   Updated strategies: {len(data.get('strategies', []))}")
        print(f"   Active strategies: {data.get('active_count', 0)}")
        
        if data.get('strategies'):
            print(f"   Strategy list:")
            for strategy in data.get('strategies', []):
                print(f"      - {strategy.get('name', 'Unknown')}")
    
    # Test opportunity discovery again
    print(f"\n🔍 Testing opportunity discovery after provisioning...")
    
    payload = {
        "message": "Find me the best investment opportunities right now",
        "mode": "analysis"
    }
    
    response = session.post(f"{BASE_URL}/chat/message", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        metadata = data.get("metadata", {})
        opportunities_count = metadata.get("opportunities_count", 0)
        
        print(f"✅ Opportunity test completed")
        print(f"   Opportunities found: {opportunities_count}")
        print(f"   Service used: {metadata.get('service_used', 'Unknown')}")
        
        if opportunities_count > 0:
            print(f"   🎉 SUCCESS! Strategies are now working!")
        else:
            print(f"   ⚠️ Still no opportunities - may need different approach")
    
    return success_count > 0

if __name__ == "__main__":
    provision_admin_strategies()