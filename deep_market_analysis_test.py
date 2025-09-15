#!/usr/bin/env python3
"""
Deep Market Analysis Test - Chat vs Direct Endpoints
Test both chat system calls and direct API calls to compare results
"""

import asyncio
import sys
import traceback
sys.path.append('/workspace')

async def test_direct_market_analysis():
    """Test direct market analysis service calls"""
    print("🔧 Testing Direct Market Analysis Service...")
    print("=" * 60)
    
    try:
        from app.services.market_analysis_core import MarketAnalysisService
        
        service = MarketAnalysisService()
        
        # Test 1: Test with the problematic "all" parameter
        print("📊 Test 1: Testing with symbols='all' (problematic call)")
        try:
            result_all = await service.realtime_price_tracking(
                symbols="all",
                exchanges="all", 
                user_id="system"
            )
            print(f"  Result with 'all': Success={result_all.get('success')}")
            print(f"  Data count: {len(result_all.get('data', {}))}")
            print(f"  Error: {result_all.get('error', 'None')}")
        except Exception as e:
            print(f"  Exception with 'all': {e}")
        
        # Test 2: Test with specific symbols
        print("\n📊 Test 2: Testing with specific symbols")
        try:
            result_specific = await service.realtime_price_tracking(
                symbols="BTC,ETH,SOL",
                exchanges="all",
                user_id="system"
            )
            print(f"  Result with specific: Success={result_specific.get('success')}")
            print(f"  Data count: {len(result_specific.get('data', {}))}")
            print(f"  Error: {result_specific.get('error', 'None')}")
            
            if result_specific.get('data'):
                print("  Sample data:")
                for symbol, data in list(result_specific.get('data', {}).items())[:2]:
                    print(f"    {symbol}: {data}")
                    
        except Exception as e:
            print(f"  Exception with specific: {e}")
        
        # Test 3: Test complete market assessment 
        print("\n📊 Test 3: Testing complete_market_assessment")
        try:
            result_complete = await service.complete_market_assessment(
                symbols="BTC,ETH,SOL",
                depth="comprehensive",
                user_id="system"
            )
            print(f"  Complete assessment: Success={result_complete.get('success')}")
            print(f"  Components: {len(result_complete.get('data', {}).get('assessment', {}))}")
            print(f"  Error: {result_complete.get('error', 'None')}")
            
        except Exception as e:
            print(f"  Exception with complete assessment: {e}")
            traceback.print_exc()
        
        return True
        
    except Exception as e:
        print(f"❌ Direct Market Analysis failed: {e}")
        traceback.print_exc()
        return False

async def test_chat_adapter_calls():
    """Test chat service adapter calls"""
    print("\n🔧 Testing Chat Service Adapter Calls...")
    print("=" * 60)
    
    try:
        from app.services.chat_service_adapters_fixed import ChatServiceAdaptersFixed
        
        adapter = ChatServiceAdaptersFixed()
        
        # Test market overview call (the problematic one)
        print("📊 Testing get_market_overview() - The Problematic Call")
        try:
            market_overview = await adapter.get_market_overview()
            print(f"  Success: {market_overview.get('success', 'No success field')}")
            print(f"  Sentiment: {market_overview.get('sentiment')}")
            print(f"  Trend: {market_overview.get('trend')}")
            print(f"  Market Cap: {market_overview.get('total_market_cap')}")
            print(f"  Volume: {market_overview.get('total_volume_24h')}")
            print(f"  Available Symbols: {len(market_overview.get('available_symbols', []))}")
            print(f"  Error: {market_overview.get('error', 'None')}")
            
        except Exception as e:
            print(f"  Exception in market overview: {e}")
            traceback.print_exc()
        
        # Test technical analysis
        print("\n📊 Testing get_technical_analysis()")
        try:
            tech_analysis = await adapter.get_technical_analysis("BTC,ETH,SOL")
            print(f"  Success: {tech_analysis.get('success')}")
            print(f"  Data count: {len(tech_analysis.get('data', {}))}")
            print(f"  Error: {tech_analysis.get('error', 'None')}")
            
        except Exception as e:
            print(f"  Exception in technical analysis: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Chat Adapter test failed: {e}")
        traceback.print_exc()
        return False

async def test_trading_endpoint():
    """Test the actual trading endpoint that works"""
    print("\n🔧 Testing Direct Trading Endpoint...")
    print("=" * 60)
    
    try:
        from app.api.v1.endpoints.trading import market_analysis
        
        # Test the working endpoint directly
        print("📊 Testing market_analysis.realtime_price_tracking()")
        result = await market_analysis.realtime_price_tracking(
            symbols="BTC,ETH,SOL",
            exchanges="all",
            user_id="system"
        )
        
        print(f"  Trading endpoint result:")
        print(f"  Success: {result.get('success')}")
        print(f"  Function: {result.get('function')}")
        print(f"  Data count: {len(result.get('data', {}))}")
        print(f"  Error: {result.get('error', 'None')}")
        
        if result.get('data'):
            print("  Sample data from trading endpoint:")
            for symbol, data in list(result.get('data', {}).items())[:2]:
                print(f"    {symbol}: Price data available = {bool(data)}")
        
        return result.get('success', False)
        
    except Exception as e:
        print(f"❌ Trading endpoint test failed: {e}")
        traceback.print_exc()
        return False

async def main():
    print("🔍 DEEP MARKET ANALYSIS TEST")
    print("Testing Chat vs Direct Endpoints")
    print("=" * 80)
    
    # Test all approaches
    direct_ok = await test_direct_market_analysis()
    chat_ok = await test_chat_adapter_calls() 
    trading_ok = await test_trading_endpoint()
    
    print("\n📊 COMPARISON SUMMARY:")
    print("=" * 60)
    print(f"Direct Market Service: {'✅' if direct_ok else '❌'}")
    print(f"Chat Service Adapter: {'✅' if chat_ok else '❌'}")
    print(f"Trading Endpoint: {'✅' if trading_ok else '❌'}")

if __name__ == "__main__":
    asyncio.run(main())