#!/usr/bin/env python3
"""
Deep test of portfolio balance issue
"""

import requests
import json
import re

def test_portfolio_deep():
    print("=== DEEP TESTING PORTFOLIO BALANCE ===")

    session = requests.Session()

    # Login
    login_resp = session.post('https://cryptouniverse.onrender.com/api/v1/auth/login',
                            json={'email': 'admin@cryptouniverse.com', 'password': 'AdminPass123!'})

    if login_resp.status_code != 200:
        print(f"Login failed: {login_resp.status_code}")
        return

    token = login_resp.json()['access_token']
    session.headers.update({'Authorization': f'Bearer {token}'})

    # Test 1: Direct trading API endpoint for portfolio
    print("\n1. Testing Trading Portfolio API:")
    trading_resp = session.get('https://cryptouniverse.onrender.com/api/v1/trading/portfolio')
    if trading_resp.status_code == 200:
        data = trading_resp.json()
        print(f"   Total Value: ${data.get('total_value_usd', 0):,.2f}")
        print(f"   Success: {data.get('success')}")
        print(f"   Balances: {len(data.get('balances', []))} assets")
        if data.get('balances'):
            for bal in data.get('balances', [])[:3]:
                print(f"   - {bal.get('asset')}: {bal.get('balance')} (${bal.get('value_usd', 0):,.2f})")
    else:
        print(f"   Failed: {trading_resp.status_code}")

    # Test 2: Portfolio via chat with different phrasings
    test_questions = [
        "What is my current portfolio balance?",
        "Show me my portfolio",
        "What's my portfolio worth?",
        "Portfolio summary"
    ]

    for i, question in enumerate(test_questions, 1):
        print(f"\n2.{i}. Testing: '{question}'")
        chat_resp = session.post('https://cryptouniverse.onrender.com/api/v1/chat/message', json={
            'message': question,
            'session_id': f'test-portfolio-{i}',
            'conversation_mode': 'general',
            'stream': False
        })

        if chat_resp.status_code == 200:
            content = chat_resp.json().get('content', '')
            print(f"   Response snippet: {content[:100]}...")

            # Look for dollar amounts
            amounts = re.findall(r'\$[\d,]+(?:\.\d{2})?', content)
            if amounts:
                print(f"   Dollar amounts found: {amounts[:5]}")

            # Check for known balance
            if any(x in content for x in ['3700', '3,700', '4007', '4,007']):
                print(f"   ✓ SUCCESS: Shows real portfolio balance!")
                break
            elif '$0' in content or 'zero' in content.lower():
                print(f"   ✗ ISSUE: Shows $0 balance")
            else:
                print(f"   ? UNCLEAR: Balance not clear in response")
        else:
            print(f"   Failed: {chat_resp.status_code}")
            if chat_resp.status_code == 500:
                print(f"   Error: {chat_resp.text[:200]}")

if __name__ == "__main__":
    test_portfolio_deep()