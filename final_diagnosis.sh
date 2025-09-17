#!/bin/bash

echo "=== FINAL DIAGNOSIS ==="

TOKEN=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Get full response with longer timeout
echo "Getting full opportunity response..."
RESPONSE=$(curl -s --max-time 120 -X POST https://cryptouniverse.onrender.com/api/v1/opportunities/discover \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"limit": 5}')

# Save to file for analysis
echo "$RESPONSE" > /tmp/opportunity_response.json

# Check specific fields
echo "$RESPONSE" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    
    # Basic info
    print(f'Success: {d.get(\"success\")}')
    print(f'Scan ID: {d.get(\"scan_id\")}')
    print(f'Total opportunities: {d.get(\"total_opportunities\")}')
    
    # Asset discovery details
    asset_disc = d.get('asset_discovery', {})
    print(f'\\nAsset Discovery:')
    print(f'  Total assets: {asset_disc.get(\"total_assets_scanned\")}')
    print(f'  Asset tiers: {asset_disc.get(\"asset_tiers\")}')
    
    # User profile
    profile = d.get('user_profile', {})
    print(f'\\nUser Profile:')
    print(f'  Active strategies: {profile.get(\"active_strategies\")}')
    print(f'  User tier: {profile.get(\"user_tier\")}')
    
    # Strategy performance (should show scanner results)
    perf = d.get('strategy_performance', {})
    print(f'\\nStrategy Performance: {perf}')
    
    # Signal analysis
    sig = d.get('signal_analysis', {})
    if sig:
        print(f'\\nSignal Analysis:')
        print(f'  Total signals: {sig.get(\"total_signals_analyzed\")}')
        
except Exception as e:
    print(f'Error parsing response: {e}')
"

echo
echo "Response saved to /tmp/opportunity_response.json"