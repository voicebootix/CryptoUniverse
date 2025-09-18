#!/usr/bin/env python3
"""
Telegram Integration Diagnostic Tool
Diagnoses and fixes Telegram bot integration issues for CryptoUniverse.
"""

import asyncio
import os
import sys
import json
import aiohttp
from datetime import datetime
from typing import Dict, Any, Optional

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import get_settings
from app.services.telegram_core import TelegramAPIConnector

class TelegramDiagnostic:
    def __init__(self):
        self.settings = get_settings()
        self.telegram_api = TelegramAPIConnector()
        self.results = {}
        
    async def run_full_diagnosis(self):
        """Run comprehensive Telegram integration diagnosis."""
        print("🔍 CryptoUniverse Telegram Integration Diagnostic")
        print("=" * 60)
        
        # Check 1: Environment Configuration
        await self.check_environment_config()
        
        # Check 2: Bot Token Validity
        await self.check_bot_token()
        
        # Check 3: Webhook Configuration
        await self.check_webhook_status()
        
        # Check 4: Backend Webhook Endpoint
        await self.check_backend_webhook()
        
        # Check 5: Database Connection Status
        await self.check_database_connection()
        
        # Generate Report
        self.generate_report()
        
        # Provide Fixes
        await self.suggest_fixes()
    
    async def check_environment_config(self):
        """Check environment variable configuration."""
        print("\n📋 1. Environment Configuration Check")
        print("-" * 40)
        
        config_status = {
            'TELEGRAM_BOT_TOKEN': bool(self.settings.TELEGRAM_BOT_TOKEN),
            'BASE_URL': bool(self.settings.BASE_URL),
            'ENVIRONMENT': self.settings.ENVIRONMENT,
        }
        
        self.results['environment'] = config_status
        
        for key, status in config_status.items():
            if isinstance(status, bool):
                emoji = "✅" if status else "❌"
                print(f"  {emoji} {key}: {'Configured' if status else 'Missing'}")
            else:
                print(f"  ℹ️  {key}: {status}")
        
        if not self.settings.TELEGRAM_BOT_TOKEN:
            print("  ⚠️  TELEGRAM_BOT_TOKEN is required for Telegram integration")
    
    async def check_bot_token(self):
        """Check if bot token is valid."""
        print("\n🤖 2. Bot Token Validation")
        print("-" * 40)
        
        if not self.settings.TELEGRAM_BOT_TOKEN:
            print("  ❌ No bot token configured")
            self.results['bot_token'] = {'valid': False, 'error': 'No token'}
            return
        
        try:
            bot_info = await self.telegram_api.get_bot_info()
            
            if bot_info.get('success'):
                bot_data = bot_info.get('bot_info', {})
                print(f"  ✅ Bot token valid")
                print(f"  📝 Bot name: {bot_data.get('first_name', 'Unknown')}")
                print(f"  🏷️  Username: @{bot_data.get('username', 'Unknown')}")
                print(f"  🆔 Bot ID: {bot_data.get('id', 'Unknown')}")
                
                self.results['bot_token'] = {
                    'valid': True,
                    'bot_info': bot_data
                }
            else:
                print(f"  ❌ Bot token invalid: {bot_info.get('error')}")
                self.results['bot_token'] = {
                    'valid': False,
                    'error': bot_info.get('error')
                }
                
        except Exception as e:
            print(f"  ❌ Error checking bot token: {str(e)}")
            self.results['bot_token'] = {'valid': False, 'error': str(e)}
    
    async def check_webhook_status(self):
        """Check current webhook configuration."""
        print("\n🔗 3. Webhook Status Check")
        print("-" * 40)
        
        if not self.settings.TELEGRAM_BOT_TOKEN:
            print("  ❌ Cannot check webhook without bot token")
            return
        
        try:
            webhook_info = await self.telegram_api.get_webhook_info()
            
            if webhook_info.get('success'):
                info = webhook_info.get('webhook_info', {})
                webhook_url = info.get('url', '')
                
                if webhook_url:
                    print(f"  ✅ Webhook configured")
                    print(f"  🔗 URL: {webhook_url}")
                    print(f"  📊 Pending updates: {info.get('pending_update_count', 0)}")
                    
                    if info.get('last_error_date'):
                        print(f"  ⚠️  Last error: {info.get('last_error_message', 'Unknown')}")
                        print(f"  📅 Error date: {datetime.fromtimestamp(info.get('last_error_date'))}")
                else:
                    print("  ❌ No webhook configured")
                
                self.results['webhook'] = {
                    'configured': bool(webhook_url),
                    'info': info
                }
            else:
                print(f"  ❌ Error getting webhook info: {webhook_info.get('error')}")
                self.results['webhook'] = {
                    'configured': False,
                    'error': webhook_info.get('error')
                }
                
        except Exception as e:
            print(f"  ❌ Error checking webhook: {str(e)}")
            self.results['webhook'] = {'configured': False, 'error': str(e)}
    
    async def check_backend_webhook(self):
        """Check if backend webhook endpoint is accessible."""
        print("\n🌐 4. Backend Webhook Endpoint Check")
        print("-" * 40)
        
        if not self.settings.BASE_URL:
            print("  ❌ BASE_URL not configured")
            return
        
        webhook_url = f"{self.settings.BASE_URL}/api/v1/telegram/webhook"
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test OPTIONS request (CORS preflight)
                async with session.options(webhook_url) as response:
                    options_status = response.status
                    print(f"  📋 OPTIONS request: {options_status}")
                
                # Test POST request (webhook simulation)
                test_payload = {"message": {"text": "test"}}
                async with session.post(
                    webhook_url,
                    json=test_payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    post_status = response.status
                    response_text = await response.text()
                    
                    if post_status == 200:
                        print(f"  ✅ POST webhook: {post_status} - Endpoint accessible")
                    elif post_status == 401:
                        print(f"  ⚠️  POST webhook: {post_status} - Webhook auth required (normal)")
                    else:
                        print(f"  ❌ POST webhook: {post_status} - {response_text[:100]}")
                
                self.results['backend_webhook'] = {
                    'accessible': post_status in [200, 401],
                    'options_status': options_status,
                    'post_status': post_status,
                    'url': webhook_url
                }
                
        except Exception as e:
            print(f"  ❌ Error checking backend webhook: {str(e)}")
            self.results['backend_webhook'] = {
                'accessible': False,
                'error': str(e),
                'url': webhook_url
            }
    
    async def check_database_connection(self):
        """Check database connectivity for Telegram integration."""
        print("\n🗄️  5. Database Connection Check")
        print("-" * 40)
        
        try:
            from app.core.database import get_database
            from app.models.telegram_integration import UserTelegramConnection
            from sqlalchemy import select
            
            # Test database connection
            async for db in get_database():
                try:
                    # Simple query to test connection
                    result = await db.execute(select(UserTelegramConnection).limit(1))
                    print("  ✅ Database connection successful")
                    print("  📊 Telegram connections table accessible")
                    
                    # Count existing connections
                    count_result = await db.execute(
                        select(UserTelegramConnection).where(
                            UserTelegramConnection.is_active == True
                        )
                    )
                    active_connections = len(count_result.scalars().all())
                    print(f"  📈 Active Telegram connections: {active_connections}")
                    
                    self.results['database'] = {
                        'accessible': True,
                        'active_connections': active_connections
                    }
                    break
                    
                except Exception as e:
                    print(f"  ❌ Database query error: {str(e)}")
                    self.results['database'] = {
                        'accessible': False,
                        'error': str(e)
                    }
                    break
                    
        except Exception as e:
            print(f"  ❌ Database connection error: {str(e)}")
            self.results['database'] = {
                'accessible': False,
                'error': str(e)
            }
    
    def generate_report(self):
        """Generate diagnostic report."""
        print("\n📊 DIAGNOSTIC REPORT")
        print("=" * 60)
        
        # Overall status
        issues = []
        
        if not self.results.get('environment', {}).get('TELEGRAM_BOT_TOKEN'):
            issues.append("❌ Telegram bot token not configured")
        
        if not self.results.get('bot_token', {}).get('valid'):
            issues.append("❌ Bot token invalid or unreachable")
        
        if not self.results.get('webhook', {}).get('configured'):
            issues.append("⚠️  Webhook not configured")
        
        if not self.results.get('backend_webhook', {}).get('accessible'):
            issues.append("❌ Backend webhook endpoint not accessible")
        
        if not self.results.get('database', {}).get('accessible'):
            issues.append("❌ Database connection issues")
        
        if not issues:
            print("✅ All checks passed! Telegram integration should work.")
        else:
            print("⚠️  Issues found:")
            for issue in issues:
                print(f"   {issue}")
        
        print(f"\n📋 Active connections: {self.results.get('database', {}).get('active_connections', 0)}")
    
    async def suggest_fixes(self):
        """Suggest fixes based on diagnostic results."""
        print("\n🔧 SUGGESTED FIXES")
        print("=" * 60)
        
        fixes = []
        
        # Bot token issues
        if not self.results.get('environment', {}).get('TELEGRAM_BOT_TOKEN'):
            fixes.append({
                'issue': 'Missing bot token',
                'fix': 'Set TELEGRAM_BOT_TOKEN environment variable in Render dashboard',
                'priority': 'HIGH'
            })
        
        if not self.results.get('bot_token', {}).get('valid'):
            fixes.append({
                'issue': 'Invalid bot token',
                'fix': 'Verify bot token with @BotFather on Telegram',
                'priority': 'HIGH'
            })
        
        # Webhook issues
        if not self.results.get('webhook', {}).get('configured'):
            webhook_url = f"{self.settings.BASE_URL}/api/v1/telegram/webhook"
            fixes.append({
                'issue': 'Webhook not configured',
                'fix': f'Set webhook URL to: {webhook_url}',
                'priority': 'HIGH',
                'action': 'setup_webhook'
            })
        
        # Backend issues
        if not self.results.get('backend_webhook', {}).get('accessible'):
            fixes.append({
                'issue': 'Backend webhook not accessible',
                'fix': 'Check Render deployment and BASE_URL configuration',
                'priority': 'HIGH'
            })
        
        # Database issues
        if not self.results.get('database', {}).get('accessible'):
            fixes.append({
                'issue': 'Database connection failed',
                'fix': 'Check DATABASE_URL and run migrations',
                'priority': 'HIGH'
            })
        
        if fixes:
            for i, fix in enumerate(fixes, 1):
                print(f"\n{i}. {fix['issue']} [{fix['priority']}]")
                print(f"   💡 Fix: {fix['fix']}")
                
                if fix.get('action') == 'setup_webhook':
                    print(f"   🤖 Run: python telegram_diagnostic.py --setup-webhook")
        else:
            print("✅ No fixes needed - integration should be working!")
        
        # User guidance
        print(f"\n👥 USER ONBOARDING STEPS:")
        print(f"   1. User connects Telegram in dashboard")
        print(f"   2. User gets auth token")
        print(f"   3. User messages bot: /auth <token>")
        print(f"   4. Bot completes authentication")
        print(f"   5. User can use trading commands")
    
    async def setup_webhook_fix(self):
        """Automatically setup webhook."""
        print("🔧 Setting up Telegram webhook...")
        
        if not self.settings.TELEGRAM_BOT_TOKEN:
            print("❌ Cannot setup webhook without bot token")
            return
        
        webhook_url = f"{self.settings.BASE_URL}/api/v1/telegram/webhook"
        
        try:
            result = await self.telegram_api.set_webhook(webhook_url)
            
            if result.get('success'):
                print(f"✅ Webhook set successfully to: {webhook_url}")
                
                # Verify setup
                await asyncio.sleep(1)
                webhook_info = await self.telegram_api.get_webhook_info()
                if webhook_info.get('success'):
                    info = webhook_info.get('webhook_info', {})
                    print(f"✅ Verification: Webhook URL is {info.get('url')}")
            else:
                print(f"❌ Failed to set webhook: {result.get('error')}")
                
        except Exception as e:
            print(f"❌ Error setting webhook: {str(e)}")

async def main():
    """Main diagnostic function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Telegram Integration Diagnostic')
    parser.add_argument('--setup-webhook', action='store_true', help='Setup webhook automatically')
    args = parser.parse_args()
    
    diagnostic = TelegramDiagnostic()
    
    if args.setup_webhook:
        await diagnostic.setup_webhook_fix()
    else:
        await diagnostic.run_full_diagnosis()

if __name__ == "__main__":
    asyncio.run(main())
