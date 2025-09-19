import requests
import json

def test_strategy_ownership_after_fix():
    """Test strategy ownership after database fix."""

    # Login
    url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    payload = {
        "email": "admin@cryptouniverse.com",
        "password": "AdminPass123!"
    }

    print("=== Testing Strategy Ownership After DB Fix ===\n")

    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        user_id = data.get("user_id")
        print(f"[OK] Admin login successful")
        print(f"User ID: {user_id}")
        print(f"Role: {data.get('role')}")

        headers = {"Authorization": f"Bearer {token}"}

        # Test multiple endpoints to find working strategy ownership check
        endpoints_to_test = [
            ("/api/v1/strategies/portfolio", "GET"),
            ("/api/v1/strategies/owned", "GET"),
            ("/api/v1/strategies/owned", "POST"),
            ("/api/v1/strategies/marketplace", "GET"),
            ("/api/v1/strategies/my", "GET")
        ]

        for endpoint, method in endpoints_to_test:
            url = f"https://cryptouniverse.onrender.com{endpoint}"
            print(f"\n--- Testing {method} {endpoint} ---")

            if method == "GET":
                response = requests.get(url, headers=headers)
            else:
                response = requests.post(url, headers=headers, json={})

            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                try:
                    result = response.json()

                    # Look for strategy ownership indicators
                    if 'active_strategies' in result:
                        strategies = result['active_strategies']
                        print(f"[SUCCESS] Found {len(strategies)} active strategies!")

                        for i, strategy in enumerate(strategies, 1):
                            print(f"\n  {i}. {strategy.get('name', 'Unknown')}")
                            print(f"     ID: {strategy.get('strategy_id', 'N/A')}")
                            print(f"     Category: {strategy.get('category', 'N/A')}")
                            print(f"     Cost: {strategy.get('monthly_cost', 0)} credits/month")
                            print(f"     Purchased: {strategy.get('is_purchased', False)}")

                        # Count free vs purchased
                        free_count = len([s for s in strategies if s.get('monthly_cost', 0) == 0])
                        paid_count = len([s for s in strategies if s.get('monthly_cost', 0) > 0])

                        print(f"\n[SUMMARY]")
                        print(f"  Total strategies: {len(strategies)}")
                        print(f"  Free strategies: {free_count}")
                        print(f"  Purchased strategies: {paid_count}")

                        if len(strategies) == 4 and free_count == 3 and paid_count == 1:
                            print(f"\n✅ PERFECT! You have exactly 4 strategies as expected:")
                            print(f"   - 3 free onboarding strategies")
                            print(f"   - 1 purchased strategy")
                        elif len(strategies) > 0:
                            print(f"\n✅ GOOD! Strategy ownership is working again!")
                        else:
                            print(f"\n❌ Still no strategies found")

                        return True  # Found working endpoint

                    elif 'strategies' in result:
                        strategies = result['strategies']
                        print(f"Found {len(strategies)} marketplace strategies")

                        # Check for ownership indicators
                        owned = [s for s in strategies if s.get('is_owned') or s.get('owned_by_user')]
                        if owned:
                            print(f"[SUCCESS] Found {len(owned)} owned strategies in marketplace!")
                            return True
                        else:
                            print("No ownership indicators found in marketplace")

                    else:
                        print(f"Response keys: {list(result.keys())}")

                except json.JSONDecodeError:
                    print(f"Non-JSON response: {response.text[:200]}")

            elif response.status_code == 405:
                print("Method not allowed - endpoint disabled/changed")
            else:
                print(f"Error: {response.text[:200]}")

        # Test credits balance
        print(f"\n--- Credit Balance Check ---")
        credits_url = "https://cryptouniverse.onrender.com/api/v1/credits/balance"
        response = requests.get(credits_url, headers=headers)
        if response.status_code == 200:
            credits = response.json()
            print(f"Credits: {credits.get('available_credits')}/{credits.get('total_credits')}")

        return False
    else:
        print(f"[FAILED] Login failed: {response.status_code}")
        print(response.text)
        return False

if __name__ == "__main__":
    test_strategy_ownership_after_fix()