#!/usr/bin/env python3
"""
Simple Strategy Test - Test basic functionality
"""

import requests
import json
import time

def test_basic_functionality():
    """Test basic API functionality."""
    print("🚀 Testing Basic API Functionality")
    print("=" * 40)
    
    base_url = "https://cryptouniverse.onrender.com/api/v1"
    
    # Test login
    print("1. Testing login...")
    login_data = {
        "email": "admin@cryptouniverse.com",
        "password": "AdminPass123!"
    }
    
    try:
        response = requests.post(f"{base_url}/auth/login", json=login_data, timeout=30)
        if response.status_code == 200:
            token = response.json().get('access_token')
            print(f"✅ Login successful - Token: {token[:20]}...")
            
            headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
            
            # Test portfolio endpoint
            print("\n2. Testing portfolio endpoint...")
            portfolio_response = requests.get(f"{base_url}/unified-strategies/portfolio", headers=headers, timeout=60)
            if portfolio_response.status_code == 200:
                portfolio_data = portfolio_response.json()
                strategies = portfolio_data.get('active_strategies', [])
                print(f"✅ Portfolio loaded - {len(strategies)} strategies found")
                
                # Test opportunity discovery
                print("\n3. Testing opportunity discovery...")
                opp_response = requests.post(f"{base_url}/opportunities/discover", headers=headers, json={}, timeout=30)
                if opp_response.status_code == 200:
                    opp_data = opp_response.json()
                    scan_id = opp_data.get('scan_id')
                    print(f"✅ Opportunity discovery started - Scan ID: {scan_id}")
                    
                    # Test a simple strategy
                    print("\n4. Testing risk management strategy...")
                    strategy_payload = {
                        "function": "risk_management",
                        "symbol": "BTC/USDT",
                        "parameters": {
                            "analysis_type": "comprehensive",
                            "symbols": ["BTC/USDT", "ETH/USDT"]
                        },
                        "simulation_mode": True
                    }
                    
                    strategy_response = requests.post(
                        f"{base_url}/strategies/execute",
                        headers=headers,
                        json=strategy_payload,
                        timeout=60
                    )
                    
                    if strategy_response.status_code == 200:
                        strategy_data = strategy_response.json()
                        success = strategy_data.get('success', False)
                        print(f"✅ Risk management strategy - Success: {success}")
                        if success:
                            print(f"   Data keys: {list(strategy_data.keys())}")
                        else:
                            print(f"   Error: {strategy_data.get('error', 'Unknown')}")
                    else:
                        print(f"❌ Risk management strategy failed - {strategy_response.status_code}")
                        print(f"   Response: {strategy_response.text}")
                else:
                    print(f"❌ Opportunity discovery failed - {opp_response.status_code}")
                    print(f"   Response: {opp_response.text}")
            else:
                print(f"❌ Portfolio endpoint failed - {portfolio_response.status_code}")
                print(f"   Response: {portfolio_response.text}")
        else:
            print(f"❌ Login failed - {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"💥 Error: {e}")

if __name__ == "__main__":
    test_basic_functionality()