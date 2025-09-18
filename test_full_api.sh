#!/bin/bash

echo "Full API Test - Post Deployment"
echo "==============================="

# Login first
echo -e "\n1. Testing Login..."
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@cryptouniverse.com",
    "password": "AdminPass123!"
  }')

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "❌ Login failed!"
    echo $LOGIN_RESPONSE
    exit 1
fi

echo "✅ Login successful"

# Test strategy portfolio endpoint
echo -e "\n2. Testing Strategy Portfolio..."
PORTFOLIO=$(curl -s -X GET https://cryptouniverse.onrender.com/api/v1/strategies/my-strategies \
  -H "Authorization: Bearer $TOKEN")

echo "Response (first 200 chars):"
echo "$PORTFOLIO" | head -c 200

# Test market analysis
echo -e "\n\n3. Testing Market Analysis..."
MARKET=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/market-analysis/technical \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "symbols": ["BTC-USDT"],
    "exchange": "binance"
  }')

echo "Response (first 200 chars):"
echo "$MARKET" | head -c 200

# Test strategy execution with detailed output
echo -e "\n\n4. Testing Strategy Execution (detailed)..."
STRATEGY=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "strategy_function": "spot_momentum_strategy",
    "symbols": ["BTC-USDT"],
    "exchange": "binance"
  }')

echo "Full strategy response:"
echo "$STRATEGY" | python3 -m json.tool 2>/dev/null || echo "$STRATEGY"

# Test opportunity discovery with minimal params
echo -e "\n\n5. Testing Opportunity Discovery (minimal params)..."
OPP_MINIMAL=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/discover \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{}')

echo "Response:"
echo "$OPP_MINIMAL" | python3 -m json.tool 2>/dev/null || echo "$OPP_MINIMAL"

# Check server health
echo -e "\n\n6. Testing Health Check..."
HEALTH=$(curl -s https://cryptouniverse.onrender.com/health 2>/dev/null || echo "No health endpoint")
echo "Health response: $HEALTH"

echo -e "\n\nTest completed!"