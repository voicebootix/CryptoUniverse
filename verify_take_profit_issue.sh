#!/bin/bash

echo "=== VERIFYING THE TAKE_PROFIT NULL ISSUE ==="

TOKEN=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "1. Testing what spot_momentum_strategy actually returns:"
RESULT=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function": "spot_momentum_strategy",
    "symbol": "BTC/USDT",
    "parameters": {"timeframe": "4h"}
  }')

echo "$RESULT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if d.get('success'):
    exec_result = d.get('execution_result', {})
    risk_mgmt = exec_result.get('risk_management', {})
    print(f'risk_management: {risk_mgmt}')
    print(f'take_profit value: {risk_mgmt.get(\"take_profit\")}')
    print(f'take_profit type: {type(risk_mgmt.get(\"take_profit\"))}')
    
    # Check if it's None/null
    if risk_mgmt.get('take_profit') is None:
        print('\\n⚠️  CONFIRMED: take_profit is null/None')
"

echo
echo "2. Checking if this would cause TypeError in float conversion:"
echo "$RESULT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if d.get('success'):
    risk_mgmt = d.get('execution_result', {}).get('risk_management', {})
    try:
        # This is what the code does
        value = float(risk_mgmt.get('take_profit', 100))
        print(f'✅ No TypeError - default works: {value}')
    except TypeError as e:
        print(f'❌ TypeError: {e}')
"