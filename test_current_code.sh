#!/bin/bash

echo "=== Testing Current Deployed Code ==="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Test what error we get
echo "Testing portfolio optimization execution:"
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function": "portfolio_optimization",
    "symbol": "PORTFOLIO",
    "parameters": {}
  }' | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'Error: {data.get(\"error\", \"No error\")}')
print(f'Full response: {json.dumps(data, indent=2)}')
"

