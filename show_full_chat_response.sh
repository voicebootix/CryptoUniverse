#!/bin/bash

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Get the best response
echo "=== CHAT RESPONSE WITH PORTFOLIO OPTIMIZATION DATA ==="
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/chat/message \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Find opportunities for me", "include_context": true}' | python3 -c "
import json, sys
data = json.load(sys.stdin)
response = data.get('response', data.get('content', ''))
print(response)
"

