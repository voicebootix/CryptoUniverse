import os
import requests
import json

# Timeout constant for all HTTP requests
REQUEST_TIMEOUT = 10  # seconds

# Configuration from environment variables
base_url = os.environ.get("CRYPTOUNIVERSE_BASE_URL", "https://cryptouniverse.onrender.com")
admin_email = os.environ.get("CRYPTOUNIVERSE_ADMIN_EMAIL")
admin_password = os.environ.get("CRYPTOUNIVERSE_ADMIN_PASSWORD")

if not admin_email or not admin_password:
    print("ERROR: Missing CRYPTOUNIVERSE_ADMIN_EMAIL or CRYPTOUNIVERSE_ADMIN_PASSWORD environment variables")
    print("Please set these environment variables for secure authentication")
    exit(1)

# Login endpoint
url = f"{base_url}/api/v1/auth/login"

# Admin credentials from environment
payload = {
    "email": admin_email,
    "password": admin_password
}

# Make the login request with timeout
response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)

# Assert successful login
assert response.status_code == 200, f"Login failed with status {response.status_code}: {response.text}"

data = response.json()
token = data.get("access_token")

# Assert token is present and valid (fail fast if missing)
assert token is not None, "Access token is missing from login response"
assert isinstance(token, str) and len(token) > 10, "Access token appears to be invalid"

print("Login successful - authentication token received")

# Now check strategies
headers = {"Authorization": f"Bearer {token}"}

# Get user strategies with timeout
strategies_url = f"{base_url}/api/v1/strategies/user"
strategies_response = requests.get(strategies_url, headers=headers, timeout=REQUEST_TIMEOUT)

print("\n=== User Strategies ===")
print(f"Status Code: {strategies_response.status_code}")

if strategies_response.status_code == 200:
    strategies = strategies_response.json()
    print(f"Total strategies: {len(strategies)}")
    for i, strategy in enumerate(strategies, 1):
        print(f"\nStrategy {i}:")
        print(f"  - ID: {strategy.get('id')}")
        print(f"  - Name: {strategy.get('name')}")
        print(f"  - Type: {strategy.get('type')}")
        print(f"  - Status: {strategy.get('status')}")
else:
    print(f"Error: {strategies_response.text}")