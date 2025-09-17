#!/bin/bash

# Simple test without jq

BASE_URL="https://cryptouniverse.onrender.com"
EMAIL="admin@cryptouniverse.com"
PASSWORD="AdminPass123!"

echo "=== Testing CryptoUniverse Deployed Service ==="
echo "Timestamp: $(date)"
echo

# Login
echo "1. Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}")

echo "Login Response:"
echo "$LOGIN_RESPONSE"
echo

# Extract token using grep and sed
TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | sed 's/"access_token":"//' | sed 's/"$//')

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to extract token"
  exit 1
fi

echo "✅ Token extracted successfully"
echo

# Test strategy execution
echo "2. Testing Strategy Execution..."
STRATEGY_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/strategies/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function": "spot_momentum_strategy",
    "parameters": {
      "symbol": "BTC/USDT",
      "timeframe": "1h",
      "amount": 1000
    }
  }')

echo "Strategy Response (first 500 chars):"
echo "$STRATEGY_RESPONSE" | head -c 500
echo
echo

# Check for null values in risk_management
if echo "$STRATEGY_RESPONSE" | grep -q '"take_profit":null'; then
  echo "⚠️  take_profit is null"
fi
if echo "$STRATEGY_RESPONSE" | grep -q '"stop_loss":null'; then
  echo "⚠️  stop_loss is null"
fi
echo

# Test opportunity discovery
echo "3. Testing Opportunity Discovery..."
START_TIME=$(date +%s)
DISCOVER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/opportunities/discover" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "risk_level": "medium",
    "investment_amount": 10000,
    "force_refresh": true
  }')
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo "Discovery took ${ELAPSED} seconds"
echo

# Check for specific errors
if echo "$DISCOVER_RESPONSE" | grep -q "float() argument must be a string or a real number"; then
  echo "❌ CRITICAL: TypeError for float(None) is still occurring!"
  echo "The nullable fields fix has NOT been applied or is incomplete"
fi

if echo "$DISCOVER_RESPONSE" | grep -q "name 'final_response' is not defined"; then
  echo "❌ Variable name error still present"
fi

# Extract total opportunities
OPPORTUNITIES=$(echo "$DISCOVER_RESPONSE" | grep -o '"total_opportunities":[0-9]*' | grep -o '[0-9]*$')
echo "Total opportunities found: ${OPPORTUNITIES:-0}"

if [ "${OPPORTUNITIES:-0}" -gt 0 ]; then
  echo "✅ SUCCESS: Found $OPPORTUNITIES opportunities!"
  echo "The nullable fields fix appears to be working!"
else
  echo "⚠️  Still finding 0 opportunities"
  
  # Show first 1000 chars of response for debugging
  echo "Response preview:"
  echo "$DISCOVER_RESPONSE" | head -c 1000
fi

echo
echo "=== Test Complete ==="