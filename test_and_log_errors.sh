#!/bin/bash

# Test endpoints and capture detailed error messages
BASE_URL="https://cryptouniverse.onrender.com"
API_URL="${BASE_URL}/api/v1"

echo "Testing Render Deployment - Capturing Error Details"
echo "===================================================="
echo "Timestamp: $(date)"
echo ""

# Get a fresh token
echo "1. Getting fresh auth token..."
LOGIN_RESPONSE=$(curl -s -X POST "${API_URL}/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@cryptouniverse.com","password":"AdminPass123!"}' 2>&1)

TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | sed 's/"access_token":"//')

if [ -z "$TOKEN" ]; then
    echo "❌ Failed to get token. Response:"
    echo "$LOGIN_RESPONSE"
else
    echo "✅ Token obtained"
fi

echo ""
echo "2. Testing problematic endpoints and capturing full error responses:"
echo ""

# Test Admin Users endpoint (500 error)
echo "=== Admin Users Endpoint ==="
ADMIN_RESPONSE=$(curl -s -X GET "${API_URL}/admin/users" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Accept: application/json" 2>&1)
echo "Response: $ADMIN_RESPONSE"
echo ""

# Test Admin System Status (500 error)
echo "=== Admin System Status ==="
STATUS_RESPONSE=$(curl -s -X GET "${API_URL}/admin/system/status" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Accept: application/json" 2>&1)
echo "Response: $STATUS_RESPONSE"
echo ""

# Test Telegram Connect (500 error)
echo "=== Telegram Connect ==="
TELEGRAM_RESPONSE=$(curl -s -X POST "${API_URL}/telegram/connect" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"telegram_id":"test_user"}' 2>&1)
echo "Response: $TELEGRAM_RESPONSE"
echo ""

# Test Market Prices (404)
echo "=== Market Prices (should be 404) ==="
MARKET_RESPONSE=$(curl -s -X GET "${API_URL}/market/prices" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Accept: application/json" \
    -w "\nHTTP_CODE:%{http_code}" 2>&1)
echo "Response: $MARKET_RESPONSE"
echo ""

# Test Chat Message (404)
echo "=== Chat Message (should be 404) ==="
CHAT_RESPONSE=$(curl -s -X POST "${API_URL}/chat/message" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"message":"Test message"}' \
    -w "\nHTTP_CODE:%{http_code}" 2>&1)
echo "Response: $CHAT_RESPONSE"
echo ""

echo "===================================================="
echo "Error capture complete. Check responses above for detailed error messages."
echo ""
echo "To view live Render logs, visit:"
echo "https://dashboard.render.com/web/[your-service-id]/logs"