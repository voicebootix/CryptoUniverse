#!/usr/bin/env python3
"""
Debug Rebalancing Data Flow
Focus: Trace exactly what happens during rebalancing to find where amounts become zero
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

class RebalancingDataFlowDebugger:
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
    
    async def test_portfolio_api_directly(self):
        """Test the portfolio API directly to confirm it works"""
        print("\n" + "="*80)
        print("🔍 TESTING PORTFOLIO API DIRECTLY")
        print("="*80)
        
        try:
            portfolio_response = await self.client.get(f"{BASE_URL}/api/v1/trading/portfolio")
            if portfolio_response.status_code == 200:
                portfolio_data = portfolio_response.json()
                
                total_value = float(portfolio_data.get('total_value', 0))
                positions = portfolio_data.get('positions', [])
                
                print(f"✅ Portfolio API Direct Test:")
                print(f"   Total Value: ${total_value}")
                print(f"   Positions Count: {len(positions)}")
                
                # Show positions with actual values
                positions_with_value = [p for p in positions if p.get('value_usd', 0) > 0]
                print(f"   Positions with Value > 0: {len(positions_with_value)}")
                
                if positions_with_value:
                    print(f"   Top 3 Positions:")
                    for i, pos in enumerate(positions_with_value[:3]):
                        symbol = pos.get('symbol', 'N/A')
                        amount = pos.get('amount', 0)
                        value_usd = pos.get('value_usd', 0)
                        print(f"     {i+1}. {symbol}: {amount} units = ${value_usd}")
                
                return portfolio_data
            else:
                print(f"❌ Portfolio API Failed: {portfolio_response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Portfolio API Error: {e}")
            return None
    
    async def test_chat_rebalancing_step_by_step(self):
        """Test chat rebalancing and capture intermediate steps"""
        print("\n" + "="*80)
        print("🔍 TESTING CHAT REBALANCING STEP BY STEP")
        print("="*80)
        
        try:
            # Send rebalancing request to chat
            chat_response = await self.client.post(
                f"{BASE_URL}/api/v1/chat/message",
                json={"message": "rebalance"}
            )
            
            if chat_response.status_code == 200:
                chat_data = chat_response.json()
                
                print(f"✅ Chat Rebalancing Response:")
                print(f"   Status Code: {chat_response.status_code}")
                print(f"   Response Keys: {list(chat_data.keys())}")
                
                # Extract the response content - try different fields
                response_content = chat_data.get('response', '') or chat_data.get('content', '') or str(chat_data)
                
                # Look for portfolio value in the response
                if '$' in response_content:
                    import re
                    portfolio_values = re.findall(r'\$([0-9,]+\.?[0-9]*)', response_content)
                    print(f"   Portfolio Values Found: {portfolio_values}")
                
                # Look for trade amounts
                if 'Amount: $' in response_content:
                    trade_amounts = re.findall(r'Amount: \$([0-9,]+\.?[0-9]*)', response_content)
                    print(f"   Trade Amounts Found: {trade_amounts}")
                    
                    # Check if all amounts are zero
                    zero_amounts = [amt for amt in trade_amounts if float(amt.replace(',', '')) == 0]
                    print(f"   Zero Amount Trades: {len(zero_amounts)}/{len(trade_amounts)}")
                
                # Look for current and target percentages
                if 'Current:' in response_content and 'Target:' in response_content:
                    current_percentages = re.findall(r'Current: ([0-9]+\.?[0-9]*)%', response_content)
                    target_percentages = re.findall(r'Target: ([0-9]+\.?[0-9]*)%', response_content)
                    print(f"   Current Percentages: {current_percentages}")
                    print(f"   Target Percentages: {target_percentages}")
                    
                    # Check if all percentages are zero
                    zero_current = [pct for pct in current_percentages if float(pct) == 0]
                    zero_target = [pct for pct in target_percentages if float(pct) == 0]
                    print(f"   Zero Current Percentages: {len(zero_current)}/{len(current_percentages)}")
                    print(f"   Zero Target Percentages: {len(zero_target)}/{len(target_percentages)}")
                
                # Show the full response for analysis
                print(f"\n   Full Response Content:")
                print(f"   {response_content}")
                
                return chat_data
            else:
                print(f"❌ Chat Rebalancing Failed: {chat_response.status_code}")
                print(f"   Response: {chat_response.text}")
                return None
        except Exception as e:
            print(f"❌ Chat Rebalancing Error: {e}")
            return None
    
    async def test_portfolio_summary_method(self):
        """Test if we can call the portfolio summary method directly"""
        print("\n" + "="*80)
        print("🔍 TESTING PORTFOLIO SUMMARY METHOD")
        print("="*80)
        
        # Try to call portfolio quick analysis which might use the same method
        try:
            quick_analysis_response = await self.client.post(
                f"{BASE_URL}/api/v1/chat/portfolio/quick-analysis"
            )
            
            if quick_analysis_response.status_code == 200:
                analysis_data = quick_analysis_response.json()
                print(f"✅ Portfolio Quick Analysis:")
                print(f"   Response Keys: {list(analysis_data.keys())}")
                
                # Look for portfolio data in the response
                if 'portfolio' in analysis_data:
                    portfolio_info = analysis_data['portfolio']
                    print(f"   Portfolio Info: {portfolio_info}")
                
                return analysis_data
            else:
                print(f"❌ Portfolio Quick Analysis Failed: {quick_analysis_response.status_code}")
                print(f"   Response: {quick_analysis_response.text}")
                return None
        except Exception as e:
            print(f"❌ Portfolio Quick Analysis Error: {e}")
            return None
    
    async def run_complete_debug(self):
        """Run complete debugging sequence"""
        print("🔍 Starting Rebalancing Data Flow Debug")
        print(f"🌐 Target: {BASE_URL}")
        print(f"⏰ Started: {datetime.now()}")
        
        if not await self.authenticate():
            return
        
        # Test sequence
        portfolio_data = await self.test_portfolio_api_directly()
        chat_data = await self.test_chat_rebalancing_step_by_step()
        analysis_data = await self.test_portfolio_summary_method()
        
        # Final analysis
        print("\n" + "="*80)
        print("🎯 REBALANCING DATA FLOW ANALYSIS")
        print("="*80)
        
        if portfolio_data and chat_data:
            portfolio_value = float(portfolio_data.get('total_value', 0))
            positions_count = len(portfolio_data.get('positions', []))
            positions_with_value = len([p for p in portfolio_data.get('positions', []) if p.get('value_usd', 0) > 0])
            
            print(f"📊 Data Consistency Check:")
            print(f"   Portfolio API Total Value: ${portfolio_value}")
            print(f"   Portfolio API Positions: {positions_count}")
            print(f"   Portfolio API Positions with Value: {positions_with_value}")
            
            # Check if chat response contains the same portfolio value
            chat_response = chat_data.get('response', '')
            if f"${portfolio_value:.2f}" in chat_response or f"${portfolio_value:,.2f}" in chat_response:
                print(f"   ✅ Chat response contains correct portfolio value")
            else:
                print(f"   ❌ Chat response may not contain correct portfolio value")
            
            # Check for the zero amounts issue
            if 'Amount: $0.00' in chat_response:
                print(f"   ❌ CONFIRMED: Chat response contains zero trade amounts")
                print(f"   🎯 ROOT CAUSE: Portfolio data is correct but trade calculation is wrong")
            else:
                print(f"   ✅ No zero trade amounts found in chat response")
        
        await self.client.aclose()
        print(f"\n⏰ Debug completed: {datetime.now()}")

async def main():
    debugger = RebalancingDataFlowDebugger()
    await debugger.run_complete_debug()

if __name__ == "__main__":
    asyncio.run(main())