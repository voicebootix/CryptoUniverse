#!/usr/bin/env python3
"""
Test Complex Trading Strategy Queries that Cause 500 Errors
"""

import requests
import json
import uuid

BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def test_complex_queries():
    print("=== TESTING COMPLEX QUERIES FOR 500 ERRORS ===")
    print()

    session = requests.Session()
    session_id = str(uuid.uuid4())

    # Login
    print("1. Authenticating...")
    login_resp = session.post(f"{BASE_URL}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if login_resp.status_code != 200:
        print(f"Login failed: {login_resp.text}")
        return

    token = login_resp.json()["access_token"]
    session.headers.update({"Authorization": f"Bearer {token}"})
    print(f"[OK] Authenticated. Session: {session_id[:8]}")

    # Complex queries that might cause 500 errors
    complex_queries = [
        {
            "name": "Simple Trading Strategy (Baseline)",
            "message": "What trading strategies are available for altcoins?",
            "mode": "live_trading",
            "complexity": "LOW"
        },
        {
            "name": "Multi-Asset DCA Strategy",
            "message": "Create a detailed DCA strategy for Bitcoin, Ethereum, and 3 altcoins with specific weekly amounts, risk management, stop-losses, and rebalancing rules for a $10,000 portfolio over 6 months.",
            "mode": "live_trading",
            "complexity": "HIGH"
        },
        {
            "name": "Advanced Portfolio Optimization",
            "message": "Analyze market correlations between BTC, ETH, ADA, DOT, LINK, UNI and create an optimized portfolio allocation using Modern Portfolio Theory with risk parity, momentum indicators, and automated rebalancing based on volatility bands.",
            "mode": "live_trading",
            "complexity": "VERY HIGH"
        },
        {
            "name": "Multi-Exchange Arbitrage",
            "message": "Identify arbitrage opportunities across Binance, Coinbase, and Kraken for the top 20 cryptocurrencies, calculate transaction costs, slippage, and create automated trading signals with risk controls.",
            "mode": "live_trading",
            "complexity": "EXTREME"
        },
        {
            "name": "Complex Technical Analysis",
            "message": "Perform comprehensive technical analysis on Bitcoin using RSI, MACD, Bollinger Bands, Fibonacci retracements, volume profile, order flow analysis, and on-chain metrics to generate trading signals for the next 30 days.",
            "mode": "analysis",
            "complexity": "VERY HIGH"
        }
    ]

    results = []

    for i, query in enumerate(complex_queries, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}: {query['name']} (Complexity: {query['complexity']})")
        print(f"{'='*80}")
        print(f"MESSAGE: {query['message'][:100]}...")
        print(f"MODE: {query['mode']}")
        print("-" * 80)

        payload = {
            "message": query['message'],
            "session_id": session_id,
            "conversation_mode": query['mode'],
            "stream": False,
            "context": {"complexity": query['complexity'].lower(), "test": "500_error_investigation"}
        }

        try:
            print("Sending request...")
            response = session.post(f"{BASE_URL}/chat/message", json=payload, timeout=180)  # 3 minute timeout

            print(f"HTTP STATUS: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                content = data.get("content", "")
                success = data.get("success", False)
                response_time = data.get("metadata", {}).get("response_time", 0)

                print(f"SUCCESS: {success}")
                print(f"RESPONSE TIME: {response_time:.2f}s")
                print(f"CONTENT LENGTH: {len(content)} characters")

                if content:
                    print(f"CONTENT PREVIEW: {content[:200]}...")
                else:
                    print("NO CONTENT")

                results.append({
                    "name": query['name'],
                    "complexity": query['complexity'],
                    "status_code": 200,
                    "success": True,
                    "content_length": len(content),
                    "response_time": response_time
                })

            elif response.status_code == 500:
                print("*** 500 INTERNAL SERVER ERROR DETECTED ***")
                try:
                    error_data = response.json()
                    print(f"Error Details: {json.dumps(error_data, indent=2)}")
                    error_msg = error_data.get("error", "Unknown server error")
                except:
                    error_msg = response.text[:500]
                    print(f"Raw Error Response: {error_msg}")

                results.append({
                    "name": query['name'],
                    "complexity": query['complexity'],
                    "status_code": 500,
                    "success": False,
                    "error": error_msg
                })

            else:
                print(f"OTHER ERROR: {response.status_code}")
                print(f"Response: {response.text[:300]}")

                results.append({
                    "name": query['name'],
                    "complexity": query['complexity'],
                    "status_code": response.status_code,
                    "success": False,
                    "error": response.text[:300]
                })

        except Exception as e:
            print(f"REQUEST EXCEPTION: {str(e)}")
            results.append({
                "name": query['name'],
                "complexity": query['complexity'],
                "success": False,
                "error": f"Exception: {str(e)}"
            })

    # Analysis
    print(f"\n{'='*80}")
    print("ERROR ANALYSIS SUMMARY")
    print(f"{'='*80}")

    total_tests = len(results)
    successful = sum(1 for r in results if r.get("success", False))
    errors_500 = sum(1 for r in results if r.get("status_code") == 500)
    other_errors = total_tests - successful - errors_500

    print(f"Total tests: {total_tests}")
    print(f"Successful: {successful}")
    print(f"500 errors: {errors_500}")
    print(f"Other errors: {other_errors}")

    if errors_500 > 0:
        print(f"\n*** QUERIES CAUSING 500 ERRORS: ***")
        for result in results:
            if result.get("status_code") == 500:
                print(f"- {result['name']} (Complexity: {result['complexity']})")
                error = result.get("error", "Unknown error")
                print(f"  Error: {error[:200]}...")

    print(f"\nCOMPLEXITY vs SUCCESS RATE:")
    complexity_levels = ["LOW", "HIGH", "VERY HIGH", "EXTREME"]
    for level in complexity_levels:
        level_results = [r for r in results if r.get("complexity") == level]
        if level_results:
            level_success = sum(1 for r in level_results if r.get("success", False))
            print(f"- {level}: {level_success}/{len(level_results)} successful")

    return results

if __name__ == "__main__":
    test_complex_queries()