#!/usr/bin/env python3
"""
Monitor Render deployment progress by checking webhook endpoint
"""

import asyncio
import aiohttp
import time
from datetime import datetime

async def check_deployment():
    """Check if deployment has taken effect."""
    async with aiohttp.ClientSession() as session:
        async with session.get('https://cryptouniverse.onrender.com/api/v1/telegram/webhook') as response:
            return response.status

async def monitor_deployment():
    """Monitor deployment until webhook is fixed."""
    print("🔍 Monitoring Render deployment progress...")
    print("Checking every 30 seconds until webhook returns 405 instead of 401...")
    print()
    
    start_time = time.time()
    check_count = 0
    
    while True:
        check_count += 1
        current_time = datetime.now().strftime("%H:%M:%S")
        
        try:
            status = await check_deployment()
            elapsed = int(time.time() - start_time)
            
            if status == 405:
                print(f"✅ {current_time} - SUCCESS! Webhook returns 405 (Method Not Allowed)")
                print(f"🎉 Deployment completed after {elapsed} seconds ({check_count} checks)")
                print("🚀 Telegram integration should now work!")
                break
            elif status == 401:
                print(f"⏳ {current_time} - Still 401 (deployment pending) - Check {check_count}")
            else:
                print(f"⚠️  {current_time} - Unexpected status: {status} - Check {check_count}")
                
            if elapsed > 900:  # 15 minutes
                print(f"⚠️  Deployment taking longer than expected ({elapsed}s)")
                print("You may want to check Render dashboard for deployment status")
                
        except Exception as e:
            print(f"❌ {current_time} - Connection error: {str(e)}")
        
        await asyncio.sleep(30)  # Check every 30 seconds

if __name__ == "__main__":
    try:
        asyncio.run(monitor_deployment())
    except KeyboardInterrupt:
        print("\n⏹️  Monitoring stopped by user")
        print("You can test manually with: python telegram_simple_test.py")
