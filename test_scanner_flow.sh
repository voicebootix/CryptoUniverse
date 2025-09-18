#!/bin/bash

echo "=== DIRECT SCANNER TEST ==="

TOKEN=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Test discovery with verbose output
echo "Testing discovery endpoint with force_refresh:"
RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/discover \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"limit": 5, "force_refresh": true}')

# Extract key info
echo "$RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)

print(f'Success: {d.get(\"success\")}')
print(f'Total opportunities: {d.get(\"total_opportunities\")}')
print(f'Assets scanned: {d.get(\"asset_discovery\", {}).get(\"total_assets_scanned\")}')

# Check signal analysis
sig_analysis = d.get('signal_analysis', {})
if sig_analysis:
    print(f'\\nSignal Analysis:')
    print(f'  Total signals analyzed: {sig_analysis.get(\"total_signals_analyzed\")}')
    
# Check strategy performance
perf = d.get('strategy_performance', {})
if perf:
    print(f'\\nStrategy Performance:')
    for strat, data in perf.items():
        print(f'  {strat}: {data}')
else:
    print(f'\\nStrategy Performance: Empty')

# Check if there's an error
if not d.get('success'):
    print(f'\\nError: {d.get(\"error\")}')
"