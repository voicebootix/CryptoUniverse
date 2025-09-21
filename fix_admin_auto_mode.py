#!/usr/bin/env python3
"""
Fix Admin Auto Mode - Ensure admin user has strategies for Auto Mode to work

The Auto Mode button fails because admin user has no active strategies.
This script provisions strategies for admin so Auto Mode works properly.
"""

import os
import requests
import json
from datetime import datetime

# Use environment variables for security
BASE_URL = os.getenv("BASE_URL", "https://cryptouniverse.onrender.com")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@cryptouniverse.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "AdminPass123!")

def fix_admin_auto_mode():
    """Fix admin Auto Mode by ensuring strategies are provisioned"""

    print("FIXING ADMIN AUTO MODE - PROVISIONING STRATEGIES")
    print("=" * 60)
    print(f"Time: {datetime.now().isoformat()}")
    print(f"Target: {BASE_URL}")
    print()

    try:
        # Step 1: Login as admin
        print("Step 1: Authenticating as admin...")

        session = requests.Session()
        session.trust_env = False

        login_response = session.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=30
        )

        if login_response.status_code != 200:
            print(f"FAILED: Login failed with status {login_response.status_code}")
            print(f"Response: {login_response.text}")
            return False

        # Parse response safely
        try:
            login_data = login_response.json()
            token = login_data.get("access_token")
        except (ValueError, KeyError) as e:
            print(f"FAILED: Could not parse login response: {e}")
            return False

        if not token:
            print(f"FAILED: No access token received")
            return False

        session.headers.update({"Authorization": f"Bearer {token}"})
        print("SUCCESS: Authenticated as admin")

        # Step 2: Check current portfolio status
        print("\nStep 2: Checking current admin portfolio...")

        portfolio_response = session.get(
            f"{BASE_URL}/api/v1/strategies/my-portfolio",
            timeout=30
        )

        current_strategies = 0
        if portfolio_response.status_code == 200:
            try:
                portfolio_data = portfolio_response.json()
                current_strategies = len(portfolio_data.get("active_strategies", []))
                print(f"Current active strategies: {current_strategies}")
            except ValueError:
                print("Could not parse portfolio response")
        else:
            print(f"Portfolio check failed: {portfolio_response.status_code}")

        # Step 3: Grant admin full strategy access if needed
        if current_strategies < 3:
            print(f"\nStep 3: Granting admin full strategy access...")

            grant_payload = {
                "strategy_type": "all",
                "grant_reason": "fix_auto_mode_functionality"
            }

            grant_response = session.post(
                f"{BASE_URL}/api/v1/admin-strategy-access/grant-full-access",
                json=grant_payload,
                timeout=60
            )

            print(f"Grant request status: {grant_response.status_code}")

            if grant_response.status_code == 200:
                try:
                    grant_data = grant_response.json()
                    print(f"SUCCESS: Strategies granted!")
                    print(f"- Total strategies: {grant_data.get('total_strategies', 'unknown')}")
                    print(f"- Execution time: {grant_data.get('execution_time_seconds', 0):.2f}s")
                except ValueError:
                    print("Grant succeeded but could not parse response")
            else:
                print(f"Grant failed: {grant_response.text[:300]}")
        else:
            print(f"Admin already has {current_strategies} strategies - skipping grant")

        # Step 4: Verify portfolio after grant
        print(f"\nStep 4: Verifying admin portfolio...")

        verify_response = session.get(
            f"{BASE_URL}/api/v1/strategies/my-portfolio",
            timeout=30
        )

        if verify_response.status_code == 200:
            try:
                verify_data = verify_response.json()
                final_strategies = len(verify_data.get("active_strategies", []))
                print(f"Final strategy count: {final_strategies}")

                if final_strategies > 0:
                    print("\nSUCCESS: Admin Auto Mode should now work!")
                    print("Sample strategies:")
                    for i, strategy in enumerate(verify_data.get("active_strategies", [])[:3]):
                        print(f"  {i+1}. {strategy.get('name', 'Unnamed')} ({strategy.get('strategy_id', 'no-id')})")

                    return True
                else:
                    print("WARNING: Still no strategies visible")
                    return False

            except ValueError:
                print("Could not parse verification response")
                return False
        else:
            print(f"Verification failed: {verify_response.status_code}")
            return False

    except requests.exceptions.Timeout:
        print("TIMEOUT: Request timed out - operation may have succeeded in background")
        print("Try refreshing the browser and clicking Auto Mode again")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    """Main execution"""

    print("CRYPTO UNIVERSE - ADMIN AUTO MODE FIX")
    print("=====================================")

    success = fix_admin_auto_mode()

    if success:
        print("\n" + "=" * 60)
        print("ADMIN AUTO MODE FIX COMPLETE!")
        print("")
        print("Next steps:")
        print("1. Refresh your browser (Ctrl+F5)")
        print("2. Click the Auto Mode button")
        print("3. You should now see real opportunities instead of error messages")
        print("")
        print("Auto Mode will now work with real strategy data!")
    else:
        print("\n" + "=" * 60)
        print("ADMIN AUTO MODE FIX INCOMPLETE")
        print("")
        print("Manual steps to try:")
        print("1. Wait 60 seconds for backend operations to complete")
        print("2. Refresh browser and try Auto Mode again")
        print("3. If still failing, check admin strategy access in browser")

if __name__ == "__main__":
    main()