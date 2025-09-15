#!/usr/bin/env python3
"""
Test Debug Info in Chat Response
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

class DebugInfoTester:
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
    
    async def test_debug_info_in_rebalancing(self):
        """Test if debug info appears in rebalancing response"""
        print("\n" + "="*80)
        print("🔍 TESTING DEBUG INFO IN REBALANCING RESPONSE")
        print("="*80)
        
        try:
            print("🚀 Triggering rebalancing to see debug info...")
            
            # Test rebalancing
            chat_response = await self.client.post(
                f"{BASE_URL}/api/v1/chat/message",
                json={"message": "rebalance"}
            )
            
            if chat_response.status_code == 200:
                chat_data = chat_response.json()
                response_content = chat_data.get('content', '')
                
                print(f"✅ Rebalancing response received")
                print(f"   Status: {chat_response.status_code}")
                
                # Check if debug information is present
                if "🔍 **Debug Information:**" in response_content:
                    print(f"\n🎯 DEBUG INFO FOUND!")
                    
                    # Extract debug information
                    import re
                    
                    # Extract debug section
                    debug_match = re.search(r'🔍 \*\*Debug Information:\*\*(.*?)(?=\n\n\*\*|$)', response_content, re.DOTALL)
                    if debug_match:
                        debug_section = debug_match.group(1).strip()
                        print(f"   Debug Section:")
                        for line in debug_section.split('\n'):
                            if line.strip():
                                print(f"     {line.strip()}")
                        
                        # Parse specific debug values
                        portfolio_positions = re.search(r'Portfolio Positions: (\d+)', debug_section)
                        optimization_weights = re.search(r'Optimization Weights: (\d+)', debug_section)
                        portfolio_symbols = re.search(r'Portfolio Symbols: (\[.*?\])', debug_section)
                        optimization_symbols = re.search(r'Optimization Symbols: (\[.*?\])', debug_section)
                        
                        print(f"\n📊 Parsed Debug Data:")
                        if portfolio_positions:
                            print(f"   Portfolio Positions: {portfolio_positions.group(1)}")
                        if optimization_weights:
                            print(f"   Optimization Weights: {optimization_weights.group(1)}")
                        if portfolio_symbols:
                            print(f"   Portfolio Symbols: {portfolio_symbols.group(1)}")
                        if optimization_symbols:
                            print(f"   Optimization Symbols: {optimization_symbols.group(1)}")
                        
                        # Analysis
                        print(f"\n🎯 ROOT CAUSE ANALYSIS:")
                        
                        if portfolio_positions and optimization_weights:
                            pos_count = int(portfolio_positions.group(1))
                            opt_count = int(optimization_weights.group(1))
                            
                            if pos_count > 0 and opt_count == 0:
                                print(f"   ❌ ISSUE: Portfolio has {pos_count} positions but optimization has 0 weights")
                                print(f"   📍 CAUSE: Optimization engine is not generating weights")
                            elif pos_count > 0 and opt_count > 0:
                                print(f"   ✅ Both portfolio ({pos_count}) and optimization ({opt_count}) have data")
                                print(f"   📍 ISSUE: Likely symbol matching problem")
                            else:
                                print(f"   ❌ ISSUE: Portfolio has {pos_count} positions")
                                print(f"   📍 CAUSE: Portfolio data is not being retrieved properly")
                        
                        if portfolio_symbols and optimization_symbols:
                            try:
                                port_syms = eval(portfolio_symbols.group(1))
                                opt_syms = eval(optimization_symbols.group(1))
                                
                                matching = set(port_syms).intersection(set(opt_syms))
                                print(f"   Symbol Matching: {len(matching)} out of {len(port_syms)} portfolio symbols")
                                
                                if len(matching) == 0:
                                    print(f"   ❌ CRITICAL: No symbols match between portfolio and optimization")
                                    print(f"   📍 This explains why all trades are $0.00")
                                elif len(matching) < len(port_syms):
                                    print(f"   ⚠️  PARTIAL: Only some symbols match")
                                    print(f"   📍 Some trades will be $0.00")
                                else:
                                    print(f"   ✅ All symbols match - issue is elsewhere")
                                    
                            except:
                                print(f"   ❌ Could not parse symbol lists")
                        
                        return True
                    else:
                        print(f"   ❌ Debug section found but could not parse")
                        return False
                else:
                    print(f"\n❌ No debug information found in response")
                    print(f"   Debug deployment may not be active yet")
                    print(f"   Response preview (first 500 chars):")
                    print(f"   {response_content[:500]}...")
                    return False
                    
            else:
                print(f"❌ Rebalancing failed: {chat_response.status_code}")
                print(f"   Response: {chat_response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def run_debug_info_test(self):
        """Run the debug info test"""
        print("🔍 Starting Debug Info Test")
        print(f"🌐 Target: {BASE_URL}")
        print(f"⏰ Started: {datetime.now()}")
        
        if not await self.authenticate():
            return False
        
        # Wait for deployment
        print("\n⏳ Waiting 60 seconds for deployment to be ready...")
        await asyncio.sleep(60)
        
        # Test debug info
        result = await self.test_debug_info_in_rebalancing()
        
        await self.client.aclose()
        
        if result is True:
            print(f"\n🎉 SUCCESS: Debug info is working and shows the root cause!")
        elif result is False:
            print(f"\n⏳ Debug info not yet active - try again in a few minutes")
        else:
            print(f"\n❌ Test failed - check system status")
        
        return result

async def main():
    tester = DebugInfoTester()
    return await tester.run_debug_info_test()

if __name__ == "__main__":
    result = asyncio.run(main())
    if result:
        print("\n🎯 Debug info test completed successfully!")
    else:
        print("\n🔍 Try running the test again in a few minutes")