#!/usr/bin/env python3
import requests
import json
from datetime import datetime, timedelta

# Read token
with open('auth_token.txt', 'r') as f:
    token = f.read().strip()

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

base_url = "http://localhost:8000/api/v1"

print("=" * 70)
print("TESTING BACKTEST WITH DIFFERENT APPROACHES")
print("=" * 70)

# Test 1: Simple backtest with minimal params
print("\n1. SIMPLE BACKTEST TEST:")
simple_payload = {
    "symbol": "BTC/USDT",
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "initial_capital": 10000
}

response = requests.post(f"{base_url}/strategies/backtest", headers=headers, json=simple_payload)
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)[:500]}")

# Test 2: With strategy code
print("\n2. BACKTEST WITH CUSTOM CODE:")
code_payload = {
    "symbol": "ETH/USDT",
    "start_date": "2024-01-01",
    "end_date": "2024-01-15",
    "initial_capital": 5000,
    "code": """
def execute(data):
    # Simple MA crossover
    if len(data) < 20:
        return {'signal': 'HOLD'}
    ma_short = data['close'][-10:].mean()
    ma_long = data['close'][-20:].mean()

    if ma_short > ma_long:
        return {'signal': 'BUY'}
    elif ma_short < ma_long:
        return {'signal': 'SELL'}
    return {'signal': 'HOLD'}
"""
}

response = requests.post(f"{base_url}/strategies/backtest", headers=headers, json=code_payload)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    if 'backtest_result' in result:
        br = result['backtest_result']
        print(f"Total Return: {br.get('total_return', 'N/A')}%")
        print(f"Sharpe Ratio: {br.get('sharpe_ratio', 'N/A')}")
        print(f"Win Rate: {br.get('win_rate', 'N/A')}%")
else:
    print(f"Error: {response.text[:200]}")

# Test 3: Check auth directly
print("\n3. CHECKING AUTH STATUS:")
response = requests.get(f"{base_url}/auth/me", headers=headers)
print(f"Auth Status: {response.status_code}")
if response.status_code == 200:
    user = response.json()
    print(f"User: {user.get('email', 'Unknown')}")
    print(f"Role: {user.get('role', 'Unknown')}")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)