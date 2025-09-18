#!/usr/bin/env python3
"""
Simple Telegram Bot Test - Direct API calls without app dependencies
"""

import asyncio
import aiohttp
import os
import json
from datetime import datetime

class SimpleTelegramTest:
    def __init__(self):
        # Try to get bot token from environment or ask user
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.base_url = "https://cryptouniverse.onrender.com"
        
    async def test_bot_token(self):
        """Test if bot token works by calling Telegram API directly."""
        print("🤖 Testing Telegram Bot Token...")
        
        if not self.bot_token:
            print("❌ No TELEGRAM_BOT_TOKEN found in environment")
            print("💡 Set it with: set TELEGRAM_BOT_TOKEN=your_token_here")
            return False
        
        api_url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            bot_info = data.get('result', {})
                            print(f"✅ Bot token valid!")
                            print(f"   📝 Bot name: {bot_info.get('first_name')}")
                            print(f"   🏷️  Username: @{bot_info.get('username')}")
                            print(f"   🆔 Bot ID: {bot_info.get('id')}")
                            return True
                        else:
                            print(f"❌ Bot API error: {data.get('description')}")
                            return False
                    else:
                        print(f"❌ HTTP error: {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Error testing bot token: {str(e)}")
            return False
    
    async def test_webhook_info(self):
        """Check current webhook status."""
        print("\n🔗 Checking Webhook Status...")
        
        if not self.bot_token:
            print("❌ No bot token available")
            return
        
        api_url = f"https://api.telegram.org/bot{self.bot_token}/getWebhookInfo"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            info = data.get('result', {})
                            webhook_url = info.get('url', '')
                            
                            if webhook_url:
                                print(f"✅ Webhook configured: {webhook_url}")
                                print(f"   📊 Pending updates: {info.get('pending_update_count', 0)}")
                                
                                if info.get('last_error_date'):
                                    error_date = datetime.fromtimestamp(info.get('last_error_date'))
                                    print(f"   ⚠️  Last error: {info.get('last_error_message')}")
                                    print(f"   📅 Error date: {error_date}")
                            else:
                                print("❌ No webhook configured")
                                
                            return info
                        else:
                            print(f"❌ API error: {data.get('description')}")
                    else:
                        print(f"❌ HTTP error: {response.status}")
        except Exception as e:
            print(f"❌ Error checking webhook: {str(e)}")
        
        return None
    
    async def test_backend_webhook(self):
        """Test if backend webhook endpoint responds."""
        print("\n🌐 Testing Backend Webhook Endpoint...")
        
        webhook_url = f"{self.base_url}/api/v1/telegram/webhook"
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test OPTIONS (CORS)
                async with session.options(webhook_url) as response:
                    print(f"   📋 OPTIONS: {response.status}")
                
                # Test POST (webhook simulation)
                test_payload = {
                    "update_id": 123456789,
                    "message": {
                        "message_id": 1,
                        "from": {"id": 123456789, "first_name": "Test"},
                        "chat": {"id": 123456789, "type": "private"},
                        "date": int(datetime.now().timestamp()),
                        "text": "/test"
                    }
                }
                
                async with session.post(
                    webhook_url,
                    json=test_payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    status = response.status
                    response_text = await response.text()
                    
                    if status == 200:
                        print(f"   ✅ POST: {status} - Webhook endpoint working")
                    elif status == 401:
                        print(f"   ⚠️  POST: {status} - Webhook auth required (expected)")
                    elif status == 422:
                        print(f"   ⚠️  POST: {status} - Validation error (expected for test payload)")
                    else:
                        print(f"   ❌ POST: {status} - {response_text[:100]}...")
                    
                    return status in [200, 401, 422]
                    
        except Exception as e:
            print(f"❌ Error testing backend: {str(e)}")
            return False
    
    async def setup_webhook(self):
        """Setup webhook to point to our backend."""
        print("\n🔧 Setting up Webhook...")
        
        if not self.bot_token:
            print("❌ No bot token available")
            return False
        
        webhook_url = f"{self.base_url}/api/v1/telegram/webhook"
        api_url = f"https://api.telegram.org/bot{self.bot_token}/setWebhook"
        
        payload = {
            "url": webhook_url,
            "max_connections": 40,
            "allowed_updates": ["message", "callback_query"]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            print(f"✅ Webhook set successfully!")
                            print(f"   🔗 URL: {webhook_url}")
                            
                            # Verify setup
                            await asyncio.sleep(1)
                            await self.test_webhook_info()
                            return True
                        else:
                            print(f"❌ API error: {data.get('description')}")
                            return False
                    else:
                        print(f"❌ HTTP error: {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Error setting webhook: {str(e)}")
            return False
    
    async def run_diagnosis(self):
        """Run complete diagnosis."""
        print("🔍 CryptoUniverse Telegram Integration Test")
        print("=" * 50)
        
        # Test bot token
        bot_valid = await self.test_bot_token()
        
        if not bot_valid:
            print("\n❌ Cannot proceed without valid bot token")
            return
        
        # Test webhook status
        webhook_info = await self.test_webhook_info()
        
        # Test backend
        backend_ok = await self.test_backend_webhook()
        
        # Summary
        print("\n📊 DIAGNOSIS SUMMARY")
        print("=" * 50)
        
        print(f"Bot Token: {'✅ Valid' if bot_valid else '❌ Invalid'}")
        
        if webhook_info:
            has_webhook = bool(webhook_info.get('url'))
            print(f"Webhook: {'✅ Configured' if has_webhook else '❌ Not configured'}")
            if has_webhook:
                print(f"   URL: {webhook_info.get('url')}")
        else:
            print("Webhook: ❌ Could not check")
        
        print(f"Backend: {'✅ Accessible' if backend_ok else '❌ Not accessible'}")
        
        # Recommendations
        print("\n💡 RECOMMENDATIONS")
        print("=" * 50)
        
        if not webhook_info or not webhook_info.get('url'):
            print("1. Setup webhook with: python telegram_simple_test.py --setup-webhook")
        
        if webhook_info and webhook_info.get('url') != f"{self.base_url}/api/v1/telegram/webhook":
            print(f"2. Update webhook URL to: {self.base_url}/api/v1/telegram/webhook")
        
        if webhook_info and webhook_info.get('pending_update_count', 0) > 0:
            print("3. Clear pending updates - bot may have been offline")
        
        print("\n👥 USER AUTHENTICATION FLOW:")
        print("1. User connects Telegram in CryptoUniverse dashboard")
        print("2. User gets auth token from dashboard") 
        print("3. User messages bot: /auth <token>")
        print("4. Bot authenticates and enables trading commands")

async def main():
    import sys
    
    test = SimpleTelegramTest()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--setup-webhook':
        await test.setup_webhook()
    else:
        await test.run_diagnosis()

if __name__ == "__main__":
    # Check if we have the bot token
    if not os.getenv('TELEGRAM_BOT_TOKEN'):
        print("⚠️  TELEGRAM_BOT_TOKEN not found in environment")
        print("Please set it first:")
        print("Windows: set TELEGRAM_BOT_TOKEN=your_token_here")
        print("Linux/Mac: export TELEGRAM_BOT_TOKEN=your_token_here")
        print()
        token = input("Or enter your bot token now: ").strip()
        if token:
            os.environ['TELEGRAM_BOT_TOKEN'] = token
    
    asyncio.run(main())
