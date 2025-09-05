"""
Tests for validating API response formats
"""

import json
import os
from datetime import datetime
import requests
from typing import Dict, Any

# Environment variables with defaults
BASE_URL = os.environ.get("API_BASE_URL", "https://cryptouniverse.onrender.com")
API_TOKEN = os.environ.get("API_TOKEN", "")

def get_auth_token() -> str:
    """Get valid authentication token."""
    if not API_TOKEN:
        # If no token in env, get one via login
        login_url = f"{BASE_URL}/api/v1/auth/login"
        login_data = {
            "email": os.environ.get("TEST_EMAIL", "test@cryptouniverse.com"),
            "password": os.environ.get("TEST_PASSWORD", "test123")
        }
        
        try:
            response = requests.post(
                login_url,
                json=login_data,
                timeout=5
            )
            response.raise_for_status()
            return response.json()["access_token"]
        except Exception as e:
            print(f"Failed to get auth token: {str(e)}")
            raise
    
    return API_TOKEN

def test_post_response_format() -> None:
    """
    Test POST request response format validation.
    Verifies that the API returns responses in the expected format.
    """
    try:
        # Setup proper endpoint URL
        url = f"{BASE_URL}/api/v1/data"
        
        # Get auth token and setup headers
        token = get_auth_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Test payload with all required fields
        payload = {
            "data": {
                "key": "test_value",
                "number": 42,
                "boolean": True,
                "timestamp": datetime.utcnow().isoformat()
            },
            "metadata": {
                "test_id": "response_format_test",
                "version": "1.0"
            }
        }
        
        print("\nSending POST request for format validation...")
        print(f"URL: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        # Send request with timeout
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=5
        )
        
        # Print response details
        print(f"\nResponse Status Code: {response.status_code}")
        print(f"Response Headers: {json.dumps(dict(response.headers), indent=2)}")
        print(f"Response Body: {response.text}")
        
        # Verify response status
        assert response.status_code == 200, \
            f"Expected status code 200 but got {response.status_code}"
        
        # Parse and validate JSON response
        try:
            json_response = response.json()
        except json.JSONDecodeError as e:
            print("Response is not valid JSON")
            print(f"Raw response: {response.text}")
            raise
        
        # Validate response format
        assert isinstance(json_response, dict), "Response should be a JSON object"
        
        # Required fields
        required_fields = ["status", "data", "timestamp"]
        for field in required_fields:
            assert field in json_response, f"Response missing required field: {field}"
        
        # Validate field types
        assert isinstance(json_response["status"], str), "status should be string"
        assert isinstance(json_response["data"], dict), "data should be object"
        assert isinstance(json_response["timestamp"], str), "timestamp should be string"
        
        # Validate status value
        assert json_response["status"] == "success", \
            f"Expected status 'success', got '{json_response['status']}'"
        
        # Validate data matches request
        response_data = json_response["data"]
        assert "key" in response_data, "Response data missing 'key' field"
        assert response_data["key"] == payload["data"]["key"], \
            "Response data does not match request data"
        
        print("\n✅ Response format validation passed!")
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Error response: {e.response.text}")
        raise
        
    except json.JSONDecodeError as e:
        print(f"\n❌ Invalid JSON response: {str(e)}")
        raise
        
    except AssertionError as e:
        print(f"\n❌ Format validation failed: {str(e)}")
        raise
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        raise

def test_error_response_format() -> None:
    """
    Test error response format validation.
    Verifies that error responses follow the expected format.
    """
    try:
        url = f"{BASE_URL}/api/v1/data"
        headers = {
            "Authorization": f"Bearer {get_auth_token()}",
            "Content-Type": "application/json"
        }
        
        # Invalid payload to trigger error
        invalid_payload = {
            "data": None  # Should cause validation error
        }
        
        print("\nTesting error response format...")
        response = requests.post(
            url,
            headers=headers,
            json=invalid_payload,
            timeout=5
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        # Should be 400 Bad Request
        assert response.status_code == 400, \
            f"Expected status code 400 but got {response.status_code}"
        
        # Validate error response format
        error_response = response.json()
        assert "error" in error_response, "Error response missing 'error' field"
        assert "status" in error_response, "Error response missing 'status' field"
        assert "timestamp" in error_response, "Error response missing 'timestamp' field"
        
        assert error_response["status"] == "error", \
            f"Expected status 'error', got '{error_response['status']}'"
        
        print("\n✅ Error response format validation passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    print("Running response format validation tests...")
    
    try:
        test_post_response_format()
        test_error_response_format()
        print("\n✅ All format validation tests passed!")
        
    except Exception as e:
        print(f"\n❌ Tests failed: {str(e)}")
        raise
