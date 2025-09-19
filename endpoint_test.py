#!/usr/bin/env python3
import requests
import time

def test_enterprise_endpoint():
    print("ENTERPRISE ENDPOINT TEST")
    print("=" * 24)

    # Login
    print("1. Getting auth token...")
    login_url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    payload = {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}
    response = requests.post(login_url, json=payload, timeout=30)

    if response.status_code != 200:
        print(f"Login failed: {response.status_code}")
        return

    token = response.json().get('access_token')
    headers = {"Authorization": f"Bearer {token}"}
    print("   [OK] Authenticated")

    # Test enterprise endpoint
    print("\n2. Testing admin endpoint...")
    try:
        status_url = "https://cryptouniverse.onrender.com/api/v1/admin-strategy-access/admin-portfolio-status"
        response = requests.get(status_url, headers=headers, timeout=45)
        print(f"   Status code: {response.status_code}")

        if response.status_code == 200:
            print("   [SUCCESS] Enterprise endpoint is LIVE!")
            data = response.json()
            print(f"   Current strategies: {data.get('current_strategies', 0)}")
            print(f"   Total available: {data.get('total_available_strategies', 0)}")
            return True

        elif response.status_code == 404:
            print("   [ERROR] Endpoint not found - still deploying")
        else:
            print(f"   [ERROR] Unexpected status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")

    except Exception as e:
        print(f"   [ERROR] Request failed: {e}")

    return False

if __name__ == "__main__":
    success = test_enterprise_endpoint()
    if success:
        print("\n✅ Enterprise endpoint is ready for use!")
    else:
        print("\n❌ Enterprise endpoint not yet available")