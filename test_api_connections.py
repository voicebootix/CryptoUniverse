#!/usr/bin/env python3
"""
Test actual API connections to verify root causes
"""

import asyncio
import aiohttp
import time

async def test_binance_api():
    """Test Binance API connection"""
    try:
        async with aiohttp.ClientSession() as session:
            # Test basic price endpoint
            url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Binance API: BTC Price = ${float(data['price']):,.2f}")
                    return True
                else:
                    print(f"❌ Binance API Error: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Binance API Exception: {e}")
        return False

async def test_kraken_api():
    """Test Kraken API connection"""
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.kraken.com/0/public/Ticker?pair=XBTUSDT"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    if "result" in data and "XBTUSDT" in data["result"]:
                        price = float(data["result"]["XBTUSDT"]["c"][0])
                        print(f"✅ Kraken API: BTC Price = ${price:,.2f}")
                        return True
                    else:
                        print(f"❌ Kraken API: Invalid response format")
                        return False
                else:
                    print(f"❌ Kraken API Error: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Kraken API Exception: {e}")
        return False

async def test_kucoin_api():
    """Test KuCoin API connection"""
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.kucoin.com/api/v1/market/stats?symbol=BTC-USDT"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    if "data" in data and data["data"]:
                        price = float(data["data"]["last"])
                        print(f"✅ KuCoin API: BTC Price = ${price:,.2f}")
                        return True
                    else:
                        print(f"❌ KuCoin API: No data")
                        return False
                else:
                    print(f"❌ KuCoin API Error: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ KuCoin API Exception: {e}")
        return False

async def test_market_analysis_service():
    """Test the actual market analysis service"""
    try:
        import sys
        sys.path.append('/workspace')
        
        from app.services.market_analysis_core import MarketAnalysisService
        
        service = MarketAnalysisService()
        
        # Test with valid symbols (not "all")
        result = await service.realtime_price_tracking(
            symbols="BTC,ETH,SOL",
            exchanges="all",
            user_id="test"
        )
        
        print(f"Market Analysis Service:")
        print(f"  Success: {result.get('success', False)}")
        print(f"  Data Count: {len(result.get('data', {}))}")
        print(f"  Error: {result.get('error', 'None')}")
        
        return result.get('success', False)
        
    except Exception as e:
        print(f"❌ Market Analysis Service Exception: {e}")
        return False

async def test_trading_strategies_risk():
    """Test the trading strategies risk management"""
    try:
        import sys
        sys.path.append('/workspace')
        
        from app.services.trading_strategies import TradingStrategiesService
        
        service = TradingStrategiesService()
        
        # Test risk management function
        result = await service.risk_management(
            analysis_type="comprehensive",
            symbols="BTC,ETH",
            user_id="test"
        )
        
        print(f"Risk Management Service:")
        print(f"  Success: {result.get('success', False)}")
        print(f"  Has Portfolio Metrics: {'portfolio_risk_metrics' in result.get('risk_management_analysis', {})}")
        print(f"  Error: {result.get('error', 'None')}")
        
        return result.get('success', False)
        
    except Exception as e:
        print(f"❌ Risk Management Service Exception: {e}")
        return False

async def main():
    print("🔍 Testing API Connections and Services...")
    print("=" * 50)
    
    # Test external APIs
    binance_ok = await test_binance_api()
    kraken_ok = await test_kraken_api()
    kucoin_ok = await test_kucoin_api()
    
    print("\n🔧 Testing Internal Services...")
    print("=" * 50)
    
    # Test internal services
    market_ok = await test_market_analysis_service()
    risk_ok = await test_trading_strategies_risk()
    
    print("\n📊 Summary:")
    print("=" * 50)
    print(f"Binance API: {'✅' if binance_ok else '❌'}")
    print(f"Kraken API: {'✅' if kraken_ok else '❌'}")
    print(f"KuCoin API: {'✅' if kucoin_ok else '❌'}")
    print(f"Market Analysis: {'✅' if market_ok else '❌'}")
    print(f"Risk Management: {'✅' if risk_ok else '❌'}")
    
    external_apis = binance_ok + kraken_ok + kucoin_ok
    internal_services = market_ok + risk_ok
    
    print(f"\nExternal APIs: {external_apis}/3 working")
    print(f"Internal Services: {internal_services}/2 working")

if __name__ == "__main__":
    asyncio.run(main())