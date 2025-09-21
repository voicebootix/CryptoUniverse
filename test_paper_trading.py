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
print("TESTING PAPER TRADING SETUP")
print("=" * 60)

# Test 1: Check current status
print("\n1. CHECKING CURRENT STATUS:")
response = requests.get(f"{base_url}/paper-trading/status", headers=headers)
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print(f"Response: {json.dumps(response.json(), indent=2)}")
else:
    print(f"Error: {response.text[:200]}")

# Test 2: Setup paper trading
print("\n2. SETTING UP PAPER TRADING:")
setup_data = {
    "enable": True,
    "initial_balance": 10000
}
response = requests.post(f"{base_url}/paper-trading/setup", headers=headers, json=setup_data)
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print(f"Response: {json.dumps(response.json(), indent=2)}")
else:
    print(f"Error: {response.text}")

# Test 3: Get paper trading state
print("\n3. GETTING PAPER TRADING STATE:")
response = requests.get(f"{base_url}/paper-trading/state", headers=headers)
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print(f"Response: {json.dumps(response.json(), indent=2)[:500]}")
else:
    print(f"Error: {response.text[:200]}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)