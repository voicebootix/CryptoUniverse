#!/usr/bin/env python3
"""Debug admin user role and credit account creation"""

import requests
import json

BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def debug_admin_credits():
    """Debug admin credit account creation process."""

    print("DEBUGGING ADMIN CREDIT ACCOUNT")
    print("=" * 40)

    # Login
    session = requests.Session()
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}

    print("1. Attempting admin login...")
    response = session.post(f"{BASE_URL}/auth/login", json=login_data)

    if response.status_code != 200:
        print(f"   Login failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return

    token_data = response.json()
    token = token_data.get("access_token")
    user_data = token_data.get("user", {})

    print(f"   Login successful!")
    print(f"   User ID: {user_data.get('id', 'N/A')}")
    print(f"   Email: {user_data.get('email', 'N/A')}")
    print(f"   Role: {user_data.get('role', 'N/A')}")

    session.headers.update({"Authorization": f"Bearer {token}"})

    # Test credits/balance endpoint - this should trigger account creation
    print("\n2. Calling /credits/balance (should create account)...")

    response = session.get(f"{BASE_URL}/credits/balance")
    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        credit_data = response.json()
        print(f"   SUCCESS! Credit data received:")
        print(f"   Available Credits: {credit_data.get('available_credits', 'N/A')}")
        print(f"   Total Credits: {credit_data.get('total_credits', 'N/A')}")
        print(f"   Used Credits: {credit_data.get('used_credits', 'N/A')}")

        if credit_data.get('available_credits', 0) > 0:
            print(f"\n   PROBLEM SOLVED! Admin now has {credit_data['available_credits']} credits")
        else:
            print(f"\n   STILL ISSUE: Credits showing as 0")
    else:
        print(f"   ERROR: {response.text}")

    # Also test profit potential endpoint
    print("\n3. Testing /credits/profit-potential...")
    response = session.get(f"{BASE_URL}/credits/profit-potential")
    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        profit_data = response.json()
        print(f"   Profit Potential: ${profit_data.get('profit_potential', 'N/A')}")
        print(f"   Active Strategies: {profit_data.get('active_strategies', 'N/A')}")

    return True

if __name__ == "__main__":
    try:
        debug_admin_credits()

        print("\n" + "="*50)
        print("DIAGNOSIS:")
        print("- If credits now show > 0: Problem solved!")
        print("- If still 0: Role comparison or DB issue")
        print("- If 502 error: Server still down")
        print("\nNext: Refresh browser and check credit balance in UI")

    except Exception as e:
        print(f"Error: {e}")