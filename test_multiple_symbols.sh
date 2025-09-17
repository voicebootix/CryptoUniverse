#!/bin/bash

echo "=== TESTING MULTIPLE SYMBOLS ==="

TOKEN=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Test different symbols
for SYMBOL in BTC ETH SOL BNB ADA DOGE; do
  echo
  echo "Testing $SYMBOL/USDT:"
  curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"function\": \"spot_momentum_strategy\",
      \"symbol\": \"$SYMBOL/USDT\",
      \"parameters\": {
        \"timeframe\": \"4h\"
      }
    }" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data.get('success'):
    sig = data['execution_result']['signal']
    ind = data['execution_result']['indicators']
    print(f'  RSI: {ind[\"rsi\"]:.1f}, MACD: {ind[\"macd_trend\"]}, Signal: {sig[\"action\"]} (strength={sig[\"strength\"]})')
else:
    print(f'  ERROR: {data}')
"
done

echo
echo "=== CHECKING ASSET DISCOVERY ==="
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/assets/discover \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tier": "tier_retail"}' | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'Response: {list(data.keys())}')
except:
    print('Not a valid JSON response')
"