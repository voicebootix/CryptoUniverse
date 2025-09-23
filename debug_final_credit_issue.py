#!/usr/bin/env python3
"""
Final Credit Issue Debug - Compare exactly what API vs Chat sees
"""

import requests
import jwt

def debug_credit_issue():
    print("=== FINAL CREDIT ISSUE DIAGNOSIS ===")

    session = requests.Session()

    # Login and get token
    login = session.post('https://cryptouniverse.onrender.com/api/v1/auth/login',
                        json={'email': 'admin@cryptouniverse.com', 'password': 'AdminPass123!'})

    if login.status_code != 200:
        print(f"Login failed: {login.status_code}")
        return

    token = login.json()['access_token']
    session.headers.update({'Authorization': f'Bearer {token}'})

    # Decode token to get user_id
    decoded = jwt.decode(token, options={'verify_signature': False})
    user_id = decoded.get('sub')

    print(f"User ID from token: {user_id}")
    print(f"User ID type: {type(user_id)}")

    # Test API endpoint
    print("\n1. CREDIT API ENDPOINT:")
    api_resp = session.get('https://cryptouniverse.onrender.com/api/v1/credits/balance')
    if api_resp.status_code == 200:
        api_data = api_resp.json()
        print(f"   Status: 200")
        print(f"   Available Credits: {api_data['available_credits']}")
        print(f"   Total Credits: {api_data['total_credits']}")
    else:
        print(f"   Status: {api_resp.status_code}")
        print(f"   Error: {api_resp.text[:100]}")

    # Test chat endpoint with explicit credit inquiry
    print("\n2. CHAT SERVICE CREDIT CHECK:")
    chat_resp = session.post('https://cryptouniverse.onrender.com/api/v1/chat/message', json={
        'message': 'Check my credit balance please',
        'session_id': 'debug-credit-session',
        'conversation_mode': 'live_trading',
        'stream': False
    })

    if chat_resp.status_code == 200:
        print(f"   Status: 200")
        content = chat_resp.json().get('content', '')

        # Look for numbers in the response
        import re
        numbers = re.findall(r'\d+', content)
        print(f"   Numbers in response: {numbers}")

        # Check for specific credit mentions
        if '900' in content or '1000' in content:
            print("   ✓ Shows real credit balance")
        elif '0' in content and 'credit' in content.lower():
            print("   ✗ Shows 0 credits")
        else:
            print("   ? Unclear credit information")

        print(f"   Content preview: {content[:200]}...")

    elif chat_resp.status_code == 402:
        print(f"   Status: 402 (Payment Required)")
        error = chat_resp.json().get('error', '')
        print(f"   Error: {error}")

        # Check what credit amount is mentioned in error
        if '0 credits' in error:
            print("   ✗ Chat service sees 0 credits")
        elif '900 credits' in error or '1000 credits' in error:
            print("   ✓ Chat service sees real credits")
    else:
        print(f"   Status: {chat_resp.status_code}")
        print(f"   Error: {chat_resp.text[:100]}")

    # Test strategy query which should trigger credit check
    print("\n3. STRATEGY QUERY (Triggers Credit Check):")
    strategy_resp = session.post('https://cryptouniverse.onrender.com/api/v1/chat/message', json={
        'message': 'What strategies are available for Bitcoin trading?',
        'session_id': 'debug-strategy-session',
        'conversation_mode': 'live_trading',
        'stream': False
    })

    if strategy_resp.status_code == 200:
        print("   Status: 200 - Strategy query succeeded")
        print("   ✓ Credit check passed")
    elif strategy_resp.status_code == 402:
        print("   Status: 402 - Blocked by credit check")
        error = strategy_resp.json().get('error', '')
        if '0 credits' in error:
            print("   ✗ Credit check sees 0 credits")
        elif '900 credits' in error or '1000 credits' in error:
            print("   ✓ Credit check sees real credits but blocks for other reason")
        print(f"   Error: {error[:150]}")

    print("\n=== DIAGNOSIS ===")
    print(f"API Credits: {api_data.get('available_credits', 'unknown') if api_resp.status_code == 200 else 'failed'}")
    print(f"Chat Status: {'Working' if chat_resp.status_code == 200 else 'Failed'}")
    print(f"Strategy Status: {'Working' if strategy_resp.status_code == 200 else 'Blocked'}")

    if api_resp.status_code == 200 and api_data['available_credits'] > 0:
        if chat_resp.status_code == 200 and '0' in chat_resp.json().get('content', ''):
            print("\nROOT CAUSE: Chat service still creates separate account")
            print("SOLUTION NEEDED: Fix database query or account lookup logic")
        elif strategy_resp.status_code == 402:
            print("\nROOT CAUSE: Credit check logic still broken")
            print("SOLUTION NEEDED: Debug credit check function implementation")

if __name__ == "__main__":
    debug_credit_issue()