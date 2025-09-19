#!/usr/bin/env python3
"""
Manual Redis Fix for Admin Strategy Access

Since the new endpoint needs deployment, let's use the existing onboarding
service to provision the admin with the standard strategy set, then manually
add more strategies using existing purchase endpoints.
"""

import requests
import json
import time

def manual_fix_admin_strategies():
    """Manually fix admin strategies using existing endpoints."""

    print("MANUAL ADMIN STRATEGY FIX")
    print("=" * 30)

    # Login
    print("1. Admin login...")
    login_url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    login_payload = {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}

    response = requests.post(login_url, json=login_payload, timeout=10)
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        return False

    token = response.json().get("access_token")
    user_id = response.json().get("user_id")
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[OK] Logged in: {user_id}")

    # Try to trigger onboarding to get the 3 free strategies
    print("\n2. Attempting onboarding trigger...")

    onboarding_endpoints = [
        "/api/v1/users/onboard",
        "/api/v1/users/complete-onboarding",
        "/api/v1/auth/onboard",
        "/api/v1/onboarding/complete"
    ]

    onboarding_success = False
    for endpoint in onboarding_endpoints:
        try:
            url = f"https://cryptouniverse.onrender.com{endpoint}"
            response = requests.post(url, headers=headers, json={}, timeout=10)
            print(f"  {endpoint}: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"  [SUCCESS] {result.get('message', 'Onboarding completed')}")
                onboarding_success = True
                break

        except Exception as e:
            print(f"  {endpoint}: Error - {e}")

    # Try purchasing additional strategies
    print("\n3. Attempting to purchase key strategies...")

    # Get marketplace to see available strategies
    marketplace_url = "https://cryptouniverse.onrender.com/api/v1/strategies/marketplace"
    response = requests.get(marketplace_url, headers=headers, timeout=10)

    if response.status_code == 200:
        marketplace = response.json()
        strategies = marketplace.get("strategies", [])[:10]  # First 10 strategies

        print(f"Found {len(strategies)} strategies to purchase")

        # Try to purchase each strategy
        purchased_count = 0
        for strategy in strategies:
            strategy_id = strategy.get("strategy_id")
            try:
                purchase_url = "https://cryptouniverse.onrender.com/api/v1/strategies/purchase"
                purchase_payload = {"strategy_id": strategy_id}

                response = requests.post(purchase_url, headers=headers, json=purchase_payload, timeout=10)
                if response.status_code == 200:
                    purchased_count += 1
                    print(f"  [OK] Purchased: {strategy_id}")
                else:
                    print(f"  [SKIP] {strategy_id}: {response.status_code}")

            except Exception as e:
                print(f"  [ERROR] {strategy_id}: {e}")

        print(f"Attempted to purchase {purchased_count} strategies")

    # Check portfolio after attempts
    print("\n4. Checking portfolio status...")
    time.sleep(3)  # Allow time for Redis updates

    portfolio_url = "https://cryptouniverse.onrender.com/api/v1/strategies/my-portfolio"
    response = requests.get(portfolio_url, headers=headers, timeout=15)

    if response.status_code == 200:
        portfolio = response.json()
        print(f"Portfolio response: {json.dumps(portfolio, indent=2)}")

        if portfolio.get("success"):
            strategies = portfolio.get("active_strategies", [])
            print(f"\n[SUCCESS] Portfolio shows {len(strategies)} strategies!")

            for i, s in enumerate(strategies, 1):
                name = s.get("name", "Unknown")
                cost = s.get("monthly_cost", 0)
                print(f"  {i}. {name} ({cost} credits/month)")

            return len(strategies) > 0

        else:
            error = portfolio.get("error", "Unknown")
            print(f"[DEGRADED] Portfolio error: {error}")

            # If still degraded, the issue is deeper
            if error == "timeout":
                print("\nThe Redis timeout issue persists.")
                print("This suggests the Redis-DB sync is still broken.")
                print("\nRecommended next steps:")
                print("1. Check Redis directly on the server")
                print("2. Deploy the enterprise admin endpoint")
                print("3. Or manually add to Redis: user_strategies:{user_id}")

    else:
        print(f"Portfolio check failed: {response.status_code}")

    return False

if __name__ == "__main__":
    success = manual_fix_admin_strategies()
    if success:
        print("\n[SUCCESS] Admin strategy access restored!")
    else:
        print("\n[INCOMPLETE] Manual fix was not sufficient")
        print("Need to deploy enterprise endpoint or fix Redis directly")