import os
import requests
import json
import pytest

def test_live_enterprise_endpoint():
    """Test enterprise endpoint with proper pytest assertions"""

    # Get configuration from environment
    base_url = os.getenv("ENTERPRISE_API_BASE", "https://cryptouniverse.onrender.com")
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")

    # Skip test if credentials not available
    if not email or not password:
        pytest.skip("ADMIN_EMAIL/ADMIN_PASSWORD not set; skipping live test")

    # Login
    login_url = f"{base_url}/api/v1/auth/login"
    login_payload = {"email": email, "password": password}

    response = requests.post(login_url, json=login_payload, timeout=15)

    # Assert successful login
    assert response.status_code == 200, f"Login failed with status {response.status_code}: {response.text}"

    data = response.json()
    token = data.get("access_token")

    # Assert token is valid
    assert token is not None, "Access token is missing from login response"
    assert len(token) > 10, "Access token appears to be invalid (too short)"

    headers = {"Authorization": f"Bearer {token}"}

    # Test endpoint availability
    status_url = f"{base_url}/api/v1/admin-strategy-access/admin-portfolio-status"
    response = requests.get(status_url, headers=headers, timeout=10)

    # Assert endpoint is available
    assert response.status_code in [200, 404], f"Unexpected status code {response.status_code}: {response.text}"

    if response.status_code == 200:
        # Test grant full access functionality
        grant_url = f"{base_url}/api/v1/admin-strategy-access/grant-full-access"
        grant_payload = {
            "strategy_type": "all",
            "grant_reason": "enterprise_admin_full_access_test"
        }

        grant_response = requests.post(grant_url, headers=headers, json=grant_payload, timeout=30)

        # Assert grant request was successful
        assert grant_response.status_code == 200, f"Grant failed with status {grant_response.status_code}: {grant_response.text}"

        result = grant_response.json()

        # Assert response structure
        assert "total_strategies" in result, "Response missing 'total_strategies' field"
        assert isinstance(result["total_strategies"], int), "'total_strategies' should be an integer"
        assert result["total_strategies"] > 0, "Should have granted at least one strategy"

    elif response.status_code == 404:
        pytest.skip("Enterprise endpoint not yet deployed - this is expected during development")

if __name__ == "__main__":
    test_live_enterprise_endpoint()