#!/bin/bash

# Test onboarding error in detail

BASE_URL="https://cryptouniverse.onrender.com"
EMAIL="admin@cryptouniverse.com"
PASSWORD="AdminPass123!"

echo "=== Testing Onboarding Error ==="
echo

# Login
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

# Try onboarding with verbose output
echo "Attempting onboarding..."
ONBOARD_RESPONSE=$(curl -v -X POST "$BASE_URL/api/v1/opportunities/onboard" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' 2>&1)

# Extract just the response body
RESPONSE_BODY=$(echo "$ONBOARD_RESPONSE" | grep -A 1000 "< {" | grep "^{" | head -1)

echo "Response body:"
echo "$RESPONSE_BODY"
echo

# Check specific error patterns
if echo "$RESPONSE_BODY" | grep -q "user_id"; then
  echo "Found 'user_id' in error message"
fi

if echo "$RESPONSE_BODY" | grep -q "KeyError"; then
  echo "Found KeyError"
fi

if echo "$RESPONSE_BODY" | grep -q "reference_id"; then
  echo "Found 'reference_id' error - this is the root cause!"
fi