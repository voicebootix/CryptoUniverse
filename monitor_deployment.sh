#!/bin/bash
# Monitor deployment and test when changes are live

BASE_URL="https://cryptouniverse.onrender.com"
EMAIL="admin@cryptouniverse.com"
PASSWORD="AdminPass123!"

echo "🔍 Monitoring for Deployment Changes"
echo "===================================="
echo "This script will check if the new signal analysis fields are present"
echo ""

# Login
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

# Function to check for new fields
check_deployment() {
  echo "Checking for deployment at $(date +%H:%M:%S)..."
  
  RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/opportunities/discover" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"force_refresh":true}')
  
  # Check for new fields
  if echo "$RESPONSE" | grep -q "signal_analysis"; then
    echo "✅ DEPLOYMENT DETECTED! New 'signal_analysis' field found!"
    echo ""
    echo "Full response:"
    echo "$RESPONSE" | python3 -m json.tool
    return 0
  elif echo "$RESPONSE" | grep -q "threshold_transparency"; then
    echo "✅ DEPLOYMENT DETECTED! New 'threshold_transparency' field found!"
    echo ""
    echo "Full response:"
    echo "$RESPONSE" | python3 -m json.tool
    return 0
  else
    # Check opportunity count
    OPP_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_opportunities', 0))" 2>/dev/null || echo "0")
    echo "❌ Old version still running. Opportunities: $OPP_COUNT"
    return 1
  fi
}

# Initial check
echo "Starting deployment monitoring..."
echo "Press Ctrl+C to stop"
echo ""

# Loop until deployment is detected
while true; do
  if check_deployment; then
    echo ""
    echo "🎉 Deployment successful! The new transparency features are live."
    
    # Show analysis
    echo ""
    echo "📊 Analyzing new response structure:"
    echo "$RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)

print(f'Total opportunities: {d.get(\"total_opportunities\", 0)}')

if 'signal_analysis' in d:
    sa = d['signal_analysis']
    print(f'\\nSignal Analysis:')
    print(f'  - Total signals analyzed: {sa.get(\"total_signals_analyzed\", 0)}')
    print(f'  - Signals by strength: {sa.get(\"signals_by_strength\", {})}')
    print(f'  - Above original threshold: {sa.get(\"threshold_analysis\", {}).get(\"opportunities_above_original\", 0)}')

if 'threshold_transparency' in d:
    print(f'\\nTransparency Message:')
    print(f'  {d[\"threshold_transparency\"].get(\"message\", \"\")}')
"
    break
  fi
  
  # Wait 30 seconds before next check
  echo "Waiting 30 seconds before next check..."
  sleep 30
done