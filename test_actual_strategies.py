#!/usr/bin/env python3
import requests
import json

# Read token
with open('auth_token.txt', 'r') as f:
    token = f.read().strip()

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

base_url = "http://localhost:8000/api/v1"

print("=" * 70)
print("TESTING ACTUAL STRATEGY ENDPOINTS")
print("=" * 70)

# Test endpoints from the strategies router
tests = [
    ("GET", "/strategies/list", None, "List all strategies"),
    ("GET", "/strategies/marketplace", None, "Get marketplace strategies"),
    ("GET", "/strategies/my-strategies", None, "Get user's strategies"),
    ("POST", "/strategies/deploy", {"strategy_id": "momentum_breakout"}, "Deploy strategy"),
    ("GET", "/strategies/performance", None, "Get strategy performance"),
    ("POST", "/strategies/backtest", {
        "strategy_id": "momentum_breakout",
        "symbol": "BTC/USDT",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31"
    }, "Backtest strategy"),
    ("POST", "/strategies/publish", {
        "strategy_id": "momentum_breakout",
        "price": 0,
        "description": "Test strategy"
    }, "Publish to marketplace"),
    ("GET", "/strategies/subscriptions", None, "Get user subscriptions"),
]

for method, endpoint, data, description in tests:
    print(f"\n{description.upper()}:")
    print(f"  Endpoint: {method} {endpoint}")

    try:
        if method == "GET":
            response = requests.get(f"{base_url}{endpoint}", headers=headers)
        else:
            response = requests.post(f"{base_url}{endpoint}", headers=headers, json=data)

        print(f"  Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list):
                print(f"  Response: Found {len(result)} items")
                if result:
                    print(f"  First item: {json.dumps(result[0], indent=4)[:300]}...")
            elif isinstance(result, dict):
                print(f"  Response: {json.dumps(result, indent=4)[:500]}...")
        else:
            print(f"  Error: {response.text[:200]}")
    except Exception as e:
        print(f"  Exception: {str(e)}")

print("\n" + "=" * 70)
print("STRATEGY ENDPOINTS TEST COMPLETE")
print("=" * 70)

# Browser la test pannuvom
print("\n📌 BROWSER TEST INSTRUCTIONS:")
print("1. Open: http://localhost:3000")
print("2. Login with: admin@cryptouniverse.com / AdminPass123!")
print("3. Navigate to 'Strategy IDE' from dashboard")
print("4. Check if strategies load and features work")
print("5. Try creating, testing, and deploying strategies")