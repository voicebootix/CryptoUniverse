import requests
import json

def grant_admin_access():
    print("ENTERPRISE ADMIN STRATEGY GRANT")
    print("=" * 40)

    # Login
    print("\n1. Admin login...")
    login_url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    login_payload = {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}

    response = requests.post(login_url, json=login_payload, timeout=10)
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        return False

    token = response.json().get("access_token")
    user_id = response.json().get("user_id")
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[OK] Logged in as: {user_id}")

    # Grant full access
    print("\n2. Granting full strategy access...")
    grant_url = "https://cryptouniverse.onrender.com/api/v1/admin-strategy-access/grant-full-access"
    grant_payload = {
        "strategy_type": "all",
        "grant_reason": "admin_full_platform_access"
    }

    response = requests.post(grant_url, headers=headers, json=grant_payload, timeout=30)

    if response.status_code == 200:
        result = response.json()
        print(f"[SUCCESS] Granted {result.get('total_strategies')} strategies!")
        print(f"Grant type: {result.get('grant_type')}")
        print(f"Execution time: {result.get('execution_time_seconds', 0):.2f}s")

        # Show some strategies
        strategies = result.get('strategies_granted', [])[:5]
        print(f"\nSample strategies:")
        for i, s in enumerate(strategies, 1):
            print(f"  {i}. {s}")

    else:
        print(f"[ERROR] Grant failed: {response.status_code}")
        print(response.text)
        return False

    # Verify portfolio
    print("\n3. Verifying portfolio...")
    import time
    time.sleep(2)

    portfolio_url = "https://cryptouniverse.onrender.com/api/v1/strategies/my-portfolio"
    response = requests.get(portfolio_url, headers=headers, timeout=15)

    if response.status_code == 200:
        portfolio = response.json()
        if portfolio.get("success"):
            strategies = portfolio.get("active_strategies", [])
            print(f"[VERIFIED] Portfolio shows {len(strategies)} active strategies!")

            if len(strategies) >= 20:
                print("[SUCCESS] Admin now has full strategy access!")
                return True
            else:
                print(f"[WARNING] Expected more strategies, got {len(strategies)}")
        else:
            print(f"[ERROR] Portfolio degraded: {portfolio.get('error')}")
    else:
        print(f"[ERROR] Portfolio check failed: {response.status_code}")

    return False

if __name__ == "__main__":
    success = grant_admin_access()
    if success:
        print("\n" + "="*40)
        print("ENTERPRISE SOLUTION COMPLETE!")
        print("Admin has full strategy access")
    else:
        print("\nSolution incomplete - check logs")