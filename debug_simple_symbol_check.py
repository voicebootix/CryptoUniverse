#!/usr/bin/env python3
"""
Simple Symbol Matching Debug
Focus: Check symbols without importing full app
"""

import asyncio
import httpx
import json
import re
from datetime import datetime

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com"
LOGIN_DATA = {
    "email": "admin@cryptouniverse.com",
    "password": "AdminPass123!"
}

class SimpleSymbolDebugger:
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
    
    async def get_portfolio_symbols(self):
        """Get symbols from portfolio API"""
        print("\n📊 Getting Portfolio Symbols")
        print("-" * 40)
        
        try:
            portfolio_response = await self.client.get(f"{BASE_URL}/api/v1/trading/portfolio")
            if portfolio_response.status_code == 200:
                portfolio_data = portfolio_response.json()
                
                total_value = float(portfolio_data.get('total_value', 0))
                positions = portfolio_data.get('positions', [])
                
                print(f"✅ Portfolio Data:")
                print(f"   Total Value: ${total_value}")
                print(f"   Positions Count: {len(positions)}")
                
                # Extract symbols and their details
                portfolio_symbols = {}
                for pos in positions:
                    symbol = pos.get('symbol')
                    amount = pos.get('amount', 0)
                    value_usd = pos.get('value_usd', 0)
                    if symbol and value_usd > 0:
                        portfolio_symbols[symbol] = {
                            'amount': amount,
                            'value_usd': value_usd,
                            'percentage': (value_usd / total_value * 100) if total_value > 0 else 0
                        }
                
                print(f"   Symbols with Value > 0: {len(portfolio_symbols)}")
                for symbol, data in list(portfolio_symbols.items())[:5]:  # Show top 5
                    print(f"     {symbol}: {data['amount']} units = ${data['value_usd']} ({data['percentage']:.1f}%)")
                
                return portfolio_symbols, total_value
            else:
                print(f"❌ Portfolio API Failed: {portfolio_response.status_code}")
                return {}, 0
        except Exception as e:
            print(f"❌ Portfolio API Error: {e}")
            return {}, 0
    
    async def get_rebalancing_symbols(self):
        """Get symbols from rebalancing chat response"""
        print("\n📊 Getting Rebalancing Symbols")
        print("-" * 40)
        
        try:
            chat_response = await self.client.post(
                f"{BASE_URL}/api/v1/chat/message",
                json={"message": "rebalance"}
            )
            
            if chat_response.status_code == 200:
                chat_data = chat_response.json()
                response_content = chat_data.get('content', '')
                
                print(f"✅ Chat Rebalancing Response Received")
                
                # Extract symbols from the response using regex
                trade_pattern = r'\*\*(BUY|SELL)\s+([A-Z]+)\*\*'
                trades = re.findall(trade_pattern, response_content)
                
                # Extract amounts
                amount_pattern = r'Amount: \$([0-9,]+\.?[0-9]*)'
                amounts = re.findall(amount_pattern, response_content)
                
                # Extract current and target percentages
                current_pattern = r'Current: ([0-9]+\.?[0-9]*)%'
                target_pattern = r'Target: ([0-9]+\.?[0-9]*)%'
                current_percentages = re.findall(current_pattern, response_content)
                target_percentages = re.findall(target_pattern, response_content)
                
                print(f"   Trades Found: {len(trades)}")
                print(f"   Amounts Found: {len(amounts)}")
                print(f"   Current %s Found: {len(current_percentages)}")
                print(f"   Target %s Found: {len(target_percentages)}")
                
                # Combine the data
                rebalancing_symbols = {}
                for i, (action, symbol) in enumerate(trades):
                    amount = float(amounts[i].replace(',', '')) if i < len(amounts) else 0
                    current_pct = float(current_percentages[i]) if i < len(current_percentages) else 0
                    target_pct = float(target_percentages[i]) if i < len(target_percentages) else 0
                    
                    rebalancing_symbols[symbol] = {
                        'action': action,
                        'amount': amount,
                        'current_pct': current_pct,
                        'target_pct': target_pct
                    }
                
                print(f"   Rebalancing Symbols: {len(rebalancing_symbols)}")
                for symbol, data in rebalancing_symbols.items():
                    print(f"     {data['action']} {symbol}: ${data['amount']} ({data['current_pct']}% → {data['target_pct']}%)")
                
                return rebalancing_symbols, response_content
            else:
                print(f"❌ Chat Rebalancing Failed: {chat_response.status_code}")
                return {}, ""
        except Exception as e:
            print(f"❌ Chat Rebalancing Error: {e}")
            return {}, ""
    
    async def run_symbol_analysis(self):
        """Run complete symbol analysis"""
        print("🔍 Starting Simple Symbol Matching Debug")
        print(f"🌐 Target: {BASE_URL}")
        print(f"⏰ Started: {datetime.now()}")
        
        if not await self.authenticate():
            return
        
        # Get data from both sources
        portfolio_symbols, portfolio_total = await self.get_portfolio_symbols()
        rebalancing_symbols, chat_response = await self.get_rebalancing_symbols()
        
        # Analysis
        print("\n" + "="*80)
        print("🎯 SYMBOL MATCHING ANALYSIS")
        print("="*80)
        
        if portfolio_symbols and rebalancing_symbols:
            portfolio_set = set(portfolio_symbols.keys())
            rebalancing_set = set(rebalancing_symbols.keys())
            
            matching = portfolio_set.intersection(rebalancing_set)
            portfolio_only = portfolio_set - rebalancing_set
            rebalancing_only = rebalancing_set - portfolio_set
            
            print(f"📊 Symbol Comparison:")
            print(f"   Portfolio Symbols: {len(portfolio_set)} - {sorted(list(portfolio_set))}")
            print(f"   Rebalancing Symbols: {len(rebalancing_set)} - {sorted(list(rebalancing_set))}")
            print(f"   Matching Symbols: {len(matching)} - {sorted(list(matching))}")
            print(f"   Portfolio Only: {len(portfolio_only)} - {sorted(list(portfolio_only))}")
            print(f"   Rebalancing Only: {len(rebalancing_only)} - {sorted(list(rebalancing_only))}")
            
            # Check for the zero amounts issue
            zero_amount_trades = [s for s, data in rebalancing_symbols.items() if data['amount'] == 0]
            zero_current_pct = [s for s, data in rebalancing_symbols.items() if data['current_pct'] == 0]
            zero_target_pct = [s for s, data in rebalancing_symbols.items() if data['target_pct'] == 0]
            
            print(f"\n🎯 ZERO VALUES ANALYSIS:")
            print(f"   Zero Amount Trades: {len(zero_amount_trades)}/{len(rebalancing_symbols)}")
            print(f"   Zero Current %: {len(zero_current_pct)}/{len(rebalancing_symbols)}")
            print(f"   Zero Target %: {len(zero_target_pct)}/{len(rebalancing_symbols)}")
            
            if len(zero_amount_trades) == len(rebalancing_symbols):
                print(f"   ❌ ALL TRADE AMOUNTS ARE ZERO")
            if len(zero_current_pct) == len(rebalancing_symbols):
                print(f"   ❌ ALL CURRENT PERCENTAGES ARE ZERO")
            if len(zero_target_pct) == len(rebalancing_symbols):
                print(f"   ❌ ALL TARGET PERCENTAGES ARE ZERO")
            
            # Detailed matching analysis
            print(f"\n📊 DETAILED MATCHING ANALYSIS:")
            for symbol in matching:
                portfolio_data = portfolio_symbols[symbol]
                rebalancing_data = rebalancing_symbols[symbol]
                
                print(f"   {symbol}:")
                print(f"     Portfolio: {portfolio_data['amount']} units = ${portfolio_data['value_usd']} ({portfolio_data['percentage']:.1f}%)")
                print(f"     Rebalancing: {rebalancing_data['action']} ${rebalancing_data['amount']} ({rebalancing_data['current_pct']}% → {rebalancing_data['target_pct']}%)")
                
                # Check if current percentage matches portfolio percentage
                if abs(portfolio_data['percentage'] - rebalancing_data['current_pct']) > 0.1:
                    print(f"     ⚠️  PERCENTAGE MISMATCH: Portfolio {portfolio_data['percentage']:.1f}% vs Rebalancing {rebalancing_data['current_pct']}%")
        
        await self.client.aclose()
        print(f"\n⏰ Debug completed: {datetime.now()}")

async def main():
    debugger = SimpleSymbolDebugger()
    await debugger.run_symbol_analysis()

if __name__ == "__main__":
    asyncio.run(main())