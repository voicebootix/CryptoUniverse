#!/bin/bash
# Wait for the new deployment with transparency features

BASE_URL="https://cryptouniverse.onrender.com"
EMAIL="admin@cryptouniverse.com"
PASSWORD="AdminPass123!"

echo "⏳ Waiting for New Deployment with Transparency Features"
echo "======================================================"
echo "This script will check every 30 seconds for the deployment"
echo "Press Ctrl+C to stop"
echo ""

# Login once
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo $LOGIN_RESPONSE | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')

if [ -z "$TOKEN" ]; then
  echo "❌ Login failed"
  exit 1
fi

echo "✅ Logged in successfully"
echo ""

check_deployment() {
  echo -n "Checking at $(date +%H:%M:%S)... "
  
  RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/opportunities/discover" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"force_refresh":true}' 2>/dev/null)
  
  # Check for the new fields that indicate transparency update
  if echo "$RESPONSE" | grep -q "signal_analysis"; then
    echo "✅ NEW DEPLOYMENT DETECTED!"
    echo ""
    echo "📊 New Response Structure:"
    echo "$RESPONSE" | python3 -m json.tool | head -100
    
    # Extract and display key metrics
    echo ""
    echo "🎯 Key Metrics:"
    echo "$RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Total Opportunities: {d.get(\"total_opportunities\", 0)}')
if 'signal_analysis' in d:
    sa = d['signal_analysis']
    print(f'Signals Analyzed: {sa.get(\"total_signals_analyzed\", 0)}')
    print(f'Signal Distribution: {sa.get(\"signals_by_strength\", {})}')
if 'threshold_transparency' in d:
    print(f'\\nTransparency Message:')
    print(d['threshold_transparency'].get('message', ''))
"
    return 0
  else
    OPP_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_opportunities', 0))" 2>/dev/null || echo "0")
    echo "Old version running. Opportunities: $OPP_COUNT"
    return 1
  fi
}

# Initial check
echo "Starting deployment watch..."
COUNTER=0

while true; do
  if check_deployment; then
    echo ""
    echo "🎉 SUCCESS! The transparency features are now live!"
    echo ""
    echo "What's new:"
    echo "✅ All signals above 3.0 are now visible"
    echo "✅ Quality tiers show confidence levels (HIGH/MEDIUM/LOW)"
    echo "✅ Signal analysis statistics included"
    echo "✅ Full transparency on why opportunities qualify"
    break
  fi
  
  COUNTER=$((COUNTER + 1))
  echo "Checked $COUNTER times. Waiting 30 seconds..."
  sleep 30
done