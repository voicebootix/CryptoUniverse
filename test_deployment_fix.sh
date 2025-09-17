#!/bin/bash

echo "=== Testing Deployed Fix - Portfolio Response Format ==="
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
    
    # Check user profile
    profile = data.get('user_profile', {})
    print(f'\\nUser Profile:')
    print(f'  Active strategies: {profile.get(\"active_strategy_count\", 0)}')
    print(f'  Risk level: {profile.get(\"risk_profile\", \"N/A\")}')
    
    # Check strategy performance  
    perf = data.get('strategy_performance', {})
    print(f'\\nStrategy Performance:')
    print(f'  Total strategies scanned: {len(perf)}')
    if perf:
        for strat, count in perf.items():
            print(f'  - {strat}: {count} opportunities')
    
    # Check asset discovery
    assets = data.get('asset_discovery', {})
    print(f'\\nAsset Discovery:')
    print(f'  Total assets scanned: {assets.get(\"total_assets_scanned\", 0)}')
    print(f'  Total signals analyzed: {assets.get(\"total_signals_analyzed\", 0)}')
    
    # Check signal analysis
    signals = data.get('signal_analysis')
    if signals:
        print(f'\\nSignal Analysis:')
        print(f'  Signals by strength: {signals.get(\"distribution\")}')
        
    # Check for errors
    if data.get('error'):
        print(f'\\n❌ ERROR: {data.get(\"error\")}')
        
    # Show first opportunity if any
    opps = data.get('opportunities', [])
    if opps:
        print(f'\\n✅ Found {len(opps)} opportunities!')
        print(f'\\nFirst opportunity:')
        opp = opps[0]
        print(f'  Symbol: {opp.get(\"symbol\")}')
        print(f'  Strategy: {opp.get(\"strategy_name\")}')
        print(f'  Signal: {opp.get(\"signal_strength\")}')
        print(f'  Action: {opp.get(\"action\")}')
    else:
        print(f'\\n❌ No opportunities found')
        
except Exception as e:
    print(f'Error parsing response: {e}')
    print('Raw response:')
    print(data if 'data' in locals() else sys.stdin.read())
"

# Check for specific issues
echo -e "\n=== Diagnostics ==="
if echo "$DISCOVERY_RESPONSE" | grep -q "User has no active strategies"; then
    echo "❌ CRITICAL: System still thinks user has no strategies!"
fi

if echo "$DISCOVERY_RESPONSE" | grep -q '"strategy_performance":{}'; then
    echo "⚠️  WARNING: Strategy performance is empty"
fi

if echo "$DISCOVERY_RESPONSE" | grep -q '"total_assets_scanned":0'; then
    echo "⚠️  WARNING: No assets were scanned"
fi

if echo "$DISCOVERY_RESPONSE" | grep -q "name 'final_response' is not defined"; then
    echo "❌ ERROR: Variable name error present"
fi

# Test portfolio endpoint to verify fix
echo -e "\n3. Testing portfolio endpoint to verify fix..."
PORTFOLIO_RESPONSE=$(curl -s -X GET https://cryptouniverse.onrender.com/api/v1/strategies/my-portfolio \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "Portfolio structure check:"
if echo "$PORTFOLIO_RESPONSE" | grep -q '"success":true'; then
    echo "✅ Portfolio has 'success: true'"
else
    echo "❌ Portfolio missing 'success: true'"
fi

if echo "$PORTFOLIO_RESPONSE" | grep -q '"active_strategies":\['; then
    echo "✅ Portfolio has 'active_strategies' array"
else
    echo "❌ Portfolio missing 'active_strategies' array"
fi

STRATEGY_COUNT=$(echo "$PORTFOLIO_RESPONSE" | grep -o '"strategy_id"' | wc -l)
echo "✅ Portfolio contains $STRATEGY_COUNT strategies"

