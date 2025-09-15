#!/usr/bin/env python3
"""
Onboard Admin User via Direct API Call

Since the admin user was created before the onboarding system,
manually provision the 3 free strategies via API.
"""

import requests
import json
import time

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def login_and_get_user_info():
    """Login and get admin user information."""
    
    print("🔐 Logging in as admin...")
    
    session = requests.Session()
    
    login_data = {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }
    
    response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        user_data = data.get("user", {})
        
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        print(f"✅ Login successful!")
        print(f"   User ID: {user_data.get('id', 'Unknown')}")
        print(f"   Email: {user_data.get('email', 'Unknown')}")
        print(f"   Role: {user_data.get('role', 'Unknown')}")
        
        return session, user_data.get('id'), token
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None, None, None

def check_current_strategies(session):
    """Check what strategies the admin user currently has."""
    
    print("\n📋 Checking current strategies...")
    
    try:
        # Check via chat sessions endpoint
        response = session.get(f"{BASE_URL}/chat/sessions")
        if response.status_code == 200:
            data = response.json()
            sessions = data.get("sessions", [])
            print(f"   Active chat sessions: {len(sessions)}")
            
        # Try to get user profile or strategy info if endpoint exists
        endpoints_to_try = [
            "/user/profile",
            "/strategies/user", 
            "/trading/strategies",
            "/opportunity-discovery/profile"
        ]
        
        for endpoint in endpoints_to_try:
            try:
                response = session.get(f"{BASE_URL}{endpoint}")
                print(f"   {endpoint}: Status {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"      Data keys: {list(data.keys())}")
            except Exception as e:
                print(f"   {endpoint}: Exception {e}")
                
    except Exception as e:
        print(f"❌ Strategy check failed: {e}")

def test_opportunity_discovery(session):
    """Test opportunity discovery to see the 'no strategies' error."""
    
    print("\n🔍 Testing opportunity discovery...")
    
    try:
        # Test via chat message
        payload = {
            "message": "Find me the best investment opportunities",
            "mode": "analysis"
        }
        
        response = session.post(f"{BASE_URL}/chat/message", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("content", "")
            metadata = data.get("metadata", {})
            
            print(f"✅ Chat response received")
            print(f"   Content length: {len(content)}")
            print(f"   Opportunities count: {metadata.get('opportunities_count', 'Unknown')}")
            print(f"   Service used: {metadata.get('service_used', 'Unknown')}")
            
            # Look for strategy-related messages
            if "strategy" in content.lower() or "onboard" in content.lower():
                print(f"   🎯 Strategy-related content detected")
                print(f"   Preview: {content[:200]}...")
            
        else:
            print(f"❌ Chat test failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Opportunity test failed: {e}")

def main():
    print("🎯 ADMIN USER STRATEGY ANALYSIS")
    print("=" * 80)
    
    # Login
    session, user_id, token = login_and_get_user_info()
    
    if not session:
        print("❌ Cannot proceed without authentication")
        return
    
    # Check current state
    check_current_strategies(session)
    
    # Test opportunity discovery to see the error
    test_opportunity_discovery(session)
    
    print("\n📊 ANALYSIS COMPLETE")
    print("=" * 50)
    print("Next steps:")
    print("1. Confirm admin user has no strategies")
    print("2. Identify onboarding endpoint or manual provisioning method")
    print("3. Provision the 3 free strategies")

if __name__ == "__main__":
    main()