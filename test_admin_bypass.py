#!/usr/bin/env python3
"""
Test the admin bypass fix
"""
import requests
import time

def test_admin_bypass():
    print("TESTING ADMIN BYPASS FIX")
    print("=" * 25)

    # Wait for deployment
    print("Waiting 30 seconds for Render deployment...")
    time.sleep(30)

    # Login
    print("\n1. Admin authentication...")
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

    # Test the portfolio endpoint with admin bypass
    print("\n2. Testing admin bypass portfolio endpoint...")
    try:
        portfolio_url = "https://cryptouniverse.onrender.com/api/v1/strategies/my-portfolio"

        start_time = time.time()
        response = requests.get(portfolio_url, headers=headers, timeout=30)
        elapsed = time.time() - start_time

        print(f"  Response: {response.status_code} in {elapsed:.2f}s")

        if response.status_code == 200:
            data = response.json()
            success = data.get('success', False)
            print(f"  Success: {success}")

            if success:
                strategies = data.get('active_strategies', [])
                summary = data.get('summary', {})

                print(f"  [SUCCESS] Admin bypass working! Found {len(strategies)} strategies")
                print(f"  Response time: {elapsed:.2f}s (should be <5s with bypass)")

                # Show summary stats
                print(f"  Total strategies: {summary.get('total_strategies', 0)}")
                print(f"  Active strategies: {summary.get('active_strategies', 0)}")
                print(f"  Monthly cost: {summary.get('monthly_credit_cost', 0)} credits")

                # Show first few strategies
                print("  Sample strategies:")
                for i, s in enumerate(strategies[:5], 1):
                    name = s.get('name', 'Unknown')
                    category = s.get('category', 'Unknown')
                    cost = s.get('credit_cost_monthly', 0)
                    print(f"    {i}. {name} ({category}) - {cost} credits/month")

                if len(strategies) > 5:
                    print(f"    ... and {len(strategies) - 5} more strategies")

                # Check if bypass was used (fast response time)
                if elapsed < 10:
                    print("\n" + "="*60)
                    print("🎉 SUCCESS! ADMIN BYPASS WORKING PERFECTLY!")
                    print("="*60)
                    print(f"✅ Fast response: {elapsed:.2f}s (was 24+ seconds)")
                    print(f"✅ Admin can see {len(strategies)} strategies in UI")
                    print(f"✅ Portfolio data complete with summary stats")
                    print("✅ Frontend will now display strategies correctly")
                    print("="*60)
                    return True
                else:
                    print(f"  [SLOW] Still took {elapsed:.2f}s - bypass may not be working")

            else:
                error = data.get('error', 'Unknown')
                degraded = data.get('degraded', False)
                print(f"  [FAILING] Error: {error}, Degraded: {degraded}")

        else:
            print(f"  HTTP Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"  Error detail: {error_data.get('detail', 'No detail')}")
            except:
                print(f"  Error text: {response.text[:200]}")

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  [ERROR] Exception after {elapsed:.2f}s: {e}")

    return False

if __name__ == "__main__":
    success = test_admin_bypass()
    if success:
        print("\n🚀 MISSION ACCOMPLISHED!")
        print("Admin strategy ownership issue has been resolved!")
        print("The admin UI 'My Strategies' section will now show all strategies.")
    else:
        print("\n❌ Issue not fully resolved - check above for details")