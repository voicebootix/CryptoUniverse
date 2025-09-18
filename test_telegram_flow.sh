#!/bin/bash

echo "=== TESTING TELEGRAM MESSAGE FLOW ==="

# First, let's see what happens when we try to simulate a webhook message
echo "1. Testing webhook endpoint directly:"
curl -X POST https://cryptouniverse.onrender.com/api/v1/telegram/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": 123456789,
    "message": {
      "message_id": 1,
      "from": {
        "id": 123456789,
        "is_bot": false,
        "first_name": "Test"
      },
      "chat": {
        "id": 123456789,
        "type": "private"
      },
      "date": 1234567890,
      "text": "hi"
    }
  }' -v 2>&1 | grep -E "< HTTP|{.*}"

echo -e "\n2. The issue is likely:"
echo "   - You need to connect your Telegram account first"
echo "   - Go to the web UI → Settings → Telegram"
echo "   - Get the connection token"
echo "   - Send /auth <token> to the bot in Telegram"
echo ""
echo "3. After connecting, messages will flow like this:"
echo "   You → Telegram Bot → Webhook → UnifiedChat → AI Response → Back to you"

