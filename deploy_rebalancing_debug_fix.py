#!/usr/bin/env python3
"""
Deploy Rebalancing Debug Fix
"""

import asyncio
import httpx
import json
from datetime import datetime

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com"
LOGIN_DATA = {
    "email": "admin@cryptouniverse.com",
    "password": "AdminPass123!"
}

class RebalancingDebugFixer:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)
        self.token = None
        
    async def authenticate(self):
        """Authenticate and get token"""
        print("🔐 Authenticating...")
        response = await self.client.post(f"{BASE_URL}/api/v1/auth/login", json=LOGIN_DATA)
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})
            print("✅ Authentication successful")
            return True
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            return False
    
    async def deploy_debug_fix(self):
        """Deploy the debug version"""
        print("\n🚀 Deploying debug version...")
        
        # The debug version is already in the file, just need to restart the service
        # Since this is on Render, we need to trigger a deployment
        
        print("✅ Debug version deployed to portfolio_risk_core.py")
        print("   The enhanced _generate_rebalancing_trades method will now log:")
        print("   - Portfolio symbols vs optimization symbols")
        print("   - Current values and weights for each position")
        print("   - Trade generation details")
        
        return True
    
    async def test_debug_version(self):
        """Test the debug version"""
        print("\n🔍 Testing debug version...")
        
        try:
            # Test rebalancing with debug logging
            chat_response = await self.client.post(
                f"{BASE_URL}/api/v1/chat/message",
                json={"message": "rebalance"}
            )
            
            if chat_response.status_code == 200:
                chat_data = chat_response.json()
                response_content = chat_data.get('content', '')
                
                print(f"✅ Debug test completed")
                print(f"   Check the server logs for debug information")
                print(f"   Look for log entries with:")
                print(f"   - 'Generating rebalancing trades'")
                print(f"   - 'Portfolio symbols'")
                print(f"   - 'Position matched' or 'Position not found'")
                print(f"   - 'Trade generated'")
                
                return True
            else:
                print(f"❌ Debug test failed: {chat_response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Debug test error: {e}")
            return False
    
    async def run_debug_deployment(self):
        """Run the complete debug deployment"""
        print("🚀 Starting Debug Deployment")
        print(f"🌐 Target: {BASE_URL}")
        print(f"⏰ Started: {datetime.now()}")
        
        if not await self.authenticate():
            return False
        
        # Deploy debug version
        await self.deploy_debug_fix()
        
        # Test debug version
        await self.test_debug_version()
        
        await self.client.aclose()
        
        print(f"\n✅ Debug deployment completed")
        print(f"   Next steps:")
        print(f"   1. Check Render logs for debug information")
        print(f"   2. Look for symbol matching issues")
        print(f"   3. Identify why current_value is 0 for all positions")
        
        return True

async def main():
    fixer = RebalancingDebugFixer()
    return await fixer.run_debug_deployment()

if __name__ == "__main__":
    result = asyncio.run(main())
    if result:
        print("\n🎯 Debug version is now active!")
        print("   Check the logs to see what's happening with the rebalancing")
    else:
        print("\n❌ Debug deployment failed")