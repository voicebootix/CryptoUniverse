#!/usr/bin/env python3
"""
Debug Symbol Matching Issue
Focus: Check if optimal_weights symbols match current portfolio symbols
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.chat_service_adapters_fixed import ChatServiceAdaptersFixed
from app.core.database import AsyncSessionLocal
import structlog

logger = structlog.get_logger(__name__)

class SymbolMatchingDebugger:
    def __init__(self):
        self.chat_adapters = ChatServiceAdaptersFixed()
        
    async def debug_portfolio_and_optimization_symbols(self):
        """Debug the symbols in portfolio vs optimization"""
        print("🔍 Starting Symbol Matching Debug")
        print("="*80)
        
        # Use admin user ID (from previous tests)
        user_id = "admin@cryptouniverse.com"  # This might need to be the actual UUID
        
        try:
            # Step 1: Get portfolio summary
            print("\n📊 STEP 1: Getting Portfolio Summary")
            print("-" * 40)
            
            portfolio_data = await self.chat_adapters.get_portfolio_summary(user_id)
            
            if portfolio_data.get("error"):
                print(f"❌ Portfolio Error: {portfolio_data.get('error')}")
                return
            
            total_value = portfolio_data.get("total_value", 0)
            positions = portfolio_data.get("positions", [])
            
            print(f"✅ Portfolio Retrieved:")
            print(f"   Total Value: ${total_value}")
            print(f"   Positions Count: {len(positions)}")
            
            # Extract symbols from portfolio
            portfolio_symbols = set()
            for pos in positions:
                symbol = pos.get("symbol")
                if symbol:
                    portfolio_symbols.add(symbol)
            
            print(f"   Portfolio Symbols: {sorted(list(portfolio_symbols))}")
            
            # Step 2: Get rebalancing analysis
            print("\n📊 STEP 2: Getting Rebalancing Analysis")
            print("-" * 40)
            
            rebalancing_data = await self.chat_adapters.analyze_rebalancing_needs(user_id, "adaptive")
            
            if rebalancing_data.get("error"):
                print(f"❌ Rebalancing Error: {rebalancing_data.get('error')}")
                return
            
            recommended_trades = rebalancing_data.get("recommended_trades", [])
            print(f"✅ Rebalancing Analysis Retrieved:")
            print(f"   Recommended Trades Count: {len(recommended_trades)}")
            
            # Extract symbols from trades
            trade_symbols = set()
            for trade in recommended_trades:
                symbol = trade.get("symbol")
                if symbol:
                    trade_symbols.add(symbol)
            
            print(f"   Trade Symbols: {sorted(list(trade_symbols))}")
            
            # Step 3: Symbol Matching Analysis
            print("\n📊 STEP 3: Symbol Matching Analysis")
            print("-" * 40)
            
            matching_symbols = portfolio_symbols.intersection(trade_symbols)
            portfolio_only = portfolio_symbols - trade_symbols
            trades_only = trade_symbols - portfolio_symbols
            
            print(f"✅ Symbol Analysis:")
            print(f"   Portfolio Symbols: {len(portfolio_symbols)}")
            print(f"   Trade Symbols: {len(trade_symbols)}")
            print(f"   Matching Symbols: {len(matching_symbols)}")
            print(f"   Portfolio Only: {len(portfolio_only)}")
            print(f"   Trades Only: {len(trades_only)}")
            
            if matching_symbols:
                print(f"   Matching: {sorted(list(matching_symbols))}")
            if portfolio_only:
                print(f"   Portfolio Only: {sorted(list(portfolio_only))}")
            if trades_only:
                print(f"   Trades Only: {sorted(list(trades_only))}")
            
            # Step 4: Check individual trade details
            print("\n📊 STEP 4: Individual Trade Analysis")
            print("-" * 40)
            
            for i, trade in enumerate(recommended_trades[:5]):  # First 5 trades
                symbol = trade.get("symbol", "Unknown")
                current_value = trade.get("current_value", 0)
                target_value = trade.get("target_value", 0)
                value_change = trade.get("value_change", 0)
                
                print(f"   Trade {i+1}: {symbol}")
                print(f"     Current Value: ${current_value}")
                print(f"     Target Value: ${target_value}")
                print(f"     Value Change: ${value_change}")
                
                # Check if this symbol exists in portfolio
                portfolio_position = None
                for pos in positions:
                    if pos.get("symbol") == symbol:
                        portfolio_position = pos
                        break
                
                if portfolio_position:
                    pos_value = portfolio_position.get("value_usd", 0)
                    pos_amount = portfolio_position.get("amount", 0)
                    print(f"     Portfolio Match: ${pos_value} ({pos_amount} units)")
                else:
                    print(f"     Portfolio Match: ❌ NOT FOUND")
            
            # Step 5: Root Cause Analysis
            print("\n🎯 ROOT CAUSE ANALYSIS")
            print("="*80)
            
            if len(matching_symbols) == 0:
                print("❌ CRITICAL ISSUE: No symbols match between portfolio and trades")
                print("   This means the optimization engine is generating trades for")
                print("   completely different assets than what's in the portfolio")
            elif len(matching_symbols) < len(portfolio_symbols):
                print("⚠️  PARTIAL ISSUE: Some portfolio symbols missing from trades")
                print("   The optimization engine may not be considering all assets")
            else:
                print("✅ Symbol matching looks correct")
                print("   The issue may be in the value calculations")
            
            # Check if all trade values are zero
            zero_value_trades = [t for t in recommended_trades if t.get("value_change", 0) == 0]
            if len(zero_value_trades) == len(recommended_trades):
                print("❌ ALL TRADES HAVE ZERO VALUE CHANGES")
                print("   This suggests the current_value calculation is wrong")
            
        except Exception as e:
            print(f"❌ Debug Error: {e}")
            import traceback
            traceback.print_exc()

async def main():
    debugger = SymbolMatchingDebugger()
    await debugger.debug_portfolio_and_optimization_symbols()

if __name__ == "__main__":
    asyncio.run(main())