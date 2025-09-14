#!/usr/bin/env python3
"""
Test Debug Logs - Check if debug version is working
"""

import asyncio
import httpx
import json
from datetime import datetime
import time

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com"
LOGIN_DATA = {
    "email": "admin@cryptouniverse.com",
    "password": "AdminPass123!"
}

class DebugLogTester:
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
    
    async def test_debug_rebalancing(self):
        """Test rebalancing with debug logging"""
        print("\n" + "="*80)
        print("🔍 TESTING DEBUG REBALANCING")
        print("="*80)
        
        try:
            print("🚀 Triggering rebalancing with debug logging...")
            
            # Test rebalancing
            chat_response = await self.client.post(
                f"{BASE_URL}/api/v1/chat/message",
                json={"message": "rebalance"}
            )
            
            if chat_response.status_code == 200:
                chat_data = chat_response.json()
                response_content = chat_data.get('content', '')
                
                print(f"✅ Rebalancing completed")
                print(f"   Status: {chat_response.status_code}")
                
                # Parse the response to check if we still have zero amounts
                import re
                
                # Extract key data
                portfolio_match = re.search(r'Portfolio Value: \$([0-9,]+\.?[0-9]*)', response_content)
                portfolio_value = portfolio_match.group(1) if portfolio_match else "Not found"
                
                trade_amounts = re.findall(r'Amount: \$([0-9,]+\.?[0-9]*)', response_content)
                current_percentages = re.findall(r'Current: ([0-9]+\.?[0-9]*)%', response_content)
                target_percentages = re.findall(r'Target: ([0-9]+\.?[0-9]*)%', response_content)
                
                print(f"\n📊 Results:")
                print(f"   Portfolio Value: ${portfolio_value}")
                print(f"   Trade Amounts: {trade_amounts}")
                print(f"   Current %: {current_percentages}")
                print(f"   Target %: {target_percentages}")
                
                # Check if issue is fixed
                zero_amounts = [amt for amt in trade_amounts if float(amt.replace(',', '')) == 0]
                zero_current = [pct for pct in current_percentages if float(pct) == 0]
                
                print(f"\n🎯 Analysis:")
                print(f"   Zero Trade Amounts: {len(zero_amounts)}/{len(trade_amounts)}")
                print(f"   Zero Current %: {len(zero_current)}/{len(current_percentages)}")
                
                if len(zero_amounts) == len(trade_amounts) and len(trade_amounts) > 0:
                    print(f"   ❌ Issue still exists - all amounts are $0.00")
                    print(f"   📋 Debug logs should show:")
                    print(f"      - 'Generating rebalancing trades'")
                    print(f"      - 'Portfolio symbols' vs 'Optimal weight symbols'")
                    print(f"      - 'Position matched' or 'Position not found' for each symbol")
                    print(f"      - Why current_value is 0 for all positions")
                    return False
                else:
                    print(f"   ✅ Issue appears to be fixed!")
                    return True
                    
            else:
                print(f"❌ Rebalancing failed: {chat_response.status_code}")
                print(f"   Response: {chat_response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    async def run_debug_test(self):
        """Run the debug test"""
        print("🔍 Starting Debug Log Test")
        print(f"🌐 Target: {BASE_URL}")
        print(f"⏰ Started: {datetime.now()}")
        
        if not await self.authenticate():
            return False
        
        # Wait a moment for deployment to be ready
        print("\n⏳ Waiting 30 seconds for deployment to be ready...")
        await asyncio.sleep(30)
        
        # Test debug version
        result = await self.test_debug_rebalancing()
        
        await self.client.aclose()
        
        if result is True:
            print(f"\n🎉 SUCCESS: Debug version fixed the issue!")
        elif result is False:
            print(f"\n🔍 Issue still exists - check Render logs for debug information")
            print(f"   Look for these log entries:")
            print(f"   1. 'Generating rebalancing trades' - shows input data")
            print(f"   2. 'Portfolio symbols' - shows what symbols are in portfolio")
            print(f"   3. 'Optimal weight symbols' - shows what symbols optimization wants")
            print(f"   4. 'Position matched' - shows successful symbol matches")
            print(f"   5. 'Position not found' - shows failed symbol matches")
            print(f"   6. 'Trade generated' - shows successful trade creation")
        else:
            print(f"\n❌ Test failed - check system status")
        
        return result

async def main():
    tester = DebugLogTester()
    return await tester.run_debug_test()

if __name__ == "__main__":
    result = asyncio.run(main())
    if result:
        print("\n🎯 Debug test completed successfully!")
    else:
        print("\n🔍 Check the logs for debug information")