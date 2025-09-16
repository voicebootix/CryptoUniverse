#!/usr/bin/env python3
"""
Simple API Test - Test just the core functionality without full framework
"""

import asyncio
import aiohttp
import sys
import os

# Set minimal environment variables to avoid config errors
os.environ['SECRET_KEY'] = 'test-key-for-analysis'
os.environ['DATABASE_URL'] = 'sqlite:///test.db'
os.environ['ENVIRONMENT'] = 'development'

sys.path.append('/workspace')

async def test_exchange_apis_detailed():
    """Test each exchange API in detail"""
    print("🔍 DETAILED EXCHANGE API TESTING")
    print("=" * 60)
    
    # Test Binance with different endpoints
    print("📊 BINANCE API DETAILED TEST")
    try:
        async with aiohttp.ClientSession() as session:
            # Test 1: Basic ticker
            print("  Test 1: Basic ticker endpoint")
            url1 = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
            async with session.get(url1, timeout=aiohttp.ClientTimeout(total=10)) as response:
                print(f"    Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"    BTC Price: ${float(data['price']):,.2f}")
                else:
                    text = await response.text()
                    print(f"    Error: {text[:200]}")
            
            # Test 2: 24hr ticker
            print("  Test 2: 24hr ticker endpoint")
            url2 = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
            async with session.get(url2, timeout=aiohttp.ClientTimeout(total=10)) as response:
                print(f"    Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"    BTC 24h Data: Price=${float(data['lastPrice']):,.2f}, Volume={float(data['volume']):,.0f}")
                else:
                    text = await response.text()
                    print(f"    Error: {text[:200]}")
                    
            # Test 3: Multiple symbols
            print("  Test 3: Multiple symbols")
            symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
            for symbol in symbols:
                url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            data = await response.json()
                            print(f"    {symbol}: ${float(data['price']):,.2f}")
                        else:
                            print(f"    {symbol}: Error {response.status}")
                except Exception as e:
                    print(f"    {symbol}: Exception {e}")
                    
    except Exception as e:
        print(f"  Binance test failed: {e}")
    
    # Test other exchanges
    print("\n📊 OTHER EXCHANGES")
    
    # Kraken
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.kraken.com/0/public/Ticker?pair=XBTUSDT"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    if "result" in data and "XBTUSDT" in data["result"]:
                        price = float(data["result"]["XBTUSDT"]["c"][0])
                        print(f"  Kraken BTC: ${price:,.2f} ✅")
                    else:
                        print(f"  Kraken: Invalid format ❌")
                else:
                    print(f"  Kraken: Error {response.status} ❌")
    except Exception as e:
        print(f"  Kraken: Exception {e} ❌")
    
    # KuCoin
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.kucoin.com/api/v1/market/stats?symbol=BTC-USDT"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    if "data" in data and data["data"]:
                        price = float(data["data"]["last"])
                        print(f"  KuCoin BTC: ${price:,.2f} ✅")
                    else:
                        print(f"  KuCoin: No data ❌")
                else:
                    print(f"  KuCoin: Error {response.status} ❌")
    except Exception as e:
        print(f"  KuCoin: Exception {e} ❌")

async def test_symbols_parameter():
    """Test what happens with different symbols parameters"""
    print("\n🔍 TESTING SYMBOLS PARAMETER BEHAVIOR")
    print("=" * 60)
    
    test_cases = [
        "all",
        "BTC",
        "BTC,ETH",
        "BTC,ETH,SOL",
        "SMART_ADAPTIVE",
        "DYNAMIC_DISCOVERY"
    ]
    
    for symbols in test_cases:
        print(f"\n📊 Testing symbols='{symbols}'")
        
        # Simulate what the code does
        symbol_list = [s.strip() for s in symbols.split(",")]
        print(f"  Split result: {symbol_list}")
        
        # Test if these would work with Binance
        for symbol in symbol_list[:3]:  # Test first 3 only
            if symbol in ["all", "SMART_ADAPTIVE", "DYNAMIC_DISCOVERY"]:
                print(f"    {symbol}: ❌ Invalid crypto symbol")
            else:
                # Try to convert to Binance format
                binance_symbol = f"{symbol}USDT" if symbol not in ["BTC", "ETH"] else f"{symbol}USDT"
                print(f"    {symbol} -> {binance_symbol}: ✅ Valid format")

async def test_working_portfolio_endpoint():
    """Test if we can access the working portfolio endpoint logic"""
    print("\n🔍 TESTING PORTFOLIO ENDPOINT LOGIC")
    print("=" * 60)
    
    try:
        # Try to import just the portfolio logic
        from app.api.v1.endpoints.exchanges import get_user_portfolio_from_exchanges
        print("✅ Portfolio function imported successfully")
        
        # This would need a database connection, so we can't test it fully
        print("  (Cannot test execution without database)")
        
    except Exception as e:
        print(f"❌ Portfolio function import failed: {e}")

async def main():
    print("🔍 SIMPLE API AND LOGIC TEST")
    print("=" * 80)
    
    await test_exchange_apis_detailed()
    await test_symbols_parameter()
    await test_working_portfolio_endpoint()

if __name__ == "__main__":
    asyncio.run(main())