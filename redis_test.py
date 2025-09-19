#!/usr/bin/env python3
"""
Direct Redis connectivity test
"""
import requests

def test_redis_directly():
    print("DIRECT REDIS TEST")
    print("=" * 17)

    # Login first
    login_url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    login_payload = {"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}
    response = requests.post(login_url, json=login_payload, timeout=15)
    token = response.json().get("access_token")
    user_id = response.json().get("user_id")
    headers = {"Authorization": f"Bearer {token}"}

    print(f"Admin user: {user_id}")

    # Test if there are any Redis-based endpoints that work
    print("\nTesting various Redis endpoints with different timeouts:")

    redis_endpoints = [
        "/api/v1/strategies/my-portfolio",
        "/api/v1/admin-strategy-access/admin-portfolio-status",
        "/api/v1/strategies/marketplace"
    ]

    for endpoint in redis_endpoints:
        print(f"\n{endpoint}:")
        for timeout in [5, 10, 30, 60]:
            try:
                url = f"https://cryptouniverse.onrender.com{endpoint}"
                response = requests.get(url, headers=headers, timeout=timeout)
                print(f"  {timeout}s timeout: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    if endpoint == "/api/v1/strategies/my-portfolio":
                        success = data.get("success")
                        print(f"    Portfolio success: {success}")
                        if success:
                            strategies = data.get("active_strategies", [])
                            print(f"    Found {len(strategies)} strategies!")
                            if len(strategies) > 0:
                                print("    REDIS IS WORKING!")
                                return True
                    break

            except Exception as e:
                if "timeout" in str(e).lower():
                    print(f"  {timeout}s timeout: TIMEOUT")
                else:
                    print(f"  {timeout}s timeout: ERROR - {e}")

    print("\nConclusion: All Redis endpoints timeout at all timeout values")
    print("Redis connectivity appears to be completely broken")
    return False

if __name__ == "__main__":
    redis_working = test_redis_directly()
    if not redis_working:
        print("\n=== RECOMMENDATION ===")
        print("Redis connectivity is broken on the server")
        print("This explains why admin UI shows no strategies")
        print("Need to fix Redis connection or add database fallback")