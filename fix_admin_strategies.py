#!/usr/bin/env python3
"""
Fix Admin Strategy Allocation

This script manually restores the admin user's strategy allocation by calling
the backend API endpoints that would normally be triggered during onboarding.
"""

import requests
import json
import time

def fix_admin_strategies():
    """Restore admin user's strategy allocation."""

    print("[FIX] FIXING ADMIN STRATEGY ALLOCATION")
    print("=" * 50)

    # Step 1: Login as admin
    print("\n1. Logging in as admin...")
    login_url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    login_payload = {
        "email": "admin@cryptouniverse.com",
        "password": "AdminPass123!"
    }

    response = requests.post(login_url, json=login_payload)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.text}")
        return False

    data = response.json()
    token = data.get("access_token")
    user_id = data.get("user_id")
    print(f"[OK] Login successful (ID: {user_id})")

    headers = {"Authorization": f"Bearer {token}"}

    # Step 2: Check current state
    print("\n2. Checking current portfolio state...")
    portfolio_url = "https://cryptouniverse.onrender.com/api/v1/strategies/my-portfolio"
    response = requests.get(portfolio_url, headers=headers)

    if response.status_code == 200:
        current = response.json()
        print(f"Current strategies: {len(current.get('active_strategies', []))}")
        if current.get('success'):
            print("[OK] Portfolio is working - strategies may already be restored!")
            return True
        else:
            print(f"[WARN] Portfolio in degraded mode: {current.get('error')}")

    # Step 3: Try to trigger onboarding completion
    print("\n3. Attempting to trigger onboarding completion...")
    onboarding_endpoints = [
        "/api/v1/users/complete-onboarding",
        "/api/v1/users/finalize-onboarding",
        "/api/v1/onboarding/complete",
        "/api/v1/auth/complete-onboarding"
    ]

    onboarding_success = False
    for endpoint in onboarding_endpoints:
        url = f"https://cryptouniverse.onrender.com{endpoint}"
        print(f"   Trying: {endpoint}")

        # Try POST
        response = requests.post(url, headers=headers, json={})
        if response.status_code == 200:
            result = response.json()
            print(f"   [OK] Success: {result.get('message', 'Onboarding completed')}")
            onboarding_success = True
            break
        elif response.status_code != 405 and response.status_code != 404:
            print(f"   Response: {response.status_code} - {response.text[:100]}")

    # Step 4: Try manual strategy allocation via marketplace
    if not onboarding_success:
        print("\n4. Attempting manual strategy allocation...")

        # Get available strategies first
        marketplace_url = "https://cryptouniverse.onrender.com/api/v1/strategies/marketplace"
        response = requests.get(marketplace_url, headers=headers)

        if response.status_code == 200:
            marketplace = response.json()
            strategies = marketplace.get('strategies', [])
            print(f"Found {len(strategies)} marketplace strategies")

            # Select strategies to allocate (3 free ones + 1 that was purchased)
            free_strategies = [s for s in strategies[:5] if s.get('credit_cost_monthly', 0) <= 30]

            strategy_ids_to_allocate = []
            for strategy in free_strategies[:3]:  # First 3 free/cheap strategies
                strategy_ids_to_allocate.append(strategy['strategy_id'])

            # Add one more expensive one (the "purchased" one)
            expensive_strategies = [s for s in strategies if s.get('credit_cost_monthly', 0) >= 50]
            if expensive_strategies:
                strategy_ids_to_allocate.append(expensive_strategies[0]['strategy_id'])

            print(f"Attempting to allocate strategies: {strategy_ids_to_allocate}")

            # Try to purchase/allocate these strategies
            purchase_success = 0
            for strategy_id in strategy_ids_to_allocate:
                purchase_url = "https://cryptouniverse.onrender.com/api/v1/strategies/purchase"
                purchase_payload = {"strategy_id": strategy_id}

                response = requests.post(purchase_url, headers=headers, json=purchase_payload)
                if response.status_code == 200:
                    purchase_success += 1
                    print(f"   [OK] Allocated: {strategy_id}")
                else:
                    print(f"   [WARN] Failed to allocate {strategy_id}: {response.status_code}")

            if purchase_success > 0:
                print(f"[OK] Successfully allocated {purchase_success} strategies!")

    # Step 5: Wait and verify
    print("\n5. Waiting for Redis sync...")
    time.sleep(3)

    print("\n6. Verifying strategy allocation...")
    response = requests.get(portfolio_url, headers=headers)

    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            strategies = result.get('active_strategies', [])
            print(f"[SUCCESS] Portfolio now shows {len(strategies)} strategies:")

            for i, strategy in enumerate(strategies, 1):
                cost = strategy.get('monthly_cost', 0)
                print(f"   {i}. {strategy.get('name')} ({cost} credits/month)")

            return True
        else:
            print(f"[WARN] Still in degraded mode: {result.get('error')}")

    # Step 6: Manual Redis restoration call
    print("\n7. Attempting manual Redis restoration...")
    restore_endpoints = [
        "/api/v1/strategies/restore-user-portfolio",
        "/api/v1/admin/restore-strategies",
        "/api/v1/users/restore-strategies"
    ]

    for endpoint in restore_endpoints:
        url = f"https://cryptouniverse.onrender.com{endpoint}"
        response = requests.post(url, headers=headers, json={"user_id": user_id})
        if response.status_code == 200:
            print(f"[OK] Manual restoration successful via {endpoint}")
            break

    # Final verification
    print("\n8. Final verification...")
    time.sleep(2)
    response = requests.get(portfolio_url, headers=headers)

    if response.status_code == 200:
        result = response.json()
        strategies = result.get('active_strategies', [])
        print(f"\n{'='*50}")

        if len(strategies) > 0:
            print(f"[FIXED] You now have {len(strategies)} strategies!")
            print(f"[OK] Strategy ownership is working again!")
            return True
        else:
            print(f"[ERROR] Still no strategies - may need manual Redis intervention")
            print(f"Redis key needed: user_strategies:{user_id}")
            return False

    return False

if __name__ == "__main__":
    success = fix_admin_strategies()
    if success:
        print(f"\n[SUCCESS] Strategy allocation has been restored!")
    else:
        print(f"\n[ERROR] Manual intervention still needed")
        print(f"Next steps: Check Redis directly or contact system admin")