#!/usr/bin/env python3
"""Fix Admin UI Strategy Display Issue - Simple Version"""

import os
import requests
from datetime import datetime

BASE_URL = os.getenv("BASE_URL", "https://cryptouniverse.onrender.com")

def get_admin_token():
    """Get admin authentication token"""
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if not admin_email or not admin_password:
        raise ValueError("ADMIN_EMAIL and ADMIN_PASSWORD environment variables are required")

    response = requests.post(f"{BASE_URL}/api/v1/auth/login",
                           json={
                               "email": admin_email,
                               "password": admin_password
                           },
                           timeout=10)

    if response.status_code != 200:
        print(f"Login failed: {response.status_code}")
        return None

    return response.json().get("access_token")

def fix_admin_strategy_access():
    """Fix admin strategy access for UI display"""

    print("FIXING ADMIN UI STRATEGY DISPLAY")
    print("=" * 50)

    token = get_admin_token()
    if not token:
        return False

    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Check current state
    print("\nStep 1: Checking current admin portfolio...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/unified-strategies/portfolio",
                               headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            current_strategies = len(data.get("strategies", []))
            print(f"   Current strategies in UI: {current_strategies}")

            if current_strategies > 0:
                print("Admin already has strategies in UI!")
                return True
        else:
            print(f"   Portfolio endpoint error: {response.status_code}")

    except Exception as e:
        print(f"   Portfolio check error: {e}")

    # Step 2: Grant admin access
    print("\nStep 2: Granting admin access...")

    try:
        grant_payload = {
            "strategy_type": "all",
            "grant_reason": "admin_ui_fix"
        }

        response = requests.post(
            f"{BASE_URL}/api/v1/admin-strategy-access/grant-full-access",
            headers=headers,
            json=grant_payload,
            timeout=45
        )

        print(f"   Grant response: {response.status_code}")

        if response.status_code == 200:
            grant_data = response.json()
            print(f"   Granted access to {grant_data.get('total_strategies', 0)} strategies")
            print(f"   Execution time: {grant_data.get('execution_time_seconds', 0):.2f}s")
        else:
            print(f"   Grant failed: {response.text[:200]}")

    except Exception as e:
        print(f"   Grant error: {e}")

    # Step 3: Verify fix worked
    print("\nStep 3: Verifying admin UI now shows strategies...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/unified-strategies/portfolio",
                               headers=headers, timeout=15)

        if response.status_code == 200:
            data = response.json()
            final_strategies = len(data.get("strategies", []))
            active_strategies = len(data.get("active_strategies", []))

            print(f"   Final strategies in UI: {final_strategies}")
            print(f"   Active strategies: {active_strategies}")

            if final_strategies > 0:
                print("SUCCESS: Admin UI now shows strategies!")

                # Show sample strategy
                if data.get("strategies"):
                    sample = data["strategies"][0]
                    print(f"   Sample strategy: {sample.get('name', 'unnamed')}")

                return True
            else:
                print("Still no strategies in UI - may need different approach")

        else:
            print(f"   Verification failed: {response.status_code}")

    except Exception as e:
        print(f"   Verification error: {e}")

    return False

def main():
    """Main execution"""

    print("ADMIN UI STRATEGY FIX")
    print(f"Target: {BASE_URL}")
    print(f"Time: {datetime.now().isoformat()}")
    print()

    success = fix_admin_strategy_access()

    if success:
        print("\n" + "=" * 50)
        print("ADMIN UI STRATEGY FIX COMPLETE!")
        print("Admin users should now see strategies in the UI")
        print("Refresh the browser to see the changes")
    else:
        print("\n" + "=" * 50)
        print("ADMIN UI STRATEGY FIX INCOMPLETE")
        print("Manual investigation may be needed")

if __name__ == "__main__":
    main()