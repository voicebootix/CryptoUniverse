#!/usr/bin/env python3
"""
Telegram Webhook Configuration Fix
This script ensures the Telegram bot webhook is properly configured for responses.
"""

import asyncio
import aiohttp
import os
from typing import Optional

class TelegramWebhookFixer:
    """Handles Telegram webhook configuration fixes."""
    
    def __init__(self, bot_token: Optional[str] = None, webhook_url: Optional[str] = None):
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.webhook_url = webhook_url or os.getenv('TELEGRAM_WEBHOOK_URL', 
                                                   'https://cryptouniverse.onrender.com/api/v1/telegram/webhook')
    
    async def fix_webhook_configuration(self) -> bool:
        """
        Fix Telegram webhook configuration to ensure proper message handling.
        
        Returns:
            bool: True if webhook was successfully configured, False otherwise
        """
        if not self.bot_token:
            print("❌ Error: TELEGRAM_BOT_TOKEN not found in environment variables")
            return False
        
        print(f"🔧 Fixing Telegram webhook configuration...")
        print(f"   Bot Token: [REDACTED]")
        print(f"   Webhook URL: {self.webhook_url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Step 1: Remove existing webhook to clear conflicts
                success = await self._remove_existing_webhook(session)
                if not success:
                    return False
                
                # Step 2: Wait for cleanup
                await asyncio.sleep(2)
                
                # Step 3: Set proper webhook configuration
                success = await self._set_webhook(session)
                if not success:
                    return False
                
                # Step 4: Verify webhook is working
                success = await self._verify_webhook(session)
                return success
                
        except Exception as e:
            print(f"❌ Error during webhook configuration: {e}")
            return False
    
    async def _remove_existing_webhook(self, session: aiohttp.ClientSession) -> bool:
        """Remove existing webhook to clear conflicts."""
        print("1️⃣  Removing existing webhook...")
        
        delete_url = f"https://api.telegram.org/bot{self.bot_token}/deleteWebhook?drop_pending_updates=true"
        
        try:
            async with session.post(delete_url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('ok'):
                        print("   ✅ Existing webhook removed successfully")
                        return True
                    else:
                        print(f"   ❌ Error removing webhook: {data.get('description')}")
                        return False
                else:
                    print(f"   ❌ HTTP error removing webhook: {response.status}")
                    return False
        except Exception as e:
            print(f"   ❌ Exception removing webhook: {e}")
            return False
    
    async def _set_webhook(self, session: aiohttp.ClientSession) -> bool:
        """Set proper webhook configuration."""
        print("2️⃣  Setting webhook configuration...")
        
        set_url = f"https://api.telegram.org/bot{self.bot_token}/setWebhook"
        payload = {
            "url": self.webhook_url,
            "max_connections": 40,
            "allowed_updates": ["message", "callback_query"],
            "drop_pending_updates": True
        }
        
        try:
            async with session.post(set_url, json=payload, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('ok'):
                        print(f"   ✅ Webhook set successfully to: {self.webhook_url}")
                        return True
                    else:
                        print(f"   ❌ Error setting webhook: {data.get('description')}")
                        return False
                else:
                    print(f"   ❌ HTTP error setting webhook: {response.status}")
                    return False
        except Exception as e:
            print(f"   ❌ Exception setting webhook: {e}")
            return False
    
    async def _verify_webhook(self, session: aiohttp.ClientSession) -> bool:
        """Verify webhook is properly configured."""
        print("3️⃣  Verifying webhook configuration...")
        
        info_url = f"https://api.telegram.org/bot{self.bot_token}/getWebhookInfo"
        
        try:
            async with session.get(info_url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('ok'):
                        webhook_info = data.get('result', {})
                        print(f"   ✅ Webhook URL: {webhook_info.get('url')}")
                        print(f"   ✅ Max Connections: {webhook_info.get('max_connections', 'N/A')}")
                        print(f"   ✅ Pending Updates: {webhook_info.get('pending_update_count', 0)}")
                        
                        if webhook_info.get('last_error_date'):
                            print(f"   ⚠️  Last Error: {webhook_info.get('last_error_message')}")
                        else:
                            print(f"   ✅ Status: No recent errors")
                        
                        return True
                    else:
                        print(f"   ❌ Error getting webhook info: {data.get('description')}")
                        return False
                else:
                    print(f"   ❌ HTTP error getting webhook info: {response.status}")
                    return False
        except Exception as e:
            print(f"   ❌ Exception verifying webhook: {e}")
            return False

async def main():
    """Main function to fix Telegram webhook configuration."""
    print("="*60)
    print("TELEGRAM WEBHOOK CONFIGURATION FIX")
    print("="*60)
    
    fixer = TelegramWebhookFixer()
    success = await fixer.fix_webhook_configuration()
    
    print("\n" + "="*60)
    print("FIX SUMMARY")
    print("="*60)
    
    if success:
        print("✅ SUCCESS: Telegram webhook configuration fixed")
        print("✅ Bot should now respond to messages properly")
        print("\nNext steps:")
        print("1. Test by messaging @AI_ARCRYPTO_BOT")
        print("2. Send /start command")
        print("3. Bot should respond within 10-30 seconds")
    else:
        print("❌ FAILED: Could not fix webhook configuration")
        print("Check your TELEGRAM_BOT_TOKEN and network connection")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
