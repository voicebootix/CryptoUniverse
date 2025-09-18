#!/bin/bash

echo "=== TESTING ALL 6 PORTFOLIO OPTIMIZATION STRATEGIES ==="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Get opportunities and show all portfolio strategies
echo "Fetching opportunities..."
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/discover \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"scan_type": "comprehensive"}' | python3 -c "
import json, sys
data = json.load(sys.stdin)

print(f'✅ Total opportunities: {data.get(\"total_opportunities\", 0)}')
print(f'✅ Portfolio optimization opportunities: {data.get(\"strategy_performance\", {}).get(\"ai_portfolio_optimization\", {}).get(\"count\", 0)}')

# Extract all unique portfolio strategies
opps = data.get('opportunities', [])
portfolio_opps = [o for o in opps if 'portfolio' in o.get('strategy_name', '').lower()]

strategies_found = {}
for opp in portfolio_opps:
    metadata = opp.get('metadata', {})
    strategy = metadata.get('strategy_used', metadata.get('strategy', 'UNKNOWN'))
    if strategy not in strategies_found:
        strategies_found[strategy] = {
            'profit': opp.get('profit_potential_usd', 0),
            'improvement': metadata.get('improvement_potential', 0),
            'symbol': opp.get('symbol', '')
        }

print('\n📊 ALL 6 PORTFOLIO OPTIMIZATION STRATEGIES:')
print('='*50)
for i, (strategy, info) in enumerate(sorted(strategies_found.items()), 1):
    print(f'{i}. {strategy}')
    print(f'   💰 Profit Potential: \${info[\"profit\"]:,.0f}')
    print(f'   📈 Improvement: {info[\"improvement\"]*100:.1f}%')
    print('   ' + '-'*40)

# Show recommendation counts by strategy
strategy_counts = {}
for opp in portfolio_opps:
    metadata = opp.get('metadata', {})
    strategy = metadata.get('strategy_used', metadata.get('strategy', 'UNKNOWN'))
    strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

print('\n📋 RECOMMENDATIONS BY STRATEGY:')
for strategy, count in sorted(strategy_counts.items()):
    print(f'  • {strategy}: {count} recommendations')
"

# Test direct execution to see raw data
echo -e "\n\n=== RAW STRATEGY ANALYSIS FROM DIRECT EXECUTION ==="
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/strategies/execute \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"function": "portfolio_optimization", "symbol": "PORTFOLIO", "parameters": {}}' | python3 -c "
import json, sys
data = json.load(sys.stdin)
result = data.get('result', {})
analysis = result.get('strategy_analysis', {})

print('📊 Expected Returns by Strategy:')
print('='*50)
strategies = ['risk_parity', 'equal_weight', 'max_sharpe', 'min_variance', 'kelly_criterion', 'adaptive']
for i, strategy in enumerate(strategies, 1):
    if strategy in analysis:
        details = analysis[strategy]
        ret = details.get('expected_return', 0) * 100
        sharpe = details.get('sharpe_ratio', 0)
        print(f'{i}. {strategy.upper().replace(\"_\", \" \")}')
        print(f'   Expected Annual Return: {ret:.1f}%')
        print(f'   Sharpe Ratio: {sharpe:.2f}')
        print('   ' + '-'*40)

summary = result.get('optimization_summary', {})
print(f'\n🏆 BEST STRATEGY: {summary.get(\"best_strategy\", \"N/A\").upper().replace(\"_\", \" \")}')
print(f'💼 Current Portfolio Value: \${summary.get(\"portfolio_value\", 0):,.2f}')
print(f'📊 Total Recommendations: {summary.get(\"recommendations_generated\", 0)}')
"

