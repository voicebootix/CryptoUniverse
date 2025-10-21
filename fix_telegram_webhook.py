#!/usr/bin/env python3
"""
Fix Telegram webhook issues by resetting and reconfiguring
"""

import asyncio
import aiohttp
import os

async def fix_webhook():
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', 'your-telegram-bot-token')
    webhook_url = "https://your-domain.com/api/v1/telegram/webhook"
    
    print("🔧 Fixing Telegram webhook configuration...")
    
    async with aiohttp.ClientSession() as session:
        # Step 1: Remove current webhook to clear pending updates
        print("1️⃣  Removing current webhook...")
        delete_url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook?drop_pending_updates=true"
        
        async with session.post(delete_url) as response:
            if response.status == 200:
                data = await response.json()
                if data.get('ok'):
                    print("   ✅ Webhook removed and pending updates cleared")
                else:
                    print(f"   ❌ Error: {data.get('description')}")
            else:
                print(f"   ❌ HTTP error: {response.status}")
        
        # Step 2: Wait a moment
        await asyncio.sleep(2)
        
        # Step 3: Set webhook again (without secret for now)
        print("2️⃣  Setting webhook...")
        set_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
        payload = {
            "url": webhook_url,
            "max_connections": 40,
            "allowed_updates": ["message", "callback_query"],
            "drop_pending_updates": True
        }
        
        async with session.post(set_url, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                if data.get('ok'):
                    print(f"   ✅ Webhook set to: {webhook_url}")
                else:
                    print(f"   ❌ Error: {data.get('description')}")
            else:
                print(f"   ❌ HTTP error: {response.status}")
        
        # Step 4: Verify webhook
        print("3️⃣  Verifying webhook...")
        info_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
        
        async with session.get(info_url) as response:
            if response.status == 200:
                data = await response.json()
                if data.get('ok'):
                    info = data.get('result', {})
                    print(f"   ✅ Webhook URL: {info.get('url')}")
                    print(f"   📊 Pending updates: {info.get('pending_update_count', 0)}")
                    
                    if info.get('last_error_date'):
                        print(f"   ⚠️  Last error: {info.get('last_error_message')}")
                    else:
                        print("   ✅ No recent errors")
                else:
                    print(f"   ❌ Error: {data.get('description')}")
            else:
                print(f"   ❌ HTTP error: {response.status}")
        
        print("\n🎉 Webhook fix complete!")
        print("Now test by messaging your bot: @AI_ARCRYPTO_BOT")

if __name__ == "__main__":
    asyncio.run(fix_webhook())
