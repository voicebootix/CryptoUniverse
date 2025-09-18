#!/bin/bash

echo "=== Checking Admin User's Actual Portfolio ==="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Check portfolio summary
echo "1. Portfolio Summary:"
curl -s -X GET https://cryptouniverse.onrender.com/api/v1/portfolio/summary \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'Total Value: ${data.get(\"total_value\", 0):,.2f}')
print(f'Positions: {data.get(\"total_positions\", 0)}')
"

# Check actual balances
echo -e "\n2. Exchange Balances:"
curl -s -X GET https://cryptouniverse.onrender.com/api/v1/exchanges/balances \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    balances = data.get('balances', {})
    
    # Show non-zero balances
    print('Non-zero balances:')
    for exchange, assets in balances.items():
        if isinstance(assets, dict):
            for asset, amount in assets.items():
                if amount > 0.01:
                    print(f'  {exchange} - {asset}: {amount:.4f}')
        elif isinstance(assets, list):
            for balance in assets:
                if balance.get('free', 0) > 0.01:
                    print(f'  {exchange} - {balance.get(\"asset\")}: {balance.get(\"free\")}')
except Exception as e:
    print(f'Error: {e}')
"

# Let me also check why portfolio optimization isn't using advanced algorithms
echo -e "\n3. Checking for Kelly Criterion and other optimization methods:"
grep -n "Kelly\|kelly\|sharpe\|mean.*variance\|black.*litterman" /workspace/app/services/trading_strategies.py | head -10

