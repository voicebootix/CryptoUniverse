#!/bin/bash

echo "=== Testing Current Deployment ==="
echo "Testing opportunity discovery on live service..."

# Login
echo -e "\n1. Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@cryptouniverse.com",
    "password": "AdminPass123!"
  }')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$ACCESS_TOKEN" ]; then
    echo "Login failed!"
    echo "$LOGIN_RESPONSE"
    exit 1
fi

echo "Login successful!"

# Test opportunity discovery
echo -e "\n2. Testing opportunity discovery..."
DISCOVERY_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/discover \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "force_refresh": true,
    "include_details": true
  }')

echo "Discovery Response:"
echo "$DISCOVERY_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$DISCOVERY_RESPONSE"

# Extract key metrics
TOTAL_OPPORTUNITIES=$(echo "$DISCOVERY_RESPONSE" | grep -o '"total_opportunities":[0-9]*' | cut -d':' -f2)
TOTAL_ASSETS=$(echo "$DISCOVERY_RESPONSE" | grep -o '"total_assets_scanned":[0-9]*' | cut -d':' -f2)
TOTAL_SIGNALS=$(echo "$DISCOVERY_RESPONSE" | grep -o '"total_signals_analyzed":[0-9]*' | cut -d':' -f2)
STRATEGY_COUNT=$(echo "$DISCOVERY_RESPONSE" | grep -o '"active_strategies":[0-9]*' | cut -d':' -f2)

echo -e "\n=== Summary ==="
echo "Total opportunities: ${TOTAL_OPPORTUNITIES:-0}"
echo "Total assets scanned: ${TOTAL_ASSETS:-0}"
echo "Total signals analyzed: ${TOTAL_SIGNALS:-0}"
echo "Active strategies: ${STRATEGY_COUNT:-0}"

# Check for specific errors
if echo "$DISCOVERY_RESPONSE" | grep -q "name 'final_response' is not defined"; then
    echo "ERROR: Variable name error still present!"
fi

if echo "$DISCOVERY_RESPONSE" | grep -q "User has no active strategies"; then
    echo "ERROR: System thinks user has no strategies!"
fi

