#!/usr/bin/env python3
"""
Test script for opportunity discovery functionality
"""
import requests
import json
import time

BASE_URL = "https://cryptouniverse.onrender.com"

def test_opportunity_discovery():
    """Test the opportunity discovery feature"""
    
    # Test 1: Check service health
    print("🔍 Testing service health...")
    try:
        health_response = requests.get(f"{BASE_URL}/api/v1/health", timeout=10)
        health_data = health_response.json()
        print(f"✅ Health Status: {health_data.get('status')}")
        print(f"📊 Database: {health_data.get('checks', {}).get('database', {}).get('status')}")
        print(f"📊 Redis: {health_data.get('checks', {}).get('redis', {}).get('status')}")
        print(f"📊 Market Data: {health_data.get('checks', {}).get('market_data', {}).get('status')}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Test 2: Try to login (this might fail due to auth service issues)
    print("\n🔐 Testing authentication...")
    try:
        login_response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "admin@admin.com", "password": "admin123"},
            timeout=10
        )
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            print("✅ Login successful")
        else:
            print(f"❌ Login failed: {login_response.status_code} - {login_response.text}")
            # Try without auth for now
            token = None
    except Exception as e:
        print(f"❌ Login error: {e}")
        token = None
    
    # Test 3: Test opportunity discovery endpoint directly
    print("\n🎯 Testing opportunity discovery...")
    try:
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        # Test the opportunity discovery endpoint
        opp_response = requests.post(
            f"{BASE_URL}/api/v1/opportunities/discover",
            json={
                "scan_type": "comprehensive",
                "max_opportunities": 5
            },
            headers=headers,
            timeout=30
        )
        
        print(f"📊 Status Code: {opp_response.status_code}")
        print(f"📊 Response: {opp_response.text[:500]}...")
        
        if opp_response.status_code == 200:
            data = opp_response.json()
            print("✅ Opportunity discovery successful!")
            print(f"📈 Scan ID: {data.get('scan_id')}")
            print(f"📊 Status: {data.get('status')}")
            return True
        else:
            print(f"❌ Opportunity discovery failed: {opp_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Opportunity discovery error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing CryptoUniverse Opportunity Discovery")
    print("=" * 50)
    
    success = test_opportunity_discovery()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")