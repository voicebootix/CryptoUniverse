#!/bin/bash

# Test the complete deployment with all fixes

BASE_URL="https://cryptouniverse.onrender.com"
EMAIL="admin@cryptouniverse.com"
PASSWORD="AdminPass123!"

echo "=== Testing Complete Deployment ==="
echo "Timestamp: $(date)"
echo "Testing all fixes:"
echo "1. CreditTransaction fix"
echo "2. Signal extraction fix"
echo "3. Nullable fields handling"
echo

# Login
echo "Step 1: Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}")

TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | sed 's/"access_token":"//' | sed 's/"$//')

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to extract token"
  echo "$LOGIN_RESPONSE"
  exit 1
fi

echo "✅ Login successful"
echo

# Check onboarding status
echo "Step 2: Checking Onboarding Status..."
ONBOARD_STATUS=$(curl -s -X GET "$BASE_URL/api/v1/opportunities/status" \
  -H "Authorization: Bearer $TOKEN")

echo "Key onboarding info:"
# Check for reference_id error
if echo "$ONBOARD_STATUS" | grep -q "reference_id"; then
  echo "❌ CreditTransaction fix NOT deployed - reference_id error still present"
else
  echo "✅ CreditTransaction fix deployed - no reference_id error"
fi

# Extract credit account status
CREDIT_SUCCESS=$(echo "$ONBOARD_STATUS" | grep -o '"credit_account":{"success":[^,]*' | grep -o 'true\|false')
echo "- Credit account success: $CREDIT_SUCCESS"

# Extract free strategies status
FREE_STRAT_SUCCESS=$(echo "$ONBOARD_STATUS" | grep -o '"free_strategies":{"success":[^,]*' | grep -o 'true\|false')
echo "- Free strategies success: $FREE_STRAT_SUCCESS"

echo

# Try onboarding if needed
if [ "$CREDIT_SUCCESS" = "false" ] || [ "$FREE_STRAT_SUCCESS" = "false" ]; then
  echo "Step 3: Attempting fresh onboarding..."
  ONBOARD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/opportunities/onboard" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{}')
  
  if echo "$ONBOARD_RESPONSE" | grep -q '"success":true'; then
    echo "✅ Onboarding successful!"
  else
    echo "⚠️ Onboarding response:"
    echo "$ONBOARD_RESPONSE" | head -c 500
  fi
  echo
fi

# Test opportunity discovery
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

# Extract metrics
SUCCESS=$(echo "$DISCOVER_RESPONSE" | grep -o '"success":[^,]*' | head -1)
TOTAL_OPP=$(echo "$DISCOVER_RESPONSE" | grep -o '"total_opportunities":[0-9]*' | grep -o '[0-9]*$')
ASSETS_SCANNED=$(echo "$DISCOVER_RESPONSE" | grep -o '"total_assets_scanned":[0-9]*' | grep -o '[0-9]*$')
SIGNALS_ANALYZED=$(echo "$DISCOVER_RESPONSE" | grep -o '"total_signals_analyzed":[0-9]*' | grep -o '[0-9]*$')
EXEC_TIME=$(echo "$DISCOVER_RESPONSE" | grep -o '"execution_time_ms":[0-9.]*' | grep -o '[0-9.]*$')

echo "Discovery Results (took ${ELAPSED}s):"
echo "- Success: $SUCCESS"
echo "- Total opportunities: ${TOTAL_OPP:-0}"
echo "- Assets scanned: ${ASSETS_SCANNED:-0}"
echo "- Signals analyzed: ${SIGNALS_ANALYZED:-0}"
echo "- Execution time: ${EXEC_TIME}ms"

# Check for errors
if echo "$DISCOVER_RESPONSE" | grep -q "float() argument must be a string"; then
  echo "❌ Nullable fields error detected"
fi

if echo "$DISCOVER_RESPONSE" | grep -q "name 'final_response' is not defined"; then
  echo "❌ Variable name error detected"
fi

# Show first opportunity if any
if [ "${TOTAL_OPP:-0}" -gt 0 ]; then
  echo
  echo "✅ OPPORTUNITIES FOUND! Showing first one:"
  FIRST_OPP=$(echo "$DISCOVER_RESPONSE" | grep -o '"opportunities":\[[^]]*' | grep -o '"symbol":"[^"]*"' | head -1)
  echo "- First opportunity: $FIRST_OPP"
fi

# Final summary
echo
echo "=== DEPLOYMENT TEST SUMMARY ==="
if [ "${TOTAL_OPP:-0}" -gt 0 ]; then
  echo "🎉 SUCCESS! All fixes working:"
  echo "✅ CreditTransaction fix: Working"
  echo "✅ Signal extraction fix: Working"
  echo "✅ Nullable fields fix: Working"
  echo "✅ Found $TOTAL_OPP trading opportunities!"
else
  echo "⚠️ Still finding 0 opportunities. Checking why..."
  
  # Debug info
  STRAT_PERF=$(echo "$DISCOVER_RESPONSE" | grep -o '"strategy_performance":{[^}]*}' | head -c 200)
  echo "- Strategy performance: ${STRAT_PERF:-empty}"
  
  if [ -z "$STRAT_PERF" ] || [ "$STRAT_PERF" = "empty" ]; then
    echo "❌ No strategies loaded - onboarding may have failed"
  fi
fi

echo
echo "=== Test Complete ==="