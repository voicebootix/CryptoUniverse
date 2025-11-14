#!/bin/bash
# Telegram Webhook Configuration Fix
# Simple curl-based fix for Telegram bot webhook issues

set -e  # Exit on any error

# Check if TELEGRAM_BOT_TOKEN is set
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ Error: TELEGRAM_BOT_TOKEN environment variable not set"
    echo "   Set it with: export TELEGRAM_BOT_TOKEN=your_bot_token"
    exit 1
fi

echo "🔧 Fixing Telegram webhook configuration..."
echo "   Bot Token: [REDACTED]"
echo "   Webhook URL: https://cryptouniverse.onrender.com/api/v1/telegram/webhook"

# Step 1: Remove existing webhook
echo "1️⃣  Removing existing webhook..."
DELETE_RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/deleteWebhook?drop_pending_updates=true")
if echo "$DELETE_RESPONSE" | grep -q '"ok":true'; then
    echo "   ✅ Existing webhook removed successfully"
else
    echo "   ❌ Error removing webhook: $DELETE_RESPONSE"
    exit 1
fi

# Wait a moment
sleep 2

# Step 2: Set proper webhook
echo "2️⃣  Setting webhook configuration..."
SET_RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://cryptouniverse.onrender.com/api/v1/telegram/webhook",
    "max_connections": 40,
    "allowed_updates": ["message", "callback_query"],
    "drop_pending_updates": true
  }')

if echo "$SET_RESPONSE" | grep -q '"ok":true'; then
    echo "   ✅ Webhook set successfully"
else
    echo "   ❌ Error setting webhook: $SET_RESPONSE"
    exit 1
fi

# Step 3: Verify webhook
echo "3️⃣  Verifying webhook configuration..."
INFO_RESPONSE=$(curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo")

if echo "$INFO_RESPONSE" | grep -q '"ok":true'; then
    echo "   ✅ Webhook configuration verified"
    echo "   📊 Webhook info:"
    echo "$INFO_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$INFO_RESPONSE"
else
    echo "   ❌ Error verifying webhook: $INFO_RESPONSE"
    exit 1
fi

echo ""
echo "🎉 SUCCESS: Telegram webhook configuration fixed!"
echo "✅ Bot should now respond to messages properly"
echo ""
echo "Next steps:"
echo "1. Open Telegram"
echo "2. Message @AI_ARCRYPTO_BOT"
echo "3. Send /start command"
echo "4. Bot should respond within 10-30 seconds"
