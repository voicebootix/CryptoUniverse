#!/bin/bash

echo "=== PROVING THE ROOT CAUSE ==="

TOKEN=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Test strategies individually to see if they work
echo "1. Testing individual strategies:"
for STRATEGY in spot_momentum_strategy spot_mean_reversion spot_breakout_strategy; do
  echo -n "  $STRATEGY: "
  RESULT=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"function\": \"$STRATEGY\",
      \"symbol\": \"BTC/USDT\",
      \"parameters\": {\"timeframe\": \"4h\"}
    }")
  
  echo "$RESULT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if d.get('success'):
    sig = d['execution_result']['signal']
    print(f'Works! Signal: {sig[\"action\"]} (strength={sig[\"strength\"]})')
else:
    print(f'Failed: {d.get(\"error\", \"Unknown error\")}')
"
done

echo
echo "2. Checking portfolio strategies:"
curl -s -X GET https://cryptouniverse.onrender.com/api/v1/strategies/portfolio \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    if 'active_strategies' in d:
        print(f'Active strategies: {len(d[\"active_strategies\"])}')
        for s in d['active_strategies'][:3]:
            print(f'  - {s.get(\"strategy_id\")}: {s.get(\"name\")}')
    else:
        print('Response:', list(d.keys()))
except Exception as e:
    print('Error:', e)
"

echo
echo "3. Final proof - checking opportunity response structure:"
RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/discover \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"limit": 1}')

echo "$RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Success: {d[\"success\"]}')
print(f'Opportunities: {d[\"total_opportunities\"]}')
print(f'Assets scanned: {d[\"asset_discovery\"][\"total_assets_scanned\"]}')
print(f'Strategy performance: {len(d[\"strategy_performance\"])} entries')

# The smoking gun - if strategies work individually but not in discovery,
# it means the asset structure is wrong
if d['total_opportunities'] == 0 and d['asset_discovery']['total_assets_scanned'] > 0:
    print('\\n🔴 ROOT CAUSE: Assets are discovered but scanners fail to process them')
    print('   This happens when asset structure doesn\\'t match expected format')
"