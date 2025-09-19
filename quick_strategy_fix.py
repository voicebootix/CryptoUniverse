import requests
import json

def quick_strategy_fix():
    """Quick attempt to restore strategies via onboarding endpoint."""

    print("QUICK STRATEGY FIX ATTEMPT")
    print("=" * 30)

    # Login
    print("1. Logging in...")
    login_url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    login_payload = {
        "email": "admin@cryptouniverse.com",
        "password": "AdminPass123!"
    }

    response = requests.post(login_url, json=login_payload, timeout=10)
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        return False

    token = response.json().get("access_token")
    user_id = response.json().get("user_id")
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Logged in as: {user_id}")

    # Try onboarding complete
    print("\n2. Triggering onboarding...")
    try:
        onboard_url = "https://cryptouniverse.onrender.com/api/v1/users/complete-onboarding"
        response = requests.post(onboard_url, headers=headers, json={}, timeout=15)
        print(f"Onboarding response: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Onboarding failed: {e}")

    # Quick portfolio check
    print("\n3. Checking portfolio...")
    try:
        portfolio_url = "https://cryptouniverse.onrender.com/api/v1/strategies/my-portfolio"
        response = requests.get(portfolio_url, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            strategies = result.get('active_strategies', [])
            print(f"Strategies found: {len(strategies)}")
            if len(strategies) > 0:
                print("SUCCESS! Strategies are now available")
                for i, s in enumerate(strategies, 1):
                    print(f"  {i}. {s.get('name')} ({s.get('monthly_cost', 0)} credits)")
                return True
            else:
                print(f"Status: {result.get('success', False)}, Error: {result.get('error', 'None')}")
        else:
            print(f"Portfolio check failed: {response.status_code}")
    except Exception as e:
        print(f"Portfolio check error: {e}")

    return False

if __name__ == "__main__":
    success = quick_strategy_fix()
    if success:
        print("\n[FIXED] Strategy allocation restored!")
    else:
        print("\n[NEEDS WORK] Still need to fix strategy allocation")