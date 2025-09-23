#!/usr/bin/env python3
"""
Corrected Chat Endpoints Test with Proper Schema
Uses the actual UnifiedChatRequest schema from the codebase
"""

import requests
import json
import sys
import time
import uuid

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def test_corrected_chat_endpoints():
    """Test chat endpoints with correct payload schema"""

    print("CryptoUniverse CORRECTED Chat Endpoints Test")
    print("=" * 60)
    print(f"URL: {BASE_URL}")
    print(f"Admin: {ADMIN_EMAIL}")
    print()

    session = requests.Session()
    session_id = str(uuid.uuid4())

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
            print(f"Generated session ID: {session_id}")
        else:
            print(f"[FAIL] Authentication failed: {login_response.status_code}")
            print(f"Response: {login_response.text}")
            return

    except Exception as e:
        print(f"[FAIL] Authentication error: {str(e)}")
        return

    # Step 2: Test Chat Capabilities
    print("\nStep 2: Testing Chat Capabilities...")
    try:
        response = session.get(f"{BASE_URL}/chat/capabilities", timeout=30)
        if response.status_code == 200:
            capabilities = response.json()
            print("[PASS] Chat Capabilities:", capabilities.get("capabilities", []))
        else:
            print(f"[FAIL] Chat Capabilities: {response.status_code}")
    except Exception as e:
        print(f"[FAIL] Chat Capabilities error: {str(e)}")

    # Step 3: Test Chat Messages with Correct Schema
    print("\nStep 3: Testing Chat Messages with Correct Schema...")

    chat_tests = [
        {
            "name": "General Chat",
            "payload": {
                "message": "Hello! I'm testing the CryptoUniverse chat system.",
                "session_id": session_id,
                "conversation_mode": "learning",
                "stream": False,
                "context": {"test": True}
            }
        },
        {
            "name": "Portfolio Question",
            "payload": {
                "message": "Can you show me my portfolio performance?",
                "session_id": session_id,
                "conversation_mode": "live_trading",
                "stream": False,
                "context": {"type": "portfolio"}
            }
        },
        {
            "name": "Market Analysis",
            "payload": {
                "message": "What are the current Bitcoin trends?",
                "session_id": session_id,
                "conversation_mode": "analysis",
                "stream": False,
                "context": {"symbol": "BTC", "type": "analysis"}
            }
        },
        {
            "name": "Trading Strategy",
            "payload": {
                "message": "What trading strategies are available for altcoins?",
                "session_id": session_id,
                "conversation_mode": "live_trading",
                "stream": False,
                "context": {"type": "strategy"}
            }
        }
    ]

    results = []

    for test in chat_tests:
        name = test["name"]
        payload = test["payload"]

        print(f"\nTesting: {name}")
        print(f"Message: {payload['message'][:50]}...")
        print(f"Mode: {payload['conversation_mode']}")

        try:
            response = session.post(
                f"{BASE_URL}/chat/message",
                json=payload,
                timeout=90  # Longer timeout for AI responses
            )

            success = response.status_code < 400
            status = "[PASS]" if success else "[FAIL]"

            print(f"{status} {name}: HTTP {response.status_code}")

            if success:
                try:
                    response_data = response.json()

                    # Extract and display key information
                    if "response" in response_data:
                        chat_response = response_data["response"]
                        print(f"AI Response: {chat_response[:150]}...")

                    if "session_id" in response_data:
                        returned_session_id = response_data["session_id"]
                        print(f"Session ID: {returned_session_id}")

                    if "conversation_mode" in response_data:
                        mode = response_data["conversation_mode"]
                        print(f"Mode: {mode}")

                    if "metadata" in response_data:
                        metadata = response_data["metadata"]
                        print(f"Metadata: {list(metadata.keys())}")

                    results.append({
                        "name": name,
                        "status_code": response.status_code,
                        "success": True,
                        "has_response": "response" in response_data,
                        "response_length": len(response_data.get("response", "")),
                    })

                except json.JSONDecodeError:
                    print(f"Response (non-JSON): {response.text[:200]}...")
                    results.append({
                        "name": name,
                        "status_code": response.status_code,
                        "success": True,
                        "error": "Non-JSON response"
                    })

            else:
                # Handle error response
                try:
                    error_data = response.json()
                    error_detail = error_data.get("detail", error_data)
                    print(f"Error: {error_detail}")
                except:
                    print(f"Error (non-JSON): {response.text[:200]}...")

                results.append({
                    "name": name,
                    "status_code": response.status_code,
                    "success": False,
                    "error": response.text
                })

        except Exception as e:
            print(f"[FAIL] {name}: {str(e)}")
            results.append({
                "name": name,
                "success": False,
                "error": str(e)
            })

    # Step 4: Test Chat Sessions
    print(f"\nStep 4: Testing Chat Sessions...")
    try:
        response = session.get(f"{BASE_URL}/chat/sessions", timeout=30)
        if response.status_code == 200:
            sessions_data = response.json()
            print(f"[PASS] Chat Sessions: {response.status_code}")

            # Handle different response formats
            if isinstance(sessions_data, dict):
                if "sessions" in sessions_data:
                    sessions = sessions_data["sessions"]
                    print(f"Found {len(sessions)} sessions")
                else:
                    print(f"Sessions response: {sessions_data}")
            elif isinstance(sessions_data, list):
                print(f"Found {len(sessions_data)} sessions (direct list)")
            else:
                print(f"Sessions data type: {type(sessions_data)}")

        else:
            print(f"[FAIL] Chat Sessions: {response.status_code}")

    except Exception as e:
        print(f"[FAIL] Chat Sessions error: {str(e)}")

    # Step 5: Test Chat History
    print(f"\nStep 5: Testing Chat History for session {session_id[:8]}...")
    try:
        response = session.get(f"{BASE_URL}/chat/history/{session_id}", timeout=30)
        if response.status_code == 200:
            history_data = response.json()
            print(f"[PASS] Chat History: {response.status_code}")

            if "messages" in history_data:
                messages = history_data["messages"]
                print(f"Found {len(messages)} messages in history")
                for i, msg in enumerate(messages[:3]):  # Show first 3
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")[:50]
                    print(f"  {i+1}. {role}: {content}...")
            else:
                print(f"History data: {history_data}")

        else:
            print(f"[FAIL] Chat History: {response.status_code}")
            if response.status_code == 404:
                print("  (Session might not have history yet)")

    except Exception as e:
        print(f"[FAIL] Chat History error: {str(e)}")

    # Final Summary
    print("\n" + "=" * 60)
    print("CORRECTED CHAT TEST SUMMARY")
    print("=" * 60)

    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.get("success", False))
    failed_tests = total_tests - passed_tests

    print(f"Total Message Tests: {total_tests}")
    print(f"Successful: {passed_tests}")
    print(f"Failed: {failed_tests}")

    if total_tests > 0:
        success_rate = passed_tests / total_tests * 100
        print(f"Success Rate: {success_rate:.1f}%")
    else:
        success_rate = 0

    # Analyze response quality
    responses_with_content = sum(1 for r in results if r.get("has_response", False))
    if responses_with_content > 0:
        avg_response_length = sum(r.get("response_length", 0) for r in results) / responses_with_content
        print(f"Responses with content: {responses_with_content}")
        print(f"Average response length: {avg_response_length:.0f} characters")

    if failed_tests > 0:
        print("\nFailed Tests:")
        for result in results:
            if not result.get("success", False):
                error = result.get("error", f"HTTP {result.get('status_code', 'N/A')}")
                print(f"  - {result['name']}: {error[:100]}")

    # Save results
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"corrected_chat_test_results_{timestamp}.json"

    with open(filename, "w") as f:
        json.dump({
            "test_summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": success_rate,
                "responses_with_content": responses_with_content,
                "session_id": session_id,
                "timestamp": timestamp
            },
            "detailed_results": results
        }, f, indent=2)

    print(f"\nDetailed results saved to: {filename}")

    return success_rate >= 75  # Consider 75%+ success rate as overall success

if __name__ == "__main__":
    success = test_corrected_chat_endpoints()
    print(f"\nOverall Test Result: {'SUCCESS' if success else 'NEEDS IMPROVEMENT'}")
    sys.exit(0 if success else 1)