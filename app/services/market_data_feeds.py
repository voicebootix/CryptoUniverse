"""
Market Data Feeds - Real Free APIs

Provides real-time market data using free APIs like CoinGecko, CoinCap,
and other free sources for the AI money manager platform.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import aiohttp
import structlog
from app.core.config import get_settings
from app.core.redis import redis_client
from app.core.supabase import supabase_client

settings = get_settings()
logger = structlog.get_logger(__name__)


class MarketDataFeeds:
    """Real market data feeds using free APIs."""
    
    def __init__(self):
        self.redis = redis_client
        
        # Free API endpoints
        self.apis = {
            "coingecko": {
                "base_url": "https://api.coingecko.com/api/v3",
                "rate_limit": 50,  # 50 calls per minute for free tier
                "endpoints": {
                    "price": "/simple/price",
                    "coins": "/coins/{id}",
                    "markets": "/coins/markets"
                }
            },
            "coincap": {
                "base_url": "https://api.coincap.io/v2",
                "rate_limit": 100,  # 100 calls per minute
                "endpoints": {
                    "assets": "/assets",
                    "asset": "/assets/{id}",
                    "rates": "/rates"
                }
            },
            "coinpaprika": {
                "base_url": "https://api.coinpaprika.com/v1",
                "rate_limit": 20000,  # 20k calls per month
                "endpoints": {
                    "tickers": "/tickers",
                    "ticker": "/tickers/{id}"
                }
            }
        }
        
        # Symbol mappings for different APIs
        self.symbol_mappings = {
            "coingecko": {
                "BTC": "bitcoin",
                "ETH": "ethereum", 
                "SOL": "solana",
                "ADA": "cardano",
                "DOT": "polkadot",
                "MATIC": "matic-network",
                "LINK": "chainlink",
                "UNI": "uniswap",
                "AVAX": "avalanche-2",
                "ATOM": "cosmos"
            },
            "coincap": {
                "BTC": "bitcoin",
                "ETH": "ethereum",
                "SOL": "solana", 
                "ADA": "cardano",
                "DOT": "polkadot",
                "MATIC": "polygon",
                "LINK": "chainlink",
                "UNI": "uniswap",
                "AVAX": "avalanche",
                "ATOM": "cosmos"
            }
        }
        
        # Cache settings
        self.cache_ttl = {
            "price": 30,      # 30 seconds for prices
            "detailed": 300,  # 5 minutes for detailed data
            "markets": 600    # 10 minutes for market data
        }
    
    async def get_real_time_price(self, symbol: str) -> Dict[str, Any]:
        """Get real-time price data for a symbol."""
        try:
            # Check cache first
            cache_key = f"price:{symbol}"
            cached_data = await self.redis.get(cache_key)
            
            if cached_data:
                try:
                    return eval(cached_data)
                except:
                    pass
            
            # Try CoinGecko first (most reliable)
            price_data = await self._fetch_coingecko_price(symbol)
            
            if not price_data.get("success"):
                # Fallback to CoinCap
                price_data = await self._fetch_coincap_price(symbol)
            
            if price_data.get("success"):
                # Cache the result
                await self.redis.setex(
                    cache_key,
                    self.cache_ttl["price"],
                    str(price_data)
                )
                
                # Sync to Supabase
                await supabase_client.sync_market_data(symbol, price_data.get("data", {}))
            
            return price_data
            
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def get_detailed_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get detailed market data including volume, market cap, etc."""
        try:
            cache_key = f"detailed:{symbol}"
            cached_data = await self.redis.get(cache_key)
            
            if cached_data:
                try:
                    return eval(cached_data)
                except:
                    pass
            
            # Get detailed data from CoinGecko
            detailed_data = await self._fetch_coingecko_detailed(symbol)
            
            if detailed_data.get("success"):
                await self.redis.setex(
                    cache_key,
                    self.cache_ttl["detailed"],
                    str(detailed_data)
                )
            
            return detailed_data
            
        except Exception as e:
            logger.error(f"Failed to get detailed data for {symbol}", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def get_multiple_prices(self, symbols: List[str]) -> Dict[str, Any]:
        """Get prices for multiple symbols efficiently."""
        try:
            # Use CoinGecko batch API
            symbol_ids = []
            symbol_map = {}
            
            for symbol in symbols:
                if symbol in self.symbol_mappings["coingecko"]:
                    coin_id = self.symbol_mappings["coingecko"][symbol]
                    symbol_ids.append(coin_id)
                    symbol_map[coin_id] = symbol
            
            if not symbol_ids:
                return {"success": False, "error": "No valid symbols"}
            
            url = f"{self.apis['coingecko']['base_url']}/simple/price"
            params = {
                "ids": ",".join(symbol_ids),
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true",
                "include_market_cap": "true"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Transform data
                        result = {"success": True, "data": {}}
                        
                        for coin_id, coin_data in data.items():
                            symbol = symbol_map.get(coin_id, coin_id.upper())
                            result["data"][symbol] = {
                                "symbol": symbol,
                                "price": coin_data.get("usd", 0),
                                "change_24h": coin_data.get("usd_24h_change", 0),
                                "volume_24h": coin_data.get("usd_24h_vol", 0),
                                "market_cap": coin_data.get("usd_market_cap", 0),
                                "timestamp": datetime.utcnow().isoformat(),
                                "source": "coingecko"
                            }
                            
                            # Cache individual prices
                            await self.redis.setex(
                                f"price:{symbol}",
                                self.cache_ttl["price"],
                                str({
                                    "success": True,
                                    "data": result["data"][symbol]
                                })
                            )
                        
                        return result
                    else:
                        return {"success": False, "error": f"API error: {response.status}"}
                        
        except Exception as e:
            logger.error("Failed to get multiple prices", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def get_trending_coins(self, limit: int = 10) -> Dict[str, Any]:
        """Get trending coins from CoinGecko."""
        try:
            url = f"{self.apis['coingecko']['base_url']}/search/trending"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        trending = []
                        for coin in data.get("coins", [])[:limit]:
                            coin_data = coin.get("item", {})
                            trending.append({
                                "symbol": coin_data.get("symbol", "").upper(),
                                "name": coin_data.get("name", ""),
                                "rank": coin_data.get("market_cap_rank", 0),
                                "price_btc": coin_data.get("price_btc", 0)
                            })
                        
                        return {
                            "success": True,
                            "data": trending,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    else:
                        return {"success": False, "error": f"API error: {response.status}"}
                        
        except Exception as e:
            logger.error("Failed to get trending coins", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _fetch_coingecko_price(self, symbol: str) -> Dict[str, Any]:
        """Fetch price from CoinGecko API."""
        try:
            if symbol not in self.symbol_mappings["coingecko"]:
                return {"success": False, "error": f"Symbol {symbol} not supported"}
            
            coin_id = self.symbol_mappings["coingecko"][symbol]
            url = f"{self.apis['coingecko']['base_url']}/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        coin_data = data.get(coin_id, {})
                        
                        if coin_data:
                            return {
                                "success": True,
                                "data": {
                                    "symbol": symbol,
                                    "price": coin_data.get("usd", 0),
                                    "change_24h": coin_data.get("usd_24h_change", 0),
                                    "volume_24h": coin_data.get("usd_24h_vol", 0),
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "source": "coingecko"
                                }
                            }
                    
                    return {"success": False, "error": f"API error: {response.status}"}
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _fetch_coincap_price(self, symbol: str) -> Dict[str, Any]:
        """Fetch price from CoinCap API as fallback."""
        try:
            if symbol not in self.symbol_mappings["coincap"]:
                return {"success": False, "error": f"Symbol {symbol} not supported"}
            
            asset_id = self.symbol_mappings["coincap"][symbol]
            url = f"{self.apis['coincap']['base_url']}/assets/{asset_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        data = response_data.get("data", {})
                        
                        if data:
                            return {
                                "success": True,
                                "data": {
                                    "symbol": symbol,
                                    "price": float(data.get("priceUsd", 0)),
                                    "change_24h": float(data.get("changePercent24Hr", 0)),
                                    "volume_24h": float(data.get("volumeUsd24Hr", 0)),
                                    "market_cap": float(data.get("marketCapUsd", 0)),
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "source": "coincap"
                                }
                            }
                    
                    return {"success": False, "error": f"API error: {response.status}"}
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _fetch_coingecko_detailed(self, symbol: str) -> Dict[str, Any]:
        """Fetch detailed data from CoinGecko."""
        try:
            if symbol not in self.symbol_mappings["coingecko"]:
                return {"success": False, "error": f"Symbol {symbol} not supported"}
            
            coin_id = self.symbol_mappings["coingecko"][symbol]
            url = f"{self.apis['coingecko']['base_url']}/coins/{coin_id}"
            params = {
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "false",
                "developer_data": "false"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        market_data = data.get("market_data", {})
                        
                        return {
                            "success": True,
                            "data": {
                                "symbol": symbol,
                                "name": data.get("name", ""),
                                "price": market_data.get("current_price", {}).get("usd", 0),
                                "market_cap": market_data.get("market_cap", {}).get("usd", 0),
                                "volume_24h": market_data.get("total_volume", {}).get("usd", 0),
                                "change_24h": market_data.get("price_change_percentage_24h", 0),
                                "change_7d": market_data.get("price_change_percentage_7d", 0),
                                "change_30d": market_data.get("price_change_percentage_30d", 0),
                                "high_24h": market_data.get("high_24h", {}).get("usd", 0),
                                "low_24h": market_data.get("low_24h", {}).get("usd", 0),
                                "ath": market_data.get("ath", {}).get("usd", 0),
                                "atl": market_data.get("atl", {}).get("usd", 0),
                                "circulating_supply": market_data.get("circulating_supply", 0),
                                "total_supply": market_data.get("total_supply", 0),
                                "max_supply": market_data.get("max_supply", 0),
                                "timestamp": datetime.utcnow().isoformat(),
                                "source": "coingecko"
                            }
                        }
                    
                    return {"success": False, "error": f"API error: {response.status}"}
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def sync_market_data_batch(self, symbols: List[str]):
        """Sync market data for multiple symbols to cache and Supabase."""
        try:
            logger.info(f"Syncing market data for {len(symbols)} symbols")
            
            # Get batch prices
            result = await self.get_multiple_prices(symbols)
            
            if result.get("success"):
                for symbol, data in result.get("data", {}).items():
                    # Sync to Supabase
                    await supabase_client.sync_market_data(symbol, data)
                
                logger.info(f"Successfully synced {len(result.get('data', {}))} symbols")
            else:
                logger.error("Failed to sync market data batch", error=result.get("error"))
                
        except Exception as e:
            logger.error("Market data batch sync failed", error=str(e))
    
    async def get_exchange_rates(self) -> Dict[str, Any]:
        """Get USD exchange rates for fiat currencies."""
        try:
            # Use a free exchange rate API
            url = "https://api.exchangerate-api.com/v4/latest/USD"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        return {
                            "success": True,
                            "data": {
                                "base": "USD",
                                "rates": data.get("rates", {}),
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        }
                    else:
                        return {"success": False, "error": f"API error: {response.status}"}
                        
        except Exception as e:
            logger.error("Failed to get exchange rates", error=str(e))
            return {"success": False, "error": str(e)}


# Global market data feeds instance
market_data_feeds = MarketDataFeeds()


# Convenience functions
async def get_crypto_price(symbol: str) -> Dict[str, Any]:
    """Get real-time crypto price."""
    return await market_data_feeds.get_real_time_price(symbol)


async def get_crypto_prices(symbols: List[str]) -> Dict[str, Any]:
    """Get multiple crypto prices."""
    return await market_data_feeds.get_multiple_prices(symbols)


async def get_market_overview() -> Dict[str, Any]:
    """Get market overview with top coins."""
    top_symbols = ["BTC", "ETH", "SOL", "ADA", "DOT", "MATIC", "LINK", "UNI"]
    return await market_data_feeds.get_multiple_prices(top_symbols)
