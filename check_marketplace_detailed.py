import requests
import json

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
    print(f"[OK] Logged in successfully as admin")
    print(f"User ID: {user_id}")

    headers = {"Authorization": f"Bearer {token}"}

    # Get marketplace strategies
    marketplace_url = "https://cryptouniverse.onrender.com/api/v1/strategies/marketplace"
    response = requests.get(marketplace_url, headers=headers)
    print(f"\n=== Marketplace Strategies ===")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        if 'strategies' in result:
            strategies = result['strategies']
            print(f"Total marketplace strategies: {len(strategies)}")

            # Check for owned field
            owned_strategies = []
            for strategy in strategies:
                if strategy.get('is_owned') or strategy.get('owned_by_user'):
                    owned_strategies.append(strategy)

            print(f"\n=== Your Owned Strategies (from marketplace) ===")
            if owned_strategies:
                print(f"Found {len(owned_strategies)} owned strategies:")
                for i, s in enumerate(owned_strategies, 1):
                    print(f"\n{i}. {s.get('name')}")
                    print(f"   ID: {s.get('strategy_id')}")
                    print(f"   Category: {s.get('category')}")
            else:
                print("No strategies marked as owned in marketplace response")

            # Show first few marketplace strategies
            print(f"\n=== All Marketplace Strategies (first 5) ===")
            for i, strategy in enumerate(strategies[:5], 1):
                print(f"\n{i}. {strategy.get('name')}")
                print(f"   ID: {strategy.get('strategy_id')}")
                print(f"   Category: {strategy.get('category')}")
                print(f"   Cost: {strategy.get('credit_cost_monthly')} credits/month")
                # Check all ownership-related fields
                for field in ['is_owned', 'owned_by_user', 'purchased', 'is_purchased']:
                    if field in strategy:
                        print(f"   {field}: {strategy[field]}")

    # Try POST to marketplace
    print(f"\n=== Testing POST to marketplace ===")
    response = requests.post(marketplace_url, headers=headers, json={
        "filter": "owned"
    })
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(json.dumps(result, indent=2)[:500])

else:
    print(f"Login failed: {response.text}")