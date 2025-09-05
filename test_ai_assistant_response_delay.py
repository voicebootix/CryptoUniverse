import json
import time
import requests
from datetime import datetime

def get_auth_token():
    """Get authentication token for API requests"""
    login_url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    login_data = {
        "email": "test@cryptouniverse.com",
        "password": "TestPassword123!"
    }
    
    try:
        login_response = requests.post(login_url, json=login_data)
        login_response.raise_for_status()  # Raise exception for non-200 status codes
        
        token_data = login_response.json()
        return token_data["access_token"]
    except requests.exceptions.RequestException as e:
        raise Exception(f"Authentication failed: {str(e)}")

def test_ai_assistant_response_delay():
    """Test AI assistant response time while ensuring proper authentication"""
    
    # Step 1: Get authentication token
    try:
        access_token = get_auth_token()
    except Exception as e:
        raise AssertionError(f"Failed to get authentication token: {str(e)}")

    # Step 2: Set up chat message request
    url = "https://cryptouniverse.onrender.com/api/v1/chat/message"
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
        response = requests.post(url, headers=headers, json=payload)
        elapsed_time = time.time() - start_time
        
        # Print response details for debugging
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Time: {elapsed_time:.3f} seconds")
        print(f"Response Body: {response.text}")
        
        # Step 4: Verify response status
        assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}. Response: {response.text}"
        
        # Step 5: Verify response time (200ms limit)
        # Note: Adding a bit of buffer for network latency
        assert elapsed_time < 0.2, f"Response time {elapsed_time:.2f} seconds exceeded expected limit of 200ms"
        
        # Step 6: Verify response structure
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
    test_ai_assistant_response_delay()
