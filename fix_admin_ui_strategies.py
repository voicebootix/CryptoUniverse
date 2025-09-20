#!/usr/bin/env python3
"""
Fix Admin UI Strategy Display Issue

The UI shows no strategies for admin because:
1. Admin has marketplace Redis access but no database strategy records
2. UI expects unified endpoint which reads from database
3. Need to create database strategy access records for admin

This script grants admin access to actual database strategies.
"""

import os
import requests
import json
from datetime import datetime

BASE_URL = "https://cryptouniverse.onrender.com"

def get_admin_token():
    """Get admin authentication token"""

    response = requests.post(f"{BASE_URL}/api/v1/auth/login",
                           json={
                               "email": "admin@cryptouniverse.com",
                               "password": "AdminPass123!"
                           })

    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return None

    return response.json().get("access_token")

def fix_admin_strategy_access():
    """Fix admin strategy access for UI display"""

    print("🔧 FIXING ADMIN UI STRATEGY DISPLAY")
    print("=" * 50)

    token = get_admin_token()
    if not token:
        return False

    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Check current state
    print("\n📊 Step 1: Checking current admin portfolio...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/unified-strategies/portfolio",
                               headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            current_strategies = len(data.get("strategies", []))
            print(f"   Current strategies in UI: {current_strategies}")

            if current_strategies > 0:
                print("✅ Admin already has strategies in UI!")
                return True
        else:
            print(f"   Portfolio endpoint error: {response.status_code}")

    except Exception as e:
        print(f"   Portfolio check error: {e}")

    # Step 2: Check available database strategies
    print("\n📋 Step 2: Checking available database strategies...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/strategies/list",
                               headers=headers, timeout=10)

        if response.status_code == 200:
            db_strategies = response.json()
            print(f"   Database strategies available: {len(db_strategies)}")

            if len(db_strategies) == 0:
                print("❌ No strategies in database to grant!")
                return False

            # Show sample strategies
            print("   Sample strategies:")
            for i, strategy in enumerate(db_strategies[:3]):
                print(f"     {i+1}. {strategy.get('name', 'unnamed')} (ID: {strategy.get('id', 'none')})")

        else:
            print(f"   Database strategies error: {response.status_code}")
            return False

    except Exception as e:
        print(f"   Database check error: {e}")
        return False

    # Step 3: Grant admin access using enterprise recovery endpoint
    print("\n🔐 Step 3: Granting admin access to database strategies...")

    # Use the enterprise recovery endpoint to restore admin strategies
    try:
        # Get a sample of strategy IDs to grant
        strategy_ids = [
            strategy.get('id') for strategy in db_strategies[:10]  # Grant first 10 strategies
            if strategy.get('id')
        ]

        if not strategy_ids:
            print("❌ No valid strategy IDs found!")
            return False

        # Convert strategy IDs to string format expected by recovery endpoint
        strategy_ids_str = [str(sid) for sid in strategy_ids]

        print(f"   Granting access to {len(strategy_ids_str)} strategies...")

        recovery_payload = {
            "user_id": "admin_user_id",  # We'll get this from the system
            "strategy_ids": strategy_ids_str[:5],  # Start with first 5
            "force_overwrite": True,
            "dry_run": False
        }

        # Actually, let's use the admin strategy access endpoint instead
        grant_payload = {
            "strategy_type": "all",
            "grant_reason": "admin_ui_fix"
        }

        response = requests.post(
            f"{BASE_URL}/api/v1/admin-strategy-access/grant-full-access",
            headers=headers,
            json=grant_payload,
            timeout=30
        )

        print(f"   Grant response: {response.status_code}")

        if response.status_code == 200:
            grant_data = response.json()
            print(f"   ✅ Granted access to {grant_data.get('total_strategies', 0)} strategies")
            print(f"   Execution time: {grant_data.get('execution_time_seconds', 0):.2f}s")
        else:
            print(f"   Grant failed: {response.text[:200]}")

    except Exception as e:
        print(f"   Grant error: {e}")

    # Step 4: Verify fix worked
    print("\n✅ Step 4: Verifying admin UI now shows strategies...")
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
                print("🎉 SUCCESS: Admin UI now shows strategies!")

                # Show sample strategy
                if data.get("strategies"):
                    sample = data["strategies"][0]
                    print(f"   Sample strategy: {sample.get('name', 'unnamed')}")

                return True
            else:
                print("❌ Still no strategies in UI - may need different approach")

        else:
            print(f"   Verification failed: {response.status_code}")

    except Exception as e:
        print(f"   Verification error: {e}")

    return False

def main():
    """Main execution"""

    print("🚀 ADMIN UI STRATEGY FIX")
    print(f"Target: {BASE_URL}")
    print(f"Time: {datetime.now().isoformat()}")
    print()

    success = fix_admin_strategy_access()

    if success:
        print("\n" + "=" * 50)
        print("✅ ADMIN UI STRATEGY FIX COMPLETE!")
        print("🎯 Admin users should now see strategies in the UI")
        print("🔄 Refresh the browser to see the changes")
    else:
        print("\n" + "=" * 50)
        print("❌ ADMIN UI STRATEGY FIX INCOMPLETE")
        print("🔍 Manual investigation may be needed")
        print("💡 Check logs and database records")

if __name__ == "__main__":
    main()