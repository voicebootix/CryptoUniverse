#!/usr/bin/env python3
"""
Test Rebalancing Fix - Check if the missing amount field fix works
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

class RebalancingFixTester:
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
    
    async def test_rebalancing_fix(self):
        """Test if the rebalancing fix works"""
        print("\n" + "="*80)
        print("🔍 TESTING REBALANCING FIX")
        print("="*80)
        
        try:
            print("🚀 Testing rebalancing with the critical fix...")
            
            # Test rebalancing
            chat_response = await self.client.post(
                f"{BASE_URL}/api/v1/chat/message",
                json={"message": "rebalance"}
            )
            
            if chat_response.status_code == 200:
                chat_data = chat_response.json()
                response_content = chat_data.get('content', '')
                
                print(f"✅ Rebalancing response received")
                
                # Parse the response to check trade amounts
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
                
                # Check if the fix worked
                zero_amounts = [amt for amt in trade_amounts if float(amt.replace(',', '')) == 0]
                zero_current = [pct for pct in current_percentages if float(pct) == 0]
                zero_target = [pct for pct in target_percentages if float(pct) == 0]
                
                print(f"\n🎯 Fix Analysis:")
                print(f"   Zero Trade Amounts: {len(zero_amounts)}/{len(trade_amounts)}")
                print(f"   Zero Current %: {len(zero_current)}/{len(current_percentages)}")
                print(f"   Zero Target %: {len(zero_target)}/{len(target_percentages)}")
                
                if len(zero_amounts) == 0 and len(trade_amounts) > 0:
                    print(f"\n🎉 SUCCESS! The fix worked!")
                    print(f"   ✅ All trade amounts are non-zero")
                    print(f"   ✅ Trade amounts: {trade_amounts}")
                    
                    # Calculate total trading volume
                    total_volume = sum(float(amt.replace(',', '')) for amt in trade_amounts)
                    print(f"   ✅ Total trading volume: ${total_volume:,.2f}")
                    
                    return True
                elif len(zero_amounts) < len(trade_amounts):
                    print(f"\n🎯 PARTIAL SUCCESS!")
                    print(f"   ✅ Some trades have non-zero amounts: {[amt for amt in trade_amounts if float(amt.replace(',', '')) > 0]}")
                    print(f"   ❌ But some are still zero: {zero_amounts}")
                    return "partial"
                else:
                    print(f"\n❌ Fix didn't work - all amounts still $0.00")
                    print(f"   📍 Need to investigate further")
                    return False
                    
            else:
                print(f"❌ Rebalancing failed: {chat_response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def run_fix_test(self):
        """Run the fix test"""
        print("🔍 Starting Rebalancing Fix Test")
        print(f"🌐 Target: {BASE_URL}")
        print(f"⏰ Started: {datetime.now()}")
        
        if not await self.authenticate():
            return False
        
        # Wait for deployment
        print("\n⏳ Waiting 120 seconds for deployment...")
        await asyncio.sleep(120)
        
        # Test the fix
        result = await self.test_rebalancing_fix()
        
        await self.client.aclose()
        
        if result is True:
            print(f"\n🎉 CRITICAL FIX SUCCESSFUL!")
            print(f"   The rebalancing zero amounts issue is RESOLVED!")
            print(f"   Trade amounts are now showing correctly!")
        elif result == "partial":
            print(f"\n🎯 PARTIAL FIX - some improvement but needs more work")
        elif result is False:
            print(f"\n❌ Fix didn't work - need to investigate further")
        else:
            print(f"\n❌ Test failed - check system status")
        
        return result

async def main():
    tester = RebalancingFixTester()
    return await tester.run_fix_test()

if __name__ == "__main__":
    result = asyncio.run(main())
    if result is True:
        print("\n🎯 REBALANCING IS FIXED! 🎉")
        print("   Users can now see proper trade amounts and percentages!")
    else:
        print("\n🔍 Check the results and investigate if needed")