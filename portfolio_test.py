#!/usr/bin/env python3
import requests

def test_portfolio_directly():
    print("DIRECT PORTFOLIO TEST")
    print("=" * 20)

    # Login
    print("1. Login...")
    login_url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    payload = {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}
    response = requests.post(login_url, json=payload, timeout=30)

    if response.status_code != 200:
        print(f"Login failed: {response.status_code}")
        return

    token = response.json().get('access_token')
    user_id = response.json().get('user_id')
    headers = {"Authorization": f"Bearer {token}"}
    print(f"   [OK] User: {user_id}")

    # Test portfolio directly
    print("\n2. Portfolio check...")
    try:
        portfolio_url = "https://cryptouniverse.onrender.com/api/v1/strategies/my-portfolio"
        response = requests.get(portfolio_url, headers=headers, timeout=30)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"   Success: {data.get('success')}")

            if data.get('success'):
                strategies = data.get('active_strategies', [])
                print(f"   Strategies: {len(strategies)}")

                if len(strategies) > 0:
                    print("   [SUCCESS] Portfolio working! Strategies found:")
                    for i, s in enumerate(strategies[:3], 1):
                        print(f"      {i}. {s.get('name', 'Unknown')}")
                else:
                    print("   [INFO] Portfolio working but no strategies")
            else:
                error = data.get('error', 'Unknown')
                print(f"   [ERROR] Portfolio degraded: {error}")
        else:
            print(f"   [ERROR] Request failed: {response.text[:100]}...")

    except Exception as e:
        print(f"   [ERROR] Exception: {e}")

if __name__ == "__main__":
    test_portfolio_directly()