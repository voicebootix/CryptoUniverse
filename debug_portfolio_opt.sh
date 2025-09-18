#!/bin/bash

echo "=== DEBUG PORTFOLIO OPTIMIZATION ==="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Check what strategies the user has
echo "1. User's strategies:"
curl -s -X GET https://cryptouniverse.onrender.com/api/v1/strategies/my-portfolio \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python3 -c "
import json, sys
data = json.load(sys.stdin)
strategies = data.get('strategies', [])
print(f'Total strategies: {len(strategies)}')
for s in strategies:
    print(f'  - {s.get(\"id\")}: {s.get(\"name\")} (active: {s.get(\"is_active\")})')
"

# Test direct portfolio optimization execution
echo -e "\n2. Direct portfolio optimization execution:"
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function": "portfolio_optimization",
    "symbol": "PORTFOLIO",
    "parameters": {}
  }' | python3 -m json.tool | head -50

# Check if ai_portfolio_optimization is in user's strategies
echo -e "\n3. Checking if ai_portfolio_optimization is provisioned:"
curl -s -X GET https://cryptouniverse.onrender.com/api/v1/strategies/my-portfolio \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python3 -c "
import json, sys
data = json.load(sys.stdin)
strategies = data.get('strategies', [])
has_portfolio_opt = any(s.get('id') == 'ai_portfolio_optimization' for s in strategies)
print(f'Has ai_portfolio_optimization: {has_portfolio_opt}')
print(f'Strategy IDs: {[s.get(\"id\") for s in strategies]}')
"

