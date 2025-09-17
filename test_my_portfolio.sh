#!/bin/bash

echo "=== Testing My Portfolio Endpoint ==="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@cryptouniverse.com",
    "password": "AdminPass123!"
  }')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Test my-portfolio endpoint
echo -e "\n1. Testing /strategies/my-portfolio endpoint..."
PORTFOLIO_RESPONSE=$(curl -s -X GET https://cryptouniverse.onrender.com/api/v1/strategies/my-portfolio \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "Portfolio Response:"
echo "$PORTFOLIO_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$PORTFOLIO_RESPONSE"

# Check the structure
echo -e "\n=== Response Structure Analysis ==="
if echo "$PORTFOLIO_RESPONSE" | grep -q '"strategies":\['; then
    STRATEGY_COUNT=$(echo "$PORTFOLIO_RESPONSE" | grep -o '"strategies":\[[^]]*' | grep -o '"strategy_id"' | wc -l)
    echo "Found 'strategies' array with $STRATEGY_COUNT strategies"
fi

if echo "$PORTFOLIO_RESPONSE" | grep -q '"active_strategies":\['; then
    echo "Found 'active_strategies' array"
fi

if echo "$PORTFOLIO_RESPONSE" | grep -q '"summary":{'; then
    echo "Found 'summary' object"
    TOTAL_STRATEGIES=$(echo "$PORTFOLIO_RESPONSE" | grep -o '"total_strategies":[0-9]*' | cut -d':' -f2)
    echo "Total strategies from summary: ${TOTAL_STRATEGIES:-0}"
fi

