import os
import requests
import json
import time
from requests.exceptions import RequestException, Timeout

def test_enterprise_deployment():
    """Test if the enterprise admin endpoint is deployed and working."""

    # Get configuration from environment
    base_url = os.environ.get("CRYPTOUNIVERSE_BASE_URL", "https://cryptouniverse.onrender.com")
    admin_email = os.environ.get("CRYPTOUNIVERSE_ADMIN_EMAIL")
    admin_password = os.environ.get("CRYPTOUNIVERSE_ADMIN_PASSWORD")

    if not admin_email or not admin_password:
        print("ERROR: Missing CRYPTOUNIVERSE_ADMIN_EMAIL or CRYPTOUNIVERSE_ADMIN_PASSWORD environment variables")
        print("Set these environment variables for secure authentication")
        return False

    print("TESTING ENTERPRISE DEPLOYMENT")
    print("=" * 35)

    # Use session for connection reuse
    session = requests.Session()

    # Login
    print("1. Admin authentication...")
    login_url = f"{base_url}/api/v1/auth/login"
    login_payload = {"email": admin_email, "password": admin_password}

    try:
        response = session.post(login_url, json=login_payload, timeout=15)
        if response.status_code != 200:
            print(f"[ERROR] Login failed: {response.text}")
            return False

        token = response.json().get("access_token")
        user_id = response.json().get("user_id")
        headers = {"Authorization": f"Bearer {token}"}
        print(f"[OK] Authenticated: {user_id}")

    except Timeout as e:
        print(f"[ERROR] Login timeout: {e}")
        return False
    except RequestException as e:
        print(f"[ERROR] Login network error: {e}")
        return False
    except (ValueError, json.JSONDecodeError) as e:
        print(f"[ERROR] Login JSON parsing error: {e}")
        return False

    # Test if new endpoint is available
    print("\n2. Testing enterprise endpoint availability...")
    try:
        status_url = f"{base_url}/api/v1/admin-strategy-access/admin-portfolio-status"
        response = session.get(status_url, headers=headers, timeout=15)

        print(f"Endpoint status: {response.status_code}")

        if response.status_code == 200:
            print("[SUCCESS] Enterprise endpoint is LIVE!")
            status = response.json()
            current = status.get("current_strategies", 0)
            total = status.get("total_available_strategies", 0)
            print(f"Current strategies: {current}/{total}")

            # If admin doesn't have full access, grant it
            if current < total or current < 20:
                print("\n3. Granting full strategy access...")
                grant_url = f"{base_url}/api/v1/admin-strategy-access/grant-full-access"
                grant_payload = {
                    "strategy_type": "all",
                    "grant_reason": "enterprise_admin_privilege"
                }

                response = session.post(grant_url, headers=headers, json=grant_payload, timeout=30)

                if response.status_code == 200:
                    result = response.json()
                    strategies_granted = result.get("total_strategies", 0)
                    print(f"[SUCCESS] Granted {strategies_granted} strategies!")
                    print(f"Execution time: {result.get('execution_time_seconds', 0):.2f}s")

                    # Wait for Redis sync
                    print("\n4. Verifying portfolio access...")
                    time.sleep(3)

                    portfolio_url = f"{base_url}/api/v1/strategies/my-portfolio"
                    response = session.get(portfolio_url, headers=headers, timeout=15)

                    if response.status_code == 200:
                        portfolio = response.json()
                        if portfolio.get("success"):
                            strategies = portfolio.get("active_strategies", [])
                            print(f"[VERIFIED] Portfolio shows {len(strategies)} active strategies!")

                            if len(strategies) >= 20:
                                print("\n" + "="*50)
                                print("🎉 ENTERPRISE SOLUTION COMPLETE!")
                                print("✅ Admin has full strategy access")
                                print("✅ Portfolio service working normally")
                                print("✅ Strategy ownership system restored")
                                print("="*50)
                                return True
                            else:
                                print(f"[WARNING] Expected more strategies, got {len(strategies)}")

                        else:
                            print(f"[ERROR] Portfolio still degraded: {portfolio.get('error')}")
                    else:
                        print(f"[ERROR] Portfolio check failed: {response.status_code}")

                else:
                    print(f"[ERROR] Strategy grant failed: {response.status_code}")
                    print(response.text)

            else:
                print("[INFO] Admin already has full strategy access!")
                return True

        elif response.status_code == 404:
            print("[WAIT] Endpoint not yet deployed - Render still deploying...")
            return False
        elif response.status_code == 405:
            print("[WAIT] Method not allowed - Render still deploying...")
            return False
        else:
            print(f"[ERROR] Unexpected response: {response.status_code}")
            print(response.text)

    except Timeout as e:
        print(f"[ERROR] Endpoint test timeout: {e}")
    except Exception as e:
        print(f"[ERROR] Endpoint test failed: {e}")

    return False

if __name__ == "__main__":
    print("Waiting for Render deployment to complete...")

    # Try multiple times as Render deployment takes a few minutes
    max_attempts = 5
    for attempt in range(max_attempts):
        print(f"\nAttempt {attempt + 1}/{max_attempts}")

        success = test_enterprise_deployment()
        if success:
            break

        if attempt < max_attempts - 1:
            print("Waiting 30 seconds before retry...")
            time.sleep(30)

    if not success:
        print("\n[INCOMPLETE] Deployment may still be in progress")
        print("Try running this script again in a few minutes")