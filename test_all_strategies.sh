#!/bin/bash

echo "=== Testing All Strategy Scanners ==="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@cryptouniverse.com",
    "password": "AdminPass123!"
  }')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Test individual strategy executions
echo -e "\n1. Testing Risk Management Strategy..."
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function": "risk_management",
    "simulation_mode": true
  }' | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f\"Success: {data.get('success')}\")
if data.get('execution_result'):
    hedges = data['execution_result'].get('hedge_recommendations', [])
    print(f\"Hedge recommendations: {len(hedges)}\")
"

echo -e "\n2. Testing Portfolio Optimization Strategy..."
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function": "portfolio_optimization",
    "simulation_mode": true
  }' | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f\"Success: {data.get('success')}\")
if data.get('execution_result'):
    rebal = data['execution_result'].get('rebalancing_recommendations', [])
    print(f\"Rebalancing recommendations: {len(rebal)}\")
"

echo -e "\n3. Testing Options Trade Strategy..."
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function": "options_trade",
    "simulation_mode": true
  }' | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(f\"Success: {data.get('success')}\")
    if data.get('execution_result'):
        opps = data['execution_result'].get('opportunities', [])
        print(f\"Options opportunities: {len(opps)}\")
except:
    print('Error parsing response')
"

