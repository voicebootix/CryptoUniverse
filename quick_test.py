#!/usr/bin/env python3
"""
Quick test of the enterprise admin endpoint
"""
import requests
import time

def quick_test():
    print("QUICK ENTERPRISE ENDPOINT TEST")
    print("=" * 30)

    # Login
    print("1. Admin login...")
    login_url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    login_payload = {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}

    try:
        response = requests.post(login_url, json=login_payload, timeout=20)
        if response.status_code != 200:
            print(f"Login failed: {response.text}")
            return

        token = response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        print("[OK] Authenticated")

    except Exception as e:
        print(f"Login error: {e}")
        return

    # Quick endpoint test
    print("\n2. Testing admin endpoint...")
    try:
        status_url = "https://cryptouniverse.onrender.com/api/v1/admin-strategy-access/admin-portfolio-status"
        response = requests.get(status_url, headers=headers, timeout=20)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            print("[SUCCESS] Admin endpoint is LIVE!")
            status = response.json()
            print(f"Current strategies: {status.get('current_strategies', 0)}")
            print(f"Total available: {status.get('total_available_strategies', 0)}")

            # If not full access, grant it
            if status.get("current_strategies", 0) < 20:
                print("\n3. Granting full access...")
                grant_url = "https://cryptouniverse.onrender.com/api/v1/admin-strategy-access/grant-full-access"
                grant_payload = {
                    "strategy_type": "all",
                    "grant_reason": "final_test"
                }

                response = requests.post(grant_url, headers=headers, json=grant_payload, timeout=30)
                if response.status_code == 200:
                    result = response.json()
                    print(f"[SUCCESS] Granted {result.get('total_strategies')} strategies!")

                    # Quick portfolio check
                    print("\n4. Portfolio verification...")
                    time.sleep(2)

                    portfolio_url = "https://cryptouniverse.onrender.com/api/v1/strategies/my-portfolio"
                    response = requests.get(portfolio_url, headers=headers, timeout=15)

                    if response.status_code == 200:
                        portfolio = response.json()
                        if portfolio.get("success"):
                            strategies = portfolio.get("active_strategies", [])
                            print(f"[VERIFIED] Portfolio shows {len(strategies)} strategies!")

                            if len(strategies) >= 20:
                                print("\n" + "="*40)
                                print("SUCCESS! ENTERPRISE SOLUTION COMPLETE!")
                                print(f"Admin has {len(strategies)} strategies")
                                print("="*40)
                            else:
                                print(f"Partial success: {len(strategies)} strategies")
                        else:
                            print(f"Portfolio error: {portfolio.get('error')}")
                    else:
                        print(f"Portfolio check failed: {response.status_code}")

                else:
                    print(f"Grant failed: {response.status_code} - {response.text}")
            else:
                print("[INFO] Admin already has full access!")

        else:
            print(f"Endpoint not ready: {response.status_code}")

    except Exception as e:
        print(f"Test error: {e}")

if __name__ == "__main__":
    quick_test()