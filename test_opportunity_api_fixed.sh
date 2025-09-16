#!/bin/bash
# Test Opportunity Discovery API with correct endpoints

BASE_URL="https://cryptouniverse.onrender.com"
EMAIL="admin@cryptouniverse.com"
PASSWORD="AdminPass123!"

echo "🔐 Testing Opportunity Discovery API (Fixed)"
echo "==========================================="
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

# Extract user info
USER_ID=$(echo $LOGIN_RESPONSE | sed -n 's/.*"id":"\([^"]*\)".*/\1/p')
echo "User ID: $USER_ID"
echo ""

# Check API status first
echo "2. Checking API status..."
API_STATUS=$(curl -s -X GET "$BASE_URL/api/v1/status")
echo "API Status: $API_STATUS" | head -c 300
echo ""
echo ""

# Check onboarding status - FIXED ENDPOINT
echo "3. Checking onboarding status (opportunities/status)..."
STATUS_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/opportunities/status" \
  -H "Authorization: Bearer $TOKEN")

echo "Response: $STATUS_RESPONSE" | head -c 500
echo ""
echo ""

# Check user strategies
echo "4. Checking user strategies..."
STRATEGIES_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/strategies/my-strategies" \
  -H "Authorization: Bearer $TOKEN")

STRATEGY_COUNT=$(echo $STRATEGIES_RESPONSE | grep -o '"strategy_id"' | wc -l)
echo "Number of strategies: $STRATEGY_COUNT"
echo "Response preview: $STRATEGIES_RESPONSE" | head -c 500
echo ""
echo ""

# If no strategies, trigger onboarding
if [ "$STRATEGY_COUNT" -eq "0" ]; then
  echo "5. No strategies found - Triggering onboarding..."
  ONBOARD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/opportunities/onboard" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"welcome_package":"standard"}')
  
  echo "Onboarding response: $ONBOARD_RESPONSE" | head -c 500
  echo ""
  echo ""
  
  # Re-check strategies after onboarding
  echo "Re-checking strategies after onboarding..."
  STRATEGIES_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/strategies/my-strategies" \
    -H "Authorization: Bearer $TOKEN")
  STRATEGY_COUNT=$(echo $STRATEGIES_RESPONSE | grep -o '"strategy_id"' | wc -l)
  echo "Number of strategies after onboarding: $STRATEGY_COUNT"
fi

# Test opportunity discovery - FIXED ENDPOINT
echo ""
echo "6. Testing opportunity discovery (with force_refresh)..."
DISCOVERY_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/opportunities/discover" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"force_refresh":true,"include_strategy_recommendations":true}')

# Pretty print with python if available
if command -v python3 &> /dev/null; then
  echo "Discovery Response (formatted):"
  echo "$DISCOVERY_RESPONSE" | python3 -m json.tool 2>/dev/null | head -c 2000
else
  echo "Discovery Response:"
  echo "$DISCOVERY_RESPONSE" | head -c 2000
fi
echo ""

# Count opportunities
OPPORTUNITIES_COUNT=$(echo $DISCOVERY_RESPONSE | grep -o '"opportunity_type"' | wc -l)
SUCCESS=$(echo $DISCOVERY_RESPONSE | grep -o '"success":true' | wc -l)
echo ""
echo "Summary:"
echo "  - Success: $([ $SUCCESS -gt 0 ] && echo '✅ Yes' || echo '❌ No')"
echo "  - Opportunities found: $OPPORTUNITIES_COUNT"

# Extract error if any
ERROR=$(echo $DISCOVERY_RESPONSE | sed -n 's/.*"error":"\([^"]*\)".*/\1/p')
if [ ! -z "$ERROR" ]; then
  echo "  - Error: $ERROR"
fi

# Test chat-based discovery
echo ""
echo "7. Testing chat-based opportunity discovery..."
CHAT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/chat/message" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Find me trading opportunities","conversation_mode":"live_trading"}')

CHAT_SUCCESS=$(echo $CHAT_RESPONSE | grep -o '"success":true' | wc -l)
echo "Chat Response preview: $CHAT_RESPONSE" | head -c 500
echo ""
echo "Chat Success: $([ $CHAT_SUCCESS -gt 0 ] && echo '✅ Yes' || echo '❌ No')"

# Save full responses
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p debug_outputs
echo "$DISCOVERY_RESPONSE" > "debug_outputs/opportunity_discovery_$TIMESTAMP.json"
echo "$STRATEGIES_RESPONSE" > "debug_outputs/user_strategies_$TIMESTAMP.json"
echo "$CHAT_RESPONSE" > "debug_outputs/chat_response_$TIMESTAMP.json"

echo ""
echo "✅ Test complete. Results saved to debug_outputs/"
echo ""
echo "🔍 Analysis:"
if [ "$OPPORTUNITIES_COUNT" -eq "0" ]; then
  echo "❌ No opportunities found!"
  echo "Possible reasons:"
  echo "  1. User has $STRATEGY_COUNT strategies - need at least 1"
  echo "  2. Strategy scanners may have too high thresholds"
  echo "  3. Asset discovery service may not be returning assets"
  echo "  4. Service initialization issues"
else
  echo "✅ Found $OPPORTUNITIES_COUNT opportunities!"
fi