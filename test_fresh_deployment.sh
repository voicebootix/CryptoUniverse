#!/bin/bash

# Test with a brand new user to avoid any caching issues

BASE_URL="https://cryptouniverse.onrender.com"
TIMESTAMP=$(date +%s)
TEST_EMAIL="freshtest${TIMESTAMP}@example.com"
TEST_PASSWORD="TestPass123!"

echo "=== Testing with Fresh User ==="
echo "Timestamp: $(date)"
echo "Test email: $TEST_EMAIL"
echo

# Register new user
echo "Step 1: Registering fresh user..."
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$TEST_EMAIL\",
    \"password\": \"$TEST_PASSWORD\",
    \"full_name\": \"Fresh Test User\"
  }")

if echo "$REGISTER_RESPONSE" | grep -q "error"; then
  echo "Registration error:"
  echo "$REGISTER_RESPONSE"
else
  echo "✅ Registration successful"
fi

# Login
echo
echo "Step 2: Login with fresh user..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$TEST_EMAIL\", \"password\": \"$TEST_PASSWORD\"}")

TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | sed 's/"access_token":"//' | sed 's/"$//')

if [ -z "$TOKEN" ]; then
  echo "❌ Login failed:"
  echo "$LOGIN_RESPONSE"
  exit 1
fi

echo "✅ Login successful"

# Onboard fresh user
echo
echo "Step 3: Onboarding fresh user..."
ONBOARD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/opportunities/onboard" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}')

echo "Onboarding response:"
if echo "$ONBOARD_RESPONSE" | grep -q '"success":true'; then
  echo "✅ Onboarding successful!"
  
  # Extract details
  ONBOARD_ID=$(echo "$ONBOARD_RESPONSE" | grep -o '"onboarding_id":"[^"]*"' | sed 's/"onboarding_id":"//' | sed 's/"$//')
  echo "- Onboarding ID: $ONBOARD_ID"
else
  echo "❌ Onboarding failed:"
  echo "$ONBOARD_RESPONSE"
  
  # Check for specific error
  if echo "$ONBOARD_RESPONSE" | grep -q "reference_id"; then
    echo
    echo "❌ CRITICAL: The reference_id error is STILL happening!"
    echo "This means the deployment is NOT using the latest code."
  fi
fi

# Try discovery anyway
echo
echo "Step 4: Testing opportunity discovery..."
DISCOVER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/opportunities/discover" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "risk_level": "medium",
    "investment_amount": 1000,
    "force_refresh": true
  }')

TOTAL_OPP=$(echo "$DISCOVER_RESPONSE" | grep -o '"total_opportunities":[0-9]*' | grep -o '[0-9]*$')
echo "Total opportunities found: ${TOTAL_OPP:-0}"

if [ "${TOTAL_OPP:-0}" -gt 0 ]; then
  echo "🎉 SUCCESS! Fresh user can discover opportunities!"
else
  echo "❌ Still 0 opportunities for fresh user"
fi

echo
echo "=== Summary ==="
echo "The code in git shows the fix is there (stripe_payment_intent_id)."
echo "But the deployed service might be:"
echo "1. Using a cached/old Docker image"
echo "2. Not actually deployed from the latest main branch"
echo "3. Having environment-specific issues"