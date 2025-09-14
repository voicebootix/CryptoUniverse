#!/usr/bin/env python3
"""
Test the actual opportunity discovery endpoint
"""

import requests
import json

def test_opportunity_discover_endpoint():
    """Test the /opportunities/discover endpoint"""
    
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
    user_id = response.json().get("user_id")
    headers = {"Authorization": f"Bearer {token}"}
    
    print("🔍 Testing /opportunities/discover endpoint...")
    print(f"✅ Login successful")
    print(f"🆔 User ID: {user_id}")
    
    # Test the discover endpoint
    print(f"\n1️⃣ Testing POST /opportunities/discover:")
    try:
        discover_data = {
            "force_refresh": True,
            "include_strategy_recommendations": True
        }
        
        discover_response = requests.post(f"{base_url}/opportunities/discover", 
                                        headers=headers, 
                                        json=discover_data,
                                        timeout=120)
        print(f"   Status: {discover_response.status_code}")
        
        if discover_response.status_code == 200:
            discover_result = discover_response.json()
            print(f"   Success: {discover_result.get('success')}")
            print(f"   Scan ID: {discover_result.get('scan_id')}")
            print(f"   Total opportunities: {discover_result.get('total_opportunities', 0)}")
            print(f"   Execution time: {discover_result.get('execution_time_ms', 0):.2f}ms")
            
            opportunities = discover_result.get('opportunities', [])
            if opportunities:
                print(f"   ✅ Found {len(opportunities)} opportunities:")
                for i, opp in enumerate(opportunities[:5]):
                    print(f"      {i+1}. {opp.get('symbol')} on {opp.get('exchange')}")
                    print(f"         Strategy: {opp.get('strategy_name')}")
                    print(f"         Profit: ${opp.get('profit_potential_usd', 0):.2f}")
                    print(f"         Confidence: {opp.get('confidence_score', 0):.1f}%")
            else:
                print(f"   ❌ No opportunities found")
                
                # Check for error details
                if 'error' in discover_result:
                    print(f"   Error: {discover_result['error']}")
                
                # Check user profile
                user_profile = discover_result.get('user_profile', {})
                if user_profile:
                    print(f"   User profile:")
                    print(f"      Active strategies: {user_profile.get('active_strategy_count', 0)}")
                    print(f"      User tier: {user_profile.get('user_tier', 'Unknown')}")
                    print(f"      Scan limit: {user_profile.get('opportunity_scan_limit', 0)}")
                
                # Check asset discovery
                asset_discovery = discover_result.get('asset_discovery', {})
                if asset_discovery:
                    print(f"   Asset discovery:")
                    print(f"      Success: {asset_discovery.get('success', False)}")
                    if 'error' in asset_discovery:
                        print(f"      Error: {asset_discovery['error']}")
                    if 'total_assets' in asset_discovery:
                        print(f"      Total assets: {asset_discovery['total_assets']}")
                
                # Check strategy performance
                strategy_performance = discover_result.get('strategy_performance', {})
                if strategy_performance:
                    print(f"   Strategy performance:")
                    for strategy_id, perf in strategy_performance.items():
                        print(f"      {strategy_id}: {perf.get('opportunities_found', 0)} opportunities")
                        if perf.get('error'):
                            print(f"         Error: {perf['error']}")
        else:
            print(f"   Error: {discover_response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Test discovery status
    print(f"\n2️⃣ Testing GET /opportunities/status:")
    try:
        status_response = requests.get(f"{base_url}/opportunities/status", 
                                     headers=headers, 
                                     timeout=30)
        print(f"   Status: {status_response.status_code}")
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"   User onboarded: {status_data.get('user_onboarded', False)}")
            print(f"   Active strategies: {status_data.get('active_strategies', 0)}")
            print(f"   Last scan: {status_data.get('last_scan_time', 'Never')}")
        else:
            print(f"   Error: {status_response.text}")
    except Exception as e:
        print(f"   Exception: {e}")

if __name__ == "__main__":
    test_opportunity_discover_endpoint()