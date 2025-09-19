import os
import requests
import json

def test_redis_strategies():
    """Redis test using requests to check strategy ownership."""

    # Skip Redis direct test since module not available
    print("Skipping Redis direct test - module not available")

def test_api_strategies():
    """Test API strategy ownership."""

    # Get configuration from environment
    base_url = os.environ.get("CRYPTOUNIVERSE_BASE_URL", "https://cryptouniverse.onrender.com")
    admin_email = os.environ.get("CRYPTOUNIVERSE_ADMIN_EMAIL")
    admin_password = os.environ.get("CRYPTOUNIVERSE_ADMIN_PASSWORD")

    if not admin_email or not admin_password:
        raise ValueError("ERROR: Missing CRYPTOUNIVERSE_ADMIN_EMAIL or CRYPTOUNIVERSE_ADMIN_PASSWORD environment variables")

    # Login
    url = f"{base_url}/api/v1/auth/login"
    payload = {
        "email": admin_email,
        "password": admin_password
    }

    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        user_id = data.get("user_id")

        # Validate token before proceeding
        if not token or len(token) < 10:
            raise ValueError("Invalid or missing access token from login response")
        if not user_id:
            raise ValueError("Missing user_id from login response")

        print(f"[OK] Logged in as admin (ID: {user_id})")

        headers = {"Authorization": f"Bearer {token}"}

        # Test portfolio endpoint
        portfolio_url = f"{base_url}/api/v1/strategies/portfolio"
        response = requests.get(portfolio_url, headers=headers)
        print(f"\n=== Strategy Portfolio Endpoint ===")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            portfolio = response.json()
            print(f"Portfolio response: {json.dumps(portfolio, indent=2)[:800]}")

            if 'active_strategies' in portfolio:
                strategies = portfolio['active_strategies']
                print(f"\nActive strategies count: {len(strategies)}")
            else:
                print("No 'active_strategies' key found")
        else:
            print(f"Error: {response.text}")
    else:
        raise ValueError(f"Login failed with status {response.status_code}: {response.text}")

if __name__ == "__main__":
    print("=== Testing Strategy Ownership Issue ===\n")

    print("1. Testing API...")
    test_api_strategies()

    print("\n2. Testing Redis...")
    test_redis_strategies()