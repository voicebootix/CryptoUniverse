#!/bin/bash

echo "=== TESTING TELEGRAM INTEGRATION WITH UNIFIEDCHAT ==="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Test different messages
test_messages=(
  "hi"
  "hello"
  "what are my opportunities?"
  "show me trading opportunities"
  "what's my balance?"
)

for msg in "${test_messages[@]}"; do
  echo -e "\n--- Testing: '$msg' ---"
  
  # Send via API (this will show what the bot would send)
  RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/telegram/send-message \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"$msg\", \"message_type\": \"info\"}")
  
  echo "$RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if data.get('success'):
        print('✅ Message sent to Telegram')
    else:
        print(f'❌ Error: {data.get(\"detail\", \"Unknown error\")}')
except:
    print('❌ Failed to parse response')
"
done

echo -e "\n=== CHECKING UNIFIEDCHAT DIRECTLY ==="
# Test the unified chat endpoint to see if it's working
curl -s -X POST https://cryptouniverse.onrender.com/api/v1/chat/message \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "hi", "include_context": false}' | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'UnifiedChat working: {data.get(\"success\", False)}')
print(f'Has response content: {len(data.get(\"response\", \"\")) > 0}')
if data.get('response'):
    print(f'Response preview: {data[\"response\"][:100]}...')
"

echo -e "\n=== SUMMARY ==="
echo "If you see the messages in Telegram:"
echo "1. Type a response directly in Telegram (don't use API)"
echo "2. Messages without '/' will use UnifiedChat"
echo "3. You should get intelligent AI responses"
echo ""
echo "The bot should now respond with the same AI as the web chat!"

