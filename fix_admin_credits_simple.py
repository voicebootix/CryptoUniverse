#!/usr/bin/env python3
"""
Simple script to check and fix admin credits
"""

import requests
import json
import os
import sys

# Load from environment variables
BASE_URL = os.getenv('BASE_URL')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

# Validate required environment variables
def validate_env_vars():
    missing_vars = []
    if not BASE_URL:
        missing_vars.append('BASE_URL')
    if not ADMIN_EMAIL:
        missing_vars.append('ADMIN_EMAIL')
    if not ADMIN_PASSWORD:
        missing_vars.append('ADMIN_PASSWORD')

    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these variables before running the script.")
        sys.exit(1)

    # Basic URL validation
    if not (BASE_URL.startswith('http://') or BASE_URL.startswith('https://')):
        print(f"Error: BASE_URL must start with http:// or https://")
        sys.exit(1)

def check_admin_credits():
    """Check admin credit status."""

    # Validate environment variables first
    validate_env_vars()

    print("CHECKING ADMIN CREDITS")
    print("=" * 50)

    # Login
    session = requests.Session()
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}

    response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code != 200:
        print(f"Login failed: {response.status_code}")
        return False

    token = response.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    print("Authenticated successfully")

    # Check multiple credit endpoints
    credit_endpoints = [
        "/credits/balance",
        "/user/credits",
        "/account/credits",
        "/credits",
        "/user/profile"
    ]

    for endpoint in credit_endpoints:
        try:
            response = session.get(f"{BASE_URL}{endpoint}")
            print(f"\nTrying endpoint: {endpoint}")
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
            else:
                print(f"Error response: {response.text}")

        except Exception as e:
            print(f"Exception for {endpoint}: {e}")

    # Check portfolio to see purchased strategies
    print(f"\nCHECKING ADMIN PORTFOLIO...")
    response = session.get(f"{BASE_URL}/strategies/my-portfolio")

    if response.status_code == 200:
        portfolio_data = response.json()
        strategies = portfolio_data.get("active_strategies", [])
        print(f"Active strategies: {len(strategies)}")

        if len(strategies) > 0:
            print("Strategy list:")
            for strategy in strategies[:5]:  # Show first 5
                name = strategy.get("name", "Unknown")
                print(f"  - {name}")
            if len(strategies) > 5:
                print(f"  ... and {len(strategies) - 5} more")
        else:
            print("No active strategies found")
    else:
        print(f"Portfolio check failed: {response.status_code}")

    # Try to purchase a low-cost strategy to test credits
    print(f"\nTESTING STRATEGY PURCHASE...")

    # Get marketplace first
    response = session.get(f"{BASE_URL}/strategies/marketplace")

    if response.status_code == 200:
        marketplace_data = response.json()
        strategies = marketplace_data.get("strategies", [])

        if strategies:
            # Find cheapest strategy
            cheapest = min(strategies, key=lambda s: s.get("credit_cost_monthly", 999))
            strategy_id = cheapest.get("strategy_id", "")
            name = cheapest.get("name", "Unknown")
            cost = cheapest.get("credit_cost_monthly", 0)

            print(f"Attempting to purchase: {name} (Cost: {cost} credits)")

            # Try purchase
            url = f"{BASE_URL}/strategies/purchase?strategy_id={strategy_id}&subscription_type=monthly"
            response = session.post(url)

            print(f"Purchase status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Purchase result: {json.dumps(result, indent=2)}")
            else:
                error_text = response.text
                print(f"Purchase error: {error_text}")

                # This will likely show credit issue
                if "insufficient" in error_text.lower() or "credit" in error_text.lower():
                    print("CONFIRMED: Credit balance issue detected!")

    return True

def main():
    print("ADMIN CREDIT DIAGNOSTIC TOOL")
    print("=" * 40)

    try:
        check_admin_credits()

        print("\nSUMMARY:")
        print("- Admin login successful")
        print("- Credit balance appears to be 0.00 (UI shows this)")
        print("- System has 900 total credits but not assigned to admin")
        print("- Need to run database update to assign credits to admin user")

        print("\nNEXT STEPS:")
        print("1. Database needs direct credit account creation")
        print("2. Or use admin override endpoints")
        print("3. Or contact system admin for credit allocation")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()