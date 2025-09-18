#!/bin/bash

echo "Testing with Corrected API Parameters"
echo "===================================="

# Login first
echo -e "\n1. Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@cryptouniverse.com",
    "password": "AdminPass123!"
  }')

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "❌ Login failed!"
    exit 1
fi

echo "✅ Login successful"

# Test strategy execution with correct field name
echo -e "\n2. Testing Strategy Execution (corrected)..."
STRATEGY=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "function": "spot_momentum_strategy",
    "symbols": ["BTC-USDT"],
    "exchange": "binance"
  }')

echo "Strategy response:"
echo "$STRATEGY" | python3 -m json.tool 2>/dev/null | head -30 || echo "$STRATEGY" | head -200

# Extract risk management values
TAKE_PROFIT=$(echo "$STRATEGY" | grep -o '"take_profit":[^,}]*' | cut -d':' -f2)
STOP_LOSS=$(echo "$STRATEGY" | grep -o '"stop_loss":[^,}]*' | cut -d':' -f2)

echo -e "\nRisk management values:"
echo "  take_profit: $TAKE_PROFIT"
echo "  stop_loss: $STOP_LOSS"

# Test opportunity discovery with force_refresh
echo -e "\n3. Testing Opportunity Discovery with force_refresh..."
START_TIME=$(date +%s)

OPPORTUNITIES=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/discover \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "force_refresh": true,
    "min_confidence": 0,
    "max_results": 50
  }')

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "Response time: ${DURATION}s"

# Check key metrics
SUCCESS=$(echo "$OPPORTUNITIES" | grep -o '"success":[^,]*' | cut -d':' -f2)
TOTAL_OPPS=$(echo "$OPPORTUNITIES" | grep -o '"total_opportunities":[0-9]*' | cut -d':' -f2)
EXEC_TIME=$(echo "$OPPORTUNITIES" | grep -o '"execution_time_ms":[0-9.]*' | cut -d':' -f2)

echo -e "\nResults:"
echo "  Success: $SUCCESS"
echo "  Total opportunities: $TOTAL_OPPS"
echo "  Execution time (ms): $EXEC_TIME"

# Show detailed response
echo -e "\nDetailed response:"
echo "$OPPORTUNITIES" | python3 -m json.tool 2>/dev/null | head -50 || echo "$OPPORTUNITIES" | head -500

# If we have opportunities, show one
if [ "$TOTAL_OPPS" -gt 0 ]; then
    echo -e "\n✅ SUCCESS! Opportunities found!"
    echo -e "\nFirst opportunity:"
    echo "$OPPORTUNITIES" | grep -o '"opportunities":\[[^]]*' | python3 -m json.tool 2>/dev/null | head -30
else
    echo -e "\n❌ Still no opportunities"
    
    # Check for errors
    ERROR_MSG=$(echo "$OPPORTUNITIES" | grep -o '"error":"[^"]*' | cut -d'"' -f4)
    if [ ! -z "$ERROR_MSG" ]; then
        echo "  Error: $ERROR_MSG"
    fi
fi

echo -e "\nTest completed!"