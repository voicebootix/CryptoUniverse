#!/usr/bin/env python3
"""
Clean Chat Analysis - No emojis, focused on content analysis
"""

import requests
import json
import uuid

BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def analyze_chat_responses():
    print("=== CHAT RESPONSE ANALYSIS ===")
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

    # Test conversations
    conversations = [
        {
            "name": "Portfolio Analysis Request",
            "message": "As my AI money manager, analyze my current portfolio and give specific recommendations on what to buy, sell, or hold.",
            "mode": "live_trading",
            "expected": "Portfolio analysis with real data and actionable advice"
        },
        {
            "name": "Market Data Query",
            "message": "What's the current price of Bitcoin and Ethereum? Show me real market data and trends.",
            "mode": "analysis",
            "expected": "Real-time market data with current prices"
        },
        {
            "name": "Trading Strategy",
            "message": "I want to invest $1000 in crypto. Create a strategic allocation plan for me right now.",
            "mode": "live_trading",
            "expected": "Specific investment strategy with real allocations"
        },
        {
            "name": "Risk Assessment",
            "message": "My portfolio is down 20% this week. What should I do as a risk management strategy?",
            "mode": "live_trading",
            "expected": "Risk management with concrete actions"
        }
    ]

    analysis_results = []

    for i, conv in enumerate(conversations, 1):
        print(f"\n{'='*60}")
        print(f"TEST {i}: {conv['name']}")
        print(f"{'='*60}")
        print(f"MESSAGE: {conv['message']}")
        print(f"MODE: {conv['mode']}")
        print(f"EXPECTED: {conv['expected']}")
        print("-" * 60)

        payload = {
            "message": conv['message'],
            "session_id": session_id,
            "conversation_mode": conv['mode'],
            "stream": False,
            "context": {"analysis_type": "comprehensive", "user_role": "admin"}
        }

        try:
            response = session.post(f"{BASE_URL}/chat/message", json=payload, timeout=120)

            print(f"HTTP STATUS: {response.status_code}")

            if response.status_code == 200:
                data = response.json()

                # Extract response using correct field name
                ai_content = data.get("content", "")
                success = data.get("success", False)
                personality = data.get("metadata", {}).get("personality", "Unknown")
                response_time = data.get("metadata", {}).get("response_time", 0)

                print(f"SUCCESS: {success}")
                print(f"PERSONALITY: {personality}")
                print(f"RESPONSE TIME: {response_time:.2f}s")
                print(f"CONTENT LENGTH: {len(ai_content)} characters")

                print("\n--- AI RESPONSE CONTENT ---")
                if ai_content:
                    print(ai_content)
                else:
                    print("NO CONTENT FOUND")
                print("--- END RESPONSE ---")

                # Analyze response quality
                print("\n--- RESPONSE ANALYSIS ---")

                # Check for real vs mock data
                real_indicators = ["$", "BTC", "ETH", "USD", "%", "price", "current", "market"]
                mock_indicators = ["sample", "example", "placeholder", "demo", "test", "mock"]

                content_lower = ai_content.lower()
                real_count = sum(1 for word in real_indicators if word.lower() in content_lower)
                mock_count = sum(1 for word in mock_indicators if word.lower() in content_lower)

                print(f"Real data indicators: {real_count}")
                print(f"Mock data indicators: {mock_count}")

                # Check for actionable advice
                action_words = ["buy", "sell", "hold", "invest", "allocate", "rebalance", "stop", "recommend"]
                actions = [word for word in action_words if word.lower() in content_lower]
                print(f"Action words found: {actions}")

                # Check for specific amounts/percentages
                has_numbers = any(char.isdigit() for char in ai_content)
                has_percentages = "%" in ai_content
                has_dollar_amounts = "$" in ai_content

                print(f"Contains numbers: {has_numbers}")
                print(f"Contains percentages: {has_percentages}")
                print(f"Contains dollar amounts: {has_dollar_amounts}")

                # Overall quality assessment
                if len(ai_content) < 50:
                    quality = "TOO SHORT"
                elif mock_count > real_count:
                    quality = "MOSTLY MOCK DATA"
                elif not actions:
                    quality = "NO ACTIONABLE ADVICE"
                elif not has_numbers and conv['mode'] == 'live_trading':
                    quality = "LACKS SPECIFIC DATA"
                else:
                    quality = "GOOD AI MONEY MANAGER RESPONSE"

                print(f"QUALITY RATING: {quality}")

                analysis_results.append({
                    "name": conv['name'],
                    "success": success,
                    "content_length": len(ai_content),
                    "real_indicators": real_count,
                    "mock_indicators": mock_count,
                    "action_words": len(actions),
                    "has_numbers": has_numbers,
                    "quality_rating": quality,
                    "personality": personality,
                    "response_time": response_time
                })

            else:
                print(f"ERROR: {response.status_code}")
                print(f"Error response: {response.text}")

        except Exception as e:
            print(f"EXCEPTION: {str(e)}")

    # Summary analysis
    print(f"\n{'='*60}")
    print("COMPREHENSIVE ANALYSIS SUMMARY")
    print(f"{'='*60}")

    if analysis_results:
        avg_content_length = sum(r['content_length'] for r in analysis_results) / len(analysis_results)
        total_real_indicators = sum(r['real_indicators'] for r in analysis_results)
        total_mock_indicators = sum(r['mock_indicators'] for r in analysis_results)
        avg_response_time = sum(r['response_time'] for r in analysis_results) / len(analysis_results)

        print(f"Tests completed: {len(analysis_results)}")
        print(f"Average content length: {avg_content_length:.0f} characters")
        print(f"Average response time: {avg_response_time:.2f} seconds")
        print(f"Total real data indicators: {total_real_indicators}")
        print(f"Total mock data indicators: {total_mock_indicators}")

        quality_ratings = [r['quality_rating'] for r in analysis_results]
        good_responses = sum(1 for q in quality_ratings if "GOOD" in q)
        print(f"Good quality responses: {good_responses}/{len(analysis_results)}")

        print("\nDetailed Results:")
        for result in analysis_results:
            print(f"- {result['name']}: {result['quality_rating']} ({result['content_length']} chars, {result['response_time']:.1f}s)")

    else:
        print("No successful responses analyzed")

if __name__ == "__main__":
    analyze_chat_responses()