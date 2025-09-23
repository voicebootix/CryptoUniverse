#!/usr/bin/env python3
"""
Test Actual Chat Endpoints with Admin Credentials
Based on the real endpoints found in the codebase
"""

import requests
import json
import sys
import time

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def test_actual_chat_endpoints():
    """Test actual chat endpoints based on router analysis"""

    print("CryptoUniverse ACTUAL Chat Endpoints Test")
    print("=" * 60)
    print(f"URL: {BASE_URL}")
    print(f"Admin: {ADMIN_EMAIL}")
    print()

    session = requests.Session()
    session_id = None

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
            print(f"Token: {access_token[:50]}...")
        else:
            print(f"[FAIL] Authentication failed: {login_response.status_code}")
            print(f"Response: {login_response.text}")
            return

    except Exception as e:
        print(f"[FAIL] Authentication error: {str(e)}")
        return

    # Step 2: Test Unified Chat Endpoints (Primary)
    print("\nStep 2: Testing Unified Chat Endpoints (/chat)...")

    unified_chat_tests = [
        {
            "method": "GET",
            "path": "/chat/capabilities",
            "name": "Chat Capabilities",
            "description": "Get chat system capabilities"
        },
        {
            "method": "GET",
            "path": "/chat/sessions",
            "name": "Chat Sessions",
            "description": "Get user chat sessions"
        },
        {
            "method": "POST",
            "path": "/chat/message",
            "name": "Send Chat Message",
            "description": "Send a message to the unified chat system",
            "payload": {
                "message": "Hello! I'm testing the CryptoUniverse chat system. Can you tell me about the current market?",
                "context": "general"
            }
        },
    ]

    # Step 3: Test Conversational Chat Compatibility
    print("\nStep 3: Testing Conversational Chat Compatibility (/conversational-chat)...")

    conversational_tests = [
        {
            "method": "POST",
            "path": "/conversational-chat/message",
            "name": "Conversational Chat Message",
            "description": "Send message via conversational chat endpoint",
            "payload": {
                "message": "What are the best trading strategies for Bitcoin?",
                "context": "trading"
            }
        },
    ]

    # Step 4: Test AI Chat Endpoints
    print("\nStep 4: Testing AI Chat Integration...")

    ai_chat_tests = [
        {
            "method": "POST",
            "path": "/ai-chat/conversational",
            "name": "AI Conversational Chat",
            "description": "Test AI conversational endpoint",
            "payload": {
                "message": "Analyze the cryptocurrency market trends",
                "context": "market_analysis"
            }
        },
    ]

    all_tests = unified_chat_tests + conversational_tests + ai_chat_tests
    results = []

    # Execute all tests
    for test_config in all_tests:
        method = test_config["method"]
        path = test_config["path"]
        name = test_config["name"]
        description = test_config.get("description", "")
        payload = test_config.get("payload")

        print(f"\nTesting: {name}")
        print(f"Description: {description}")
        print(f"Endpoint: {method} {path}")

        try:
            if method == "GET":
                response = session.get(f"{BASE_URL}{path}", timeout=60)
            elif method == "POST":
                response = session.post(f"{BASE_URL}{path}", json=payload, timeout=60)
            else:
                print(f"[SKIP] Unsupported method: {method}")
                continue

            success = response.status_code < 400
            status = "[PASS]" if success else "[FAIL]"

            print(f"{status} {name}: HTTP {response.status_code}")

            # Parse and display response
            try:
                response_data = response.json()

                if success:
                    if "response" in response_data:
                        # Chat response
                        chat_response = response_data["response"]
                        print(f"Chat Response: {chat_response[:200]}...")

                        # Extract session_id if available
                        if "session_id" in response_data and not session_id:
                            session_id = response_data["session_id"]
                            print(f"Session ID: {session_id}")

                    elif "sessions" in response_data:
                        # Sessions list
                        sessions = response_data["sessions"]
                        print(f"Found {len(sessions)} sessions")
                        if sessions and not session_id:
                            session_id = sessions[0].get("id")

                    elif "capabilities" in response_data:
                        # Capabilities
                        capabilities = response_data["capabilities"]
                        print(f"Capabilities: {list(capabilities.keys())}")

                    else:
                        # Generic success
                        print(f"Success: {response_data}")

                else:
                    # Error response
                    error_detail = response_data.get("detail", response_data)
                    print(f"Error: {error_detail}")

            except json.JSONDecodeError:
                print(f"Response (non-JSON): {response.text[:200]}...")

            results.append({
                "name": name,
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "success": success,
                "description": description
            })

        except Exception as e:
            print(f"[FAIL] {name}: {str(e)}")
            results.append({
                "name": name,
                "method": method,
                "path": path,
                "error": str(e),
                "success": False,
                "description": description
            })

    # Step 5: Test Chat History (if we have a session_id)
    if session_id:
        print(f"\nStep 5: Testing Chat History with session {session_id}...")

        history_tests = [
            {
                "method": "GET",
                "path": f"/chat/history/{session_id}",
                "name": "Chat History",
                "description": f"Get chat history for session {session_id}"
            }
        ]

        for test_config in history_tests:
            method = test_config["method"]
            path = test_config["path"]
            name = test_config["name"]

            print(f"\nTesting: {name}")
            print(f"Endpoint: {method} {path}")

            try:
                response = session.get(f"{BASE_URL}{path}", timeout=30)
                success = response.status_code < 400
                status = "[PASS]" if success else "[FAIL]"

                print(f"{status} {name}: HTTP {response.status_code}")

                if success:
                    history_data = response.json()
                    if "messages" in history_data:
                        messages = history_data["messages"]
                        print(f"Found {len(messages)} messages in history")
                    else:
                        print(f"History data: {history_data}")

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
                    "error": str(e),
                    "success": False
                })

    # Final Summary
    print("\n" + "=" * 60)
    print("COMPREHENSIVE CHAT TEST SUMMARY")
    print("=" * 60)

    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.get("success", False))
    failed_tests = total_tests - passed_tests

    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")

    print("\nTest Results by Category:")
    print("- Unified Chat (/chat): ", end="")
    unified_results = [r for r in results if "/chat" in r.get("path", "") and "/conversational-chat" not in r.get("path", "")]
    unified_passed = sum(1 for r in unified_results if r.get("success", False))
    print(f"{unified_passed}/{len(unified_results)} passed")

    print("- Conversational Chat (/conversational-chat): ", end="")
    conv_results = [r for r in results if "/conversational-chat" in r.get("path", "")]
    conv_passed = sum(1 for r in conv_results if r.get("success", False))
    print(f"{conv_passed}/{len(conv_results)} passed")

    print("- AI Chat (/ai-chat): ", end="")
    ai_results = [r for r in results if "/ai-chat" in r.get("path", "")]
    ai_passed = sum(1 for r in ai_results if r.get("success", False))
    print(f"{ai_passed}/{len(ai_results)} passed")

    if failed_tests > 0:
        print("\nFailed Tests Details:")
        for result in results:
            if not result.get("success", False):
                status_code = result.get("status_code", "N/A")
                error = result.get("error", f"HTTP {status_code}")
                print(f"  - {result['name']}: {error}")

    # Save detailed results
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"actual_chat_test_results_{timestamp}.json"

    with open(filename, "w") as f:
        json.dump({
            "test_summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": passed_tests/total_tests*100,
                "timestamp": timestamp,
                "admin_user": ADMIN_EMAIL,
                "base_url": BASE_URL,
                "session_id": session_id
            },
            "detailed_results": results
        }, f, indent=2)

    print(f"\nDetailed results saved to: {filename}")

    return passed_tests == total_tests

if __name__ == "__main__":
    success = test_actual_chat_endpoints()
    print(f"\nOverall Test Result: {'SUCCESS' if success else 'PARTIAL SUCCESS'}")
    sys.exit(0 if success else 1)