#!/bin/bash
# Test Opportunity Discovery API

BASE_URL="https://cryptouniverse.onrender.com"
EMAIL="admin@cryptouniverse.com"
PASSWORD="AdminPass123!"

echo "🔐 Testing Opportunity Discovery API"
echo "=================================="
echo "Base URL: $BASE_URL"
echo "Time: $(date)"
echo ""

# Login
echo "1. Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

# Extract token using sed
TOKEN=$(echo $LOGIN_RESPONSE | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to login"
  echo "Response: $LOGIN_RESPONSE"
  exit 1
fi

echo "✅ Login successful"
echo "Token: ${TOKEN:0:20}..."
echo ""

# Check onboarding status
echo "2. Checking onboarding status..."
STATUS_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/opportunity/status" \
  -H "Authorization: Bearer $TOKEN")

echo "Response: $STATUS_RESPONSE" | head -c 500
echo ""
echo ""

# Check user strategies
echo "3. Checking user strategies..."
STRATEGIES_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/strategies/my-strategies" \
  -H "Authorization: Bearer $TOKEN")

echo "Response: $STRATEGIES_RESPONSE" | head -c 500
echo ""
echo ""

# Test opportunity discovery
echo "4. Testing opportunity discovery (with force_refresh)..."
DISCOVERY_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/opportunity/discover" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"force_refresh":true,"include_strategy_recommendations":true}')

echo "Response: $DISCOVERY_RESPONSE" | head -c 1000
echo ""
echo ""

# Count opportunities
OPPORTUNITIES_COUNT=$(echo $DISCOVERY_RESPONSE | grep -o '"opportunity_type"' | wc -l)
echo "Opportunities found: $OPPORTUNITIES_COUNT"

# Test chat-based discovery
echo ""
echo "5. Testing chat-based opportunity discovery..."
CHAT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/chat/unified/message" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Find me trading opportunities","conversation_mode":"live_trading"}')

echo "Response: $CHAT_RESPONSE" | head -c 500
echo ""

# Save full responses
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
echo "$DISCOVERY_RESPONSE" > "opportunity_api_test_$TIMESTAMP.json"
echo ""
echo "✅ Test complete. Full discovery response saved to: opportunity_api_test_$TIMESTAMP.json"