#!/bin/bash
# Deep debug of opportunity generation

BASE_URL="https://cryptouniverse.onrender.com"
EMAIL="admin@cryptouniverse.com"
PASSWORD="AdminPass123!"

echo "🔍 Deep Debug: Opportunity Generation"
echo "===================================="

# Login
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo $LOGIN_RESPONSE | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')

# Test different opportunity request variations
echo "1. Testing with different parameters..."

# Test 1: Basic request
echo -e "\n📌 Test 1: Basic discovery"
curl -s -X POST "$BASE_URL/api/v1/opportunities/discover" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"force_refresh":true}' | \
  python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Success: {d.get(\"success\")}, Opportunities: {d.get(\"total_opportunities\")}, Error: {d.get(\"error\")}')"

# Test 2: With risk filter
echo -e "\n📌 Test 2: Low risk only"
curl -s -X POST "$BASE_URL/api/v1/opportunities/discover" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "force_refresh":true,
    "filter_by_risk_level":"low"
  }' | \
  python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Success: {d.get(\"success\")}, Opportunities: {d.get(\"total_opportunities\")}')"

# Test 3: With specific opportunity types
echo -e "\n📌 Test 3: Specific opportunity types"
curl -s -X POST "$BASE_URL/api/v1/opportunities/discover" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "force_refresh":true,
    "opportunity_type":["spot_momentum","pairs_trading"]
  }' | \
  python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Success: {d.get(\"success\")}, Opportunities: {d.get(\"total_opportunities\")}')"

# Test 4: Check what the chat says about opportunities
echo -e "\n📌 Test 4: Chat interpretation of opportunities"
CHAT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/chat/message" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How many trading opportunities are available right now? Please check the opportunity scanner.",
    "conversation_mode": "live_trading"
  }')

echo "$CHAT_RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
content = d.get('content', '')
# Look for numbers in the response
import re
numbers = re.findall(r'\d+', content)
print(f'Chat says: {content[:200]}...')
if numbers:
    print(f'Numbers mentioned: {numbers[:5]}')
"

# Test 5: Get raw opportunity data
echo -e "\n📌 Test 5: Full opportunity response (saving to file)"
FULL_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/opportunities/discover" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"force_refresh":true,"include_strategy_recommendations":true}')

echo "$FULL_RESPONSE" > deep_debug_opportunities_$(date +%Y%m%d_%H%M%S).json

# Analyze the response
echo -e "\n📊 Analysis of opportunity response:"
echo "$FULL_RESPONSE" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(f'Success: {d.get(\"success\")}')
    print(f'Total opportunities: {d.get(\"total_opportunities\")}')
    print(f'User has {d.get(\"user_profile\", {}).get(\"active_strategies\", 0)} active strategies')
    print(f'Assets scanned: {d.get(\"asset_discovery\", {}).get(\"total_assets_scanned\", 0)}')
    
    if d.get('opportunities'):
        print(f'\\nFirst opportunity:')
        opp = d['opportunities'][0]
        for k, v in opp.items():
            print(f'  {k}: {v}')
    
    if d.get('error'):
        print(f'\\nError: {d.get(\"error\")}')
    
    if d.get('strategy_performance'):
        print(f'\\nStrategy performance data: {len(d.get(\"strategy_performance\", {}))} entries')
        
except Exception as e:
    print(f'Error parsing response: {e}')
"