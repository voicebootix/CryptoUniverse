#!/usr/bin/env python3
"""
Clear pending Telegram webhook updates
"""

import asyncio
import aiohttp
import os

async def clear_updates():
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '8302604205:AAFHfxC-_lmgB_RdupqgCHS-wKmCT4tBpio')
    
    print("🧹 Clearing pending Telegram updates...")
    
    # Get updates with high offset to clear them
    api_url = f"https://api.telegram.org/bot{bot_token}/getUpdates?timeout=1&offset=-1"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('ok'):
                        updates = data.get('result', [])
                        print(f"✅ Cleared {len(updates)} pending updates")
                        
                        # Verify webhook status
                        webhook_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
                        async with session.get(webhook_url) as resp:
                            if resp.status == 200:
                                webhook_data = await resp.json()
                                if webhook_data.get('ok'):
                                    info = webhook_data.get('result', {})
                                    print(f"📊 Pending updates now: {info.get('pending_update_count', 0)}")
                    else:
                        print(f"❌ API error: {data.get('description')}")
                else:
                    print(f"❌ HTTP error: {response.status}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(clear_updates())
