#!/usr/bin/env python3
"""
Test the correct exchange API endpoints
"""

import requests
import json

def test_exchange_api_correct():
    print("=== TESTING CORRECT EXCHANGE API ENDPOINTS ===")

    session = requests.Session()

    # Login
    login_resp = session.post('https://cryptouniverse.onrender.com/api/v1/auth/login',
                            json={'email': 'admin@cryptouniverse.com', 'password': 'AdminPass123!'})

    if login_resp.status_code != 200:
        print(f"Login failed: {login_resp.status_code}")
        return

    token = login_resp.json()['access_token']
    session.headers.update({'Authorization': f'Bearer {token}'})

    # Test 1: List exchange connections
    print("\n1. Testing GET /api/v1/exchanges/list:")
    list_resp = session.get('https://cryptouniverse.onrender.com/api/v1/exchanges/list')
    if list_resp.status_code == 200:
        exchanges = list_resp.json()
        print(f"   Found {len(exchanges)} exchange connections:")
        for exc in exchanges:
            print(f"   - {exc.get('exchange_type')} (ID: {exc.get('id')}, Status: {exc.get('status')})")
            print(f"     API Key Status: {exc.get('api_keys', [{}])[0].get('status') if exc.get('api_keys') else 'N/A'}")
    else:
        print(f"   Failed: {list_resp.status_code}")
        print(f"   Response: {list_resp.text[:500]}")

    # Test 2: Get balances for specific exchange (if any found)
    if list_resp.status_code == 200:
        exchanges = list_resp.json()
        if exchanges:
            first_exchange = exchanges[0]['exchange_type']
            print(f"\n2. Testing GET /api/v1/exchanges/{first_exchange}/balances:")
            balances_resp = session.get(f'https://cryptouniverse.onrender.com/api/v1/exchanges/{first_exchange}/balances')
            if balances_resp.status_code == 200:
                balances_data = balances_resp.json()
                print(f"   Success: {balances_data.get('success')}")
                print(f"   Total Value: ${balances_data.get('total_value', 0):,.2f}")
                balances = balances_data.get('balances', [])
                print(f"   Assets: {len(balances)}")
                for bal in balances[:5]:  # First 5
                    print(f"   - {bal.get('symbol')}: {bal.get('balance')} (${bal.get('value_usd', 0):,.2f})")
            else:
                print(f"   Failed: {balances_resp.status_code}")
                print(f"   Response: {balances_resp.text[:500]}")

    # Test 3: Direct call to get_user_portfolio_from_exchanges function via trading API
    print("\n3. Testing GET /api/v1/trading/portfolio:")
    trading_resp = session.get('https://cryptouniverse.onrender.com/api/v1/trading/portfolio')
    if trading_resp.status_code == 200:
        portfolio_data = trading_resp.json()
        print(f"   Success: {portfolio_data.get('success')}")
        print(f"   Total Value: ${portfolio_data.get('total_value_usd', 0):,.2f}")
        print(f"   Balances: {len(portfolio_data.get('balances', []))} assets")
        print(f"   Message: {portfolio_data.get('message', 'N/A')}")
    else:
        print(f"   Failed: {trading_resp.status_code}")
        print(f"   Response: {trading_resp.text[:500]}")

if __name__ == "__main__":
    test_exchange_api_correct()