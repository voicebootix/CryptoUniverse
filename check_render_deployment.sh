#!/bin/bash
# Check what version is actually deployed on Render

BASE_URL="https://cryptouniverse.onrender.com"

echo "🔍 Checking Render Deployment Status"
echo "===================================="
echo ""

# Check health endpoint to see if service is up
echo "1. Checking service health..."
HEALTH_RESPONSE=$(curl -s "$BASE_URL/api/v1/health")
echo "Health check response received"

# Check for deployment info (if available)
echo ""
echo "2. Looking for deployment markers..."

# Try to find version info in the response
curl -s "$BASE_URL/api/v1/status" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(f'API Status: {d.get(\"status\")}')
    print(f'Version: {d.get(\"version\")}')
except:
    pass
"

# Check git commit info if exposed
echo ""
echo "3. Checking for git commit info..."
curl -s "$BASE_URL/api/v1/admin/system-info" 2>/dev/null | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    if 'git_commit' in d:
        print(f'Deployed commit: {d.get(\"git_commit\")}')
except:
    print('No git info available')
"

echo ""
echo "4. Testing for new response fields..."
# Quick test without auth to see error structure
TEST_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/opportunities/discover" \
  -H "Content-Type: application/json" \
  -d '{}')

if echo "$TEST_RESPONSE" | grep -q "signal_analysis"; then
  echo "✅ New 'signal_analysis' field detected - transparency update IS deployed!"
elif echo "$TEST_RESPONSE" | grep -q "threshold_transparency"; then
  echo "✅ New 'threshold_transparency' field detected - transparency update IS deployed!"
else
  echo "❌ New fields NOT detected - old version may still be running"
  echo ""
  echo "Response structure:"
  echo "$TEST_RESPONSE" | head -c 200
fi

echo ""
echo "5. Deployment Diagnosis:"
echo "========================"
echo "If the new fields aren't showing, possible reasons:"
echo "1. Render may still be building/deploying (takes 5-10 minutes)"
echo "2. Render may be caching the old version"
echo "3. The main branch might not have the latest changes"
echo ""
echo "To force a new deployment on Render:"
echo "1. Go to https://dashboard.render.com"
echo "2. Find your cryptouniverse service"
echo "3. Click 'Manual Deploy' > 'Deploy latest commit'"