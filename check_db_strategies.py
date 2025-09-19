#!/usr/bin/env python3
"""
Check if admin user actually has strategies in the database
"""
import requests

def check_db_strategies():
    print("CHECKING DATABASE STRATEGIES")
    print("=" * 28)

    # Login
    login_url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    login_payload = {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}

    response = requests.post(login_url, json=login_payload, timeout=15)
    token = response.json().get("access_token")
    user_id = response.json().get("user_id")
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Admin user: {user_id}")

    # Check what endpoint the frontend actually calls for strategies
    # Based on your analysis, it should be database-based, not Redis

    print("\n1. Testing different strategy endpoints...")

    endpoints = [
        "/api/v1/strategies/list",           # Database strategies
        "/api/v1/strategies/user-strategies", # User's strategies
        "/api/v1/users/strategies",          # Another possible endpoint
        "/api/v1/trading-strategies/list",   # Trading strategies
    ]

    for endpoint in endpoints:
        try:
            url = f"https://cryptouniverse.onrender.com{endpoint}"
            response = requests.get(url, headers=headers, timeout=15)

            print(f"\n{endpoint}:")
            print(f"  Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    print(f"  Found: {len(data)} strategies")
                    if len(data) > 0:
                        print("  SUCCESS - Strategies found in database!")
                        for i, s in enumerate(data[:3], 1):
                            name = s.get('name', s.get('strategy_name', 'Unknown'))
                            print(f"    {i}. {name}")
                        return True
                elif isinstance(data, dict):
                    strategies = data.get('strategies', data.get('data', []))
                    if strategies:
                        print(f"  Found: {len(strategies)} strategies")
                        print("  SUCCESS - Strategies found in database!")
                        return True
                    else:
                        print(f"  Response: {data}")
            else:
                try:
                    error = response.json()
                    print(f"  Error: {error}")
                except:
                    print(f"  Error: {response.text[:100]}")

        except Exception as e:
            print(f"  Exception: {e}")

    print("\n2. The frontend calls /strategies/my-portfolio but that's Redis-based")
    print("Need to find the correct database endpoint that has your 4 strategies")

    return False

if __name__ == "__main__":
    found = check_db_strategies()
    if not found:
        print("\nNo strategies found in any database endpoint!")
        print("This means the strategies were never actually saved to the database.")
        print("The onboarding process may have failed to create database records.")