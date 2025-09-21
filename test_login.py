#!/usr/bin/env python3
import requests
import json

base_url = "http://localhost:8000/api/v1"

print("=" * 60)
print("TESTING LOGIN")
print("=" * 60)

# Test login
print("\nTesting /auth/login endpoint:")
data = {
    "email": "admin@cryptouniverse.com", 
    "password": "AdminPass123!"
}

try:
    response = requests.post(
        f"{base_url}/auth/login", 
        json=data,
        timeout=10  # 10 second timeout
    )
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("Login successful!")
        print(f"Response: {json.dumps(response.json(), indent=2)[:500]}")
    else:
        print(f"Login failed: {response.text[:500]}")
except requests.Timeout:
    print("Request timed out after 10 seconds")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
