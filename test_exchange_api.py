#!/usr/bin/env python3
"""
Test the exchange API endpoints directly
"""

import requests
import json

def test_exchange_api():
    print("=== TESTING EXCHANGE API ENDPOINTS ===")

    session = requests.Session()

    # Login
    login_resp = session.post('https://cryptouniverse.onrender.com/api/v1/auth/login',
                            json={'email': 'admin@cryptouniverse.com', 'password': 'AdminPass123!'})

    if login_resp.status_code != 200:
        print(f"Login failed: {login_resp.status_code}")
        return

    token = login_resp.json()['access_token']
    session.headers.update({'Authorization': f'Bearer {token}'})

    # Test 1: List exchange accounts
    print("\n1. Testing GET /api/v1/exchanges/accounts:")
    accounts_resp = session.get('https://cryptouniverse.onrender.com/api/v1/exchanges/accounts')
    if accounts_resp.status_code == 200:
        accounts_data = accounts_resp.json()
        print(f"   Found {len(accounts_data)} exchange accounts:")
        for acc in accounts_data:
            print(f"   - {acc.get('exchange_type')} (Status: {acc.get('status')})")
    else:
        print(f"   Failed: {accounts_resp.status_code}")
        print(f"   Response: {accounts_resp.text[:300]}")

    # Test 2: Get portfolio/balances
    print("\n2. Testing GET /api/v1/exchanges/portfolio:")
    portfolio_resp = session.get('https://cryptouniverse.onrender.com/api/v1/exchanges/portfolio')
    if portfolio_resp.status_code == 200:
        portfolio_data = portfolio_resp.json()
        print(f"   Success: {portfolio_data.get('success')}")
        print(f"   Total Value: ${portfolio_data.get('total_value_usd', 0):,.2f}")
        print(f"   Balances: {len(portfolio_data.get('balances', []))} assets")
        print(f"   Message: {portfolio_data.get('message', 'N/A')}")

        # Show some balance details
        balances = portfolio_data.get('balances', [])[:5]  # First 5
        for bal in balances:
            print(f"   - {bal.get('asset')}: {bal.get('balance')} (${bal.get('value_usd', 0):,.2f})")
    else:
        print(f"   Failed: {portfolio_resp.status_code}")
        print(f"   Response: {portfolio_resp.text[:500]}")

    # Test 3: List all exchange routes
    print("\n3. Testing available exchange endpoints:")
    test_endpoints = [
        '/api/v1/exchanges',
        '/api/v1/exchanges/status',
        '/api/v1/exchanges/balances',
    ]

    for endpoint in test_endpoints:
        test_resp = session.get(f'https://cryptouniverse.onrender.com{endpoint}')
        print(f"   {endpoint}: {test_resp.status_code}")

if __name__ == "__main__":
    test_exchange_api()