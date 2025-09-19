import os
import requests
import json

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

# Make the login request
response = requests.post(url, json=payload)

print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

if response.status_code == 200:
    data = response.json()
    token = data.get("access_token")
    if token:
        print(f"\nAccess Token: {token[:50]}...")

        # Now check strategies
        headers = {"Authorization": f"Bearer {token}"}

        # Get user strategies
        strategies_url = f"{base_url}/api/v1/strategies/user"
        strategies_response = requests.get(strategies_url, headers=headers)

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