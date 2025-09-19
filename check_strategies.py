import os
import requests
import json
from requests.exceptions import RequestException

# Get config from environment
base_url = os.environ.get("CRYPTOUNIVERSE_BASE_URL", "https://cryptouniverse.onrender.com")
email = os.environ.get("CRYPTOUNIVERSE_ADMIN_EMAIL")
password = os.environ.get("CRYPTOUNIVERSE_ADMIN_PASSWORD")

if not email or not password:
    print("ERROR: Missing CRYPTOUNIVERSE_ADMIN_EMAIL or CRYPTOUNIVERSE_ADMIN_PASSWORD environment variables")
    print("Set these environment variables or add them to your .env file")
    exit(1)

# Login endpoint
url = f"{base_url}/api/v1/auth/login"

# Admin credentials from environment
payload = {
    "email": email,
    "password": password
}

# Make the login request
try:
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()

    data = response.json()
    token = data.get("access_token")

    if not token:
        print("Authentication failed: No token received")
        exit(1)

    print(f"[OK] Logged in successfully as admin")
    # Never log tokens - only log success status

except RequestException as e:
    print(f"Login request failed: {e}")
    exit(1)
except json.JSONDecodeError as e:
    print(f"Login response JSON parsing failed: {e}")
    exit(1)

if token:

    headers = {"Authorization": f"Bearer {token}"}

    # Try different strategy endpoints
    endpoints = [
        "/api/v1/strategies",
        "/api/v1/strategies/my",
        "/api/v1/strategies/marketplace",
        "/api/v1/strategies/owned",
        "/api/v1/strategies/purchased",
        "/api/v1/portfolio/strategies"
    ]

    for endpoint in endpoints:
        endpoint_url = f"{base_url}{endpoint}"
        print(f"\n=== Testing {endpoint} ===")

        try:
            # Try GET request with timeout
            response = requests.get(endpoint_url, headers=headers, timeout=10)
            response.raise_for_status()
            print(f"GET Status: {response.status_code}")

            try:
                data = response.json()
                if isinstance(data, list):
                    print(f"Found {len(data)} strategies")
                    for i, strategy in enumerate(data[:5], 1):  # Show first 5
                        if isinstance(strategy, dict):
                            print(f"\n  Strategy {i}:")
                            for key in ['id', 'name', 'type', 'status', 'description']:
                                if key in strategy:
                                    print(f"    - {key}: {strategy[key]}")
                else:
                    print(f"Response: {json.dumps(data, indent=2)[:500]}")
                break  # Found working endpoint

            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                print(f"Raw response: {response.text[:200]}")

        except RequestException as e:
            print(f"Network error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code != 405:  # Ignore method not allowed
                    print(f"Error details: {e.response.text[:200]}")
else:
    print("Authentication token not available")