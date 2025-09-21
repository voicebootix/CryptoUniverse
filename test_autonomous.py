#!/usr/bin/env python3
import requests
import json

# Read token
with open('auth_token.txt', 'r') as f:
    token = f.read().strip()

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

base_url = "http://localhost:8000/api/v1"

print("=" * 60)
print("TESTING AUTONOMOUS MODE TOGGLE")
print("=" * 60)

# Test autonomous toggle endpoint - with correct path
print("\nTesting /trading/autonomous/toggle endpoint:")
data = {
    "enable": True,
    "mode": "balanced"
}

response = requests.post(f"{base_url}/trading/autonomous/toggle", headers=headers, json=data)
print(f"Status Code: {response.status_code}")

if response.status_code == 200:
    print(f"Response: {json.dumps(response.json(), indent=2)}")
elif response.status_code == 402:
    print("Error: Insufficient credits (need minimum 10 credits)")
    print(f"Response: {response.json()}")
else:
    print(f"Error: {response.text[:500]}")

print("\n" + "=" * 60)
