#!/usr/bin/env python3
"""
Test different Binance endpoints to see which ones are geo-blocked
"""

import asyncio
import aiohttp

async def test_binance_endpoints():
    """Test various Binance endpoints"""
    
    endpoints = [
        {
            "name": "Public Price Ticker",
            "url": "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
            "auth_required": False
        },
        {
            "name": "Public 24hr Ticker", 
            "url": "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT",
            "auth_required": False
        },
        {
            "name": "Exchange Info",
            "url": "https://api.binance.com/api/v3/exchangeInfo",
            "auth_required": False
        },
        {
            "name": "Ping",
            "url": "https://api.binance.com/api/v3/ping",
            "auth_required": False
        },
        {
            "name": "Server Time",
            "url": "https://api.binance.com/api/v3/time",
            "auth_required": False
        },
        {
            "name": "All 24hr Tickers",
            "url": "https://api.binance.com/api/v3/ticker/24hr",
            "auth_required": False
        }
    ]
    
    print("🔍 TESTING BINANCE ENDPOINTS")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            print(f"\n📊 Testing: {endpoint['name']}")
            print(f"   URL: {endpoint['url']}")
            
            try:
                async with session.get(
                    endpoint['url'], 
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    print(f"   Status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        if endpoint['name'] == 'Ping':
                            print(f"   Result: ✅ Ping successful")
                        elif endpoint['name'] == 'Server Time':
                            print(f"   Result: ✅ Server time: {data}")
                        elif endpoint['name'] == 'Exchange Info':
                            symbols_count = len(data.get('symbols', []))
                            print(f"   Result: ✅ {symbols_count} trading pairs available")
                        elif 'ticker' in endpoint['name'].lower():
                            if isinstance(data, list):
                                print(f"   Result: ✅ {len(data)} tickers returned")
                            else:
                                price = data.get('price') or data.get('lastPrice')
                                if price:
                                    print(f"   Result: ✅ BTC Price: ${float(price):,.2f}")
                                else:
                                    print(f"   Result: ✅ Data: {str(data)[:100]}...")
                    
                    elif response.status == 451:
                        text = await response.text()
                        print(f"   Result: ❌ GEO-BLOCKED (451)")
                        print(f"   Message: {text[:100]}...")
                        
                    else:
                        text = await response.text()
                        print(f"   Result: ❌ Error {response.status}")
                        print(f"   Message: {text[:100]}...")
                        
            except Exception as e:
                print(f"   Result: ❌ Exception: {e}")
    
    print("\n🌐 TESTING ALTERNATIVE BINANCE DOMAINS")
    print("=" * 60)
    
    alternative_domains = [
        "https://api1.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
        "https://api2.binance.com/api/v3/ticker/price?symbol=BTCUSDT", 
        "https://api3.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
        "https://api.binance.us/api/v3/ticker/price?symbol=BTCUSDT"
    ]
    
    async with aiohttp.ClientSession() as session:
        for url in alternative_domains:
            domain = url.split('/')[2]
            print(f"\n📊 Testing: {domain}")
            
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    print(f"   Status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        price = data.get('price')
                        print(f"   Result: ✅ BTC Price: ${float(price):,.2f}")
                    else:
                        text = await response.text()
                        print(f"   Result: ❌ {text[:100]}...")
                        
            except Exception as e:
                print(f"   Result: ❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_binance_endpoints())