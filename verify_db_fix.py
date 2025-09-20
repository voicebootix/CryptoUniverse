import os
import requests
import json
from requests.exceptions import RequestException, Timeout

def test_strategy_ownership_after_fix():
    """Test strategy ownership after database fix."""

    # Get configuration from environment
    base_url = os.environ.get("CRYPTOUNIVERSE_BASE_URL", "https://cryptouniverse.onrender.com")
    admin_email = os.environ.get("CRYPTOUNIVERSE_ADMIN_EMAIL")
    admin_password = os.environ.get("CRYPTOUNIVERSE_ADMIN_PASSWORD")

    if not admin_email or not admin_password:
        print("ERROR: Missing CRYPTOUNIVERSE_ADMIN_EMAIL or CRYPTOUNIVERSE_ADMIN_PASSWORD environment variables")
        print("Set these environment variables for secure authentication")
        return False

    # Login
    url = f"{base_url}/api/v1/auth/login"
    payload = {
        "email": admin_email,
        "password": admin_password
    }

    print("=== Testing Strategy Ownership After DB Fix ===\n")

    # Use session for connection reuse
    session = requests.Session()

    try:
        response = session.post(url, json=payload, timeout=15)
        response.raise_for_status()
    except Timeout as e:
        print(f"[FAILED] Login timeout: {e}")
        return False
    except RequestException as e:
        print(f"[FAILED] Login network error: {e}")
        return False
    except (ValueError, json.JSONDecodeError) as e:
        print(f"[FAILED] Login JSON parsing error: {e}")
        return False
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
            endpoint_url = f"{base_url}{endpoint}"
            print(f"\n--- Testing {method} {endpoint} ---")

            try:
                if method == "GET":
                    response = session.get(endpoint_url, headers=headers, timeout=15)
                else:
                    response = session.post(endpoint_url, headers=headers, json={}, timeout=15)
                response.raise_for_status()
            except Timeout as e:
                print(f"Timeout error: {e}")
                continue
            except RequestException as e:
                print(f"Network error: {e}")
                continue

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
        credits_url = f"{base_url}/api/v1/credits/balance"
        try:
            response = session.get(credits_url, headers=headers, timeout=15)
            response.raise_for_status()
        except Timeout as e:
            print(f"Credits check timeout: {e}")
            response = None
        except RequestException as e:
            print(f"Credits check network error: {e}")
            response = None
        if response and response.status_code == 200:
            credits = response.json()
            print(f"Credits: {credits.get('available_credits')}/{credits.get('total_credits')}")

        return False
    else:
        print(f"[FAILED] Login failed: {response.status_code}")
        print(response.text)
        return False

if __name__ == "__main__":
    test_strategy_ownership_after_fix()