#!/usr/bin/env python3
"""
Check if admin user actually has strategies in the database
"""
import os
import requests
from requests.exceptions import RequestException, Timeout
import json

def check_db_strategies():
    # Gate live tests behind environment variable
    if os.environ.get("RUN_LIVE_TESTS") != "1":
        print("Live database tests disabled (set RUN_LIVE_TESTS=1 to enable)")
        return False

    print("CHECKING DATABASE STRATEGIES")
    print("=" * 28)

    # Login with session for connection reuse
    session = requests.Session()
    base_url = os.environ.get("CRYPTOUNIVERSE_BASE_URL", "https://cryptouniverse.onrender.com")
    admin_email = os.environ.get("CRYPTOUNIVERSE_ADMIN_EMAIL", "admin@cryptouniverse.com")
    admin_password = os.environ.get("CRYPTOUNIVERSE_ADMIN_PASSWORD", "AdminPass123!")

    login_url = f"{base_url}/api/v1/auth/login"
    login_payload = {"email": admin_email, "password": admin_password}

    try:
        response = session.post(login_url, json=login_payload, timeout=15)
        response.raise_for_status()
        auth_data = response.json()
        token = auth_data.get("access_token")
        user_id = auth_data.get("user_id")

        if not token:
            print("Authentication failed: No token received")
            return False

        headers = {"Authorization": f"Bearer {token}"}
        print(f"Admin user: {user_id}")
    except RequestException as e:
        print(f"Login failed: {e}")
        return False
    except (ValueError, KeyError) as e:
        print(f"Login response parsing failed: {e}")
        return False

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
            url = f"{base_url}{endpoint}"
            response = session.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            print(f"\n{endpoint}:")
            print(f"  Status: {response.status_code}")

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                print(f"  JSON parsing error: {e}")
                continue

            if isinstance(data, list):
                print(f"  Found: {len(data)} strategies")
                if len(data) > 0:
                    print("  SUCCESS - Strategies found in database!")
                    for i, s in enumerate(data[:3], 1):
                        if isinstance(s, dict):
                            name = s.get('name', s.get('strategy_name', 'Unknown'))
                            print(f"    {i}. {name}")
                    return True
            elif isinstance(data, dict):
                # Defensive access to nested data
                strategies = data.get('strategies', data.get('data', data))
                if isinstance(strategies, list) and len(strategies) > 0:
                    print(f"  Found: {len(strategies)} strategies")
                    print("  SUCCESS - Strategies found in database!")
                    return True
                else:
                    print(f"  Response: {str(data)[:200]}")

        except RequestException as e:
            print(f"  Network error: {e}")
        except (ValueError, KeyError, TypeError) as e:
            print(f"  Data processing error: {e}")

    print("\n2. The frontend calls /strategies/my-portfolio but that's Redis-based")
    print("Need to find the correct database endpoint that has your 4 strategies")

    return False

if __name__ == "__main__":
    found = check_db_strategies()
    if not found:
        print("\nNo strategies found in any database endpoint!")
        print("This means the strategies were never actually saved to the database.")
        print("The onboarding process may have failed to create database records.")