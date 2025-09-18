#!/bin/bash

echo "=== TESTING CHAT DIRECTLY ==="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# First get opportunities directly
echo "1. Getting opportunities directly:"
OPPS=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/discover \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"scan_type": "comprehensive"}')

echo "$OPPS" | python3 -c "
import json, sys
data = json.load(sys.stdin)
portfolio_count = data.get('strategy_performance', {}).get('ai_portfolio_optimization', {}).get('count', 0)
print(f'Portfolio opportunities found: {portfolio_count}')
"

# Try simpler chat message
echo -e "\n2. Testing simple chat message:"
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/chat/message \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "hello"}' | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(f'Success: {data.get(\"success\", False)}')
    print(f'Error: {data.get(\"error\", \"None\")}')
    if data.get('response'):
        print(f'Response preview: {data[\"response\"][:100]}...')
except Exception as e:
    print(f'Parse error: {e}')
"

# Try without include_context
echo -e "\n3. Testing opportunity request without context:"
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/chat/message \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "find opportunities"}' | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(f'Success: {data.get(\"success\", False)}')
    response = data.get('response', '')
    if response:
        print(f'Response length: {len(response)}')
        print('Response preview:')
        print(response[:500] + '...' if len(response) > 500 else response)
except Exception as e:
    print(f'Parse error: {e}')
"

