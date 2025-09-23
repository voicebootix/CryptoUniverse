#!/usr/bin/env python3
"""
Test portfolio balance to see if it's broken
"""

import requests
import re

def test_portfolio_balance():
    print("=== TESTING PORTFOLIO BALANCE ===")

    session = requests.Session()

    # Login
    login_resp = session.post('https://cryptouniverse.onrender.com/api/v1/auth/login',
                            json={'email': 'admin@cryptouniverse.com', 'password': 'AdminPass123!'})

    if login_resp.status_code != 200:
        print(f"Login failed: {login_resp.status_code}")
        return

    token = login_resp.json()['access_token']
    session.headers.update({'Authorization': f'Bearer {token}'})

    # Test portfolio API directly
    print("\n1. Testing Portfolio API directly:")
    portfolio_resp = session.get('https://cryptouniverse.onrender.com/api/v1/portfolio/summary')
    if portfolio_resp.status_code == 200:
        data = portfolio_resp.json()
        print(f"   API Total Value: ${data.get('total_value', 0):,.2f}")
        print(f"   API Cash Balance: ${data.get('cash_balance', 0):,.2f}")
    else:
        print(f"   API Failed: {portfolio_resp.status_code}")

    # Test portfolio via chat
    print("\n2. Testing Portfolio via Chat:")
    chat_resp = session.post('https://cryptouniverse.onrender.com/api/v1/chat/message', json={
        'message': 'What is my current portfolio balance?',
        'session_id': 'test-portfolio',
        'conversation_mode': 'general',
        'stream': False
    })

    if chat_resp.status_code == 200:
        content = chat_resp.json().get('content', '')
        print(f"   Chat Response: {content[:150]}...")

        # Look for dollar amounts
        amounts = re.findall(r'\$[\d,]+(?:\.\d{2})?', content)
        print(f"   Dollar amounts found: {amounts}")

        if '3700' in content or '3,700' in content:
            print("   SUCCESS: Shows real portfolio balance")
        elif '$0' in content or 'zero' in content.lower():
            print("   ISSUE: Shows $0 balance")
        else:
            print("   UNCLEAR: Balance not clear in response")
    else:
        print(f"   Chat Failed: {chat_resp.status_code}")

if __name__ == "__main__":
    test_portfolio_balance()