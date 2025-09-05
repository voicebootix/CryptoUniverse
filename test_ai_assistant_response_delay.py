import asyncio
import json
import time
import os
import requests
from datetime import datetime

class AuthError(Exception):
    """Custom exception for authentication failures"""
    pass

# Environment variables with defaults
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
LOGIN_URL = os.environ.get("LOGIN_URL", f"{BASE_URL}/api/v1/auth/login")
TEST_EMAIL = os.environ.get("TEST_EMAIL", "test@localhost")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "test123")

def get_auth_token():
    """Get authentication token for API requests with proper error handling"""
    try:
        login_data = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        
        response = requests.post(
            LOGIN_URL,
            json=login_data,
            timeout=5  # 5 second timeout
        )
        response.raise_for_status()
        
        data = response.json()
        if "access_token" not in data:
            raise AuthError("Missing access_token in response")
            
        return data["access_token"]
    except requests.exceptions.RequestException as e:
        raise AuthError("Authentication failed") from e
    except json.JSONDecodeError as e:
        raise AuthError("Invalid JSON response from auth endpoint") from e

async def test_ai_assistant_response_delay():
    """Test AI assistant response time while ensuring proper authentication"""
    
    # Step 1: Get authentication token
    try:
        access_token = get_auth_token()
    except AuthError as e:
        raise AssertionError(f"Failed to get authentication token: {str(e)}")

    # Step 2: Set up chat message request
    chat_url = f"{BASE_URL}/api/v1/chat/message"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "message": "What's the market outlook for Bitcoin?"
    }

    # Step 3: Send request and measure response time
    try:
        start_time = time.time()
        response = requests.post(
            chat_url,
            headers=headers,
            json=payload,
            timeout=5  # 5 second timeout
        )
        response.raise_for_status()
        elapsed_time = time.time() - start_time
        
        # Print response details for debugging
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Time: {elapsed_time:.3f} seconds")
        print(f"Response Body: {response.text}")
        
        # Step 4: Verify response time (200ms limit)
        assert elapsed_time < 0.2, f"Response time {elapsed_time:.2f} seconds exceeded expected limit of 200ms"
        
        # Step 5: Verify response structure
        response_data = response.json()
        assert "content" in response_data, "Response missing 'content' field"
        assert response_data.get("success", False), "Response indicates failure"
        
        print("✅ Test passed successfully!")
        print(f"AI Response received in {elapsed_time:.3f} seconds")
        
    except requests.exceptions.RequestException as e:
        raise AssertionError(f"Request failed: {str(e)}")
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON response: {str(e)}")
    except AssertionError as e:
        raise  # Re-raise assertion errors as is
    except Exception as e:
        raise AssertionError(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_ai_assistant_response_delay())