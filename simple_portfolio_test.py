#!/usr/bin/env python3
"""
Simple test to see if admin bypass activates
"""
import requests
import time

def simple_portfolio_test():
    print("SIMPLE PORTFOLIO TEST")
    print("=" * 21)

    # Login
    login_url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    login_payload = {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}

    response = requests.post(login_url, json=login_payload, timeout=15)
    token = response.json().get("access_token")
    user_id = response.json().get("user_id")
    headers = {"Authorization": f"Bearer {token}"}
    print(f"User ID: {user_id}")

    # Test portfolio with shorter timeout to see if bypass works
    print("\nTesting portfolio endpoint (10s timeout)...")
    portfolio_url = "https://cryptouniverse.onrender.com/api/v1/strategies/my-portfolio"

    start_time = time.time()
    try:
        response = requests.get(portfolio_url, headers=headers, timeout=10)
        elapsed = time.time() - start_time

        print(f"Response: {response.status_code} in {elapsed:.2f}s")

        if response.status_code == 200:
            data = response.json()
            success = data.get('success', False)

            if success:
                strategies = data.get('active_strategies', [])
                print(f"SUCCESS! Found {len(strategies)} strategies in {elapsed:.2f}s")
                print("Admin bypass is working!")
                return True
            else:
                print(f"Failed: {data.get('error', 'unknown')}")

        else:
            print(f"HTTP error: {response.status_code}")

    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"TIMEOUT after {elapsed:.2f}s - admin bypass NOT working")
        print("Still using slow Redis path")

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"Error after {elapsed:.2f}s: {e}")

    return False

if __name__ == "__main__":
    success = simple_portfolio_test()
    if success:
        print("\nAdmin bypass working - UI should show strategies!")
    else:
        print("\nAdmin bypass not working - need to fix role check")