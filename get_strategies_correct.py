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
    print(f"[OK] Logged in successfully as admin")
    print(f"User ID: {data.get('user_id')}")

    headers = {"Authorization": f"Bearer {token}"}

    # Use POST for owned strategies
    strategies_url = "https://cryptouniverse.onrender.com/api/v1/strategies/owned"
    response = requests.post(strategies_url, headers=headers, json={
        "include_inactive": True
    })
    print(f"\n=== Your Owned Strategies ===")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        if 'strategies' in result:
            strategies = result['strategies']
            print(f"\nTotal strategies owned: {len(strategies)}")
            print("-" * 60)

            for i, strategy in enumerate(strategies, 1):
                print(f"\n{i}. Strategy: {strategy.get('name', 'Unknown')}")
                print(f"   ID: {strategy.get('strategy_id')}")
                print(f"   Category: {strategy.get('category', 'N/A')}")
                print(f"   Publisher: {strategy.get('publisher_name', 'N/A')}")
                print(f"   Is Purchased: {strategy.get('is_purchased', False)}")
                print(f"   Is AI Strategy: {strategy.get('is_ai_strategy', False)}")
                print(f"   Description: {strategy.get('description', '')[:80]}...")

            # Separate free vs purchased
            free_strategies = [s for s in strategies if not s.get('is_purchased', False)]
            purchased_strategies = [s for s in strategies if s.get('is_purchased', False)]

            print(f"\n" + "="*60)
            print(f"SUMMARY:")
            print(f"  - Free strategies (from onboarding): {len(free_strategies)}")
            print(f"  - Purchased strategies: {len(purchased_strategies)}")
            print(f"  - TOTAL: {len(strategies)}")

            if len(strategies) == 4:
                print(f"\n[VERIFIED] You have 4 strategies as expected (3 free + 1 purchased)")
            else:
                print(f"\n[WARNING] Expected 4 strategies but found {len(strategies)}")
        else:
            print(f"Response: {json.dumps(result, indent=2)}")
    elif response.status_code == 405:
        # Try with GET instead
        response = requests.get(strategies_url, headers=headers)
        if response.status_code == 200:
            print("(Using GET method)")
            print(json.dumps(response.json(), indent=2)[:1000])
    else:
        print(f"Error: {response.text[:500]}")

else:
    print(f"Login failed: {response.text}")