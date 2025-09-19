import requests
import json

def test_live_enterprise_endpoint():
    print("TESTING LIVE ENTERPRISE ENDPOINT")
    print("=" * 35)

    # Login
    print("1. Admin login...")
    login_url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    login_payload = {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}

    response = requests.post(login_url, json=login_payload, timeout=15)
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        return False

    token = response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Authenticated")

    # Test endpoint availability
    print("\n2. Testing endpoint...")
    status_url = "https://cryptouniverse.onrender.com/api/v1/admin-strategy-access/admin-portfolio-status"
    response = requests.get(status_url, headers=headers, timeout=10)
    print(f"Status endpoint: {response.status_code}")

    if response.status_code == 200:
        print("[SUCCESS] Endpoint is LIVE!")

        # Grant full access
        print("\n3. Granting full access...")
        grant_url = "https://cryptouniverse.onrender.com/api/v1/admin-strategy-access/grant-full-access"
        grant_payload = {
            "strategy_type": "all",
            "grant_reason": "enterprise_admin_full_access"
        }

        response = requests.post(grant_url, headers=headers, json=grant_payload, timeout=30)
        print(f"Grant request: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"[SUCCESS] Granted {result.get('total_strategies')} strategies!")
            return True
        else:
            print(f"Grant failed: {response.text}")

    elif response.status_code == 404:
        print("[ERROR] Endpoint not found - deployment issue")
    else:
        print(f"Unexpected status: {response.status_code}")
        print(response.text)

    return False

if __name__ == "__main__":
    test_live_enterprise_endpoint()