#!/bin/bash

# Test current state after deployment

BASE_URL="https://cryptouniverse.onrender.com"
EMAIL="admin@cryptouniverse.com"
PASSWORD="AdminPass123!"

echo "=== Testing Current State After Deployment ==="
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

echo "✅ Login successful"
echo

# Check strategy execution with risk_management fields
echo "2. Testing Strategy Execution (checking risk_management fields)..."
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

# Extract risk management fields
TAKE_PROFIT=$(echo "$STRATEGY_RESPONSE" | grep -o '"take_profit":[^,}]*' | sed 's/"take_profit"://')
STOP_LOSS=$(echo "$STRATEGY_RESPONSE" | grep -o '"stop_loss":[^,}]*' | sed 's/"stop_loss"://')

echo "Risk Management Fields:"
echo "- take_profit: $TAKE_PROFIT"
echo "- stop_loss: $STOP_LOSS"

if [ "$TAKE_PROFIT" = "null" ]; then
  echo "⚠️  take_profit is still null - this will cause TypeError in opportunity scanner"
else
  echo "✅ take_profit has a value"
fi
echo

# Skip onboarding and go directly to discovery
echo "3. Testing Opportunity Discovery (bypassing onboarding)..."
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

# Check for errors
if echo "$DISCOVER_RESPONSE" | grep -q "Opportunity discovery failed"; then
  ERROR_MSG=$(echo "$DISCOVER_RESPONSE" | grep -o '"error":"[^"]*"' | sed 's/"error":"//' | sed 's/"$//')
  echo "❌ Discovery failed with error: $ERROR_MSG"
else
  # Extract metrics
  TOTAL_OPP=$(echo "$DISCOVER_RESPONSE" | grep -o '"total_opportunities":[0-9]*' | grep -o '[0-9]*$')
  ASSETS_SCANNED=$(echo "$DISCOVER_RESPONSE" | grep -o '"total_assets_scanned":[0-9]*' | grep -o '[0-9]*$')
  SIGNALS_ANALYZED=$(echo "$DISCOVER_RESPONSE" | grep -o '"total_signals_analyzed":[0-9]*' | grep -o '[0-9]*$')
  
  echo "Discovery Results:"
  echo "- Total opportunities: ${TOTAL_OPP:-0}"
  echo "- Assets scanned: ${ASSETS_SCANNED:-0}" 
  echo "- Signals analyzed: ${SIGNALS_ANALYZED:-0}"
  
  if [ "${TOTAL_OPP:-0}" -gt 0 ]; then
    echo "🎉 SUCCESS! Found $TOTAL_OPP opportunities!"
  fi
fi

echo
echo "=== Key Findings ==="
echo "From the logs:"
echo "1. User HAS 4 strategies in Redis: ai_portfolio_optimization, ai_spot_momentum_strategy, ai_options_trade, ai_risk_management"
echo "2. Onboarding endpoint has a bug - returns dict without 'user_id' when user already onboarded"
echo "3. The 'reference_id' error is STILL present in the initial credit account creation"
echo "4. There are SQL enum casting errors with 'tradestatus'"
echo
echo "=== Test Complete ==="