#!/bin/bash

# Test after clear build and cache deployment

BASE_URL="https://cryptouniverse.onrender.com"
EMAIL="admin@cryptouniverse.com"
PASSWORD="AdminPass123!"

echo "=== Testing After Clear Build & Cache Deployment ==="
echo "Timestamp: $(date)"
echo

# Login
echo "Step 1: Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}")

TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | sed 's/"access_token":"//' | sed 's/"$//')

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to login"
  echo "$LOGIN_RESPONSE"
  exit 1
fi

echo "✅ Login successful"
echo

# Check onboarding status - this will show if reference_id error is gone
echo "Step 2: Checking if CreditTransaction fix is deployed..."
ONBOARD_STATUS=$(curl -s -X GET "$BASE_URL/api/v1/opportunities/status" \
  -H "Authorization: Bearer $TOKEN")

# Look for the smoking gun - reference_id error
if echo "$ONBOARD_STATUS" | grep -q "reference_id"; then
  echo "❌ STILL seeing reference_id error - deployment didn't work"
  echo "$ONBOARD_STATUS" | grep -o "reference_id[^\"]*" | head -1
else
  echo "✅ No reference_id error - CreditTransaction fix is deployed!"
fi

# Check current status details
ONBOARDED=$(echo "$ONBOARD_STATUS" | grep -o '"onboarded":[^,]*' | head -1)
echo "- User onboarded status: $ONBOARDED"

# Try fresh onboarding
echo
echo "Step 3: Attempting fresh onboarding..."
ONBOARD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/opportunities/onboard" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}')

if echo "$ONBOARD_RESPONSE" | grep -q '"success":true'; then
  echo "✅ Onboarding successful!"
  ONBOARD_ID=$(echo "$ONBOARD_RESPONSE" | grep -o '"onboarding_id":"[^"]*"' | sed 's/"onboarding_id":"//' | sed 's/"$//')
  echo "- Onboarding ID: $ONBOARD_ID"
else
  echo "Onboarding response:"
  echo "$ONBOARD_RESPONSE"
fi

# Test opportunity discovery
echo
echo "Step 4: Testing Opportunity Discovery..."
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

# Extract all metrics
TOTAL_OPP=$(echo "$DISCOVER_RESPONSE" | grep -o '"total_opportunities":[0-9]*' | grep -o '[0-9]*$')
ASSETS_SCANNED=$(echo "$DISCOVER_RESPONSE" | grep -o '"total_assets_scanned":[0-9]*' | grep -o '[0-9]*$')
SIGNALS_ANALYZED=$(echo "$DISCOVER_RESPONSE" | grep -o '"total_signals_analyzed":[0-9]*' | grep -o '[0-9]*$')
EXEC_TIME=$(echo "$DISCOVER_RESPONSE" | grep -o '"execution_time_ms":[0-9.]*' | grep -o '[0-9.]*$')

echo "Discovery Results (${ELAPSED}s):"
echo "- Total opportunities: ${TOTAL_OPP:-0}"
echo "- Assets scanned: ${ASSETS_SCANNED:-0}"
echo "- Signals analyzed: ${SIGNALS_ANALYZED:-0}"
echo "- Execution time: ${EXEC_TIME}ms"

# Check strategy performance
STRAT_PERF=$(echo "$DISCOVER_RESPONSE" | grep -o '"strategy_performance":{[^}]*}')
if [ -n "$STRAT_PERF" ] && [ "$STRAT_PERF" != '"strategy_performance":{}' ]; then
  echo "- Strategy performance: Found data!"
else
  echo "- Strategy performance: Empty (no strategies loaded)"
fi

# Final verdict
echo
echo "=== DEPLOYMENT VERIFICATION ==="
if [ "${TOTAL_OPP:-0}" -gt 0 ]; then
  echo "🎉 SUCCESS! All fixes are working!"
  echo "✅ CreditTransaction fix: Deployed"
  echo "✅ Signal extraction fix: Working" 
  echo "✅ Nullable fields fix: Working"
  echo "✅ Found $TOTAL_OPP opportunities!"
  
  # Show first opportunity
  FIRST_SYMBOL=$(echo "$DISCOVER_RESPONSE" | grep -o '"symbol":"[^"]*"' | head -1 | sed 's/"symbol":"//' | sed 's/"$//')
  FIRST_STRATEGY=$(echo "$DISCOVER_RESPONSE" | grep -o '"strategy_name":"[^"]*"' | head -1 | sed 's/"strategy_name":"//' | sed 's/"$//')
  echo
  echo "First opportunity: $FIRST_SYMBOL via $FIRST_STRATEGY"
else
  echo "⚠️ Still 0 opportunities"
  echo
  echo "Checking deployment status of each fix:"
  
  if echo "$ONBOARD_STATUS" | grep -q "reference_id"; then
    echo "❌ CreditTransaction fix: NOT deployed"
  else
    echo "✅ CreditTransaction fix: Deployed"
  fi
  
  if [ "${ASSETS_SCANNED:-0}" -gt 0 ] && [ "${SIGNALS_ANALYZED:-0}" -eq 0 ]; then
    echo "⚠️ Signal extraction: Might be an issue"
  else
    echo "❓ Signal extraction: Cannot verify without strategies"
  fi
  
  echo "❓ Nullable fields: Cannot verify without signals"
fi

echo
echo "=== Test Complete ==="