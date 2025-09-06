"""
Tests for data processing endpoints
"""

import pytest
import requests
import json
from typing import Dict, Any

def test_post_special_characters() -> None:
    """Test processing of special characters in POST requests."""
    
    url = "https://cryptouniverse.onrender.com/api/v1/data/process"
    headers = {
        "Content-Type": "application/json"
    }
    
    # Test cases with different special characters
    test_cases = [
        {
            "data": "@#$%^&*()_+==='/",
            "description": "Basic special characters"
        },
        {
            "data": "<test>special</test>",
            "description": "HTML-like content"
        },
        {
            "data": "Hello 世界",
            "description": "Unicode characters"
        },
        {
            "data": "javascript:alert(1)",
            "description": "Potential XSS content"
        },
        {
            "data": "' OR '1'='1",
            "description": "SQL injection attempt"
        }
    ]
    
    for test_case in test_cases:
        payload = {"data": test_case["data"]}
        
        try:
            print(f"\nTesting: {test_case['description']}")
            print(f"Input: {test_case['data']}")
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=5  # 5 second timeout
            )
            
            # Verify response
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            # Basic assertions
            assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
            
            response_data = response.json()
            assert "processed_data" in response_data, "Response missing processed_data field"
            assert "original_data" in response_data, "Response missing original_data field"
            assert response_data["status"] == "success", "Response status is not success"
            
            # Verify dangerous patterns are removed
            processed_data = response_data["processed_data"]
            assert "<script" not in processed_data.lower(), "Found script tag in processed data"
            assert "javascript:" not in processed_data.lower(), "Found javascript: in processed data"
            
            print("✅ Test passed")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {str(e)}")
            raise
        except AssertionError as e:
            print(f"❌ Assertion failed: {str(e)}")
            raise
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            raise

def test_error_handling() -> None:
    """Test error handling for invalid inputs."""
    
    url = "https://cryptouniverse.onrender.com/api/v1/data/process"
    headers = {
        "Content-Type": "application/json"
    }
    
    # Test cases with invalid inputs
    test_cases = [
        {
            # Missing data field
            "payload": {},
            "expected_status": 422
        },
        {
            # None value
            "payload": {"data": None},
            "expected_status": 422
        },
        {
            # Very long input
            "payload": {"data": "a" * 10000},
            "expected_status": 400
        }
    ]
    
    for test_case in test_cases:
        try:
            print(f"\nTesting error handling")
            print(f"Payload: {test_case['payload']}")
            
            response = requests.post(
                url,
                headers=headers,
                json=test_case["payload"],
                timeout=5
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            assert response.status_code == test_case["expected_status"], \
                f"Expected status code {test_case['expected_status']}, got {response.status_code}"
            
            response_data = response.json()
            assert "error" in response_data, "Error response missing error field"
            assert response_data["status"] == "error", "Error response status is not error"
            
            print("✅ Test passed")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {str(e)}")
            raise
        except AssertionError as e:
            print(f"❌ Assertion failed: {str(e)}")
            raise
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            raise

if __name__ == "__main__":
    print("\nRunning special characters tests...")
    test_post_special_characters()
    
    print("\nRunning error handling tests...")
    test_error_handling()
