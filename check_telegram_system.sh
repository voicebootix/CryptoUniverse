#!/bin/bash

echo "=== CHECKING TELEGRAM SYSTEM STATUS ==="

# Login
LOGIN_RESPONSE=$(curl -s -X POST https://cryptouniverse.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@cryptouniverse.com", "password": "AdminPass123!"}')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# 1. Check if webhook is configured
echo "1. Webhook Status:"
curl -s -X GET https://cryptouniverse.onrender.com/api/v1/telegram/webhook-info \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if 'webhook_info' in data:
        info = data['webhook_info']
        print(f'  Webhook URL: {info.get(\"url\", \"Not set\")}')
        print(f'  Last error: {info.get(\"last_error_message\", \"None\")}')
        print(f'  Pending updates: {info.get(\"pending_update_count\", 0)}')
    else:
        print(f'  Error: {data}')
except Exception as e:
    print(f'  Failed to check webhook: {e}')
"

# 2. Check system health
echo -e "\n2. System Health:"
curl -s -X GET https://cryptouniverse.onrender.com/api/v1/system/health \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(f'  Overall status: {data.get(\"status\", \"Unknown\")}')
    services = data.get('services', {})
    if services:
        for service, status in services.items():
            print(f'  {service}: {status}')
except:
    print('  Could not check health')
"

# 3. Test a simple endpoint
echo -e "\n3. Testing Simple Endpoint:"
TEST_RESPONSE=$(curl -s -X GET https://cryptouniverse.onrender.com/api/v1/opportunities/status \
  -H "Authorization: Bearer $ACCESS_TOKEN")
echo "  Response received: $(echo "$TEST_RESPONSE" | wc -c) bytes"

# 4. Check if the bot can receive messages
echo -e "\n4. Telegram Connection:"
curl -s -X GET https://cryptouniverse.onrender.com/api/v1/telegram/connection \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if data.get('connection'):
        conn = data['connection']
        print(f'  Connected: {conn.get(\"is_active\", False)}')
        print(f'  Telegram username: {conn.get(\"telegram_username\", \"Not set\")}')
        print(f'  Chat ID: {conn.get(\"telegram_chat_id\", \"Not set\")}')
    else:
        print('  No Telegram connection found')
except:
    print('  Could not check connection')
"

echo -e "\n=== TROUBLESHOOTING ==="
echo "If the bot is not responding:"
echo "1. Check if webhook URL is set correctly"
echo "2. Ensure the bot has received your /auth command"
echo "3. Try sending /start to the bot first"
echo "4. Check if there are pending updates (webhook might be blocked)"

