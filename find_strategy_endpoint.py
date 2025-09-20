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
    print(f"[OK] Logged in successfully")

    headers = {"Authorization": f"Bearer {token}"}

    # Check portfolio endpoint
    portfolio_url = "https://cryptouniverse.onrender.com/api/v1/portfolio"
    response = requests.get(portfolio_url, headers=headers)
    print(f"\n=== Portfolio ===")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        portfolio = response.json()
        print(json.dumps(portfolio, indent=2)[:1000])

    # Check user strategies with POST
    strategies_url = "https://cryptouniverse.onrender.com/api/v1/strategies/owned"
    response = requests.post(strategies_url, headers=headers, json={})
    print(f"\n=== POST /strategies/owned ===")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, dict) and 'strategies' in data:
            strategies = data['strategies']
            print(f"Total strategies: {len(strategies)}")
            for i, s in enumerate(strategies, 1):
                print(f"\n{i}. {s.get('name')} ({s.get('strategy_id')})")
                print(f"   Category: {s.get('category')}")
                print(f"   Purchased: {s.get('is_purchased', False)}")
        else:
            print(json.dumps(data, indent=2)[:500])

    # Check credits
    credits_url = "https://cryptouniverse.onrender.com/api/v1/credits/balance"
    response = requests.get(credits_url, headers=headers)
    print(f"\n=== Credits Balance ===")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Credits: {response.json()}")

    # Check subscriptions/purchased strategies
    purchases_url = "https://cryptouniverse.onrender.com/api/v1/strategies/purchases"
    response = requests.get(purchases_url, headers=headers)
    print(f"\n=== Strategy Purchases ===")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(response.json())

else:
    print(f"Login failed: {response.text}")