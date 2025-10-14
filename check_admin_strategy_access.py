#!/usr/bin/env python3
"""
Check Admin Strategy Access
"""

import requests
import json

def check_admin_strategy_access():
    """Check what strategies the admin user actually has access to."""
    print("🔍 CHECKING ADMIN STRATEGY ACCESS")
    print("=" * 50)
    
    # Login
    login_data = {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}
    response = requests.post("https://cryptouniverse.onrender.com/api/v1/auth/login", json=login_data, timeout=30)
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return
    
    token = response.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    print("✅ Authentication successful")
    
    # Get admin's portfolio/strategies
    print("\n📊 Checking Admin Portfolio...")
    
    try:
        portfolio_response = requests.get(
            "https://cryptouniverse.onrender.com/api/v1/unified-strategies/portfolio",
            headers=headers,
            timeout=60
        )
        
        if portfolio_response.status_code == 200:
            portfolio_data = portfolio_response.json()
            active_strategies = portfolio_data.get('active_strategies', [])
            
            print(f"   ✅ Portfolio loaded successfully")
            print(f"   📊 Active Strategies: {len(active_strategies)}")
            
            if active_strategies:
                print(f"   📋 Strategy Details:")
                for i, strategy in enumerate(active_strategies[:10]):  # Show first 10
                    strategy_id = strategy.get('strategy_id', 'unknown')
                    strategy_name = strategy.get('name', 'unknown')
                    print(f"      {i+1}. {strategy_id}: {strategy_name}")
                
                if len(active_strategies) > 10:
                    print(f"      ... and {len(active_strategies) - 10} more")
            else:
                print(f"   ❌ No active strategies found!")
                
                # Check if there are any strategies at all
                all_strategies = portfolio_data.get('all_strategies', [])
                print(f"   📊 All Strategies Available: {len(all_strategies)}")
                
                if all_strategies:
                    print(f"   📋 Available Strategies:")
                    for i, strategy in enumerate(all_strategies[:10]):
                        strategy_id = strategy.get('strategy_id', 'unknown')
                        strategy_name = strategy.get('name', 'unknown')
                        print(f"      {i+1}. {strategy_id}: {strategy_name}")
        else:
            print(f"   ❌ Portfolio fetch failed: {portfolio_response.status_code}")
            print(f"   Error: {portfolio_response.text[:200]}")
            
    except Exception as e:
        print(f"   💥 Exception: {str(e)}")
    
    # Check admin strategy access endpoint
    print("\n🔑 Checking Admin Strategy Access...")
    
    try:
        access_response = requests.get(
            "https://cryptouniverse.onrender.com/api/v1/admin-strategy-access/admin-portfolio-status",
            headers=headers,
            timeout=30
        )
        
        if access_response.status_code == 200:
            access_data = access_response.json()
            print(f"   ✅ Admin access endpoint working")
            print(f"   📊 Access Data: {json.dumps(access_data, indent=2)}")
        else:
            print(f"   ❌ Admin access failed: {access_response.status_code}")
            print(f"   Error: {access_response.text[:200]}")
            
    except Exception as e:
        print(f"   💥 Exception: {str(e)}")

if __name__ == "__main__":
    check_admin_strategy_access()