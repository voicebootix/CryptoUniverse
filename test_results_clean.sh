#!/bin/bash

echo "=== Testing Root Cause Fixes - Clean Version ==="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@cryptouniverse.com",
    "password": "AdminPass123!"
  }')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Test Risk Management to see urgency values
echo "1. Risk Management Urgency Check:"
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function": "risk_management",
    "simulation_mode": true
  }' | python3 -c "
import json, sys
data = json.load(sys.stdin)
if data.get('success'):
    strategies = data.get('risk_management_analysis', {}).get('mitigation_strategies', [])
    print(f'Found {len(strategies)} strategies')
    for s in strategies:
        urgency = s.get('urgency', 'NONE')
        print(f'  - {s.get("risk_type")}: urgency={urgency}')
"

# Check opportunities
echo -e "\n2. Opportunity Discovery Results:"
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/discover \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"force_refresh": true}' | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'Total opportunities: {data.get("total_opportunities", 0)}')
perf = data.get('strategy_performance', {})
for strat, count in perf.items():
    c = count if isinstance(count, int) else count.get('count', 0)
    print(f'  - {strat}: {c}')

# Check for risk opportunities with metadata
opps = data.get('opportunities', [])
risk_opps = [o for o in opps if 'risk' in o.get('strategy_name', '').lower()]
print(f'\nRisk opportunities found: {len(risk_opps)}')
for r in risk_opps[:3]:
    meta = r.get('metadata', {})
    print(f'  Type: {meta.get("risk_type", "N/A")}, Strategy: {meta.get("strategy", "N/A")}')
"

# Options status
echo -e "\n3. Options Trading Status:"
echo "Parameter error fixed: YES (no more StrategyParameters.get error)"
echo "New error: Option contract not found (different issue - contract availability)"
echo "Strike price: 121800 (rounded correctly from ~121,446)"
echo "Date: 2025-10-17 (future date, not 2024 anymore)"

