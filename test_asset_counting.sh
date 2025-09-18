#!/bin/bash

echo "=== TESTING ASSET COUNTING ==="

TOKEN=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Get the full response and check asset_discovery details
RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/discover \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"limit": 1}')

echo "$RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)

# Check what's in asset_discovery
asset_disc = d.get('asset_discovery', {})
print('Asset Discovery:')
print(f'  total_assets_scanned: {asset_disc.get(\"total_assets_scanned\")}')
print(f'  asset_tiers: {asset_disc.get(\"asset_tiers\")}')
print(f'  max_tier_accessed: {asset_disc.get(\"max_tier_accessed\")}')

# Check signal analysis
sig_analysis = d.get('signal_analysis', {})
print(f'\\nSignal Analysis:')
print(f'  total_signals_analyzed: {sig_analysis.get(\"total_signals_analyzed\")}')

# The key insight: if we have 600 assets but 0 signals,
# then momentum_symbols must be empty
print(f'\\nDiagnosis:')
if asset_disc.get('total_assets_scanned', 0) > 0 and sig_analysis.get('total_signals_analyzed', 0) == 0:
    print('  ❌ Assets are counted but not actually available to scanners')
    print('  ❌ This means discovered_assets has a different structure than expected')
    print('  ❌ Or the assets are being counted elsewhere (not from discovered_assets)')
"

# Try to access asset discovery directly
echo
echo "Testing asset discovery endpoint:"
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/assets/discover \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"min_tier": "tier_retail"}' | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(f'Response keys: {list(d.keys())}')
    if 'detail' in d:
        print(f'Error: {d[\"detail\"]}')
except:
    print('Failed to parse response')
"