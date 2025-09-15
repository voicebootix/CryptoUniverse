#!/usr/bin/env python3
"""
Deploy Debug Version to Test Live System
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

class DebugDeployer:
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
    
    async def test_current_rebalancing(self):
        """Test the current rebalancing to see what's happening"""
        print("\n" + "="*80)
        print("🔍 TESTING CURRENT REBALANCING BEHAVIOR")
        print("="*80)
        
        try:
            # Test rebalancing
            chat_response = await self.client.post(
                f"{BASE_URL}/api/v1/chat/message",
                json={"message": "rebalance"}
            )
            
            if chat_response.status_code == 200:
                chat_data = chat_response.json()
                response_content = chat_data.get('content', '')
                
                print(f"✅ Current Rebalancing Response:")
                print(f"   Status: {chat_response.status_code}")
                
                # Parse the response to extract key data
                import re
                
                # Extract portfolio value
                portfolio_match = re.search(r'Portfolio Value: \$([0-9,]+\.?[0-9]*)', response_content)
                portfolio_value = portfolio_match.group(1) if portfolio_match else "Not found"
                
                # Extract trade amounts
                trade_amounts = re.findall(r'Amount: \$([0-9,]+\.?[0-9]*)', response_content)
                
                # Extract percentages
                current_percentages = re.findall(r'Current: ([0-9]+\.?[0-9]*)%', response_content)
                target_percentages = re.findall(r'Target: ([0-9]+\.?[0-9]*)%', response_content)
                
                print(f"   Portfolio Value: ${portfolio_value}")
                print(f"   Trade Amounts: {trade_amounts}")
                print(f"   Current %: {current_percentages}")
                print(f"   Target %: {target_percentages}")
                
                # Check if all amounts are zero
                zero_amounts = [amt for amt in trade_amounts if float(amt.replace(',', '')) == 0]
                zero_current = [pct for pct in current_percentages if float(pct) == 0]
                zero_target = [pct for pct in target_percentages if float(pct) == 0]
                
                print(f"\n   Analysis:")
                print(f"   Zero Trade Amounts: {len(zero_amounts)}/{len(trade_amounts)}")
                print(f"   Zero Current %: {len(zero_current)}/{len(current_percentages)}")
                print(f"   Zero Target %: {len(zero_target)}/{len(target_percentages)}")
                
                if len(zero_amounts) == len(trade_amounts) and len(trade_amounts) > 0:
                    print(f"   🎯 CONFIRMED: All trade amounts are $0.00")
                    return True
                else:
                    print(f"   ✅ Trade amounts look normal")
                    return False
                    
            else:
                print(f"❌ Chat failed: {chat_response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    async def run_debug_test(self):
        """Run the debug test"""
        print("🔍 Starting Debug Test on Live System")
        print(f"🌐 Target: {BASE_URL}")
        print(f"⏰ Started: {datetime.now()}")
        
        if not await self.authenticate():
            return False
        
        # Test current behavior
        has_zero_amounts = await self.test_current_rebalancing()
        
        await self.client.aclose()
        
        if has_zero_amounts:
            print(f"\n🎯 CONFIRMED: The zero amounts issue exists on live system")
            print(f"   Now we can deploy the debug version to see what's happening")
            return True
        else:
            print(f"\n✅ No zero amounts issue found")
            return False

async def main():
    deployer = DebugDeployer()
    return await deployer.run_debug_test()

if __name__ == "__main__":
    result = asyncio.run(main())
    if result:
        print("\n🚀 Ready to deploy debug version!")
    else:
        print("\n❌ Issue not confirmed, check the system")