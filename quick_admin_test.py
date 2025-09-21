import requests

# Quick test with timeout
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"

print("Testing login endpoint...")

login_data = {
    "email": "admin@cryptouniverse.com",
    "password": "AdminPass123!"
}

try:
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data, timeout=30)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("Login successful!")
        token = data.get("access_token")
        print(f"Token: {token[:50]}..." if token else "No token received")

        # Quick portfolio check
        headers = {"Authorization": f"Bearer {token}"}
        portfolio_response = requests.get(f"{BASE_URL}/strategies/my-portfolio", headers=headers, timeout=30)
        print(f"Portfolio check: {portfolio_response.status_code}")

        if portfolio_response.status_code == 200:
            portfolio_data = portfolio_response.json()
            active_strategies = portfolio_data.get("active_strategies", [])
            print(f"Current active strategies: {len(active_strategies)}")

            if len(active_strategies) == 0:
                print("No strategies found - this is the issue!")
            else:
                print("Strategies found:")
                for strategy in active_strategies[:3]:
                    print(f"  - {strategy.get('name', 'Unnamed')}")
        else:
            print(f"Portfolio error: {portfolio_response.text[:200]}")
    else:
        print(f"Login failed: {response.text}")

except requests.exceptions.Timeout:
    print("Request timed out - backend is slow")
except Exception as e:
    print(f"Error: {e}")