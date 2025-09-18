#!/bin/bash

echo "=== COMPREHENSIVE DEPLOYMENT VERIFICATION ==="
echo "Waiting 30 seconds for deployment..."
sleep 30

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$ACCESS_TOKEN" ]; then
    echo "❌ Login failed!"
    echo "$LOGIN_RESPONSE"
    exit 1
fi

echo "✅ Login successful"

# Test 1: Direct portfolio optimization execution
echo -e "\n=== TEST 1: Portfolio Optimization Direct Execution ==="
PORTFOLIO_OPT=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function": "portfolio_optimization",
    "symbol": "PORTFOLIO",
    "parameters": {}
  }')

echo "$PORTFOLIO_OPT" | python3 -c "
import json, sys
data = json.load(sys.stdin)

if 'error' in data:
    print(f'❌ Error: {data[\"error\"]}')
else:
    result = data.get('result', {})
    
    # Check strategy analysis
    strategy_analysis = result.get('strategy_analysis', {})
    if strategy_analysis:
        print('✅ Strategy analysis found:')
        for strategy, details in strategy_analysis.items():
            print(f'  - {strategy}: {details}')
    else:
        print('❌ No strategy analysis found')
    
    # Check recommendations
    recs = result.get('rebalancing_recommendations', [])
    print(f'\n✅ Recommendations: {len(recs)} found')
    
    # Check summary
    summary = result.get('optimization_summary', {})
    if summary:
        print(f'✅ Summary: Best strategy = {summary.get(\"best_strategy\")}')
"

# Test 2: Opportunity Discovery  
echo -e "\n=== TEST 2: Opportunity Discovery with Portfolio Optimization ==="
OPPORTUNITIES=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/discover \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scan_type": "comprehensive",
    "risk_tolerance": "balanced"
  }')

echo "$OPPORTUNITIES" | python3 -c "
import json, sys
data = json.load(sys.stdin)

print(f'Total opportunities: {data.get(\"total_opportunities\", 0)}')

# Count portfolio optimization opportunities
opps = data.get('opportunities', [])
portfolio_opps = [o for o in opps if 'portfolio' in o.get('strategy_name', '').lower()]
print(f'Portfolio optimization opportunities: {len(portfolio_opps)}')

# Show unique portfolio strategies
strategies = set()
for opp in portfolio_opps:
    metadata = opp.get('metadata', {})
    if metadata.get('strategy'):
        strategies.add(metadata['strategy'])

if strategies:
    print(f'✅ Portfolio strategies found: {strategies}')
else:
    print('❌ No portfolio strategies found')
"

# Test 3: Chat Interface
echo -e "\n=== TEST 3: Chat Interface Response ==="
CHAT_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/chat/message \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me portfolio rebalancing options",
    "include_context": true
  }')

echo "$CHAT_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if data.get('success'):
        response = data.get('response', '')
        
        # Check if response mentions portfolio strategies
        strategies = ['kelly', 'sharpe', 'risk parity', 'variance', 'equal', 'adaptive']
        mentioned = sum(1 for s in strategies if s.lower() in response.lower())
        
        if mentioned > 0:
            print(f'✅ Chat mentions {mentioned}/6 portfolio strategies')
        else:
            print('❌ Chat does not mention portfolio strategies')
            
        # Check response quality
        if 'portfolio' in response.lower() and 'optimization' in response.lower():
            print('✅ Chat discusses portfolio optimization')
        else:
            print('❌ Chat response lacks portfolio optimization content')
    else:
        print(f'❌ Chat error: {data.get(\"error\")}')
except Exception as e:
    print(f'❌ Error parsing chat response: {e}')
"

echo -e "\n=== DEPLOYMENT VERIFICATION COMPLETE ==="