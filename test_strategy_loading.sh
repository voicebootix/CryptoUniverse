#!/bin/bash

# Test strategy loading and discovery process

BASE_URL="https://cryptouniverse.onrender.com"
EMAIL="admin@cryptouniverse.com"
PASSWORD="AdminPass123!"

echo "=== Testing Strategy Loading and Discovery Process ==="
echo "Timestamp: $(date)"
echo

# Login
echo "1. Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}")

TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | sed 's/"access_token":"//' | sed 's/"$//')

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to extract token"
  exit 1
fi

echo "✅ Token extracted"
echo

# Check user profile
echo "2. Checking User Profile..."
PROFILE_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/users/profile" \
  -H "Authorization: Bearer $TOKEN")

echo "User Profile Response:"
echo "$PROFILE_RESPONSE" | grep -E "(active_strategies|total_strategies|credits|user_id)"
echo

# Check strategy portfolio
echo "3. Checking Strategy Portfolio..."
PORTFOLIO_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/strategies/portfolio" \
  -H "Authorization: Bearer $TOKEN")

echo "Strategy Portfolio Response (first 500 chars):"
echo "$PORTFOLIO_RESPONSE" | head -c 500
echo
echo

# Count strategies
STRATEGY_COUNT=$(echo "$PORTFOLIO_RESPONSE" | grep -o '"strategy_function"' | wc -l)
echo "Number of strategies in portfolio: $STRATEGY_COUNT"
echo

# Check onboarding status
echo "4. Checking Onboarding Status..."
ONBOARD_STATUS=$(curl -s -X GET "$BASE_URL/api/v1/opportunities/status" \
  -H "Authorization: Bearer $TOKEN")

echo "Onboarding Status:"
echo "$ONBOARD_STATUS" | grep -E "(onboarded|credits|strategies)"
echo

# Try to onboard if not already
echo "5. Attempting Onboarding (if needed)..."
ONBOARD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/opportunities/onboard" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}')

echo "Onboarding Response:"
echo "$ONBOARD_RESPONSE"
echo

# Test discovery with verbose error checking
echo "6. Testing Discovery with Force Refresh..."
DISCOVER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/opportunities/discover" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "risk_level": "medium",
    "investment_amount": 10000,
    "force_refresh": true
  }')

# Check for specific patterns
echo "Discovery Analysis:"
echo "- Success: $(echo "$DISCOVER_RESPONSE" | grep -o '"success":[^,]*' | head -1)"
echo "- Total opportunities: $(echo "$DISCOVER_RESPONSE" | grep -o '"total_opportunities":[0-9]*' | grep -o '[0-9]*$')"
echo "- Error: $(echo "$DISCOVER_RESPONSE" | grep -o '"error":"[^"]*"' | sed 's/"error":"//' | sed 's/"$//')"
echo "- Execution time: $(echo "$DISCOVER_RESPONSE" | grep -o '"execution_time_ms":[0-9.]*' | grep -o '[0-9.]*$')"

# Check for strategy performance
STRATEGY_PERF=$(echo "$DISCOVER_RESPONSE" | grep -o '"strategy_performance":{[^}]*}')
if [ -n "$STRATEGY_PERF" ]; then
  echo "- Strategy performance: $STRATEGY_PERF"
else
  echo "- Strategy performance: Empty or not found"
fi

echo
echo "=== Test Complete ==="