#!/bin/bash
# Test all chat capabilities

BASE_URL="https://cryptouniverse.onrender.com"
EMAIL="admin@cryptouniverse.com"
PASSWORD="AdminPass123!"

echo "🤖 Testing CryptoUniverse Chat Capabilities"
echo "=========================================="

# Login
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo $LOGIN_RESPONSE | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')

if [ -z "$TOKEN" ]; then
  echo "❌ Login failed"
  exit 1
fi

echo "✅ Logged in successfully"
echo ""

# Test 1: Get Chat Capabilities
echo "1. Getting platform capabilities..."
CAPABILITIES=$(curl -s -X GET "$BASE_URL/api/v1/chat/capabilities" \
  -H "Authorization: Bearer $TOKEN")

echo "Chat Capabilities:"
echo "$CAPABILITIES" | python3 -m json.tool 2>/dev/null || echo "$CAPABILITIES"
echo ""

# Test 2: Portfolio Analysis
echo "2. Testing Portfolio Analysis..."
PORTFOLIO_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/chat/message" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Analyze my portfolio and show me current holdings",
    "conversation_mode": "live_trading"
  }')

echo "Portfolio Analysis Response:"
echo "$PORTFOLIO_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('content', '')[:500] + '...')" 2>/dev/null
echo ""

# Test 3: Market Analysis
echo "3. Testing Market Analysis..."
MARKET_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/chat/message" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the current market sentiment for Bitcoin and Ethereum?",
    "conversation_mode": "analysis"
  }')

echo "Market Analysis Response:"
echo "$MARKET_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('content', '')[:500] + '...')" 2>/dev/null
echo ""

# Test 4: Trading Opportunities
echo "4. Testing Trading Opportunities..."
OPP_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/chat/message" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find me the best trading opportunities right now",
    "conversation_mode": "live_trading"
  }')

echo "Opportunities Response:"
echo "$OPP_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('content', '')[:500] + '...')" 2>/dev/null
echo ""

# Test 5: Strategy Information
echo "5. Testing Strategy Information..."
STRATEGY_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/chat/message" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What trading strategies do I have access to?",
    "conversation_mode": "learning"
  }')

echo "Strategy Response:"
echo "$STRATEGY_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('content', '')[:500] + '...')" 2>/dev/null
echo ""

# Test 6: Paper Trading
echo "6. Testing Paper Trading Mode..."
PAPER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/chat/message" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Switch to paper trading mode and show me how it works",
    "conversation_mode": "paper_trading"
  }')

echo "Paper Trading Response:"
echo "$PAPER_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('content', '')[:500] + '...')" 2>/dev/null

echo ""
echo "✅ Chat capability tests complete!"