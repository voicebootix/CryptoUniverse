#!/usr/bin/env python3
"""
Test Enhanced Debug Info
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

class EnhancedDebugTester:
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
    
    async def test_enhanced_debug_rebalancing(self):
        """Test rebalancing with enhanced debug info"""
        print("\n" + "="*80)
        print("🔍 TESTING ENHANCED DEBUG REBALANCING")
        print("="*80)
        
        try:
            print("🚀 Triggering rebalancing with enhanced debug info...")
            
            # Test rebalancing
            chat_response = await self.client.post(
                f"{BASE_URL}/api/v1/chat/message",
                json={"message": "rebalance"}
            )
            
            if chat_response.status_code == 200:
                chat_data = chat_response.json()
                response_content = chat_data.get('content', '')
                
                print(f"✅ Rebalancing response received")
                
                # Check for enhanced debug information
                if "🔍 **Debug Information:**" in response_content:
                    print(f"\n🎯 ENHANCED DEBUG INFO FOUND!")
                    
                    # Extract debug section
                    import re
                    debug_match = re.search(r'🔍 \*\*Debug Information:\*\*(.*?)(?=\n\n\*\*|$)', response_content, re.DOTALL)
                    if debug_match:
                        debug_section = debug_match.group(1).strip()
                        print(f"\n📊 Enhanced Debug Data:")
                        for line in debug_section.split('\n'):
                            if line.strip():
                                print(f"   {line.strip()}")
                        
                        # Parse position values
                        position_values_match = re.search(r'Position Values: (\[.*?\])', debug_section)
                        optimization_weights_match = re.search(r'Optimization Weights: (\{.*?\})', debug_section)
                        
                        if position_values_match:
                            try:
                                position_values = eval(position_values_match.group(1))
                                print(f"\n🎯 POSITION VALUES ANALYSIS:")
                                for pos_val in position_values:
                                    print(f"   {pos_val}")
                                
                                # Check if all position values are $0
                                zero_values = [pv for pv in position_values if '$0' in pv or '$0.0' in pv]
                                if len(zero_values) == len(position_values):
                                    print(f"   ❌ CRITICAL: All position values are $0!")
                                    print(f"   📍 ROOT CAUSE: Portfolio positions have no value_usd")
                                elif len(zero_values) > 0:
                                    print(f"   ⚠️  PARTIAL: {len(zero_values)}/{len(position_values)} positions have $0 value")
                                else:
                                    print(f"   ✅ All positions have non-zero values")
                                    
                            except Exception as e:
                                print(f"   ❌ Could not parse position values: {e}")
                        
                        if optimization_weights_match:
                            try:
                                optimization_weights = eval(optimization_weights_match.group(1))
                                print(f"\n🎯 OPTIMIZATION WEIGHTS ANALYSIS:")
                                for symbol, weight in optimization_weights.items():
                                    print(f"   {symbol}: {weight:.4f} ({weight*100:.2f}%)")
                                
                                # Check if all weights are zero
                                zero_weights = [w for w in optimization_weights.values() if w == 0]
                                if len(zero_weights) == len(optimization_weights):
                                    print(f"   ❌ CRITICAL: All optimization weights are 0!")
                                    print(f"   📍 ROOT CAUSE: Optimization engine returning zero weights")
                                elif len(zero_weights) > 0:
                                    print(f"   ⚠️  PARTIAL: {len(zero_weights)}/{len(optimization_weights)} weights are 0")
                                else:
                                    print(f"   ✅ All weights are non-zero")
                                    
                            except Exception as e:
                                print(f"   ❌ Could not parse optimization weights: {e}")
                        
                        # Final diagnosis
                        print(f"\n🎯 FINAL DIAGNOSIS:")
                        if position_values_match and optimization_weights_match:
                            try:
                                pos_vals = eval(position_values_match.group(1))
                                opt_weights = eval(optimization_weights_match.group(1))
                                
                                zero_pos_vals = len([pv for pv in pos_vals if '$0' in pv])
                                zero_opt_weights = len([w for w in opt_weights.values() if w == 0])
                                
                                if zero_pos_vals == len(pos_vals):
                                    print(f"   🎯 ISSUE: Portfolio positions have $0 values")
                                    print(f"   📍 FIX NEEDED: Check get_portfolio_summary value_usd calculation")
                                elif zero_opt_weights == len(opt_weights):
                                    print(f"   🎯 ISSUE: Optimization weights are all 0")
                                    print(f"   📍 FIX NEEDED: Check optimization engine weight calculation")
                                else:
                                    print(f"   🎯 ISSUE: Trade generation logic problem")
                                    print(f"   📍 FIX NEEDED: Check _generate_rebalancing_trades method")
                                    
                            except:
                                print(f"   ❌ Could not perform final diagnosis")
                        
                        return True
                    else:
                        print(f"   ❌ Debug section found but could not parse")
                        return False
                else:
                    print(f"\n❌ No enhanced debug information found")
                    return False
                    
            else:
                print(f"❌ Rebalancing failed: {chat_response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def run_enhanced_debug_test(self):
        """Run the enhanced debug test"""
        print("🔍 Starting Enhanced Debug Test")
        print(f"🌐 Target: {BASE_URL}")
        print(f"⏰ Started: {datetime.now()}")
        
        if not await self.authenticate():
            return False
        
        # Wait for deployment
        print("\n⏳ Waiting 90 seconds for deployment...")
        await asyncio.sleep(90)
        
        # Test enhanced debug
        result = await self.test_enhanced_debug_rebalancing()
        
        await self.client.aclose()
        
        if result is True:
            print(f"\n🎉 SUCCESS: Enhanced debug reveals the exact root cause!")
        elif result is False:
            print(f"\n⏳ Enhanced debug not yet active")
        else:
            print(f"\n❌ Test failed")
        
        return result

async def main():
    tester = EnhancedDebugTester()
    return await tester.run_enhanced_debug_test()

if __name__ == "__main__":
    result = asyncio.run(main())
    if result:
        print("\n🎯 Enhanced debug test completed - root cause identified!")
    else:
        print("\n🔍 Try again in a few minutes")