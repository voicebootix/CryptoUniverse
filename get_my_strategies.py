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
    user_id = data.get("user_id")
    print(f"[OK] Logged in successfully as admin")
    print(f"User ID: {user_id}")

    headers = {"Authorization": f"Bearer {token}"}

    # Try to get owned strategies
    owned_url = "https://cryptouniverse.onrender.com/api/v1/strategies/owned"
    response = requests.get(owned_url, headers=headers)
    print(f"\n=== Owned Strategies (GET /api/v1/strategies/owned) ===")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        if 'strategies' in data:
            strategies = data['strategies']
            print(f"Total owned strategies: {len(strategies)}")
            for i, strategy in enumerate(strategies, 1):
                print(f"\nStrategy {i}:")
                print(f"  - ID: {strategy.get('strategy_id')}")
                print(f"  - Name: {strategy.get('name')}")
                print(f"  - Category: {strategy.get('category')}")
                print(f"  - Type: {strategy.get('type')}")
                print(f"  - Is Purchased: {strategy.get('is_purchased', False)}")
                print(f"  - Description: {strategy.get('description', '')[:100]}")
        else:
            print(json.dumps(data, indent=2))
    else:
        print(f"Response: {response.text}")

    # Also check user profile for strategy info
    profile_url = "https://cryptouniverse.onrender.com/api/v1/users/profile"
    response = requests.get(profile_url, headers=headers)
    print(f"\n=== User Profile ===")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        profile = response.json()
        print(f"Credits: {profile.get('credits', 0)}")
        print(f"Role: {profile.get('role', 'N/A')}")
        if 'subscription' in profile:
            print(f"Subscription: {profile['subscription']}")
else:
    print(f"Login failed: {response.text}")