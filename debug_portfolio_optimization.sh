#!/bin/bash

echo "=== Debugging Portfolio Optimization ==="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@cryptouniverse.com",
    "password": "AdminPass123!"
  }')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# 1. Test portfolio optimization directly
echo -e "\n1. Testing Portfolio Optimization Strategy Directly:"
PORTFOLIO_OPT=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function": "portfolio_optimization",
    "simulation_mode": true
  }')

echo "$PORTFOLIO_OPT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'Success: {data.get(\"success\")}')

# Check execution result
exec_result = data.get('execution_result', {})
if exec_result:
    print(f'Execution result keys: {list(exec_result.keys())}')
    
# Check for recommendations
rebal = exec_result.get('rebalancing_recommendations', [])
print(f'\\nRebalancing recommendations: {len(rebal)}')
if rebal:
    for r in rebal[:3]:
        print(f'  - {r.get(\"symbol\")}: {r.get(\"action\")}')
else:
    print('  (No recommendations generated)')

# Print full response structure
print(f'\\nFull response structure:')
import pprint
pprint.pprint(data, depth=3)
"

# 2. Get current portfolio to understand why no rebalancing
echo -e "\n\n2. Checking Current Portfolio State:"
curl -s -X GET https://cryptouniverse.onrender.com/api/v1/portfolio/holdings \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    holdings = data.get('holdings', [])
    print(f'Total holdings: {len(holdings)}')
    
    # Show position sizes and returns
    for h in holdings[:5]:
        symbol = h.get('symbol', 'N/A')
        weight = h.get('portfolio_weight', 0)
        pnl = h.get('unrealized_pnl_percentage', 0)
        days = h.get('holding_period_days', 0)
        print(f'  {symbol}: {weight:.1f}% weight, {pnl:.1f}% PnL, {days} days')
    
    # Check if conditions for rebalancing are met
    print(f'\\nRebalancing conditions:')
    print('  - Any position > 30 days with < 5% return?')
    print('  - Any position > 20% of portfolio?')
    print('  - Any position with > 15% gain (profit taking)?')
    print('  - Any position with > 10% loss (stop loss)?')
    
except Exception as e:
    print(f'Error: {e}')
"

# 3. Test position management directly to see raw analysis
echo -e "\n\n3. Testing Position Management (underlying function):"
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function": "position_management",
    "parameters": {
      "action": "analyze"
    },
    "simulation_mode": true
  }' | python3 -c "
import json, sys
data = json.load(sys.stdin)
if data.get('success'):
    print('Position management analysis completed')
    # Look for any recommendations
    exec_result = data.get('execution_result', {})
    if 'position_analysis' in str(exec_result):
        print('Has position analysis data')
else:
    print('Failed:', data.get('error', 'Unknown'))
"

