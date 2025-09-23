#!/usr/bin/env python3
"""
Simple Chat Endpoints Test with Admin Credentials
"""

import requests
import json
import sys

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def test_chat_endpoints():
    """Test chat endpoints with admin credentials"""

    print("CryptoUniverse Chat Endpoints Test")
    print("=" * 50)
    print(f"URL: {BASE_URL}")
    print(f"Admin: {ADMIN_EMAIL}")
    print()

    session = requests.Session()

    # Step 1: Login
    print("Step 1: Authenticating...")
    try:
        login_response = session.post(
            f"{BASE_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=30
        )

        if login_response.status_code == 200:
            token_data = login_response.json()
            access_token = token_data.get("access_token")
            session.headers.update({"Authorization": f"Bearer {access_token}"})
            print("[PASS] Authentication successful")
        else:
            print(f"[FAIL] Authentication failed: {login_response.status_code}")
            print(f"Response: {login_response.text}")
            return

    except Exception as e:
        print(f"[FAIL] Authentication error: {str(e)}")
        return

    # Step 2: Test Chat Endpoints
    print("\nStep 2: Testing Chat Endpoints...")

    endpoints_to_test = [
        ("GET", "/chat", "Get Chat History"),
        ("GET", "/chat/conversations", "Get Conversations"),
        ("GET", "/chat/status", "Chat Status"),
        ("POST", "/chat/message", "Send Chat Message", {"message": "Hello, testing chat system"}),
        ("GET", "/ai-chat", "AI Chat Status"),
        ("POST", "/ai-chat/message", "AI Chat Message", {"message": "What is Bitcoin?"}),
    ]

    results = []

    for endpoint_data in endpoints_to_test:
        method = endpoint_data[0]
        path = endpoint_data[1]
        name = endpoint_data[2]
        payload = endpoint_data[3] if len(endpoint_data) > 3 else None

        print(f"\nTesting: {name} ({method} {path})")

        try:
            if method == "GET":
                response = session.get(f"{BASE_URL}{path}", timeout=30)
            elif method == "POST":
                response = session.post(f"{BASE_URL}{path}", json=payload, timeout=30)
            else:
                print(f"[SKIP] Unsupported method: {method}")
                continue

            success = response.status_code < 400
            status = "[PASS]" if success else "[FAIL]"

            print(f"{status} {name}: {response.status_code}")

            # Try to parse JSON response
            try:
                response_data = response.json()
                if success and isinstance(response_data, dict):
                    if "response" in response_data:
                        print(f"Response: {response_data['response'][:100]}...")
                    elif "message" in response_data:
                        print(f"Message: {response_data['message']}")
                else:
                    print(f"Error: {response_data}")
            except:
                print(f"Response text: {response.text[:100]}...")

            results.append({
                "name": name,
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "success": success
            })

        except Exception as e:
            print(f"[FAIL] {name}: {str(e)}")
            results.append({
                "name": name,
                "method": method,
                "path": path,
                "error": str(e),
                "success": False
            })

    # Step 3: Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)

    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.get("success", False))
    failed_tests = total_tests - passed_tests

    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")

    if failed_tests > 0:
        print("\nFailed Tests:")
        for result in results:
            if not result.get("success", False):
                print(f"  - {result['name']}: {result.get('status_code', 'Error')}")

    # Save results
    with open("chat_test_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nDetailed results saved to: chat_test_results.json")

    return passed_tests == total_tests

if __name__ == "__main__":
    success = test_chat_endpoints()
    sys.exit(0 if success else 1)