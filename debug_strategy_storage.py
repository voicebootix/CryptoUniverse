#!/usr/bin/env python3
"""
Debug Strategy Storage

Check where strategies are actually stored and why portfolio shows 0
"""

import requests
import json

# Configuration  
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def debug_strategy_storage():
    """Debug where strategies are stored."""
    
    print("🔍 DEBUGGING STRATEGY STORAGE")
    print("=" * 60)
    
    # Login
    session = requests.Session()
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    
    response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code != 200:
        print(f"❌ Login failed")
        return
    
    token = response.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    
    # Test various strategy-related endpoints
    endpoints_to_test = [
        "/strategies/my-portfolio",
        "/strategies/list", 
        "/strategies/available",
        "/strategies/marketplace",
        "/trading/strategies",
        "/user/strategies"
    ]
    
    print("📊 Testing all strategy endpoints...")
    
    for endpoint in endpoints_to_test:
        try:
            response = session.get(f"{BASE_URL}{endpoint}")
            print(f"\n🔍 {endpoint}")
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Success: {data.get('success', 'No success field')}")
                
                # Look for strategy-related data
                if isinstance(data, dict):
                    for key, value in data.items():
                        if 'strateg' in key.lower():
                            print(f"   {key}: {value}")
                        elif 'count' in key.lower():
                            print(f"   {key}: {value}")
                        elif isinstance(value, list):
                            print(f"   {key}: {len(value)} items")
                
            elif response.status_code == 422:
                error_data = response.json()
                print(f"   Validation error: {error_data}")
            else:
                print(f"   Error: {response.text[:100]}")
                
        except Exception as e:
            print(f"   Exception: {e}")
    
    # Test a specific chat message to see detailed metadata
    print(f"\n🔍 Testing detailed chat response for strategy info...")
    
    payload = {
        "message": "What strategies do I have active?",
        "mode": "analysis"
    }
    
    response = session.post(f"{BASE_URL}/chat/message", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Chat response:")
        print(f"   Intent: {data.get('intent')}")
        print(f"   Confidence: {data.get('confidence')}")
        
        metadata = data.get("metadata", {})
        print(f"   Metadata keys: {list(metadata.keys())}")
        
        # Look for strategy-related metadata
        for key, value in metadata.items():
            if 'strateg' in key.lower() or 'opportunit' in key.lower():
                print(f"   {key}: {value}")
        
        # Check content for strategy information
        content = data.get("content", "")
        if "strateg" in content.lower():
            print(f"   🎯 Strategy content found:")
            print(f"      {content[:300]}...")

if __name__ == "__main__":
    debug_strategy_storage()