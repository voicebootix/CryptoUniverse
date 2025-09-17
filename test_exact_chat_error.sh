#!/bin/bash

echo "=== Testing Exact Chat Error ==="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@cryptouniverse.com",
    "password": "AdminPass123!"
  }')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Test with the exact message that's failing
echo "Testing with 'Find the best opportunities now'..."
CHAT_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST https://cryptouniverse.onrender.com/api/v1/chat/message \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find the best opportunities now",
    "context": {
      "intent": "opportunity_discovery",
      "has_opportunities": true
    }
  }')

HTTP_STATUS=$(echo "$CHAT_RESPONSE" | grep "HTTP_STATUS:" | cut -d':' -f2)
RESPONSE_BODY=$(echo "$CHAT_RESPONSE" | sed '/HTTP_STATUS:/d')

echo "HTTP Status: $HTTP_STATUS"
echo "Response:"
echo "$RESPONSE_BODY" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE_BODY"

# Test portfolio performance request
echo -e "\n\nTesting 'Show my portfolio performance'..."
CHAT_RESPONSE2=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST https://cryptouniverse.onrender.com/api/v1/chat/message \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show my portfolio performance",
    "context": {}
  }')

HTTP_STATUS2=$(echo "$CHAT_RESPONSE2" | grep "HTTP_STATUS:" | cut -d':' -f2)
RESPONSE_BODY2=$(echo "$CHAT_RESPONSE2" | sed '/HTTP_STATUS:/d')

echo "HTTP Status: $HTTP_STATUS2"
echo "Response:"
echo "$RESPONSE_BODY2" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE_BODY2"

