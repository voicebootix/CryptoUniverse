#!/bin/bash

echo "=== Testing Final Enterprise Deployment ==="
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

# Parse and display comprehensive results
echo "=== 📊 COMPREHENSIVE RESULTS ==="
echo "$DISCOVERY_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    
    # Overall summary
    print(f'✅ Success: {data.get(\"success\")}')
    print(f'📈 Total opportunities: {data.get(\"total_opportunities\", 0)}')
    print(f'⏱️  Execution time: {data.get(\"execution_time_ms\", 0)/1000:.1f}s')
    
    # Strategy performance breakdown
    perf = data.get('strategy_performance', {})
    print(f'\\n�� STRATEGY BREAKDOWN:')
    print(f'Total strategies scanned: {len(perf)}')
    
    total_by_strategy = 0
    if perf:
        print('\\nOpportunities by strategy:')
        for strat, info in sorted(perf.items()):
            count = info.get('count', 0) if isinstance(info, dict) else info
            total_by_strategy += count
            emoji = '🚀' if 'momentum' in strat else '🛡️' if 'risk' in strat else '💼' if 'portfolio' in strat else '📈'
            print(f'  {emoji} {strat}: {count} opportunities')
    
    # Show opportunities grouped by strategy
    opps = data.get('opportunities', [])
    if opps:
        print(f'\\n✅ OPPORTUNITIES BY TYPE:')
        
        # Group by strategy
        by_strategy = {}
        for opp in opps:
            strat_name = opp.get('strategy_name', 'Unknown')
            if strat_name not in by_strategy:
                by_strategy[strat_name] = []
            by_strategy[strat_name].append(opp)
        
        # Display each strategy's opportunities
        for strat_name, strat_opps in by_strategy.items():
            print(f'\\n{strat_name} ({len(strat_opps)} opportunities):')
            for i, opp in enumerate(strat_opps[:3], 1):  # Show first 3
                symbol = opp.get('symbol', 'N/A')
                confidence = opp.get('confidence_score', 0)
                opp_type = opp.get('opportunity_type', '')
                metadata = opp.get('metadata', {})
                
                print(f'  {i}. {symbol}')
                print(f'     Confidence: {confidence:.1f}%')
                print(f'     Type: {opp_type}')
                
                # Show strategy-specific details
                if 'risk_type' in metadata:
                    print(f'     Risk: {metadata.get(\"risk_type\")}')
                    print(f'     Action: {metadata.get(\"strategy\")}')
                elif 'signal_strength' in metadata:
                    print(f'     Signal: {metadata.get(\"signal_strength\")}/10')
                    print(f'     Action: {metadata.get(\"signal_action\", \"N/A\")}')
                elif 'greeks' in metadata:
                    greeks = metadata.get('greeks', {})
                    print(f'     Greeks: Δ={greeks.get(\"delta\", 0):.2f}')
                elif 'rebalance_action' in metadata:
                    print(f'     Action: {metadata.get(\"rebalance_action\")}')
            
            if len(strat_opps) > 3:
                print(f'  ... and {len(strat_opps) - 3} more')
    else:
        print('\\n❌ No opportunities found')
    
    # Check for errors
    if data.get('error'):
        print(f'\\n❌ ERROR: {data.get(\"error\")}')
        
except Exception as e:
    print(f'Error parsing response: {e}')
"

# Test individual strategies to verify they're working
echo -e "\n\n=== 🔍 STRATEGY VERIFICATION ==="

echo -e "\n3. Options Trade Strategy (with fixed dates):"
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
        print('✅ Options strategy NOW WORKING!')
        exec_result = data.get('execution_result', {})
        print(f'   Strategy executed successfully')
        if 'error' not in str(data):
            print('   No more date/strike errors!')
    else:
        error = data.get('error', 'Unknown')
        if '2024' in error:
            print('❌ STILL using old dates!')
        elif 'contract not found' in error:
            print('❌ Contract error:', error[:100])
        else:
            print('❌ Failed:', error[:100])
except Exception as e:
    print(f'❌ Parse error: {e}')
"

echo -e "\n4. Risk Management (with lower thresholds):"
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
        print(f'✅ Found {len(strategies)} mitigation strategies')
        for s in strategies[:2]:
            print(f'   - {s.get(\"risk_type\", \"N/A\")}: {s.get(\"strategy\", \"N/A\")}')
except:
    print('❌ Error parsing response')
"

echo -e "\n\n=== 📊 FINAL SUMMARY ==="
echo "Testing complete. Check results above for:"
echo "1. Total opportunities across all strategies"
echo "2. Breakdown by each strategy type"
echo "3. Options trading now working with future dates"
echo "4. More opportunities from lowered thresholds"

