#!/bin/bash

echo "=== CHECKING TELEGRAM BOT SETUP ==="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Check if bot is configured
echo "1. Checking bot configuration:"
BOT_INFO=$(curl -s -X GET https://cryptouniverse.onrender.com/api/v1/telegram/bot-info \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "$BOT_INFO" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if data.get('bot_info'):
        info = data['bot_info']
        print(f'  Bot name: {info.get(\"username\", \"Not configured\")}')
        print(f'  Bot active: {info.get(\"success\", False)}')
    else:
        print('  ❌ Bot not configured or accessible')
except:
    print('  ❌ Could not parse bot info')
"

# Try to check webhook directly
echo -e "\n2. Checking webhook configuration:"
curl -s -X GET https://cryptouniverse.onrender.com/api/v1/telegram/webhook-info \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if 'error' in data:
        print(f'  ❌ Error: {data[\"error\"]}')
    elif data.get('webhook_info'):
        info = data['webhook_info']
        url = info.get('url', 'Not set')
        print(f'  Webhook URL: {url}')
        if url and url != 'Not set':
            print('  ✅ Webhook is configured')
        else:
            print('  ❌ Webhook not configured - bot cannot receive messages')
    else:
        print('  ❌ No webhook info available')
except Exception as e:
    print(f'  ❌ Error: {e}')
"

echo -e "\n=== SUMMARY ==="
echo "For natural language to work:"
echo "1. Webhook must be configured (to receive messages)"
echo "2. You must type directly in Telegram (not via API)"
echo "3. Messages without '/' are processed as natural language"
echo ""
echo "The /telegram/send-message API only sends messages FROM bot TO you."
echo "It does NOT process natural language queries."

