#!/usr/bin/env python3
"""
Debug credit account - Check and potentially create credit account for admin user
"""

import requests
import jwt
import uuid

def debug_credit_account():
    print("=== CREDIT ACCOUNT DEBUG ===")

    # Get admin user token
    session = requests.Session()
    login = session.post('https://cryptouniverse.onrender.com/api/v1/auth/login',
                        json={'email': 'admin@cryptouniverse.com', 'password': 'AdminPass123!'})

    if login.status_code != 200:
        print(f"Login failed: {login.status_code}")
        return

    token = login.json()['access_token']
    decoded = jwt.decode(token, options={'verify_signature': False})
    user_id = decoded.get('sub')

    print(f"Admin User ID: {user_id}")

    # Check if there are any API endpoints to manage credits directly
    session.headers.update({'Authorization': f'Bearer {token}'})

    # Try to get user profile or account info
    profile_resp = session.get('https://cryptouniverse.onrender.com/api/v1/auth/me')
    if profile_resp.status_code == 200:
        profile = profile_resp.json()
        print(f"User profile: {profile}")

    # Try various credit-related endpoints
    endpoints_to_test = [
        '/credits',
        '/credits/account',
        '/credits/balance',
        '/user/credits',
        '/account/credits'
    ]

    for endpoint in endpoints_to_test:
        try:
            resp = session.get(f'https://cryptouniverse.onrender.com/api/v1{endpoint}')
            print(f"GET {endpoint}: {resp.status_code}")
            if resp.status_code == 200:
                print(f"  Response: {resp.json()}")
        except:
            pass

    # Test creating credit account via POST if there's an endpoint
    try:
        create_resp = session.post('https://cryptouniverse.onrender.com/api/v1/credits/account',
                                  json={'credits': 900})
        print(f"Create account attempt: {create_resp.status_code}")
        if create_resp.status_code in [200, 201]:
            print(f"  Success: {create_resp.json()}")
    except:
        pass

if __name__ == "__main__":
    debug_credit_account()