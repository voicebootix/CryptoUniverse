#!/bin/bash

echo "=== Testing All Strategies After Enterprise Fix ==="
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
    echo "$LOGIN_RESPONSE"
    exit 1
fi

echo "✅ Login successful!"

# Test opportunity discovery with force refresh
echo -e "\n2. Testing opportunity discovery (force refresh)..."
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
echo ""

# Parse and display results
echo "=== Discovery Results ==="
echo "$DISCOVERY_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(f'Success: {data.get(\"success\")}')
    print(f'Total opportunities: {data.get(\"total_opportunities\", 0)}')
    print(f'Execution time: {data.get(\"execution_time_ms\", 0)}ms')
    
    # Check strategy performance
    perf = data.get('strategy_performance', {})
    print(f'\\n📊 Strategy Performance:')
    print(f'Total strategies scanned: {len(perf)}')
    
    if perf:
        print('\\nOpportunities by strategy:')
        for strat, info in perf.items():
            count = info.get('count', 0) if isinstance(info, dict) else info
            print(f'  • {strat}: {count} opportunities')
    
    # Show sample opportunities
    opps = data.get('opportunities', [])
    if opps:
        print(f'\\n✅ Sample opportunities (showing first 5):')
        for i, opp in enumerate(opps[:5], 1):
            print(f'\\n{i}. {opp.get(\"symbol\")} - {opp.get(\"strategy_name\")}')
            print(f'   Type: {opp.get(\"opportunity_type\")}')
            print(f'   Confidence: {opp.get(\"confidence_score\", 0):.1f}%')
            print(f'   Action: {opp.get(\"action\", \"N/A\")}')
            metadata = opp.get('metadata', {})
            if 'risk_type' in metadata:
                print(f'   Risk Type: {metadata.get(\"risk_type\")}')
                print(f'   Strategy: {metadata.get(\"strategy\")}')
            elif 'signal_strength' in metadata:
                print(f'   Signal Strength: {metadata.get(\"signal_strength\")}')
    else:
        print('\\n❌ No opportunities found')
        
    # Check for errors
    if data.get('error'):
        print(f'\\n❌ ERROR: {data.get(\"error\")}')
        
except Exception as e:
    print(f'Error parsing response: {e}')
    print('Raw response:')
    print(data if 'data' in locals() else sys.stdin.read())
"

# Test individual strategies to see what they return
echo -e "\n\n=== Testing Individual Strategy Responses ==="

echo -e "\n3. Risk Management Strategy:"
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function": "risk_management",
    "simulation_mode": true
  }' | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if data.get('success'):
        risk = data.get('risk_management_analysis', {})
        strategies = risk.get('mitigation_strategies', [])
        print(f'✅ Success! Found {len(strategies)} mitigation strategies')
        if strategies:
            print('Sample:', strategies[0].get('risk_type', ''), '-', strategies[0].get('strategy', ''))
    else:
        print('❌ Failed:', data.get('error', 'Unknown error'))
except:
    print('❌ Error parsing response')
"

echo -e "\n4. Portfolio Optimization Strategy:"
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function": "portfolio_optimization",
    "simulation_mode": true
  }' | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if data.get('success'):
        rebal = data.get('execution_result', {}).get('rebalancing_recommendations', [])
        print(f'✅ Success! Found {len(rebal)} rebalancing recommendations')
    else:
        print('❌ Failed:', data.get('error', 'Unknown error'))
except:
    print('❌ Error parsing response')
"

echo -e "\n5. Options Trade Strategy:"
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function": "options_trade",
    "simulation_mode": true,
    "symbol": "BTC/USDT"
  }' | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if data.get('success'):
        print('✅ Success! Options strategy executed')
        exec_result = data.get('execution_result', {})
        if 'greeks' in exec_result:
            print('Has Greeks data')
        if 'option_details' in exec_result:
            print('Has option details')
    else:
        print('❌ Failed:', data.get('error', 'Unknown error'))
except Exception as e:
    print(f'❌ Error: {e}')
"

