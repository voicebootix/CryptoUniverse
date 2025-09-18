#!/bin/bash

echo "=== TESTING CHAT WITH PORTFOLIO OPTIMIZATION CONTEXT ==="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Test different chat messages
echo "1. Testing: 'find opportunities'"
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/chat/message \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "find opportunities", "include_context": true}' | python3 -c "
import json, sys
data = json.load(sys.stdin)
response = data.get('response', '')
print('Response length:', len(response))
print('Mentions portfolio?', 'portfolio' in response.lower())
print('Mentions strategies?', any(s in response.lower() for s in ['kelly', 'sharpe', 'risk parity']))
print()
if len(response) > 0:
    print('First 300 chars:')
    print(response[:300] + '...' if len(response) > 300 else response)
"

echo -e "\n2. Testing: 'show me portfolio optimization opportunities'"
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/chat/message \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "show me portfolio optimization opportunities", "include_context": true}' | python3 -c "
import json, sys
data = json.load(sys.stdin)
response = data.get('response', '')
metadata = data.get('metadata', {})
print('Response length:', len(response))
print('Intent:', data.get('intent', 'unknown'))
print('Context keys:', metadata.get('context_data_keys', []))
"

# Check what context is being passed
echo -e "\n3. Debug: Raw chat response for opportunity discovery"
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/chat/message \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What trading opportunities do you recommend?", "include_context": true}' | python3 -m json.tool | head -100

