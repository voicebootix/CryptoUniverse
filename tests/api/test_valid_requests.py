"""
Tests for validating API requests with proper authentication
"""

import base64
import json
import os
import requests
from typing import Dict, Any

# Environment variables with defaults
BASE_URL = os.environ.get("API_BASE_URL", "https://cryptouniverse.onrender.com")
TEST_USER = os.environ.get("TEST_USER", "test_user")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "test_password")

def get_auth_headers() -> Dict[str, str]:
    """
    Generate authentication headers with proper Base64 encoding.
    
    Returns:
        Dict containing properly formatted headers
    """
    # Create auth string and encode
    auth_string = f"{TEST_USER}:{TEST_PASSWORD}"
    auth_bytes = auth_string.encode('utf-8')
    auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
    
    return {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/json"
    }

def test_valid_post_request() -> None:
    """
    Test POST request with valid authentication and data.
    Verifies proper request processing and response handling.
    """
    try:
        # Setup
        url = f"{BASE_URL}/api/v1/test"
        headers = get_auth_headers()
        
        # Test payload
        payload = {
            "example_field": "example_value",
            "number_field": 42,
            "boolean_field": True
        }
        
        print("\nSending POST request...")
        print(f"URL: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        # Send request with timeout
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=5  # 5 second timeout
        )
        
        # Check response immediately
        response.raise_for_status()
        
        # Print response details
        print(f"\nResponse Status Code: {response.status_code}")
        print(f"Response Headers: {json.dumps(dict(response.headers), indent=2)}")
        print(f"Response Body: {response.text}")
        
        # Verify response
        assert response.status_code == 200, \
            f"Expected status code 200 but got {response.status_code}"
        
        # Parse and verify response data
        response_data = response.json()
        assert "status" in response_data, "Response missing 'status' field"
        assert response_data["status"] == "success", "Response status is not 'success'"
        
        print("\n✅ Test passed successfully!")
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {str(e)}")
        if hasattr(e.response, 'text'):
            print(f"Error response: {e.response.text}")
        raise
        
    except json.JSONDecodeError as e:
        print(f"\n❌ Invalid JSON response: {str(e)}")
        raise
        
    except AssertionError as e:
        print(f"\n❌ Assertion failed: {str(e)}")
        raise
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        raise

def test_invalid_auth() -> None:
    """
    Test request with invalid authentication.
    Verifies proper error handling for auth failures.
    """
    try:
        url = f"{BASE_URL}/api/v1/test"
        
        # Invalid auth headers
        invalid_headers = {
            "Authorization": "Basic invalid_token",
            "Content-Type": "application/json"
        }
        
        payload = {"test": "data"}
        
        print("\nTesting invalid authentication...")
        response = requests.post(
            url,
            headers=invalid_headers,
            json=payload,
            timeout=5
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        # Should get 401 Unauthorized
        assert response.status_code == 401, \
            f"Expected status code 401 but got {response.status_code}"
        
        print("\n✅ Invalid auth test passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        raise

def test_malformed_request() -> None:
    """
    Test handling of malformed requests.
    Verifies proper error responses for invalid data.
    """
    try:
        url = f"{BASE_URL}/api/v1/test"
        headers = get_auth_headers()
        
        # Test cases with invalid data
        test_cases = [
            {
                "payload": "invalid_json",
                "expected_status": 400,
                "description": "Invalid JSON"
            },
            {
                "payload": {"missing": "required_fields"},
                "expected_status": 400,
                "description": "Missing required fields"
            },
            {
                "payload": None,
                "expected_status": 400,
                "description": "Null payload"
            }
        ]
        
        for test_case in test_cases:
            print(f"\nTesting: {test_case['description']}")
            
            response = requests.post(
                url,
                headers=headers,
                json=test_case["payload"],
                timeout=5
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            assert response.status_code == test_case["expected_status"], \
                f"Expected status code {test_case['expected_status']} but got {response.status_code}"
        
        print("\n✅ Malformed request tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    print("Running API validation tests...")
    
    try:
        test_valid_post_request()
        test_invalid_auth()
        test_malformed_request()
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Tests failed: {str(e)}")
        raise
