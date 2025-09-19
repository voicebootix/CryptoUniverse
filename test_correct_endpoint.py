import requests
import json

def test_correct_portfolio_endpoint():
    """Test the correct portfolio endpoint after finding it in code."""

    # Login
    url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    payload = {
        "email": "admin@cryptouniverse.com",
        "password": "AdminPass123!"
    }

    print("=== Testing Correct Strategy Portfolio Endpoint ===\n")

    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        user_id = data.get("user_id")
        print(f"[OK] Admin login successful (ID: {user_id})")

        headers = {"Authorization": f"Bearer {token}"}

        # Test the correct endpoint found in the code
        portfolio_url = "https://cryptouniverse.onrender.com/api/v1/strategies/my-portfolio"
        print(f"\n--- Testing GET /api/v1/strategies/my-portfolio ---")

        response = requests.get(portfolio_url, headers=headers)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            try:
                result = response.json()
                print(f"[SUCCESS] Portfolio endpoint is working!")

                # Pretty print the full response to see structure
                print(f"\nFull Response:")
                print(json.dumps(result, indent=2))

                # Look for strategy data
                if 'active_strategies' in result:
                    strategies = result['active_strategies']
                    print(f"\n✅ FOUND {len(strategies)} ACTIVE STRATEGIES!")

                    for i, strategy in enumerate(strategies, 1):
                        print(f"\n{i}. Strategy: {strategy.get('name', 'Unknown')}")
                        print(f"   ID: {strategy.get('strategy_id', 'N/A')}")
                        print(f"   Category: {strategy.get('category', 'N/A')}")
                        print(f"   Monthly Cost: {strategy.get('monthly_cost', 0)} credits")
                        print(f"   Is Purchased: {strategy.get('is_purchased', False)}")

                    # Analyze the breakdown
                    free_strategies = [s for s in strategies if s.get('monthly_cost', 0) == 0]
                    paid_strategies = [s for s in strategies if s.get('monthly_cost', 0) > 0]

                    print(f"\n=== ANALYSIS ===")
                    print(f"Total strategies: {len(strategies)}")
                    print(f"Free strategies: {len(free_strategies)}")
                    print(f"Paid strategies: {len(paid_strategies)}")

                    if len(strategies) == 4:
                        print(f"\n🎉 PERFECT! You have exactly 4 strategies as expected!")
                        if len(free_strategies) == 3 and len(paid_strategies) == 1:
                            print(f"✅ Breakdown is correct: 3 free + 1 purchased")
                        else:
                            print(f"⚠️ Breakdown differs from expected (3 free + 1 paid)")
                    elif len(strategies) > 0:
                        print(f"\n✅ Good! Strategy ownership is working, but count is different than expected")
                    else:
                        print(f"\n❌ No strategies found - issue still exists")

                elif 'strategies' in result:
                    print(f"Found 'strategies' key with {len(result['strategies'])} items")

                else:
                    print(f"Available keys: {list(result.keys())}")

            except json.JSONDecodeError:
                print(f"Non-JSON response: {response.text}")
        else:
            print(f"Error {response.status_code}: {response.text}")

        # Also test credit balance for reference
        credits_url = "https://cryptouniverse.onrender.com/api/v1/credits/balance"
        credits_response = requests.get(credits_url, headers=headers)
        if credits_response.status_code == 200:
            credits = credits_response.json()
            print(f"\n--- Credits Balance ---")
            print(f"Available: {credits.get('available_credits')}")
            print(f"Total: {credits.get('total_credits')}")
            print(f"Used: {credits.get('used_credits')}")

    else:
        print(f"Login failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    test_correct_portfolio_endpoint()