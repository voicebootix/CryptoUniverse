#!/usr/bin/env python3
"""
Check if admin user strategies were granted to Redis
"""
import requests

def redis_key_check():
    print("REDIS KEY CHECK")
    print("=" * 15)

    # Login
    login_url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    login_payload = {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}

    response = requests.post(login_url, json=login_payload, timeout=15)
    token = response.json().get("access_token")
    user_id = response.json().get("user_id")
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Admin user: {user_id}")

    # Check if the admin grant actually worked by looking at status
    print("\n1. Checking admin portfolio status...")
    try:
        status_url = "https://cryptouniverse.onrender.com/api/v1/admin-strategy-access/admin-portfolio-status"
        response = requests.get(status_url, headers=headers, timeout=15)

        if response.status_code == 200:
            data = response.json()
            print(f"  Success: {data.get('success')}")
            print(f"  Current strategies: {data.get('current_strategies', 0)}")
            print(f"  Total available: {data.get('total_available_strategies', 0)}")
            print(f"  Has full access: {data.get('has_full_access', False)}")
            print(f"  Portfolio status: {data.get('portfolio_status', 'unknown')}")
            print(f"  Portfolio error: {data.get('portfolio_error', 'none')}")

            if data.get('current_strategies', 0) > 0:
                print(f"  [SUCCESS] Admin has {data.get('current_strategies')} strategies!")
                return True
            else:
                print("  [ISSUE] Admin shows 0 strategies")
        else:
            print(f"  Status check failed: {response.status_code}")
    except Exception as e:
        print(f"  Error: {e}")

    return False

if __name__ == "__main__":
    success = redis_key_check()
    if success:
        print("\nAdmin has strategies - Redis grant worked!")
        print("Problem is the portfolio service timeout, not missing strategies")
    else:
        print("\nAdmin strategies missing - need to re-grant")