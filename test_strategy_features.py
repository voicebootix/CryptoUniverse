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

print("=" * 60)
print("TESTING STRATEGY IDE REAL FEATURES")
print("=" * 60)

# 1. Test Strategy IDE Endpoints
print("\n1. STRATEGY IDE - LIST USER STRATEGIES:")
response = requests.get(f"{base_url}/strategies/ide/list", headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)[:500]}")

# 2. Test Create Custom Strategy
print("\n2. CREATING CUSTOM STRATEGY:")
strategy_code = """
# Moving Average Crossover Strategy
def execute(data):
    fast_ma = data['close'].rolling(window=10).mean()
    slow_ma = data['close'].rolling(window=20).mean()

    if fast_ma.iloc[-1] > slow_ma.iloc[-1] and fast_ma.iloc[-2] < slow_ma.iloc[-2]:
        return {'signal': 'BUY', 'confidence': 0.8}
    elif fast_ma.iloc[-1] < slow_ma.iloc[-1] and fast_ma.iloc[-2] > slow_ma.iloc[-2]:
        return {'signal': 'SELL', 'confidence': 0.8}
    return {'signal': 'HOLD', 'confidence': 0.5}
"""

create_payload = {
    "name": "MA Crossover Test",
    "description": "Testing MA crossover in IDE",
    "code": strategy_code,
    "language": "python",
    "parameters": {
        "fast_period": 10,
        "slow_period": 20
    }
}

response = requests.post(f"{base_url}/strategies/ide/create", headers=headers, json=create_payload)
print(f"Status: {response.status_code}")
print(f"Response: {response.json() if response.status_code != 404 else 'Endpoint not found'}")

# 3. Test Backtesting
print("\n3. RUNNING BACKTEST:")
backtest_payload = {
    "strategy_name": "momentum_breakout",
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "start_date": (datetime.now() - timedelta(days=30)).isoformat(),
    "end_date": datetime.now().isoformat(),
    "initial_balance": 10000
}

response = requests.post(f"{base_url}/strategies/ide/backtest", headers=headers, json=backtest_payload)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    results = response.json()
    print(f"Backtest Results: {json.dumps(results, indent=2)[:500]}")

# 4. Test Live Performance
print("\n4. GETTING LIVE PERFORMANCE DATA:")
response = requests.get(f"{base_url}/strategies/ide/performance", headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    perf = response.json()
    print(f"Performance: {json.dumps(perf, indent=2)[:500]}")

# 5. Test Strategy Submission
print("\n5. SUBMITTING STRATEGY TO MARKETPLACE:")
submission_payload = {
    "strategy_id": "test_strategy",
    "title": "Test MA Strategy",
    "description": "A test moving average strategy",
    "price": 0,  # Free
    "tags": ["moving-average", "trend-following"]
}

response = requests.post(f"{base_url}/strategies/ide/submit", headers=headers, json=submission_payload)
print(f"Status: {response.status_code}")
print(f"Response: {response.json() if response.status_code != 404 else 'Endpoint not found'}")

# 6. Test Get Market Data
print("\n6. GETTING REAL-TIME MARKET DATA:")
response = requests.get(f"{base_url}/strategies/ide/market-data?symbol=BTC/USDT", headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    market = response.json()
    print(f"Market Data: {json.dumps(market, indent=2)[:500]}")

print("\n" + "=" * 60)
print("TEST COMPLETE - CHECK RESULTS ABOVE")
print("=" * 60)