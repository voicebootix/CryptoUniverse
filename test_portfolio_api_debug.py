#!/usr/bin/env python3
"""
Test portfolio API with debug info to see exact failure
"""

import requests
import json

def test_portfolio_debug():
    print("=== TESTING PORTFOLIO API WITH DEBUG ===")

    session = requests.Session()

    # Login
    login_resp = session.post('https://cryptouniverse.onrender.com/api/v1/auth/login',
                            json={'email': 'admin@cryptouniverse.com', 'password': 'AdminPass123!'})

    if login_resp.status_code != 200:
        print(f"Login failed: {login_resp.status_code}")
        return

    token = login_resp.json()['access_token']
    session.headers.update({'Authorization': f'Bearer {token}'})

    # Test the trading/portfolio endpoint that uses get_user_portfolio_from_exchanges
    print("\n1. Testing GET /api/v1/trading/portfolio (calls get_user_portfolio_from_exchanges):")
    portfolio_resp = session.get('https://cryptouniverse.onrender.com/api/v1/trading/portfolio')

    print(f"Status: {portfolio_resp.status_code}")
    if portfolio_resp.status_code == 200:
        data = portfolio_resp.json()
        print(f"Response: {json.dumps(data, indent=2)}")

        # Look for debug info
        if 'debug_info' in data:
            print("\nDEBUG INFO FOUND:")
            for exchange_info in data['debug_info']:
                print(f"  Exchange: {exchange_info['exchange']}")
                print(f"  Account Status: {exchange_info['account_status']}")
                print(f"  API Key Status: {exchange_info['api_key_status']}")
                print(f"  Is Validated: {exchange_info['is_validated']}")
                print()
    else:
        print(f"Error: {portfolio_resp.text}")

if __name__ == "__main__":
    test_portfolio_debug()