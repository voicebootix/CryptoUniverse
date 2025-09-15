"""
SIMPLE ASSET DISCOVERY SERVICE

A simplified version that uses only confirmed working APIs:
- Kraken: Confirmed working
- KuCoin: Confirmed working  
- Binance.us: Confirmed working

This replaces the complex dynamic discovery until all parsers are implemented.
"""

import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Any
import structlog

logger = structlog.get_logger(__name__)


class SimpleAssetDiscovery:
    """Simple asset discovery using only working APIs."""
    
    def __init__(self):
        self.working_exchanges = {
            "kraken": {
                "url": "https://api.kraken.com/0/public/Ticker",
                "parser": self._parse_kraken
            },
            "kucoin": {
                "url": "https://api.kucoin.com/api/v1/market/allTickers", 
                "parser": self._parse_kucoin
            },
            "binance_us": {
                "url": "https://api.binance.us/api/v3/ticker/24hr",
                "parser": self._parse_binance
            }
        }
        
        self.session = None
    
    async def async_init(self):
        """Initialize async components."""
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
    
    async def get_top_assets(self, count: int = 50) -> List[str]:
        """Get top assets by volume from working exchanges."""
        
        await self.async_init()
        
        all_assets = []
        
        for exchange_id, config in self.working_exchanges.items():
            try:
                logger.info(f"Fetching from {exchange_id}")
                
                async with self.session.get(config["url"]) as response:
                    if response.status == 200:
                        data = await response.json()
                        assets = config["parser"](data)
                        all_assets.extend(assets)
                        logger.info(f"✅ {exchange_id}: {len(assets)} assets")
                    else:
                        logger.warning(f"❌ {exchange_id}: Status {response.status}")
                        
            except Exception as e:
                logger.error(f"❌ {exchange_id}: {e}")
        
        # Sort by volume and return top symbols
        all_assets.sort(key=lambda x: x["volume_usd"], reverse=True)
        top_symbols = [asset["symbol"] for asset in all_assets[:count]]
        
        logger.info(f"✅ Total assets discovered: {len(all_assets)}")
        logger.info(f"✅ Top {count} symbols: {top_symbols[:10]}...")
        
        return top_symbols
    
    def _parse_kraken(self, data: Dict) -> List[Dict]:
        """Parse Kraken ticker data."""
        assets = []
        
        if "result" in data:
            for symbol, ticker in data["result"].items():
                try:
                    # Extract base symbol (remove USDT, USD suffixes)
                    base_symbol = symbol.replace("USDT", "").replace("USD", "").replace("XBT", "BTC")
                    
                    # Get price and volume
                    price = float(ticker["c"][0]) if ticker.get("c") else 0
                    volume_24h = float(ticker["v"][1]) if ticker.get("v") else 0
                    volume_usd = volume_24h * price
                    
                    if base_symbol and volume_usd > 10000:  # Min $10K volume
                        assets.append({
                            "symbol": base_symbol,
                            "exchange": "kraken",
                            "price": price,
                            "volume_usd": volume_usd
                        })
                        
                except Exception:
                    continue
        
        return assets
    
    def _parse_kucoin(self, data: Dict) -> List[Dict]:
        """Parse KuCoin ticker data."""
        assets = []
        
        if "data" in data and "ticker" in data["data"]:
            for item in data["data"]["ticker"]:
                try:
                    symbol = item.get("symbol", "").replace("-USDT", "").replace("-USDC", "")
                    price = float(item.get("last", 0))
                    volume_usd = float(item.get("volValue", 0))
                    
                    if symbol and volume_usd > 10000:  # Min $10K volume
                        assets.append({
                            "symbol": symbol,
                            "exchange": "kucoin", 
                            "price": price,
                            "volume_usd": volume_usd
                        })
                        
                except Exception:
                    continue
        
        return assets
    
    def _parse_binance(self, data: List) -> List[Dict]:
        """Parse Binance.us ticker data."""
        assets = []
        
        for item in data:
            try:
                symbol = item.get("symbol", "").replace("USDT", "").replace("BUSD", "")
                price = float(item.get("lastPrice", 0))
                volume_usd = float(item.get("quoteVolume", 0))
                
                if symbol and volume_usd > 10000:  # Min $10K volume
                    assets.append({
                        "symbol": symbol,
                        "exchange": "binance_us",
                        "price": price, 
                        "volume_usd": volume_usd
                    })
                    
            except Exception:
                continue
        
        return assets
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.session:
            await self.session.close()


# Global instance
simple_asset_discovery = SimpleAssetDiscovery()