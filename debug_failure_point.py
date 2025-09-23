#!/usr/bin/env python3
"""
Debug Failure Point - Test each step in the chat processing pipeline
"""

import asyncio
import requests
import json
import uuid
import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

async def debug_processing_pipeline():
    print("=== DEBUGGING CHAT PROCESSING PIPELINE ===")
    print()

    # Test the endpoint directly first
    session = requests.Session()
    session_id = str(uuid.uuid4())

    # Login
    print("1. Testing Authentication...")
    login_resp = session.post(f"{BASE_URL}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if login_resp.status_code != 200:
        print(f"❌ Login failed: {login_resp.text}")
        return

    token = login_resp.json()["access_token"]
    session.headers.update({"Authorization": f"Bearer {token}"})
    print("✅ Authentication successful")

    # Test the problematic queries
    test_queries = [
        {
            "name": "Simple Strategy Query (Known to fail)",
            "message": "What trading strategies are available for altcoins?",
            "mode": "live_trading"
        },
        {
            "name": "Complex Technical Analysis (Known to fail)",
            "message": "Perform comprehensive technical analysis on Bitcoin using RSI, MACD, Bollinger Bands",
            "mode": "analysis"
        },
        {
            "name": "Working Query (Control)",
            "message": "Hello, what's my portfolio value?",
            "mode": "live_trading"
        }
    ]

    for i, query in enumerate(test_queries, 2):
        print(f"\n{i}. Testing: {query['name']}")
        print(f"   Message: {query['message'][:50]}...")
        print(f"   Mode: {query['mode']}")

        payload = {
            "message": query['message'],
            "session_id": session_id,
            "conversation_mode": query['mode'],
            "stream": False,
            "context": {"debug": True, "test": "pipeline_debug"}
        }

        try:
            # Test with extended timeout to see if it's a timeout issue
            response = session.post(f"{BASE_URL}/chat/message", json=payload, timeout=300)  # 5 minutes

            print(f"   HTTP Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                content_length = len(data.get("content", ""))
                print(f"   ✅ SUCCESS - Content length: {content_length}")
                if content_length > 0:
                    print(f"   Content preview: {data['content'][:100]}...")
                else:
                    print("   ⚠️ Empty content but success=True")
            elif response.status_code == 500:
                print("   ❌ 500 ERROR")
                try:
                    error_data = response.json()
                    error_msg = error_data.get("detail", "Unknown error")
                    print(f"   Error: {error_msg}")
                except:
                    print(f"   Raw error: {response.text[:200]}")
            else:
                print(f"   ❌ OTHER ERROR: {response.status_code}")
                print(f"   Response: {response.text[:200]}")

        except requests.exceptions.Timeout:
            print("   ❌ REQUEST TIMEOUT (>5 minutes)")
        except Exception as e:
            print(f"   ❌ EXCEPTION: {str(e)}")

    print(f"\n=== TESTING CHAT AI SERVICE DIRECTLY ===")

    # Test if we can access the ChatAI service directly (requires server access)
    try:
        from app.services.chat_ai_service import chat_ai_service
        from app.core.config import get_settings

        settings = get_settings()
        print(f"OpenAI API Key present: {'Yes' if settings.OPENAI_API_KEY else 'No'}")
        print(f"Model: {getattr(settings, 'CHAT_AI_MODEL', 'gpt-4')}")

        # Test simple API call
        print("\nTesting direct ChatAI service call...")
        simple_response = await chat_ai_service.generate_response(
            prompt="Hello, this is a test",
            temperature=0.7
        )

        print(f"Direct API test result: {simple_response.get('success', False)}")
        if not simple_response.get('success', False):
            print(f"Direct API error: {simple_response.get('error', 'Unknown')}")

        # Test intent analysis specifically
        print("\nTesting intent analysis...")
        intent_response = await chat_ai_service.analyze_intent(
            message="What trading strategies are available for altcoins?",
            context={}
        )

        print(f"Intent analysis result: {intent_response.get('success', False)}")
        if not intent_response.get('success', False):
            print(f"Intent analysis error: {intent_response.get('error', 'Unknown')}")
        else:
            print(f"Detected intent: {intent_response.get('intent_data', {}).get('primary_intent', 'Unknown')}")

    except ImportError as e:
        print(f"Cannot import services (expected in external testing): {e}")
    except Exception as e:
        print(f"Error testing ChatAI service directly: {e}")

    print(f"\n=== ANALYSIS ===")
    print("If working queries succeed but strategy queries fail consistently,")
    print("the issue is likely in:")
    print("1. Intent classification for strategy-related queries")
    print("2. Context data gathering for strategy intents")
    print("3. OpenAI API rate limiting or content filtering")
    print("4. Specific prompt formatting for strategy queries")

if __name__ == "__main__":
    asyncio.run(debug_processing_pipeline())