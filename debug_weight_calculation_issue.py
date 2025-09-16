#!/usr/bin/env python3
"""
Debug Weight Calculation Issue
Focus: Why are all weights showing as 0.0% when portfolio value is correct?
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

class WeightCalculationDebugger:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)
        self.token = None
        
    async def authenticate(self):
        """Authenticate and get token"""
        print("🔐 Authenticating...")
        response = await self.client.post(
            f"{BASE_URL}/api/v1/auth/login", 
            json=LOGIN_DATA
        )
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})
            print("✅ Authentication successful")
            return True
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    async def debug_portfolio_data_flow(self):
        """Debug the complete data flow from portfolio to weights"""
        print("\n" + "="*80)
        print("🔍 DEBUGGING WEIGHT CALCULATION DATA FLOW")
        print("="*80)
        
        # Step 1: Get raw portfolio data
        print("\n📊 STEP 1: Raw Portfolio Data")
        print("-" * 40)
        try:
            portfolio_response = await self.client.get(f"{BASE_URL}/api/v1/trading/portfolio")
            if portfolio_response.status_code == 200:
                portfolio_data = portfolio_response.json()
                print(f"✅ Portfolio API Success")
                print(f"   Total Value: ${portfolio_data.get('total_value', 'N/A')}")
                print(f"   Positions Count: {len(portfolio_data.get('positions', []))}")
                
                # Show individual positions
                positions = portfolio_data.get('positions', [])
                print(f"\n   Individual Positions:")
                for i, pos in enumerate(positions[:5]):  # Show first 5
                    symbol = pos.get('symbol', 'Unknown')
                    balance = pos.get('balance', 0)
                    value = pos.get('value', 0)
                    print(f"   {i+1}. {symbol}: {balance} units = ${value}")
                    
                return portfolio_data
            else:
                print(f"❌ Portfolio API Failed: {portfolio_response.status_code}")
                print(f"   Response: {portfolio_response.text}")
                return None
        except Exception as e:
            print(f"❌ Portfolio API Error: {e}")
            return None
    
    async def debug_rebalancing_weights(self):
        """Debug rebalancing weight calculations"""
        print("\n📊 STEP 2: Rebalancing Weight Calculations")
        print("-" * 40)
        try:
            # Test rebalancing through chat since that's how it works
            rebalance_response = await self.client.post(
                f"{BASE_URL}/api/v1/chat/message", 
                json={"message": "rebalance"}
            )
            if rebalance_response.status_code == 200:
                rebalance_data = rebalance_response.json()
                print(f"✅ Rebalancing API Success")
                print(f"   Portfolio Value: ${rebalance_data.get('portfolio_value', 'N/A')}")
                print(f"   Trades Count: {len(rebalance_data.get('trades', []))}")
                
                # Show trade details
                trades = rebalance_data.get('trades', [])
                print(f"\n   Trade Details:")
                for i, trade in enumerate(trades[:5]):  # Show first 5
                    symbol = trade.get('symbol', 'Unknown')
                    action = trade.get('action', 'Unknown')
                    amount = trade.get('amount', 0)
                    current_pct = trade.get('current_weight', 0)
                    target_pct = trade.get('target_weight', 0)
                    print(f"   {i+1}. {action} {symbol}: ${amount}")
                    print(f"       Current: {current_pct}% → Target: {target_pct}%")
                
                # Check for optimization data
                optimization = rebalance_data.get('optimization', {})
                print(f"\n   Optimization Data:")
                print(f"   Current Weights: {optimization.get('current_weights', 'Missing')}")
                print(f"   Target Weights: {optimization.get('target_weights', 'Missing')}")
                
                return rebalance_data
            else:
                print(f"❌ Rebalancing API Failed: {rebalance_response.status_code}")
                print(f"   Response: {rebalance_response.text}")
                return None
        except Exception as e:
            print(f"❌ Rebalancing API Error: {e}")
            return None
    
    async def debug_weight_calculation_internals(self):
        """Try to access internal weight calculation methods"""
        print("\n📊 STEP 3: Internal Weight Calculation Analysis")
        print("-" * 40)
        
        # Try to get user profile and strategy
        try:
            profile_response = await self.client.get(f"{BASE_URL}/api/v1/auth/me")
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                print(f"✅ User Profile Retrieved")
                print(f"   Strategy: {profile_data.get('trading_strategy', 'N/A')}")
                print(f"   Risk Level: {profile_data.get('risk_level', 'N/A')}")
            else:
                print(f"❌ Profile API Failed: {profile_response.status_code}")
        except Exception as e:
            print(f"❌ Profile API Error: {e}")
        
        # Try to get available strategies
        try:
            strategies_response = await self.client.get(f"{BASE_URL}/api/v1/strategies/available")
            if strategies_response.status_code == 200:
                strategies_data = strategies_response.json()
                print(f"✅ Strategies Retrieved: {len(strategies_data)} strategies")
                for strategy in strategies_data[:3]:  # Show first 3
                    name = strategy.get('name', 'Unknown')
                    assets = len(strategy.get('assets', []))
                    print(f"   - {name}: {assets} assets")
            else:
                print(f"❌ Strategies API Failed: {strategies_response.status_code}")
        except Exception as e:
            print(f"❌ Strategies API Error: {e}")
    
    async def run_complete_debug(self):
        """Run complete debugging sequence"""
        print("🔍 Starting Weight Calculation Debug")
        print(f"🌐 Target: {BASE_URL}")
        print(f"⏰ Started: {datetime.now()}")
        
        if not await self.authenticate():
            return
        
        # Debug data flow
        portfolio_data = await self.debug_portfolio_data_flow()
        rebalance_data = await self.debug_rebalancing_weights()
        await self.debug_weight_calculation_internals()
        
        # Analysis
        print("\n" + "="*80)
        print("🎯 WEIGHT CALCULATION ANALYSIS")
        print("="*80)
        
        if portfolio_data and rebalance_data:
            portfolio_value = float(portfolio_data.get('total_value', 0))
            rebalance_portfolio_value = float(rebalance_data.get('portfolio_value', 0) or 0)
            
            print(f"📊 Portfolio Value Consistency:")
            print(f"   Portfolio API: ${portfolio_value}")
            print(f"   Rebalancing API: ${rebalance_portfolio_value}")
            print(f"   Match: {'✅' if abs(portfolio_value - rebalance_portfolio_value) < 0.01 else '❌'}")
            
            # Check positions vs trades
            positions = portfolio_data.get('positions', [])
            trades = rebalance_data.get('trades', [])
            
            print(f"\n📊 Position vs Trade Analysis:")
            print(f"   Portfolio Positions: {len(positions)}")
            print(f"   Rebalancing Trades: {len(trades)}")
            
            # Check if positions have values but trades have zero amounts
            position_symbols = {pos.get('symbol') for pos in positions if pos.get('value', 0) > 0}
            zero_amount_trades = [trade for trade in trades if trade.get('amount', 0) == 0]
            
            print(f"   Positions with Value: {len(position_symbols)}")
            print(f"   Zero Amount Trades: {len(zero_amount_trades)}")
            
            if len(position_symbols) > 0 and len(zero_amount_trades) == len(trades):
                print(f"🎯 ROOT CAUSE IDENTIFIED:")
                print(f"   ❌ Portfolio has positions with value")
                print(f"   ❌ But all rebalancing trades show $0.00 amounts")
                print(f"   ❌ This indicates weight calculation is failing")
                print(f"   📍 LIKELY ISSUE: Position values not being converted to weights properly")
        
        await self.client.aclose()
        print(f"\n⏰ Debug completed: {datetime.now()}")

async def main():
    debugger = WeightCalculationDebugger()
    await debugger.run_complete_debug()

if __name__ == "__main__":
    asyncio.run(main())