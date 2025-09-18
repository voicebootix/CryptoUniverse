#!/bin/bash

echo "=== Checking Strategy ID Mapping ==="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Get user's actual strategies with IDs
curl -s -X GET https://cryptouniverse.onrender.com/api/v1/strategies/my-portfolio \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python3 -c "
import json, sys
data = json.load(sys.stdin)
strategies = data.get('strategies', [])
print('User strategies:')
for s in strategies:
    # Print all fields to see structure
    print(f'Strategy: {s}')
    print('---')
"

