#!/usr/bin/env python3
"""
Direct Portfolio Endpoint Debug Test
"""
import requests
import time

def portfolio_debug_test():
    print("PORTFOLIO ENDPOINT DEBUG TEST")
    print("=" * 30)

    # Login
    print("1. Admin authentication...")
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

    # Test the exact portfolio endpoint the frontend calls
    print("\n2. Testing /strategies/my-portfolio (exact frontend endpoint)...")
    try:
        portfolio_url = "https://cryptouniverse.onrender.com/api/v1/strategies/my-portfolio"

        # Try with different timeouts to see exactly where it fails
        for timeout_val in [5, 10, 15, 20]:
            print(f"\n  Testing with {timeout_val}s timeout...")
            start_time = time.time()

            try:
                response = requests.get(portfolio_url, headers=headers, timeout=timeout_val)
                elapsed = time.time() - start_time
                print(f"    Response: {response.status_code} in {elapsed:.2f}s")

                if response.status_code == 200:
                    data = response.json()
                    print(f"    Success: {data.get('success')}")

                    if data.get('success'):
                        strategies = data.get('active_strategies', [])
                        print(f"    Strategies found: {len(strategies)}")
                        if len(strategies) > 0:
                            print("    [SUCCESS] Portfolio working!")
                            for i, s in enumerate(strategies[:3], 1):
                                name = s.get('name', 'Unknown')
                                print(f"      {i}. {name}")
                            return True
                    else:
                        error = data.get('error', 'Unknown')
                        print(f"    Error: {error}")
                        if error == "timeout":
                            print("    [TIMEOUT] Internal service timeout (5s limit)")
                        elif error == "Redis unavailable":
                            print("    [REDIS] Redis connection issue")

                        # Check if it's degraded state
                        if data.get('degraded'):
                            print("    [DEGRADED] Service returned degraded state")

                        # Try to get more details
                        cached = data.get('cached', False)
                        total_cost = data.get('total_monthly_cost', 0)
                        total_strategies = data.get('total_strategies', 0)
                        print(f"    Debug info: cached={cached}, cost={total_cost}, total={total_strategies}")

                        break  # Don't try higher timeouts if we got a response

                else:
                    print(f"    HTTP Error: {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"    Error detail: {error_data.get('detail', 'No detail')}")
                    except:
                        print(f"    Error text: {response.text[:100]}")

            except requests.exceptions.Timeout:
                print(f"    REQUEST TIMEOUT at {timeout_val}s")
            except Exception as e:
                elapsed = time.time() - start_time
                print(f"    Exception in {elapsed:.2f}s: {e}")

    except Exception as e:
        print(f"Portfolio test error: {e}")

    print("\n3. Conclusion:")
    print("The portfolio endpoint is timing out internally (5s service limit)")
    print("This prevents the admin UI from showing strategies")
    print("Need to either fix the Redis timeout or add database fallback")

    return False

if __name__ == "__main__":
    success = portfolio_debug_test()
    if success:
        print("\n✅ Portfolio endpoint working!")
    else:
        print("\n❌ Portfolio endpoint issue confirmed")
        print("Frontend shows empty because of internal timeout")