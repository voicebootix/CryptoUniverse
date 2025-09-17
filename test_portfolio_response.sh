#!/bin/bash

echo "=== Testing Strategy Portfolio Response ==="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@cryptouniverse.com",
    "password": "AdminPass123!"
  }')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Test strategy portfolio endpoint directly
echo -e "\n1. Testing strategy portfolio endpoint..."
PORTFOLIO_RESPONSE=$(curl -s -X GET https://cryptouniverse.onrender.com/api/v1/strategies/portfolio \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "Portfolio Response:"
echo "$PORTFOLIO_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$PORTFOLIO_RESPONSE"

# Check the structure
if echo "$PORTFOLIO_RESPONSE" | grep -q '"strategies":\['; then
    echo -e "\nFound 'strategies' key in response"
fi

if echo "$PORTFOLIO_RESPONSE" | grep -q '"active_strategies":\['; then
    echo -e "\nFound 'active_strategies' key in response"
fi

if echo "$PORTFOLIO_RESPONSE" | grep -q '"success":true'; then
    echo -e "\nFound 'success:true' in response"
fi

