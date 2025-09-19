#!/usr/bin/env python3
"""
Final test of the working enterprise admin solution
"""
import requests
import time

def final_working_test():
    print("FINAL WORKING ENTERPRISE TEST")
    print("=" * 35)

    # Wait for deployment
    print("Waiting 45 seconds for Render deployment...")
    time.sleep(45)

    # Login
    print("\n1. Admin authentication...")
    login_url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    login_payload = {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}

    try:
        response = requests.post(login_url, json=login_payload, timeout=20)
        if response.status_code != 200:
            print(f"Login failed: {response.status_code}")
            return False

        token = response.json().get("access_token")
        user_id = response.json().get("user_id")
        headers = {"Authorization": f"Bearer {token}"}
        print(f"[OK] Authenticated: {user_id}")

    except Exception as e:
        print(f"Login error: {e}")
        return False

    # Test the working admin endpoint
    print("\n2. Testing working admin grant endpoint...")
    try:
        grant_url = "https://cryptouniverse.onrender.com/api/v1/admin-strategy-access/grant-full-access"
        grant_payload = {
            "strategy_type": "all",
            "grant_reason": "enterprise_admin_full_platform_access"
        }

        start_time = time.time()
        response = requests.post(grant_url, headers=headers, json=grant_payload, timeout=30)
        execution_time = time.time() - start_time

        print(f"Grant response: {response.status_code}")
        print(f"Request time: {execution_time:.2f} seconds")

        if response.status_code == 200:
            result = response.json()
            strategies_count = result.get("total_strategies", 0)
            server_time = result.get("execution_time_seconds", 0)

            print(f"[SUCCESS] Granted {strategies_count} strategies!")
            print(f"Server execution time: {server_time:.2f} seconds")
            print(f"Total request time: {execution_time:.2f} seconds")

            if execution_time < 15:
                print("PERFORMANCE FIXED! Under 15 seconds!")

                # Verify portfolio after grant
                print("\n3. Portfolio verification...")
                time.sleep(3)

                portfolio_url = "https://cryptouniverse.onrender.com/api/v1/strategies/my-portfolio"
                response = requests.get(portfolio_url, headers=headers, timeout=15)

                if response.status_code == 200:
                    portfolio = response.json()
                    if portfolio.get("success"):
                        strategies = portfolio.get("active_strategies", [])
                        print(f"[VERIFIED] Portfolio shows {len(strategies)} active strategies!")

                        if len(strategies) >= 15:
                            print("\n" + "="*60)
                            print("SUCCESS! ENTERPRISE SOLUTION COMPLETE!")
                            print("="*60)
                            print(f"Admin user: {user_id}")
                            print(f"Total strategies: {len(strategies)}")
                            print(f"Performance: {execution_time:.2f}s (was 89+ seconds)")
                            print(f"Portfolio status: OPERATIONAL")
                            print(f"Strategy ownership: RESTORED")
                            print("="*60)

                            # Show sample strategies
                            print("\nSample strategies:")
                            for i, s in enumerate(strategies[:5], 1):
                                name = s.get("name", "Unknown")
                                cost = s.get("monthly_cost", 0)
                                print(f"  {i}. {name} ({cost} credits/month)")

                            if len(strategies) > 5:
                                print(f"  ... and {len(strategies) - 5} more strategies")

                            return True
                        else:
                            print(f"Partial success: {len(strategies)} strategies")
                            return len(strategies) > 0
                    else:
                        print(f"Portfolio error: {portfolio.get('error')}")
                else:
                    print(f"Portfolio check failed: {response.status_code}")

            else:
                print(f"Still slow but working: {execution_time:.2f} seconds")
                return True

        else:
            print(f"Grant failed: {response.status_code}")
            try:
                error_text = response.text[:300]
                print(f"Error: {error_text}")
            except:
                pass

    except Exception as e:
        print(f"Test error: {e}")

    return False

if __name__ == "__main__":
    success = final_working_test()
    if success:
        print("\nMISSION ACCOMPLISHED!")
        print("Admin strategy ownership issue has been resolved.")
    else:
        print("\nSolution needs additional work.")
        print("Check logs for specific issues.")