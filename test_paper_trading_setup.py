import json
import requests
import os
from datetime import datetime

# Environment variables with defaults
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
LOGIN_URL = os.environ.get("LOGIN_URL", f"{BASE_URL}/api/v1/auth/login")
TEST_EMAIL = os.environ.get("TEST_EMAIL", "test@localhost")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "test123")

class TestSetupError(Exception):
    """Custom exception for paper trading setup errors"""
    pass

def get_auth_token():
    """Get valid authentication token"""
    login_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    
    try:
        print("🔑 Getting authentication token...")
        response = requests.post(
            LOGIN_URL,
            json=login_data,
            timeout=5
        )
        response.raise_for_status()
        
        token_data = response.json()
        if "access_token" not in token_data:
            raise TestSetupError("Missing access_token in response")
            
        print("✅ Authentication successful")
        return token_data["access_token"]
    except requests.exceptions.RequestException as e:
        raise TestSetupError(f"Authentication failed: {str(e)}")
    except json.JSONDecodeError as e:
        raise TestSetupError(f"Invalid authentication response: {str(e)}")

def validate_paper_trading_response(response_data):
    """Validate paper trading setup response"""
    required_fields = ["success", "virtual_balance", "portfolio_id"]
    
    for field in required_fields:
        if field not in response_data:
            raise TestSetupError(f"Response missing required field: {field}")
    
    if not response_data["success"]:
        raise TestSetupError("Paper trading setup failed")
    
    if response_data["virtual_balance"] != 10000:
        raise TestSetupError(f"Incorrect virtual balance. Expected 10000, got {response_data['virtual_balance']}")

def test_setup_paper_trading_account():
    """Test paper trading account setup with proper authentication"""
    
    try:
        # Step 1: Get authentication token
        access_token = get_auth_token()
        
        # Step 2: Setup paper trading account
        print("\n📈 Setting up paper trading account...")
        setup_url = f"{BASE_URL}/api/v1/paper-trading/setup"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "virtual_balance": 10000,  # Starting balance
            "reset_portfolio": False,   # Don't reset if exists
            "test_mode": True          # Enable test mode
        }
        
        # Step 3: Send setup request
        response = requests.post(
            setup_url,
            headers=headers,
            json=payload,
            timeout=5
        )
        response.raise_for_status()
        
        # Print response details for debugging
        print(f"\nResponse Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        # Step 4: Parse and validate response
        response_data = response.json()
        validate_paper_trading_response(response_data)
        
        # Step 5: Verify paper trading account settings
        verify_url = f"{setup_url}/verify"
        verify_response = requests.get(
            verify_url,
            headers=headers,
            timeout=5
        )
        verify_response.raise_for_status()
        verify_data = verify_response.json()
        
        assert verify_data["is_active"], "Paper trading account not active"
        assert verify_data["virtual_balance"] == 10000, "Incorrect virtual balance"
        
        print("\n✅ Paper trading account setup successful!")
        print(f"🏦 Virtual Balance: ${verify_data['virtual_balance']:,}")
        print(f"📊 Portfolio ID: {verify_data.get('portfolio_id', 'N/A')}")
        
    except requests.exceptions.RequestException as e:
        raise TestSetupError(f"Request failed: {str(e)}")
    except json.JSONDecodeError as e:
        raise TestSetupError(f"Invalid JSON response: {str(e)}")
    except AssertionError as e:
        raise TestSetupError(f"Assertion failed: {str(e)}")
    except Exception as e:
        raise TestSetupError(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    try:
        test_setup_paper_trading_account()
    except TestSetupError as e:
        print(f"\n❌ Test failed: {str(e)}")
        raise
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        raise