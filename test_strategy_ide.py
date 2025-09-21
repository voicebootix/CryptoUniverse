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
print("TESTING STRATEGY IDE FEATURES")
print("=" * 60)

# 1. Test List Strategies
print("\n1. LISTING ALL STRATEGIES:")
response = requests.get(f"{base_url}/strategies/list", headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    strategies = response.json()
    print(f"Total strategies available: {len(strategies)}")
    for idx, strategy in enumerate(strategies[:3]):  # Show first 3
        print(f"  - {strategy.get('name', 'Unknown')}: {strategy.get('description', '')[:50]}...")

# 2. Test Market Data
print("\n2. GETTING REAL-TIME MARKET DATA:")
response = requests.get(f"{base_url}/strategies/market-data/BTC/USDT", headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"  BTC/USDT Price: ${data.get('price', 'N/A')}")
    print(f"  24h Change: {data.get('change_24h', 'N/A')}%")
    print(f"  Volume: ${data.get('volume', 'N/A')}")

# 3. Test Create Strategy
print("\n3. CREATING A NEW STRATEGY:")
new_strategy = {
    "name": "Test Moving Average Strategy",
    "description": "A simple MA crossover strategy for testing",
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "parameters": {
        "fast_ma": 10,
        "slow_ma": 20,
        "risk_percent": 2
    },
    "code": """
def execute(data, params):
    fast_ma = data['close'].rolling(params['fast_ma']).mean()
    slow_ma = data['close'].rolling(params['slow_ma']).mean()

    if fast_ma.iloc[-1] > slow_ma.iloc[-1]:
        return {'action': 'BUY', 'amount': params['risk_percent']}
    elif fast_ma.iloc[-1] < slow_ma.iloc[-1]:
        return {'action': 'SELL', 'amount': params['risk_percent']}
    return {'action': 'HOLD', 'amount': 0}
"""
}

response = requests.post(f"{base_url}/strategies/create", headers=headers, json=new_strategy)
print(f"Status: {response.status_code}")
if response.status_code in [200, 201]:
    result = response.json()
    strategy_id = result.get('id')
    print(f"  Strategy created successfully! ID: {strategy_id}")
else:
    print(f"  Error: {response.json()}")

# 4. Test Backtest
print("\n4. TESTING BACKTEST FUNCTIONALITY:")
backtest_params = {
    "strategy_id": "momentum_breakout",  # Using existing strategy
    "symbol": "BTC/USDT",
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "initial_capital": 10000
}

response = requests.post(f"{base_url}/strategies/backtest", headers=headers, json=backtest_params)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    results = response.json()
    print(f"  Total Return: {results.get('total_return', 'N/A')}%")
    print(f"  Sharpe Ratio: {results.get('sharpe_ratio', 'N/A')}")
    print(f"  Max Drawdown: {results.get('max_drawdown', 'N/A')}%")
    print(f"  Win Rate: {results.get('win_rate', 'N/A')}%")

# 5. Test Performance Analytics
print("\n5. GETTING PERFORMANCE ANALYTICS:")
response = requests.get(f"{base_url}/strategies/performance/momentum_breakout", headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    performance = response.json()
    print(f"  30-Day Return: {performance.get('return_30d', 'N/A')}%")
    print(f"  Total Trades: {performance.get('total_trades', 'N/A')}")
    print(f"  Success Rate: {performance.get('success_rate', 'N/A')}%")

# 6. Test Strategy Marketplace
print("\n6. CHECKING MARKETPLACE FEATURES:")
response = requests.get(f"{base_url}/strategies/marketplace", headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    marketplace = response.json()
    print(f"  Published Strategies: {marketplace.get('published_count', 'N/A')}")
    print(f"  Your Subscriptions: {marketplace.get('subscriptions', 'N/A')}")
    print(f"  Revenue Earned: ${marketplace.get('revenue', 'N/A')}")

# 7. Test Live Trading Status
print("\n7. CHECKING LIVE TRADING STATUS:")
response = requests.get(f"{base_url}/strategies/live-status", headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    status = response.json()
    print(f"  Active Strategies: {status.get('active_strategies', 'N/A')}")
    print(f"  Today's P&L: ${status.get('daily_pnl', 'N/A')}")
    print(f"  Open Positions: {status.get('open_positions', 'N/A')}")

print("\n" + "=" * 60)
print("STRATEGY IDE FEATURE TEST COMPLETE")
print("=" * 60)