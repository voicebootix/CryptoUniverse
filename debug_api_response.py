#!/usr/bin/env python3
"""
Debug API Response - See exactly what the chat API returns
"""

import requests
import json
import uuid

BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def debug_api_response():
    print("DEBUGGING CHAT API RESPONSE")
    print("=" * 50)

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
    print(f"Authenticated with session: {session_id[:8]}")

    # Test simple chat message
    print("\n2. Testing Chat Message...")
    payload = {
        "message": "Hello, what's my portfolio value?",
        "session_id": session_id,
        "conversation_mode": "live_trading",
        "stream": False,
        "context": {"debug": True}
    }

    print(f"Request payload:")
    print(json.dumps(payload, indent=2))

    try:
        response = session.post(f"{BASE_URL}/chat/message", json=payload, timeout=120)

        print(f"\n3. Response Analysis:")
        print(f"HTTP Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")

        # Get raw response text first
        raw_response = response.text
        print(f"\nRaw Response Text (first 500 chars):")
        print("-" * 50)
        print(raw_response[:500])
        print("-" * 50)

        # Try to parse as JSON
        try:
            json_response = response.json()
            print(f"\nParsed JSON Response:")
            print(json.dumps(json_response, indent=2, default=str))

            # Check for specific fields
            print(f"\n4. Field Analysis:")
            if isinstance(json_response, dict):
                for key, value in json_response.items():
                    value_preview = str(value)[:100] if value else "None/Empty"
                    print(f"  {key}: {value_preview}")

                # Look for common response field names
                possible_content_fields = ['content', 'response', 'message', 'text', 'reply', 'answer']
                print(f"\n5. Content Field Detection:")
                for field in possible_content_fields:
                    if field in json_response:
                        content = json_response[field]
                        if content:
                            print(f"  {field}: FOUND - {len(str(content))} chars")
                            print(f"    Preview: {str(content)[:200]}...")
                        else:
                            print(f"  {field}: FOUND but EMPTY")
                    else:
                        print(f"  {field}: NOT FOUND")

        except json.JSONDecodeError as e:
            print(f"\nJSON Parse Error: {e}")
            print("Response is not valid JSON")

    except Exception as e:
        print(f"Request failed: {str(e)}")

if __name__ == "__main__":
    debug_api_response()