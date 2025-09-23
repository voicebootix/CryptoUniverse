#!/usr/bin/env python3
"""
Simple Debug - Test problematic queries with proper encoding
"""

import requests
import json
import uuid

BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def debug_simple():
    print("=== SIMPLE DEBUG TEST ===")
    print()

    session = requests.Session()
    session_id = str(uuid.uuid4())

    # Login
    print("1. Testing Authentication...")
    login_resp = session.post(f"{BASE_URL}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if login_resp.status_code != 200:
        print(f"[FAIL] Login failed: {login_resp.text}")
        return

    token = login_resp.json()["access_token"]
    session.headers.update({"Authorization": f"Bearer {token}"})
    print("[PASS] Authentication successful")

    # Test queries that fail vs work
    test_queries = [
        {
            "name": "Known Working Query",
            "message": "Hello, what's my portfolio value?",
            "mode": "live_trading",
            "expected": "SUCCESS"
        },
        {
            "name": "Known Failing Query - Strategy",
            "message": "What trading strategies are available for altcoins?",
            "mode": "live_trading",
            "expected": "FAIL_500"
        },
        {
            "name": "Known Failing Query - Analysis",
            "message": "Perform comprehensive technical analysis on Bitcoin using RSI, MACD, Bollinger Bands",
            "mode": "analysis",
            "expected": "FAIL_500"
        },
        {
            "name": "Simple Strategy Test",
            "message": "What strategies do you have?",
            "mode": "live_trading",
            "expected": "UNKNOWN"
        }
    ]

    results = []

    for i, query in enumerate(test_queries, 2):
        print(f"\n{i}. {query['name']}")
        print(f"   Message: {query['message'][:60]}...")
        print(f"   Expected: {query['expected']}")

        payload = {
            "message": query['message'],
            "session_id": session_id,
            "conversation_mode": query['mode'],
            "stream": False,
            "context": {"debug": True}
        }

        try:
            response = session.post(f"{BASE_URL}/chat/message", json=payload, timeout=120)

            result = {
                "name": query['name'],
                "expected": query['expected'],
                "status_code": response.status_code,
                "success": response.status_code == 200
            }

            if response.status_code == 200:
                data = response.json()
                content_length = len(data.get("content", ""))
                result["has_content"] = content_length > 0
                result["content_length"] = content_length
                print(f"   [SUCCESS] HTTP 200 - Content: {content_length} chars")
                if content_length > 50:
                    print(f"   Preview: {data['content'][:80]}...")

            elif response.status_code == 500:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("detail", "Unknown 500 error")
                    result["error"] = error_msg
                    print(f"   [500 ERROR] {error_msg}")
                except:
                    result["error"] = response.text[:100]
                    print(f"   [500 ERROR] Raw: {response.text[:100]}")

            else:
                result["error"] = f"HTTP {response.status_code}"
                print(f"   [ERROR] HTTP {response.status_code}")

            results.append(result)

        except requests.exceptions.Timeout:
            print(f"   [TIMEOUT] Request timed out")
            results.append({
                "name": query['name'],
                "expected": query['expected'],
                "error": "Timeout",
                "success": False
            })
        except Exception as e:
            print(f"   [EXCEPTION] {str(e)}")
            results.append({
                "name": query['name'],
                "expected": query['expected'],
                "error": str(e),
                "success": False
            })

    # Analysis
    print(f"\n=== RESULTS ANALYSIS ===")

    working_queries = [r for r in results if r.get("success", False)]
    failing_queries = [r for r in results if not r.get("success", False)]

    print(f"Working queries: {len(working_queries)}")
    print(f"Failing queries: {len(failing_queries)}")

    if failing_queries:
        print(f"\nFailure patterns:")
        for result in failing_queries:
            print(f"- {result['name']}: {result.get('error', 'Unknown error')}")

    # Pattern analysis
    strategy_queries = [r for r in results if "strateg" in r['name'].lower()]
    analysis_queries = [r for r in results if "analysis" in r['name'].lower()]

    strategy_fails = [r for r in strategy_queries if not r.get("success", False)]
    analysis_fails = [r for r in analysis_queries if not r.get("success", False)]

    print(f"\nPattern Analysis:")
    print(f"Strategy-related queries: {len(strategy_queries)} total, {len(strategy_fails)} failed")
    print(f"Analysis-related queries: {len(analysis_queries)} total, {len(analysis_fails)} failed")

    if len(strategy_fails) > 0 or len(analysis_fails) > 0:
        print(f"\nCONCLUSION: Specific intent types are failing consistently")
        print(f"Root cause likely in intent classification or context gathering for these types")
    else:
        print(f"\nCONCLUSION: Issues are not intent-specific, likely broader system issue")

if __name__ == "__main__":
    debug_simple()