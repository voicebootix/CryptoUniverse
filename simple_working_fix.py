#!/usr/bin/env python3
"""
Simple Working Fix - Use Existing Onboarding Service
"""
import requests

def simple_working_fix():
    print("USING EXISTING ONBOARDING SERVICE")
    print("=" * 35)

    # Login
    login_url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    login_payload = {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}

    response = requests.post(login_url, json=login_payload, timeout=15)
    token = response.json().get("access_token")
    user_id = response.json().get("user_id")
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Admin user: {user_id}")

    # Check current portfolio status
    print("\n1. Current portfolio status...")
    portfolio_url = "https://cryptouniverse.onrender.com/api/v1/strategies/my-portfolio"
    response = requests.get(portfolio_url, headers=headers, timeout=15)

    if response.status_code == 200:
        portfolio = response.json()
        if portfolio.get("success"):
            strategies = portfolio.get("active_strategies", [])
            print(f"Current: {len(strategies)} strategies")
            if len(strategies) > 0:
                print("Admin already has strategies working!")
                return True
        else:
            print(f"Portfolio error: {portfolio.get('error')}")

    # Try the purchase endpoint that we know works
    print("\n2. Manually purchasing the 3 core strategies...")

    core_strategies = [
        "ai_risk_management",
        "ai_portfolio_optimization",
        "ai_spot_momentum_strategy"
    ]

    purchased = 0
    for strategy_id in core_strategies:
        try:
            purchase_url = "https://cryptouniverse.onrender.com/api/v1/strategies/purchase"
            purchase_payload = {"strategy_id": strategy_id}

            response = requests.post(purchase_url, headers=headers, json=purchase_payload, timeout=15)
            print(f"  {strategy_id}: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    purchased += 1
                    print(f"    SUCCESS - {result.get('message', 'Purchased')}")
                else:
                    print(f"    ERROR - {result.get('error', 'Failed')}")
            else:
                print(f"    HTTP ERROR - {response.text[:100]}")

        except Exception as e:
            print(f"    EXCEPTION - {e}")

    print(f"\nPurchased {purchased} strategies")

    # Verify the fix worked
    print("\n3. Verifying the fix...")
    import time
    time.sleep(3)  # Allow Redis to sync

    response = requests.get(portfolio_url, headers=headers, timeout=15)
    if response.status_code == 200:
        portfolio = response.json()
        if portfolio.get("success"):
            strategies = portfolio.get("active_strategies", [])
            print(f"VERIFICATION: Admin now has {len(strategies)} strategies!")

            if len(strategies) >= 3:
                print("\n" + "="*40)
                print("SUCCESS! ADMIN STRATEGIES WORKING!")
                print("="*40)
                print(f"Admin can now see {len(strategies)} strategies in UI")

                for i, s in enumerate(strategies, 1):
                    name = s.get("name", "Unknown")
                    print(f"  {i}. {name}")

                return True
            else:
                print(f"Partial success: {len(strategies)} strategies")
        else:
            error = portfolio.get("error")
            print(f"Still error: {error}")

    return False

if __name__ == "__main__":
    success = simple_working_fix()
    if success:
        print("\n✅ Admin can now see strategies in UI!")
    else:
        print("\n❌ Issue still needs more work")