#!/bin/bash

echo "Debugging Nullable Fields Fix"
echo "============================="

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

# Test strategy execution for multiple symbols to see what data we're getting
echo -e "\n2. Testing strategy execution for multiple symbols..."

SYMBOLS=("BTC-USDT" "ETH-USDT" "BNB-USDT")

for SYMBOL in "${SYMBOLS[@]}"; do
    echo -e "\nTesting $SYMBOL..."
    
    RESULT=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -d "{
        \"strategy_function\": \"spot_momentum_strategy\",
        \"symbols\": [\"$SYMBOL\"],
        \"exchange\": \"binance\"
      }")
    
    # Extract key values
    SUCCESS=$(echo $RESULT | grep -o '"success":[^,]*' | cut -d':' -f2)
    SIGNAL_STRENGTH=$(echo $RESULT | grep -o '"signal_strength":[^,]*' | cut -d':' -f2)
    TAKE_PROFIT=$(echo $RESULT | grep -o '"take_profit":[^,}]*' | cut -d':' -f2)
    STOP_LOSS=$(echo $RESULT | grep -o '"stop_loss":[^,}]*' | cut -d':' -f2)
    
    echo "  Success: $SUCCESS"
    echo "  Signal strength: $SIGNAL_STRENGTH"
    echo "  Take profit: $TAKE_PROFIT"
    echo "  Stop loss: $STOP_LOSS"
    
    # Show risk_management section
    RISK_MGMT=$(echo $RESULT | grep -o '"risk_management":{[^}]*}')
    echo "  Full risk_management: $RISK_MGMT"
done

# Now test opportunity discovery with detailed output
echo -e "\n3. Testing opportunity discovery with full response..."
FULL_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/discover \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "force_refresh": true,
    "min_confidence": 0,
    "max_results": 50
  }')

# Save full response for analysis
echo "$FULL_RESPONSE" > /tmp/opportunity_response.json

# Check if response contains any error information
if echo "$FULL_RESPONSE" | grep -q "error"; then
    echo -e "\nError found in response:"
    echo "$FULL_RESPONSE" | grep -o '"error":[^,]*' || echo "$FULL_RESPONSE" | grep -o '"message":[^,]*'
fi

# Check strategy_performance
STRAT_PERF=$(echo "$FULL_RESPONSE" | grep -o '"strategy_performance":{[^}]*}')
echo -e "\nStrategy performance: $STRAT_PERF"

# Check signal_analysis
SIGNAL_ANALYSIS=$(echo "$FULL_RESPONSE" | grep -o '"signal_analysis":{[^}]*}')
echo -e "\nSignal analysis: $SIGNAL_ANALYSIS"

echo -e "\nFull response saved to /tmp/opportunity_response.json"
echo "Response size: $(echo "$FULL_RESPONSE" | wc -c) bytes"

# Pretty print a portion of the response
echo -e "\nFirst 500 chars of response:"
echo "$FULL_RESPONSE" | head -c 500

echo -e "\n\nTest completed!"