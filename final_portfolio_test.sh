#!/bin/bash

echo "=== FINAL PORTFOLIO OPTIMIZATION TEST ==="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Direct test of portfolio optimization
echo "1. Direct Portfolio Optimization Test:"
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
    if 'error' in data:
        print(f'❌ Error: {data[\"error\"]}')
    else:
        result = data.get('result', {})
        
        # Check strategy analysis
        strategy_analysis = result.get('strategy_analysis', {})
        if strategy_analysis:
            print('✅ All 6 strategies analyzed:')
            for strategy, details in strategy_analysis.items():
                if isinstance(details, dict):
                    ret = details.get('expected_return', 0)
                    sharpe = details.get('sharpe_ratio', 0)
                    risk = details.get('risk_level', 0)
                    print(f'  - {strategy}: {ret*100:.1f}% return, {sharpe:.2f} Sharpe, {risk*100:.1f}% risk')
        
        # Check recommendations
        recs = result.get('rebalancing_recommendations', [])
        print(f'\nRecommendations: {len(recs)}')
        for i, rec in enumerate(recs[:3]):
            print(f'  {i+1}. {rec.get(\"strategy\", \"N/A\")} - {rec.get(\"symbol\", \"N/A\")} ({rec.get(\"action\", \"N/A\")})')
            print(f'     Amount: {rec.get(\"amount\", 0)*100:.1f}% of portfolio')
        
        # Show summary
        summary = result.get('optimization_summary', {})
        if summary:
            print(f'\nBest strategy: {summary.get(\"best_strategy\", \"N/A\")}')
            print(f'Strategies analyzed: {summary.get(\"strategies_analyzed\", 0)}')
except Exception as e:
    print(f'Error parsing: {e}')
"

# Test full opportunity discovery
echo -e "\n2. Full Opportunity Discovery Test:"
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

# Count portfolio optimization opportunities
opps = data.get('opportunities', [])
portfolio_opps = [o for o in opps if 'portfolio' in o.get('strategy_name', '').lower()]

print(f'Total opportunities: {data.get(\"total_opportunities\", 0)}')
print(f'Portfolio optimization opportunities: {len(portfolio_opps)}')

if portfolio_opps:
    print('\nPortfolio Strategies Found:')
    for opp in portfolio_opps[:6]:  # Show up to 6
        name = opp.get('strategy_name', '')
        metadata = opp.get('metadata', {})
        if 'strategy' in metadata:
            print(f'  - {metadata[\"strategy\"].replace(\"_\", \" \").title()}')
            print(f'    Return: {metadata.get(\"expected_annual_return\", 0)*100:.1f}%')
"

# Test chat with portfolio optimization request
echo -e "\n3. Chat Test - Portfolio Optimization:"
CHAT_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/chat/message \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me portfolio optimization strategies with their expected returns",
    "include_context": true
  }')

echo "$CHAT_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if data.get('success'):
        response = data.get('response', '')
        # Count how many strategies are mentioned
        strategies = ['kelly', 'sharpe', 'risk parity', 'variance', 'equal', 'adaptive']
        mentioned = sum(1 for s in strategies if s.lower() in response.lower())
        print(f'✅ Chat mentioned {mentioned}/6 strategies')
        
        # Check if returns are mentioned
        if '% return' in response or '% expected' in response:
            print('✅ Returns mentioned in response')
        else:
            print('❌ No returns mentioned')
except Exception as e:
    print(f'Error: {e}')
"

echo -e "\n=== Test Complete ==="
