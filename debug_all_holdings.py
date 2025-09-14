#!/usr/bin/env python3
"""
Debug All Holdings - Check why only 5 out of 27 holdings are processed
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

class AllHoldingsDebugger:
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
    
    async def debug_all_holdings(self):
        """Debug all holdings across exchanges"""
        print("\n" + "="*80)
        print("🔍 DEBUGGING ALL HOLDINGS")
        print("="*80)
        
        try:
            # Get portfolio summary
            portfolio_response = await self.client.get(f"{BASE_URL}/api/v1/trading/portfolio")
            if portfolio_response.status_code == 200:
                portfolio_data = portfolio_response.json()
                
                total_value = float(portfolio_data.get('total_value', 0))
                positions = portfolio_data.get('positions', [])
                
                print(f"✅ Portfolio API Response:")
                print(f"   Total Value: ${total_value:,.2f}")
                print(f"   Total Positions: {len(positions)}")
                
                # Analyze all positions
                positions_with_value = [p for p in positions if p.get('value_usd', 0) > 0]
                positions_over_1_dollar = [p for p in positions if p.get('value_usd', 0) > 1.0]
                positions_over_10_dollars = [p for p in positions if p.get('value_usd', 0) > 10.0]
                
                print(f"\n📊 Position Analysis:")
                print(f"   Positions with any value: {len(positions_with_value)}")
                print(f"   Positions > $1: {len(positions_over_1_dollar)}")
                print(f"   Positions > $10: {len(positions_over_10_dollars)}")
                
                # Show all positions with value
                print(f"\n💰 ALL POSITIONS WITH VALUE:")
                for i, pos in enumerate(positions_with_value):
                    symbol = pos.get('symbol', 'Unknown')
                    amount = pos.get('amount', 0)
                    value_usd = pos.get('value_usd', 0)
                    exchange = pos.get('exchange', 'Unknown')
                    percentage = (value_usd / total_value * 100) if total_value > 0 else 0
                    
                    print(f"   {i+1:2d}. {symbol:8s} | ${value_usd:8.2f} ({percentage:5.2f}%) | {amount:12.4f} | {exchange}")
                
                # Show dust positions (< $1)
                dust_positions = [p for p in positions if 0 < p.get('value_usd', 0) <= 1.0]
                if dust_positions:
                    print(f"\n🧹 DUST POSITIONS (< $1):")
                    for pos in dust_positions:
                        symbol = pos.get('symbol', 'Unknown')
                        value_usd = pos.get('value_usd', 0)
                        exchange = pos.get('exchange', 'Unknown')
                        print(f"   {symbol:8s} | ${value_usd:6.2f} | {exchange}")
                
                return positions_with_value
            else:
                print(f"❌ Portfolio API Failed: {portfolio_response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    async def test_rebalancing_with_all_holdings(self):
        """Test rebalancing to see how many holdings are actually processed"""
        print("\n" + "="*80)
        print("🔍 TESTING REBALANCING WITH ALL HOLDINGS")
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
                
                # Extract debug information
                if "🔍 **Debug Information:**" in response_content:
                    import re
                    debug_match = re.search(r'🔍 \*\*Debug Information:\*\*(.*?)(?=\n\n\*\*|$)', response_content, re.DOTALL)
                    if debug_match:
                        debug_section = debug_match.group(1).strip()
                        
                        # Extract position count
                        positions_match = re.search(r'Portfolio Positions: (\d+)', debug_section)
                        weights_match = re.search(r'Optimization Weights: (\d+)', debug_section)
                        
                        if positions_match and weights_match:
                            portfolio_positions = int(positions_match.group(1))
                            optimization_weights = int(weights_match.group(1))
                            
                            print(f"📊 Rebalancing Analysis:")
                            print(f"   Portfolio Positions Processed: {portfolio_positions}")
                            print(f"   Optimization Weights Generated: {optimization_weights}")
                            
                            return portfolio_positions, optimization_weights
                
                print(f"❌ Could not extract debug information from rebalancing response")
                return None, None
                
            else:
                print(f"❌ Rebalancing failed: {chat_response.status_code}")
                return None, None
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return None, None
    
    async def test_fix_effectiveness(self):
        """Test if the fix improved holdings processing"""
        print("\n" + "="*80)
        print("🔧 TESTING FIX EFFECTIVENESS")
        print("="*80)
        
        print("⏳ Waiting 60 seconds for deployment...")
        await asyncio.sleep(60)
        
        # Test rebalancing after fix
        rebalance_positions_after, rebalance_weights_after = await self.test_rebalancing_with_all_holdings()
        
        if rebalance_positions_after is not None:
            print(f"\n📊 Fix Results:")
            print(f"   Holdings Processed After Fix: {rebalance_positions_after}")
            
            if rebalance_positions_after > 5:
                print(f"   🎉 SUCCESS: Fix increased processed holdings from 5 to {rebalance_positions_after}")
                return True
            else:
                print(f"   ❌ Fix didn't work: Still only processing {rebalance_positions_after} holdings")
                return False
        else:
            print(f"   ❌ Could not test fix effectiveness")
            return None

    async def run_complete_debug(self):
        """Run complete holdings debug with fix testing"""
        print("🔍 Starting All Holdings Debug + Fix Test")
        print(f"🌐 Target: {BASE_URL}")
        print(f"⏰ Started: {datetime.now()}")
        
        if not await self.authenticate():
            return
        
        # Debug all holdings
        all_positions = await self.debug_all_holdings()
        
        # Test rebalancing BEFORE fix
        print("\n📊 BEFORE FIX:")
        rebalance_positions_before, rebalance_weights_before = await self.test_rebalancing_with_all_holdings()
        
        # Test fix effectiveness
        fix_worked = await self.test_fix_effectiveness()
        
        # Final Analysis
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE ANALYSIS")
        print("="*80)
        
        if all_positions and rebalance_positions_before is not None:
            total_holdings = len(all_positions)
            significant_holdings = len([p for p in all_positions if p.get('value_usd', 0) > 5.0])
            
            print(f"📊 Portfolio Composition:")
            print(f"   Total Holdings with Value: {total_holdings}")
            print(f"   Significant Holdings (>$5): {significant_holdings}")
            print(f"   Holdings Processed Before Fix: {rebalance_positions_before}")
            
            if fix_worked is True:
                print(f"   Holdings Processed After Fix: Improved!")
                print(f"\n🎉 FIX SUCCESS:")
                print(f"   ✅ More holdings are now being processed")
                print(f"   ✅ Rebalancing will be more accurate")
                print(f"   ✅ Major positions like AAVE, SOL will be included")
            elif fix_worked is False:
                print(f"\n❌ FIX NEEDS MORE WORK:")
                print(f"   📍 Still filtering out significant holdings")
                print(f"   📍 May need to adjust minimum value threshold")
                print(f"   📍 May need to check exchange processing")
            else:
                print(f"\n⏳ FIX STATUS UNKNOWN:")
                print(f"   📍 Could not determine if fix worked")
                print(f"   📍 Try testing again after deployment completes")
            
            # Show which major holdings are being missed
            major_holdings = [p for p in all_positions if p.get('value_usd', 0) > 50.0]
            if len(major_holdings) > rebalance_positions_before:
                print(f"\n🚨 MAJOR HOLDINGS BEING IGNORED:")
                for pos in major_holdings[rebalance_positions_before:]:
                    symbol = pos.get('symbol', 'Unknown')
                    value = pos.get('value_usd', 0)
                    exchange = pos.get('exchange', 'Unknown')
                    percentage = (value / sum(p.get('value_usd', 0) for p in all_positions) * 100)
                    print(f"   {symbol}: ${value:.2f} ({percentage:.1f}%) on {exchange}")
        
        await self.client.aclose()
        print(f"\n⏰ Debug completed: {datetime.now()}")

async def main():
    debugger = AllHoldingsDebugger()
    await debugger.run_complete_debug()

if __name__ == "__main__":
    asyncio.run(main())