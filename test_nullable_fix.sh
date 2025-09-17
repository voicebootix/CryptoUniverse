#!/bin/bash

echo "Testing Nullable Fields Fix on CryptoUniverse"
echo "=============================================="

# First login
echo -e "\n1. Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@cryptouniverse.com",
    "password": "AdminPass123!"
  }')

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "Login failed!"
    echo $LOGIN_RESPONSE
    exit 1
fi

echo "Login successful!"

# Test opportunity discovery with force_refresh
echo -e "\n2. Testing opportunity discovery (with force_refresh)..."
START_TIME=$(date +%s)

OPPORTUNITIES=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/discover \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "force_refresh": true,
    "min_confidence": 0,
    "max_results": 10
  }')

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "Response time: ${DURATION}s"

# Extract key metrics
SUCCESS=$(echo $OPPORTUNITIES | grep -o '"success":[^,]*' | cut -d':' -f2)
TOTAL_OPPS=$(echo $OPPORTUNITIES | grep -o '"total_opportunities":[0-9]*' | cut -d':' -f2)
ASSETS_SCANNED=$(echo $OPPORTUNITIES | grep -o '"total_assets_scanned":[0-9]*' | cut -d':' -f2)
SIGNALS_ANALYZED=$(echo $OPPORTUNITIES | grep -o '"total_signals_analyzed":[0-9]*' | cut -d':' -f2)
ACTIVE_STRATS=$(echo $OPPORTUNITIES | grep -o '"active_strategies":[0-9]*' | cut -d':' -f2)

echo -e "\nResults:"
echo "  Success: $SUCCESS"
echo "  Total opportunities: $TOTAL_OPPS"
echo "  Assets scanned: $ASSETS_SCANNED"
echo "  Total signals analyzed: $SIGNALS_ANALYZED"
echo "  Active strategies: $ACTIVE_STRATS"

# Check if we have opportunities now
if [ "$TOTAL_OPPS" -gt 0 ]; then
    echo -e "\n✅ SUCCESS! Opportunities are now being generated!"
    
    # Show first opportunity details
    FIRST_OPP=$(echo $OPPORTUNITIES | grep -o '"opportunities":\[[^]]*' | head -1)
    echo -e "\nFirst opportunity sample:"
    echo $FIRST_OPP | python3 -m json.tool 2>/dev/null | head -20 || echo "(Unable to parse opportunity details)"
else
    echo -e "\n❌ Still no opportunities found"
    
    # Check for any error messages
    ERROR=$(echo $OPPORTUNITIES | grep -o '"error":"[^"]*' | cut -d'"' -f4)
    if [ ! -z "$ERROR" ]; then
        echo "  Error: $ERROR"
    fi
fi

# Test a specific strategy execution to verify it returns valid data
echo -e "\n3. Testing spot momentum strategy directly..."
STRATEGY_RESULT=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "strategy_function": "spot_momentum_strategy",
    "symbols": ["BTC-USDT"],
    "exchange": "binance"
  }')

# Check if risk_management fields are still null
TAKE_PROFIT=$(echo $STRATEGY_RESULT | grep -o '"take_profit":[^,}]*' | cut -d':' -f2)
STOP_LOSS=$(echo $STRATEGY_RESULT | grep -o '"stop_loss":[^,}]*' | cut -d':' -f2)

echo -e "\nStrategy risk_management values:"
echo "  take_profit: $TAKE_PROFIT"
echo "  stop_loss: $STOP_LOSS"

if [[ "$TAKE_PROFIT" == "null" ]] || [[ "$STOP_LOSS" == "null" ]]; then
    echo "  ⚠️  Warning: Strategy still returning null values"
else
    echo "  ✅ Strategy returning valid numeric values"
fi

echo -e "\nTest completed!"