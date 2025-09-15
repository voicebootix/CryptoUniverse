#!/usr/bin/env python3
"""
Quick Verification Test

Test key areas to verify fixes are working
"""

import requests
import json
import time

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def quick_test():
    """Quick test of key functionality."""
    
    print("🚀 QUICK VERIFICATION TEST")
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
    print("✅ Authenticated successfully")
    
    # Test 1: Market Analysis (should now have real data)
    print(f"\n📊 Test 1: Market Analysis")
    
    payload = {
        "message": "What's the current market situation?",
        "mode": "analysis"
    }
    
    start_time = time.time()
    response = session.post(f"{BASE_URL}/chat/message", json=payload, timeout=45)
    response_time = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        metadata = data.get("metadata", {})
        market_overview = metadata.get("market_overview", {})
        
        print(f"   Response time: {response_time:.1f}s")
        print(f"   Intent: {data.get('intent')}")
        print(f"   Market cap: ${market_overview.get('total_market_cap', 0):,}")
        print(f"   Available symbols: {len(market_overview.get('available_symbols', []))}")
        print(f"   Sentiment: {market_overview.get('sentiment', 'Unknown')}")
        
        # Check for improvement
        if (market_overview.get('total_market_cap', 0) > 0 or 
            len(market_overview.get('available_symbols', [])) > 5 or
            market_overview.get('sentiment') not in ['Unknown', 'Live']):
            print(f"   🎉 IMPROVEMENT DETECTED!")
        else:
            print(f"   ⚠️ Still placeholder data")
    else:
        print(f"   ❌ Failed: {response.status_code}")
    
    # Test 2: Opportunity Discovery (should now find opportunities)
    print(f"\n🔍 Test 2: Opportunity Discovery")
    
    payload = {
        "message": "Find investment opportunities",
        "mode": "analysis"
    }
    
    start_time = time.time()
    response = session.post(f"{BASE_URL}/chat/message", json=payload, timeout=45)
    response_time = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        metadata = data.get("metadata", {})
        
        print(f"   Response time: {response_time:.1f}s")
        print(f"   Intent: {data.get('intent')}")
        print(f"   Opportunities: {metadata.get('opportunities_count', 0)}")
        print(f"   Service: {metadata.get('service_used', 'Unknown')}")
        
        if metadata.get('opportunities_count', 0) > 0:
            print(f"   🎉 OPPORTUNITIES FOUND!")
        else:
            print(f"   ⚠️ Still no opportunities")
    else:
        print(f"   ❌ Failed: {response.status_code}")
    
    # Test 3: Risk Assessment (should now have real calculations)
    print(f"\n🛡️ Test 3: Risk Assessment")
    
    payload = {
        "message": "What's my portfolio risk?",
        "mode": "analysis"
    }
    
    start_time = time.time()
    response = session.post(f"{BASE_URL}/chat/message", json=payload, timeout=30)
    response_time = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        metadata = data.get("metadata", {})
        risk_analysis = metadata.get("risk_analysis", {})
        
        print(f"   Response time: {response_time:.1f}s")
        print(f"   Intent: {data.get('intent')}")
        print(f"   VaR 24h: ${risk_analysis.get('var_24h', 0):,.2f}")
        print(f"   Sharpe ratio: {risk_analysis.get('sharpe_ratio', 0):.2f}")
        
        if risk_analysis.get('var_24h', 0) > 0:
            print(f"   🎉 REAL RISK CALCULATIONS!")
        else:
            print(f"   ⚠️ Still zero calculations")
    else:
        print(f"   ❌ Failed: {response.status_code}")

if __name__ == "__main__":
    quick_test()