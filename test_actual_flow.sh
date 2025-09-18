#!/bin/bash

echo "=== TESTING ACTUAL TELEGRAM FLOW ==="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# 1. Test the unified chat directly
echo "1. Testing UnifiedChat endpoint directly with 'hi':"
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/chat/message \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "hi", "include_context": false}' | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'Success: {data.get(\"success\")}')
print(f'Response length: {len(data.get(\"response\", \"\"))}')
if data.get('response'):
    print(f'Response preview: {data[\"response\"][:200]}...')
"

# 2. Check if the issue is with UnifiedChatService import
echo -e "\n2. Checking service status:"
curl -s -X GET https://cryptouniverse.onrender.com/api/v1/system/health \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    services = data.get('services', {})
    print(f'Chat service: {services.get(\"chat\", \"Unknown\")}')
    print(f'Telegram service: {services.get(\"telegram\", \"Unknown\")}')
except:
    print('Could not parse health check')
"

# 3. Test AI consensus directly (what the fallback uses)
echo -e "\n3. Testing AI consensus service (fallback):"
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/ai/analyze \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_request": "Analyze this trading-related message and extract intent: hi",
    "confidence_threshold": 70.0
  }' | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(f'Success: {data.get(\"success\")}')
    print(f'Error: {data.get(\"error\", \"None\")}')
except Exception as e:
    print(f'Parse error: {e}')
"

