#!/usr/bin/env python3
"""
Test the specific credit fix to see if it resolves the 500 errors
"""

import requests
import json
import uuid

BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def test_credit_fix():
    print("=== TESTING CREDIT FIX ===")
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

    # Test specific query that should trigger credit check
    print("\n2. Testing Strategy Query (Should trigger credit check)...")

    payload = {
        "message": "What trading strategies are available for altcoins?",
        "session_id": session_id,
        "conversation_mode": "live_trading",  # This should trigger credit check
        "stream": False,
        "context": {"debug": True}
    }

    try:
        response = session.post(f"{BASE_URL}/chat/message", json=payload, timeout=30)

        print(f"HTTP Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            content = data.get("content", "")
            print(f"[SUCCESS] Content length: {len(content)}")
            print(f"Content preview: {content[:150]}...")

        elif response.status_code == 402:
            # Payment required - this means our credit fix worked!
            print("[EXPECTED] HTTP 402 - Payment Required (Credit fix working!)")
            try:
                error_data = response.json()
                print(f"Credit message: {error_data.get('detail', 'No detail')}")
            except:
                print(f"Raw response: {response.text}")

        elif response.status_code == 500:
            print("[FAIL] Still getting 500 error - fix didn't work or not deployed")
            try:
                error_data = response.json()
                print(f"Error: {error_data.get('detail', 'Unknown')}")
            except:
                print(f"Raw error: {response.text[:200]}")

        else:
            print(f"[UNEXPECTED] HTTP {response.status_code}")
            print(f"Response: {response.text[:200]}")

    except Exception as e:
        print(f"[EXCEPTION] {str(e)}")

    # Test with paper trading mode - should work
    print("\n3. Testing Strategy Query with Paper Trading Mode...")

    payload_paper = {
        "message": "What trading strategies are available for altcoins?",
        "session_id": session_id,
        "conversation_mode": "paper_trading",  # No credit check needed
        "stream": False,
        "context": {"debug": True}
    }

    try:
        response = session.post(f"{BASE_URL}/chat/message", json=payload_paper, timeout=30)

        print(f"HTTP Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            content = data.get("content", "")
            print(f"[SUCCESS] Paper trading works! Content length: {len(content)}")
            print(f"Content preview: {content[:150]}...")
        else:
            print(f"[FAIL] Paper trading also failing: {response.status_code}")
            print(f"Response: {response.text[:200]}")

    except Exception as e:
        print(f"[EXCEPTION] {str(e)}")

if __name__ == "__main__":
    test_credit_fix()