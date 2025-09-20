#!/usr/bin/env python3
"""
Grant Admin Full Strategy Access - Enterprise CTO Solution

This script grants the admin user access to ALL marketplace strategies,
providing full platform access for testing and demonstration purposes.
"""

import requests
import json
import time

def grant_admin_full_strategy_access():
    """Grant admin user full access to all strategies."""

    print("[ENTERPRISE] ADMIN STRATEGY GRANT")
    print("=" * 50)

    # Step 1: Login as admin
    print("\n1. Admin Authentication...")
    login_url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    login_payload = {
        "email": "admin@cryptouniverse.com",
        "password": "AdminPass123!"
    }

    response = requests.post(login_url, json=login_payload, timeout=10)
    if response.status_code != 200:
        print(f"[ERROR] Admin login failed: {response.text}")
        return False

    data = response.json()
    token = data.get("access_token")
    user_id = data.get("user_id")
    print(f"✅ Admin authenticated: {user_id}")

    headers = {"Authorization": f"Bearer {token}"}

    # Step 2: Check current portfolio status
    print("\n2. Checking current strategy access...")
    try:
        status_url = "https://cryptouniverse.onrender.com/api/v1/admin-strategy-access/admin-portfolio-status"
        response = requests.get(status_url, headers=headers, timeout=10)

        if response.status_code == 200:
            status_data = response.json()
            current_strategies = status_data.get("current_strategies", 0)
            total_available = status_data.get("total_available_strategies", 0)
            has_full_access = status_data.get("has_full_access", False)

            print(f"📊 Current Status:")
            print(f"   - Current strategies: {current_strategies}")
            print(f"   - Total available: {total_available}")
            print(f"   - Has full access: {has_full_access}")
            print(f"   - Portfolio status: {status_data.get('portfolio_status', 'unknown')}")

            if has_full_access and current_strategies > 20:
                print("✅ Admin already has full strategy access!")
                return True

        else:
            print(f"⚠️ Could not check status: {response.status_code}")

    except Exception as e:
        print(f"⚠️ Status check failed: {e}")

    # Step 3: Grant full strategy access
    print("\n3. Granting full strategy access...")
    try:
        grant_url = "https://cryptouniverse.onrender.com/api/v1/admin-strategy-access/grant-full-access"
        grant_payload = {
            "strategy_type": "all",
            "grant_reason": "admin_privilege_full_platform_access"
        }

        response = requests.post(grant_url, headers=headers, json=grant_payload, timeout=30)

        if response.status_code == 200:
            grant_result = response.json()

            print("🎉 SUCCESS! Full strategy access granted!")
            print(f"📈 Grant Details:")
            print(f"   - User ID: {grant_result.get('user_id')}")
            print(f"   - Strategies granted: {grant_result.get('total_strategies')}")
            print(f"   - Grant type: {grant_result.get('grant_type')}")
            execution_time = grant_result.get('execution_time_seconds', 0)
            print(f"   - Execution time: {execution_time:.2f}s")
            print(f"   - Message: {grant_result.get('message')}")

            strategies_list = grant_result.get('strategies_granted', [])
            if len(strategies_list) > 0:
                print(f"\n📋 Sample strategies granted:")
                for i, strategy in enumerate(strategies_list[:10], 1):
                    print(f"   {i}. {strategy}")
                if len(strategies_list) > 10:
                    print(f"   ... and {len(strategies_list) - 10} more strategies")

        else:
            print(f"❌ Strategy grant failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Grant request failed: {e}")
        return False

    # Step 4: Verify the grant worked
    print("\n4. Verifying strategy access...")
    time.sleep(2)  # Allow Redis to sync

    try:
        portfolio_url = "https://cryptouniverse.onrender.com/api/v1/strategies/my-portfolio"
        response = requests.get(portfolio_url, headers=headers, timeout=15)

        if response.status_code == 200:
            portfolio_result = response.json()

            if portfolio_result.get("success"):
                strategies = portfolio_result.get("active_strategies", [])
                print(f"✅ VERIFICATION SUCCESSFUL!")
                print(f"📊 Portfolio now shows: {len(strategies)} active strategies")

                if len(strategies) >= 20:  # Should have lots of strategies now
                    print("🎉 ADMIN FULL ACCESS CONFIRMED!")

                    # Show strategy breakdown
                    free_strategies = [s for s in strategies if s.get("monthly_cost", 0) == 0]
                    paid_strategies = [s for s in strategies if s.get("monthly_cost", 0) > 0]

                    print(f"\n📈 Strategy Breakdown:")
                    print(f"   - Free strategies: {len(free_strategies)}")
                    print(f"   - Paid strategies: {len(paid_strategies)}")
                    print(f"   - Total: {len(strategies)}")

                    # Show some examples
                    if len(strategies) > 0:
                        print(f"\n🔍 Example strategies:")
                        for i, strategy in enumerate(strategies[:5], 1):
                            cost = strategy.get("monthly_cost", 0)
                            print(f"   {i}. {strategy.get('name')} ({cost} credits/month)")

                    return True
                else:
                    print(f"⚠️ Expected more strategies, only got {len(strategies)}")

            else:
                print(f"❌ Portfolio still in degraded mode: {portfolio_result.get('error')}")
                return False

        else:
            print(f"❌ Portfolio verification failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

    return False

if __name__ == "__main__":
    print("🚀 Starting Enterprise Admin Strategy Grant Process...\n")

    success = grant_admin_full_strategy_access()

    if success:
        print(f"\n" + "="*50)
        print("🎉 ENTERPRISE SOLUTION COMPLETE!")
        print("✅ Admin now has full access to ALL strategies")
        print("✅ Portfolio service is working normally")
        print("✅ Strategy ownership system restored")
        print(f"="*50)
    else:
        print(f"\n" + "="*50)
        print("❌ SOLUTION INCOMPLETE")
        print("⚠️  Manual intervention may be needed")
        print(f"="*50)