#!/bin/bash
# Script to test opportunity scan API and check for issues

set -e

BASE_URL="${BASE_URL:-https://cryptouniverse.onrender.com}"
EMAIL="${ADMIN_EMAIL:-admin@cryptouniverse.com}"
PASSWORD="${ADMIN_PASSWORD:-AdminPass123!}"

echo "================================================================================"
echo "OPPORTUNITY SCAN API TEST"
echo "================================================================================"
echo "Base URL: $BASE_URL"
echo "Email: $EMAIL"
echo ""

# Login
echo "🔐 Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
USER_ID=$(echo "$LOGIN_RESPONSE" | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "❌ Login failed"
  echo "Response: $LOGIN_RESPONSE"
  exit 1
fi

echo "✅ Login successful"
echo "User ID: $USER_ID"
echo ""

# Initiate scan
echo "🚀 Initiating opportunity scan..."
SCAN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/opportunities/discover" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{}")

SCAN_ID=$(echo "$SCAN_RESPONSE" | grep -o '"scan_id":"[^"]*' | cut -d'"' -f4)

if [ -z "$SCAN_ID" ]; then
  echo "❌ Scan initiation failed"
  echo "Response: $SCAN_RESPONSE"
  exit 1
fi

echo "✅ Scan initiated"
echo "Scan ID: $SCAN_ID"
echo ""

# Monitor scan status
echo "📊 Monitoring scan status (60 polls, 3s interval)..."
echo ""

NOT_FOUND_COUNT=0
SCANNING_COUNT=0
COMPLETE_COUNT=0
TOTAL_POLLS=60

for i in $(seq 1 $TOTAL_POLLS); do
  STATUS_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/opportunities/status/$SCAN_ID" \
    -H "Authorization: Bearer $TOKEN")
  
  STATUS=$(echo "$STATUS_RESPONSE" | grep -o '"status":"[^"]*' | cut -d'"' -f4 || echo "unknown")
  
  if [ "$STATUS" = "not_found" ]; then
    NOT_FOUND_COUNT=$((NOT_FOUND_COUNT + 1))
  elif [ "$STATUS" = "scanning" ]; then
    SCANNING_COUNT=$((SCANNING_COUNT + 1))
  elif [ "$STATUS" = "complete" ]; then
    COMPLETE_COUNT=$((COMPLETE_COUNT + 1))
  fi
  
  # Extract progress info
  STRATEGIES_COMPLETED=$(echo "$STATUS_RESPONSE" | grep -o '"strategies_completed":[0-9]*' | cut -d':' -f2 || echo "0")
  TOTAL_STRATEGIES=$(echo "$STATUS_RESPONSE" | grep -o '"total_strategies":[0-9]*' | cut -d':' -f2 || echo "0")
  
  # Print every 10th poll or on status changes
  if [ $((i % 10)) -eq 0 ] || [ "$STATUS" = "complete" ] || [ "$STATUS" = "failed" ]; then
    echo "  Poll $i: status=$STATUS, progress=$STRATEGIES_COMPLETED/$TOTAL_STRATEGIES"
  fi
  
  if [ "$STATUS" = "complete" ]; then
    echo ""
    echo "✅ Scan completed at poll $i"
    break
  fi
  
  sleep 3
done

echo ""
echo "================================================================================"
echo "SUMMARY"
echo "================================================================================"
echo "Total polls: $TOTAL_POLLS"
echo "  - not_found: $NOT_FOUND_COUNT"
echo "  - scanning: $SCANNING_COUNT"
echo "  - complete: $COMPLETE_COUNT"
echo ""

if [ $NOT_FOUND_COUNT -gt 0 ]; then
  echo "⚠️  WARNING: Intermittent 'not_found' responses detected ($NOT_FOUND_COUNT/$TOTAL_POLLS)"
  echo "   This indicates lookup key issues in Redis."
fi

# Try to get results
if [ "$STATUS" = "complete" ]; then
  echo ""
  echo "📥 Fetching scan results..."
  
  for attempt in 1 2 3 4 5; do
    RESULTS_RESPONSE=$(curl -s -X GET "$BASE_URL/api/v1/opportunities/results/$SCAN_ID" \
      -H "Authorization: Bearer $TOKEN")
    
    RESULTS_STATUS=$(echo "$RESULTS_RESPONSE" | grep -o '"status":"[^"]*' | cut -d'"' -f4 || echo "unknown")
    
    if [ "$RESULTS_STATUS" != "not_found" ] && [ "$RESULTS_STATUS" != "error" ]; then
      echo "✅ Results fetched successfully on attempt $attempt"
      OPPORTUNITIES_COUNT=$(echo "$RESULTS_RESPONSE" | grep -o '"opportunities":\[.*\]' | grep -o 'opportunity' | wc -l || echo "0")
      echo "   Opportunities found: $OPPORTUNITIES_COUNT"
      break
    else
      echo "  Attempt $attempt: Results not available (status: $RESULTS_STATUS)"
      sleep 2
    fi
  done
  
  if [ "$RESULTS_STATUS" = "not_found" ] || [ "$RESULTS_STATUS" = "error" ]; then
    echo ""
    echo "❌ Results endpoint failed after 5 attempts"
    echo "   This indicates cache key resolution is failing."
  fi
fi

echo ""
echo "================================================================================"
echo "RECOMMENDATIONS"
echo "================================================================================"
echo "1. Check Render logs for:"
echo "   - 'Failed to resolve scan cache key'"
echo "   - 'opportunity_scan_lookup'"
echo "   - 'redis_error'"
echo "   - 'all_lookup_methods_failed'"
echo ""
echo "2. Verify Redis keys exist:"
echo "   - opportunity_scan_lookup:$SCAN_ID"
echo "   - opportunity_scan_result_index:$SCAN_ID"
echo "   - opportunity_user_latest_scan:$USER_ID"
echo ""
echo "3. Check TTL values - lookup keys should outlive cache entries"
echo ""
