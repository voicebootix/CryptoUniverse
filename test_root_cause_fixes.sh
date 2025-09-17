#!/bin/bash

echo "=== Testing Root Cause Fixes ==="
echo "Date: $(date)"
echo ""

# Login
echo "1. Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@cryptouniverse.com",
    "password": "AdminPass123!"
  }')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$ACCESS_TOKEN" ]; then
    echo "Login failed!"
    exit 1
fi

echo "✅ Login successful!"

# Test Options Trading Fix
echo -e "\n2. Testing Options Trading (parameter fix)..."
OPTIONS_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function": "options_trade",
    "simulation_mode": true,
    "symbol": "BTC/USDT",
    "parameters": {
      "expiry_days": 30
    }
  }')

echo "$OPTIONS_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if data.get('success'):
        print('✅ OPTIONS FIXED! Strategy executed successfully')
        exec_result = data.get('execution_result', {})
        print(f'   Result keys: {list(exec_result.keys())[:5]}')
    else:
        error = data.get('error', 'Unknown')
        if 'StrategyParameters' in error:
            print('❌ STILL BROKEN: Parameter handling error')
        else:
            print(f'❌ Different error: {error[:100]}...')
except Exception as e:
    print(f'Parse error: {e}')
"

# Test Risk Management with urgency fix
echo -e "\n3. Testing Risk Management (urgency fix)..."
RISK_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function": "risk_management",
    "simulation_mode": true
  }')

echo "$RISK_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if data.get('success'):
        risk = data.get('risk_management_analysis', {})
        strategies = risk.get('mitigation_strategies', [])
        print(f'✅ Found {len(strategies)} mitigation strategies')
        
        # Check if urgency field is present
        for i, s in enumerate(strategies[:3]):
            urgency = s.get('urgency', 'MISSING')
            print(f'   {i+1}. {s.get(\"risk_type\")}: urgency={urgency} ({"✓" if urgency != "MISSING" else "✗"})')
except:
    print('❌ Error parsing response')
"

# Test full opportunity discovery
echo -e "\n4. Testing Full Opportunity Discovery..."
START_TIME=$(date +%s)

DISCOVERY_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/discover \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "force_refresh": true,
    "include_details": true
  }')

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "Response time: ${DURATION}s"

# Parse results
echo "$DISCOVERY_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    
    print(f'\\n📊 RESULTS:')
    print(f'Total opportunities: {data.get(\"total_opportunities\", 0)}')
    
    # Strategy breakdown
    perf = data.get('strategy_performance', {})
    print(f'\\nStrategies scanned: {len(perf)}')
    
    total = 0
    for strat, info in sorted(perf.items()):
        count = info.get('count', 0) if isinstance(info, dict) else info
        total += count
        status = '✅' if count > 0 else '❌'
        print(f'{status} {strat}: {count} opportunities')
    
    # Check specific improvements
    print(f'\\n🔍 IMPROVEMENTS:')
    
    # Risk opportunities
    risk_opps = [o for o in data.get('opportunities', []) if 'risk' in o.get('strategy_name', '').lower()]
    print(f'Risk Management: {len(risk_opps)} opportunities')
    if risk_opps:
        print('  Sample risks found:')
        for r in risk_opps[:3]:
            meta = r.get('metadata', {})
            print(f'  - {meta.get("risk_type")}: {meta.get("strategy")}')
    
    # Options opportunities  
    options_opps = [o for o in data.get('opportunities', []) if 'options' in o.get('strategy_name', '').lower()]
    print(f'\\nOptions Trading: {len(options_opps)} opportunities')
    if options_opps:
        print('  ✅ Options scanner is working!')
    
    # Portfolio opportunities
    portfolio_opps = [o for o in data.get('opportunities', []) if 'portfolio' in o.get('strategy_name', '').lower()]
    print(f'\\nPortfolio Optimization: {len(portfolio_opps)} opportunities')
    
except Exception as e:
    print(f'Parse error: {e}')
"

echo -e "\n\n=== SUMMARY ==="
echo "Check above for:"
echo "1. ✅ Options trading should work (no parameter error)"
echo "2. ✅ Risk strategies should have urgency values"
echo "3. ✅ More risk opportunities (with urgency > 0.3)"
echo "4. ❓ Options opportunities if contracts exist"

