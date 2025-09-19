#!/usr/bin/env python3
"""
Simple Admin Fix - Directly Add Basic Strategies to Redis
"""
import requests
import asyncio
import json

async def simple_admin_fix():
    print("SIMPLE ADMIN STRATEGY FIX")
    print("=" * 25)

    # Login
    print("1. Admin login...")
    login_url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    login_payload = {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}

    try:
        response = requests.post(login_url, json=login_payload, timeout=15)
        if response.status_code != 200:
            print(f"Login failed: {response.status_code}")
            return False

        token = response.json().get("access_token")
        user_id = response.json().get("user_id")
        headers = {"Authorization": f"Bearer {token}"}
        print(f"[OK] User: {user_id}")

    except Exception as e:
        print(f"Login error: {e}")
        return False

    # Use the basic onboarding to get at least 3 strategies
    print("\n2. Triggering user onboarding...")
    try:
        # Try different onboarding endpoints
        endpoints_to_try = [
            "/api/v1/onboarding/provision-strategies",
            "/api/v1/auth/complete-registration",
            "/api/v1/users/initialize",
        ]

        onboarding_success = False
        for endpoint in endpoints_to_try:
            try:
                url = f"https://cryptouniverse.onrender.com{endpoint}"
                response = requests.post(url, headers=headers, json={}, timeout=20)
                print(f"  {endpoint}: {response.status_code}")

                if response.status_code == 200:
                    print(f"  [SUCCESS] Onboarding triggered")
                    onboarding_success = True
                    break

            except Exception as e:
                print(f"  {endpoint}: {e}")

    except Exception as e:
        print(f"Onboarding error: {e}")

    # Check portfolio after onboarding attempt
    print("\n3. Portfolio verification...")
    try:
        import time
        time.sleep(3)  # Allow Redis to sync

        portfolio_url = "https://cryptouniverse.onrender.com/api/v1/strategies/my-portfolio"
        response = requests.get(portfolio_url, headers=headers, timeout=15)

        if response.status_code == 200:
            portfolio = response.json()
            print(f"Portfolio success: {portfolio.get('success')}")

            if portfolio.get("success"):
                strategies = portfolio.get("active_strategies", [])
                print(f"[SUCCESS] {len(strategies)} strategies found!")

                for i, s in enumerate(strategies, 1):
                    name = s.get("name", "Unknown")
                    print(f"  {i}. {name}")

                return len(strategies) > 0

            else:
                error = portfolio.get("error", "Unknown")
                print(f"[ERROR] Portfolio still degraded: {error}")

                if error == "timeout":
                    print("\nThe Redis key is still missing.")
                    print(f"Need to manually add: user_strategies:{user_id}")
                    print("Or wait for the enterprise admin endpoint to work.")

        else:
            print(f"Portfolio check failed: {response.status_code}")

    except Exception as e:
        print(f"Portfolio error: {e}")

    return False

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(simple_admin_fix())
    if success:
        print("\n[SUCCESS] Admin strategies restored!")
    else:
        print("\n[INCOMPLETE] Manual intervention still needed")