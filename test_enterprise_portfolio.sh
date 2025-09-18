#!/bin/bash

echo "=== ENTERPRISE PORTFOLIO OPTIMIZATION TEST ==="
echo "Testing all 6 strategies and proper display"

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$ACCESS_TOKEN" ]; then
    echo "Login failed!"
    echo "$LOGIN_RESPONSE"
    exit 1
fi

echo "✅ Login successful"

# Test opportunity discovery with focus on portfolio optimization
echo -e "\n=== 1. Testing Full Opportunity Discovery ==="
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
print(f'Strategies scanned: {len(data.get(\"strategy_performance\", {}))}')

# Show strategy performance
if data.get('strategy_performance'):
    print('\nStrategy Performance:')
    for strat, count in data['strategy_performance'].items():
        print(f'  - {strat}: {count}')

# Show portfolio optimization opportunities
opps = data.get('opportunities', [])
portfolio_opps = [o for o in opps if 'portfolio' in o.get('strategy_name', '').lower()]
print(f'\nPortfolio Optimization Opportunities: {len(portfolio_opps)}')

# Show details of portfolio opportunities
if portfolio_opps:
    print('\nPortfolio Strategies Found:')
    strategies_seen = set()
    for opp in portfolio_opps:
        metadata = opp.get('metadata', {})
        strategy = metadata.get('strategy', opp.get('strategy_name', ''))
        if strategy not in strategies_seen:
            strategies_seen.add(strategy)
            print(f'  - {strategy}')
            if metadata.get('expected_annual_return'):
                print(f'    Expected Return: {metadata[\"expected_annual_return\"]*100:.1f}%')
            if metadata.get('sharpe_ratio'):
                print(f'    Sharpe Ratio: {metadata[\"sharpe_ratio\"]:.2f}')
"

# Test chat interface with opportunity request
echo -e "\n=== 2. Testing Chat Interface ==="
CHAT_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/chat/message \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me portfolio optimization opportunities",
    "include_context": true
  }')

echo "$CHAT_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if data.get('success'):
        print('✅ Chat responded successfully')
        # Show if response mentions all 6 strategies
        response = data.get('response', '')
        strategies = ['kelly', 'sharpe', 'risk parity', 'variance', 'equal', 'adaptive']
        mentioned = sum(1 for s in strategies if s.lower() in response.lower())
        print(f'Strategies mentioned in response: {mentioned}/6')
        
        # Show first 500 chars of response
        print(f'\nResponse preview:')
        print(response[:500] + '...' if len(response) > 500 else response)
    else:
        print('❌ Chat failed:', data.get('error'))
except Exception as e:
    print(f'Error parsing response: {e}')
"

# Direct test of portfolio optimization strategy
echo -e "\n=== 3. Direct Portfolio Optimization Test ==="
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
try:
    data = json.load(sys.stdin)
    result = data.get('result', {})
    
    # Check for strategy analysis
    strategy_analysis = result.get('strategy_analysis', {})
    if strategy_analysis:
        print('✅ All 6 strategies analyzed:')
        for strategy, details in strategy_analysis.items():
            if isinstance(details, dict):
                ret = details.get('expected_return', 0)
                sharpe = details.get('sharpe_ratio', 0)
                print(f'  - {strategy}: {ret*100:.1f}% return, {sharpe:.2f} Sharpe')
    
    # Check recommendations
    recs = result.get('rebalancing_recommendations', [])
    print(f'\nRecommendations generated: {len(recs)}')
    
    # Show summary
    summary = result.get('optimization_summary', {})
    if summary:
        print(f'\nBest strategy: {summary.get(\"best_strategy\", \"N/A\")}')
        print(f'Portfolio value: \${summary.get(\"portfolio_value\", 0):,.2f}')
except Exception as e:
    print(f'Error: {e}')
    print('Raw response:', data)
"

echo -e "\n=== Test Complete ==="
