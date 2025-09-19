import requests
import json

def test_redis_strategies():
    """Redis test using requests to check strategy ownership."""

    # Skip Redis direct test since module not available
    print("Skipping Redis direct test - module not available")

def test_api_strategies():
    """Test API strategy ownership."""

    # Login
    url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    payload = {
        "email": "admin@cryptouniverse.com",
        "password": "AdminPass123!"
    }

    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        user_id = data.get("user_id")
        print(f"[OK] Logged in as admin (ID: {user_id})")

        headers = {"Authorization": f"Bearer {token}"}

        # Test portfolio endpoint
        portfolio_url = "https://cryptouniverse.onrender.com/api/v1/strategies/portfolio"
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
        print(f"Login failed: {response.text}")

if __name__ == "__main__":
    print("=== Testing Strategy Ownership Issue ===\n")

    print("1. Testing API...")
    test_api_strategies()

    print("\n2. Testing Redis...")
    test_redis_strategies()