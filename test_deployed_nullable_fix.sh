#!/bin/bash

# Test deployed service for nullable fields fix

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

if ! echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
  echo "❌ Login failed:"
  echo "$LOGIN_RESPONSE" | jq '.' 2>/dev/null || echo "$LOGIN_RESPONSE"
  exit 1
fi

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
echo "✅ Login successful"
echo

# Test strategy execution to check risk_management fields
echo "2. Testing Strategy Execution (checking nullable fields)..."
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

echo "Strategy Response:"
echo "$STRATEGY_RESPONSE" | jq '.risk_management' 2>/dev/null || echo "$STRATEGY_RESPONSE"
echo

# Check if take_profit and stop_loss are null
TAKE_PROFIT=$(echo "$STRATEGY_RESPONSE" | jq '.risk_management.take_profit')
STOP_LOSS=$(echo "$STRATEGY_RESPONSE" | jq '.risk_management.stop_loss')

echo "Risk Management Fields:"
echo "- take_profit: $TAKE_PROFIT"
echo "- stop_loss: $STOP_LOSS"
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

echo "Discovery Response (took ${ELAPSED}s):"
echo "$DISCOVER_RESPONSE" | jq '{
  success: .success,
  total_opportunities: .total_opportunities,
  total_assets_scanned: .signal_analysis.total_assets_scanned,
  total_signals_analyzed: .signal_analysis.total_signals_analyzed,
  execution_time_ms: .execution_time_ms,
  error: .error
}' 2>/dev/null || echo "$DISCOVER_RESPONSE"

# Check for specific error message
if echo "$DISCOVER_RESPONSE" | grep -q "float() argument must be a string or a real number"; then
  echo "❌ NULLABLE FIELDS ERROR STILL PRESENT!"
  echo "The TypeError for float(None) is still occurring"
fi

# Check if opportunities > 0
OPPORTUNITIES=$(echo "$DISCOVER_RESPONSE" | jq -r '.total_opportunities // 0')
if [ "$OPPORTUNITIES" -gt 0 ]; then
  echo "✅ Found $OPPORTUNITIES opportunities - nullable fields fix appears to be working!"
else
  echo "⚠️  Still 0 opportunities - checking for other issues..."
  
  # Check for error details
  ERROR=$(echo "$DISCOVER_RESPONSE" | jq -r '.error // empty')
  if [ -n "$ERROR" ]; then
    echo "Error message: $ERROR"
  fi
fi

echo
echo "=== Test Complete ==="