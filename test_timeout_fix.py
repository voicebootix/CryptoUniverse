#!/usr/bin/env python3
"""
Test the timeout fix for portfolio endpoint
"""
import os
import requests
import time
from requests.exceptions import RequestException, Timeout

def test_timeout_fix():
    print("TESTING TIMEOUT FIX")
    print("=" * 20)

    # Get configuration from environment
    base_url = os.environ.get("CRYPTOUNIVERSE_BASE_URL", "https://cryptouniverse.onrender.com")
    admin_email = os.environ.get("CRYPTOUNIVERSE_ADMIN_EMAIL")
    admin_password = os.environ.get("CRYPTOUNIVERSE_ADMIN_PASSWORD")

    if not admin_email or not admin_password:
        print("ERROR: Missing CRYPTOUNIVERSE_ADMIN_EMAIL or CRYPTOUNIVERSE_ADMIN_PASSWORD environment variables")
        print("Set these environment variables for secure authentication")
        return False

    # Wait for deployment
    print("Waiting 45 seconds for Render deployment...")
    time.sleep(45)

    # Use session for connection reuse
    session = requests.Session()

    # Login
    print("\n1. Admin authentication...")
    login_url = f"{base_url}/api/v1/auth/login"
    login_payload = {"email": admin_email, "password": admin_password}

    try:
        response = session.post(login_url, json=login_payload, timeout=20)
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

    # Test the portfolio endpoint with new timeouts
    print("\n2. Testing portfolio endpoint with timeout fixes...")
    try:
        portfolio_url = f"{base_url}/api/v1/strategies/my-portfolio"

        start_time = time.time()
        response = session.get(portfolio_url, headers=headers, timeout=30)  # Give it more time
        elapsed = time.time() - start_time

        print(f"  Response: {response.status_code} in {elapsed:.2f}s")

        if response.status_code == 200:
            data = response.json()
            success = data.get('success', False)
            print(f"  Success: {success}")

            if success:
                strategies = data.get('active_strategies', [])
                print(f"  [SUCCESS] Portfolio working! Found {len(strategies)} strategies")

                # Show first few strategies
                for i, s in enumerate(strategies[:5], 1):
                    name = s.get('name', 'Unknown')
                    cost = s.get('credit_cost_monthly', 0)
                    print(f"    {i}. {name} ({cost} credits/month)")

                if len(strategies) > 5:
                    print(f"    ... and {len(strategies) - 5} more strategies")

                print("\n" + "="*50)
                print("SUCCESS! ADMIN PORTFOLIO IS NOW WORKING!")
                print("="*50)
                print(f"Frontend will now display {len(strategies)} strategies in My Strategies")
                return True

            else:
                error = data.get('error', 'Unknown')
                degraded = data.get('degraded', False)
                print(f"  [STILL FAILING] Error: {error}, Degraded: {degraded}")

                if error == "timeout":
                    print("  Still timing out - may need even higher timeouts")
                elif error == "Redis unavailable":
                    print("  Redis connection issue")

        else:
            print(f"  HTTP Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"  Error detail: {error_data.get('detail', 'No detail')}")
            except:
                print(f"  Error text: {response.text[:200]}")

    except requests.exceptions.Timeout as e:
        elapsed = time.time() - start_time
        print(f"  [TIMEOUT] Request timeout after {elapsed:.2f}s: {e}")
        print("  Service is still too slow - may need further optimization")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  [ERROR] Exception after {elapsed:.2f}s: {e}")

    # Gate admin grant behind environment variable to prevent accidental production grants
    if os.environ.get("ALLOW_GRANT") == "1":
        print("\n3. Checking if admin grant is still working...")
        try:
            grant_url = f"{base_url}/api/v1/admin-strategy-access/grant-full-access"
            grant_payload = {"strategy_type": "all", "grant_reason": "test_after_timeout_fix"}

            response = session.post(grant_url, headers=headers, json=grant_payload, timeout=25)
            if response.status_code == 200:
                result = response.json()
                strategies_granted = result.get("total_strategies", 0)
                print(f"  [OK] Admin grant still works, granted {strategies_granted} strategies")
            else:
                print(f"  [ISSUE] Admin grant status: {response.status_code}")
        except RequestException as e:
            print(f"  Admin grant test error: {e}")
    else:
        print("\n3. Admin grant check skipped (set ALLOW_GRANT=1 to enable)")

    return False

if __name__ == "__main__":
    success = test_timeout_fix()
    if success:
        print("\nProblem SOLVED! Admin can now see strategies in UI")
    else:
        print("\nStill needs more work - check logs above for specific issues")