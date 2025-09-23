#!/usr/bin/env python3
"""
Debug exchange list response
"""

import requests
import json

def debug_exchange_list():
    print("=== DEBUGGING EXCHANGE LIST ===")

    session = requests.Session()

    # Login
    login_resp = session.post('https://cryptouniverse.onrender.com/api/v1/auth/login',
                            json={'email': 'admin@cryptouniverse.com', 'password': 'AdminPass123!'})

    if login_resp.status_code != 200:
        print(f"Login failed: {login_resp.status_code}")
        return

    token = login_resp.json()['access_token']
    session.headers.update({'Authorization': f'Bearer {token}'})

    print("\nTesting GET /api/v1/exchanges/list:")
    list_resp = session.get('https://cryptouniverse.onrender.com/api/v1/exchanges/list')
    if list_resp.status_code == 200:
        data = list_resp.json()
        print(f"Response type: {type(data)}")
        print(f"Raw response: {json.dumps(data, indent=2)}")
    else:
        print(f"Failed: {list_resp.status_code}")
        print(f"Response: {list_resp.text}")

if __name__ == "__main__":
    debug_exchange_list()