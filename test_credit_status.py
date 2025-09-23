#!/usr/bin/env python3
"""
Simple test to check current credit status after final fix deployment
"""

import requests
import json

def test_credit_status():
    print("=== TESTING FINAL CREDIT FIX STATUS ===")

    session = requests.Session()

    # Login
    login_resp = session.post('https://cryptouniverse.onrender.com/api/v1/auth/login',
                            json={'email': 'admin@cryptouniverse.com', 'password': 'AdminPass123!'})

    if login_resp.status_code != 200:
        print(f"Login failed: {login_resp.status_code}")
        return

    token = login_resp.json()['access_token']
    session.headers.update({'Authorization': f'Bearer {token}'})

    print("1. Testing Credit API Endpoint:")
    api_resp = session.get('https://cryptouniverse.onrender.com/api/v1/credits/balance')
    if api_resp.status_code == 200:
        api_data = api_resp.json()
        print(f"   API Credits: {api_data['available_credits']} / {api_data['total_credits']}")
    else:
        print(f"   API Failed: {api_resp.status_code}")

    print("\n2. Testing Credit Balance Query via Chat:")
    chat_resp = session.post('https://cryptouniverse.onrender.com/api/v1/chat/message', json={
        'message': 'How many credits do I have?',
        'session_id': 'test-credit-query',
        'conversation_mode': 'general',
        'stream': False
    })

    if chat_resp.status_code == 200:
        content = chat_resp.json().get('content', '')
        print(f"   Chat Response: {content[:100]}...")

        # Check if it mentions real credits
        if '900' in content:
            print("   SUCCESS: Chat shows real credit balance!")
        elif '0' in content and 'credit' in content.lower():
            print("   ISSUE: Chat still shows 0 credits")
        else:
            print("   UNCLEAR: No clear credit info in response")
    else:
        print(f"   Chat Failed: {chat_resp.status_code}")

    print("\n3. Testing Strategy Query Status:")
    strategy_resp = session.post('https://cryptouniverse.onrender.com/api/v1/chat/message', json={
        'message': 'What Bitcoin trading strategies are available?',
        'session_id': 'test-strategy',
        'conversation_mode': 'live_trading',
        'stream': False
    })

    if strategy_resp.status_code == 200:
        print("   SUCCESS: Strategy queries working!")
    elif strategy_resp.status_code == 402:
        print("   EXPECTED: 402 Payment Required (credit check working)")
        error_data = strategy_resp.json()
        print(f"   Error: {error_data.get('detail', 'No detail')}")
    elif strategy_resp.status_code == 500:
        print("   ISSUE: Still getting 500 errors")
    else:
        print(f"   UNEXPECTED: {strategy_resp.status_code}")

if __name__ == "__main__":
    test_credit_status()