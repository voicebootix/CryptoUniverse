import requests
import json
import time

def test_enterprise_deployment():
    """Test if the enterprise admin endpoint is deployed and working."""

    print("TESTING ENTERPRISE DEPLOYMENT")
    print("=" * 35)

    # Login
    print("1. Admin authentication...")
    login_url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    login_payload = {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}

    try:
        response = requests.post(login_url, json=login_payload, timeout=10)
        if response.status_code != 200:
            print(f"[ERROR] Login failed: {response.text}")
            return False

        token = response.json().get("access_token")
        user_id = response.json().get("user_id")
        headers = {"Authorization": f"Bearer {token}"}
        print(f"[OK] Authenticated: {user_id}")

    except Exception as e:
        print(f"[ERROR] Login failed: {e}")
        return False

    # Test if new endpoint is available
    print("\n2. Testing enterprise endpoint availability...")
    try:
        status_url = "https://cryptouniverse.onrender.com/api/v1/admin-strategy-access/admin-portfolio-status"
        response = requests.get(status_url, headers=headers, timeout=10)

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
                grant_url = "https://cryptouniverse.onrender.com/api/v1/admin-strategy-access/grant-full-access"
                grant_payload = {
                    "strategy_type": "all",
                    "grant_reason": "enterprise_admin_privilege"
                }

                response = requests.post(grant_url, headers=headers, json=grant_payload, timeout=30)

                if response.status_code == 200:
                    result = response.json()
                    strategies_granted = result.get("total_strategies", 0)
                    print(f"[SUCCESS] Granted {strategies_granted} strategies!")
                    print(f"Execution time: {result.get('execution_time_seconds', 0):.2f}s")

                    # Wait for Redis sync
                    print("\n4. Verifying portfolio access...")
                    time.sleep(3)

                    portfolio_url = "https://cryptouniverse.onrender.com/api/v1/strategies/my-portfolio"
                    response = requests.get(portfolio_url, headers=headers, timeout=15)

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