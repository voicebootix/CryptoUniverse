import requests
import json

# Login endpoint
url = "https://cryptouniverse.onrender.com/api/v1/auth/login"

# Admin credentials
payload = {
    "email": "admin@cryptouniverse.com",
    "password": "AdminPass123!"
}

# Make the login request
response = requests.post(url, json=payload)

if response.status_code == 200:
    data = response.json()
    token = data.get("access_token")
    print(f"[OK] Logged in successfully as admin")
    print(f"Token: {token[:50]}...")

    headers = {"Authorization": f"Bearer {token}"}

    # Try different strategy endpoints
    endpoints = [
        "/api/v1/strategies",
        "/api/v1/strategies/my",
        "/api/v1/strategies/marketplace",
        "/api/v1/strategies/owned",
        "/api/v1/strategies/purchased",
        "/api/v1/portfolio/strategies"
    ]

    for endpoint in endpoints:
        url = f"https://cryptouniverse.onrender.com{endpoint}"
        print(f"\n=== Testing {endpoint} ===")

        # Try GET request
        response = requests.get(url, headers=headers)
        print(f"GET Status: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list):
                    print(f"Found {len(data)} strategies")
                    for i, strategy in enumerate(data[:5], 1):  # Show first 5
                        if isinstance(strategy, dict):
                            print(f"\n  Strategy {i}:")
                            for key in ['id', 'name', 'type', 'status', 'description']:
                                if key in strategy:
                                    print(f"    - {key}: {strategy[key]}")
                else:
                    print(f"Response: {json.dumps(data, indent=2)[:500]}")
                break  # Found working endpoint
            except:
                print(f"Response: {response.text[:200]}")
        elif response.status_code != 405:
            print(f"Error: {response.text[:200]}")
else:
    print(f"Login failed: {response.text}")