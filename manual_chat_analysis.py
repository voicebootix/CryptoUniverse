#!/usr/bin/env python3
"""
Manual Deep Chat Analysis - Get Full Response Content
Analyze what the AI is actually saying vs what it should be saying
"""

import requests
import json
import uuid

BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def deep_chat_analysis():
    print("=== DEEP CHAT CONVERSATION ANALYSIS ===")
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

    # Test conversations with detailed analysis
    conversations = [
        {
            "name": "AI Money Manager Portfolio Check",
            "message": "As my AI money manager, please analyze my current portfolio and give me specific recommendations on what to buy, sell, or hold right now.",
            "mode": "live_trading",
            "expected": "Specific portfolio analysis, real holdings, actionable recommendations"
        },
        {
            "name": "Real-time Market Analysis",
            "message": "What's happening in the crypto markets right now? Give me real data on Bitcoin, Ethereum, and identify opportunities.",
            "mode": "analysis",
            "expected": "Current prices, trends, real market data, specific opportunities"
        },
        {
            "name": "Trading Strategy Implementation",
            "message": "I want to implement a DCA strategy for Bitcoin with $500 weekly. Set this up for me and explain the strategy.",
            "mode": "live_trading",
            "expected": "Strategy setup, execution details, risk parameters"
        },
        {
            "name": "Risk Management Query",
            "message": "My portfolio is down 15% this month. As my risk manager, what immediate actions should I take?",
            "mode": "live_trading",
            "expected": "Risk assessment, concrete actions, position adjustments"
        }
    ]

    for i, conv in enumerate(conversations, 1):
        print(f"\n{'='*60}")
        print(f"CONVERSATION {i}: {conv['name']}")
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
            "context": {"analysis_type": "deep", "user_role": "admin"}
        }

        try:
            response = session.post(f"{BASE_URL}/chat/message", json=payload, timeout=120)

            print(f"HTTP STATUS: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()

                    # Extract all response data
                    ai_response = data.get("response", "")
                    session_returned = data.get("session_id", "")
                    mode_returned = data.get("conversation_mode", "")
                    metadata = data.get("metadata", {})

                    print(f"SESSION ID: {session_returned}")
                    print(f"MODE RETURNED: {mode_returned}")
                    print(f"METADATA: {metadata}")

                    print("\n📤 AI RESPONSE:")
                    if ai_response:
                        print(f"Length: {len(ai_response)} characters")
                        print("-" * 40)
                        print(ai_response)
                        print("-" * 40)

                        # Analysis of response quality
                        print("\n🔍 RESPONSE ANALYSIS:")

                        # Check for real vs mock data indicators
                        real_data_indicators = ["$", "BTC", "ETH", "USD", "%", "price", "volume", "market cap"]
                        mock_indicators = ["sample", "example", "placeholder", "demo", "test", "mock"]

                        real_count = sum(1 for indicator in real_data_indicators if indicator.lower() in ai_response.lower())
                        mock_count = sum(1 for indicator in mock_indicators if indicator.lower() in ai_response.lower())

                        print(f"Real data indicators: {real_count}")
                        print(f"Mock data indicators: {mock_count}")

                        # Check for specific action recommendations
                        action_words = ["buy", "sell", "hold", "invest", "divest", "rebalance", "stop-loss", "take-profit"]
                        actions_found = [word for word in action_words if word.lower() in ai_response.lower()]
                        print(f"Action recommendations: {actions_found}")

                        # Check for AI money manager persona
                        manager_phrases = ["portfolio", "recommend", "strategy", "risk", "allocation", "diversification"]
                        manager_score = sum(1 for phrase in manager_phrases if phrase.lower() in ai_response.lower())
                        print(f"Money manager relevance score: {manager_score}/6")

                        # Overall assessment
                        if len(ai_response) < 50:
                            quality = "❌ TOO SHORT"
                        elif mock_count > real_count:
                            quality = "⚠️ MOSTLY MOCK DATA"
                        elif manager_score < 2:
                            quality = "⚠️ NOT ACTING AS MONEY MANAGER"
                        elif len(actions_found) == 0:
                            quality = "⚠️ NO ACTIONABLE ADVICE"
                        else:
                            quality = "✅ GOOD AI MONEY MANAGER RESPONSE"

                        print(f"QUALITY ASSESSMENT: {quality}")

                    else:
                        print("❌ NO AI RESPONSE CONTENT!")
                        print("This indicates the chat system accepted the request but failed to generate AI content")

                except json.JSONDecodeError as e:
                    print(f"❌ JSON Parse Error: {e}")
                    print(f"Raw response: {response.text}")

            else:
                print(f"❌ HTTP ERROR: {response.status_code}")
                print(f"Error response: {response.text}")

        except Exception as e:
            print(f"❌ EXCEPTION: {str(e)}")

    print(f"\n{'='*60}")
    print("OVERALL CHAT SYSTEM ANALYSIS")
    print(f"{'='*60}")

if __name__ == "__main__":
    deep_chat_analysis()