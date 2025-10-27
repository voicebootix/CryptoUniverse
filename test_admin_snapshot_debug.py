#!/usr/bin/env python3
"""
Test admin snapshot service to debug portfolio issues
"""

import requests
import json
import time

def test_admin_snapshot_debug():
    """Test admin snapshot service directly"""
    
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
    
    print(f"✅ Login successful - User ID: {user_id}")
    
    # Test admin snapshot endpoint directly
    print("\n👑 Testing admin snapshot endpoint...")
    try:
        admin_response = requests.get(f"{base_url}/strategies/admin-snapshot", headers=headers, timeout=60)
        print(f"Admin snapshot status: {admin_response.status_code}")
        
        if admin_response.status_code == 200:
            admin_data = admin_response.json()
            print(f"Admin snapshot success: {admin_data.get('success')}")
            print(f"Admin strategies count: {len(admin_data.get('active_strategies', []))}")
            print(f"Admin strategies: {[s.get('name') for s in admin_data.get('active_strategies', [])[:10]]}")
        else:
            print(f"Admin snapshot error: {admin_response.text}")
    except Exception as e:
        print(f"Admin snapshot exception: {e}")
    
    # Test user portfolio endpoint
    print("\n👤 Testing user portfolio endpoint...")
    try:
        portfolio_response = requests.get(f"{base_url}/user/portfolio", headers=headers, timeout=60)
        print(f"User portfolio status: {portfolio_response.status_code}")
        
        if portfolio_response.status_code == 200:
            portfolio_data = portfolio_response.json()
            print(f"User portfolio success: {portfolio_data.get('success')}")
            print(f"User strategies count: {len(portfolio_data.get('active_strategies', []))}")
            print(f"User strategies: {[s.get('name') for s in portfolio_data.get('active_strategies', [])[:10]]}")
        else:
            print(f"User portfolio error: {portfolio_response.text}")
    except Exception as e:
        print(f"User portfolio exception: {e}")
    
    # Test strategies list endpoint
    print("\n🎯 Testing strategies list endpoint...")
    try:
        strategies_response = requests.get(f"{base_url}/strategies", headers=headers, timeout=60)
        print(f"Strategies list status: {strategies_response.status_code}")
        
        if strategies_response.status_code == 200:
            strategies_data = strategies_response.json()
            print(f"Strategies list success: {strategies_data.get('success')}")
            print(f"Total strategies: {len(strategies_data.get('strategies', []))}")
            print(f"Strategy names: {[s.get('name') for s in strategies_data.get('strategies', [])[:10]]}")
        else:
            print(f"Strategies list error: {strategies_response.text}")
    except Exception as e:
        print(f"Strategies list exception: {e}")

if __name__ == "__main__":
    test_admin_snapshot_debug()