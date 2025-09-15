"""
BINANCE SMART ROUTER SERVICE

Intelligently routes Binance API calls:
- Market Data (Public): Uses api.binance.us (geo-unrestricted)
- Trading/Account (Private): Uses api.binance.com (with user's API keys)

This solves the geo-blocking issue while maintaining full trading functionality.

Author: CTO Assistant
Date: 2025-09-15
"""

import asyncio
import time
import hmac
import hashlib
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlencode
import aiohttp
import structlog

from app.core.config import get_settings
from app.core.logging import LoggerMixin

settings = get_settings()
logger = structlog.get_logger(__name__)


class BinanceSmartRouter(LoggerMixin):
    """
    SMART ROUTER FOR BINANCE API CALLS
    
    Automatically routes requests to optimal endpoint:
    - Public data: api.binance.us (works from Germany)
    - Private trading: api.binance.com (with authentication)
    """
    
    def __init__(self):
        super().__init__()
        
        # Public data endpoints (geo-unrestricted)
        self.data_endpoints = {
            "base_url": "https://api.binance.us",
            "endpoints": {
                "ticker_24hr": "/api/v3/ticker/24hr",
                "ticker_price": "/api/v3/ticker/price",
                "exchange_info": "/api/v3/exchangeInfo",
                "klines": "/api/v3/klines",
                "depth": "/api/v3/depth",
                "trades": "/api/v3/trades",
                "avg_price": "/api/v3/avgPrice"
            },
            "rate_limit": 1200,
            "purpose": "public_market_data"
        }
        
        # Private trading endpoints (requires authentication)
        self.trading_endpoints = {
            "base_url": "https://api.binance.com",
            "endpoints": {
                "account": "/api/v3/account",
                "order": "/api/v3/order",
                "open_orders": "/api/v3/openOrders",
                "all_orders": "/api/v3/allOrders",
                "my_trades": "/api/v3/myTrades",
                "user_data_stream": "/api/v3/userDataStream"
            },
            "rate_limit": 1200,
            "purpose": "private_trading"
        }
        
        # Rate limiting
        self.rate_limits = {
            "data": {"requests": 0, "window_start": time.time(), "max_requests": 1200},
            "trading": {"requests": 0, "window_start": time.time(), "max_requests": 1200}
        }
        
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def async_init(self):
        """Initialize async components."""
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.session:
            await self.session.close()
    
    def _is_public_endpoint(self, endpoint: str) -> bool:
        """Determine if endpoint is public (market data) or private (trading)."""
        public_patterns = [
            "ticker", "exchangeInfo", "klines", "depth", "trades", "avgPrice"
        ]
        return any(pattern in endpoint for pattern in public_patterns)
    
    def _get_endpoint_config(self, endpoint: str) -> Dict[str, Any]:
        """Get appropriate configuration based on endpoint type."""
        if self._is_public_endpoint(endpoint):
            return self.data_endpoints
        else:
            return self.trading_endpoints
    
    def _check_rate_limit(self, endpoint_type: str) -> bool:
        """Check if we're within rate limits."""
        now = time.time()
        limits = self.rate_limits[endpoint_type]
        
        # Reset window if needed
        if now - limits["window_start"] > 60:  # 1-minute window
            limits["requests"] = 0
            limits["window_start"] = now
        
        # Check if we can make request
        if limits["requests"] >= limits["max_requests"]:
            return False
        
        limits["requests"] += 1
        return True
    
    def _create_signature(self, query_string: str, secret_key: str) -> str:
        """Create HMAC SHA256 signature for authenticated requests."""
        return hmac.new(
            secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def get_market_data(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get public market data using geo-unrestricted endpoint.
        
        Args:
            endpoint: API endpoint (e.g., "ticker/24hr", "ticker/price")
            params: Query parameters
            
        Returns:
            API response data
        """
        await self.async_init()
        
        # Use data endpoints (Binance.us)
        config = self.data_endpoints
        endpoint_type = "data"
        
        # Check rate limit
        if not self._check_rate_limit(endpoint_type):
            raise Exception("Rate limit exceeded for market data")
        
        # Build URL
        if not endpoint.startswith('/'):
            endpoint = f"/api/v3/{endpoint}"
        
        url = f"{config['base_url']}{endpoint}"
        
        try:
            self.logger.debug("Fetching market data",
                            url=url,
                            params=params,
                            endpoint_type=endpoint_type)
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    self.logger.debug("Market data retrieved successfully",
                                    endpoint=endpoint,
                                    data_size=len(str(data)))
                    return {"success": True, "data": data}
                else:
                    error_text = await response.text()
                    self.logger.error("Market data API error",
                                    status=response.status,
                                    error=error_text,
                                    endpoint=endpoint)
                    return {"success": False, "error": f"API error {response.status}: {error_text}"}
                    
        except Exception as e:
            self.logger.error("Market data request failed",
                            error=str(e),
                            endpoint=endpoint)
            return {"success": False, "error": str(e)}
    
    async def get_account_data(
        self,
        endpoint: str,
        api_key: str,
        secret_key: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get private account/trading data using authenticated endpoint.
        
        Args:
            endpoint: API endpoint (e.g., "account", "openOrders")
            api_key: User's Binance API key
            secret_key: User's Binance secret key
            params: Query parameters
            
        Returns:
            API response data
        """
        await self.async_init()
        
        # Use trading endpoints (Binance.com with auth)
        config = self.trading_endpoints
        endpoint_type = "trading"
        
        # Check rate limit
        if not self._check_rate_limit(endpoint_type):
            raise Exception("Rate limit exceeded for trading data")
        
        # Prepare authenticated request
        if not endpoint.startswith('/'):
            endpoint = f"/api/v3/{endpoint}"
        
        # Add timestamp and signature
        timestamp = int(time.time() * 1000)
        query_params = params or {}
        query_params['timestamp'] = timestamp
        
        # Create signature
        query_string = urlencode(query_params)
        signature = self._create_signature(query_string, secret_key)
        query_params['signature'] = signature
        
        # Build URL
        url = f"{config['base_url']}{endpoint}"
        
        # Headers with API key
        headers = {
            'X-MBX-APIKEY': api_key,
            'Content-Type': 'application/json'
        }
        
        try:
            self.logger.debug("Fetching account data",
                            endpoint=endpoint,
                            endpoint_type=endpoint_type)
            
            async with self.session.get(url, params=query_params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    self.logger.debug("Account data retrieved successfully",
                                    endpoint=endpoint)
                    return {"success": True, "data": data}
                else:
                    error_text = await response.text()
                    self.logger.error("Account data API error",
                                    status=response.status,
                                    error=error_text,
                                    endpoint=endpoint)
                    return {"success": False, "error": f"API error {response.status}: {error_text}"}
                    
        except Exception as e:
            self.logger.error("Account data request failed",
                            error=str(e),
                            endpoint=endpoint)
            return {"success": False, "error": str(e)}
    
    async def get_symbol_price(self, symbol: str) -> Dict[str, Any]:
        """Get current price for a symbol using market data endpoint."""
        return await self.get_market_data("ticker/price", {"symbol": symbol})
    
    async def get_24hr_ticker(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get 24hr ticker statistics."""
        params = {"symbol": symbol} if symbol else None
        return await self.get_market_data("ticker/24hr", params)
    
    async def get_exchange_info(self) -> Dict[str, Any]:
        """Get exchange trading rules and symbol information."""
        return await self.get_market_data("exchangeInfo")
    
    async def get_user_account(self, api_key: str, secret_key: str) -> Dict[str, Any]:
        """Get user account information."""
        return await self.get_account_data("account", api_key, secret_key)
    
    async def get_open_orders(self, api_key: str, secret_key: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get user's open orders."""
        params = {"symbol": symbol} if symbol else None
        return await self.get_account_data("openOrders", api_key, secret_key, params)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of both endpoints."""
        results = {}
        
        # Test market data endpoint
        try:
            market_result = await self.get_market_data("ticker/price", {"symbol": "BTCUSDT"})
            results["market_data"] = {
                "status": "healthy" if market_result.get("success") else "unhealthy",
                "endpoint": self.data_endpoints["base_url"],
                "test_result": market_result
            }
        except Exception as e:
            results["market_data"] = {
                "status": "unhealthy",
                "endpoint": self.data_endpoints["base_url"],
                "error": str(e)
            }
        
        # Test trading endpoint (without auth - just connectivity)
        try:
            await self.async_init()
            url = f"{self.trading_endpoints['base_url']}/api/v3/ping"
            async with self.session.get(url) as response:
                results["trading_endpoint"] = {
                    "status": "healthy" if response.status == 200 else "unhealthy",
                    "endpoint": self.trading_endpoints["base_url"],
                    "connectivity": response.status == 200
                }
        except Exception as e:
            results["trading_endpoint"] = {
                "status": "unhealthy", 
                "endpoint": self.trading_endpoints["base_url"],
                "error": str(e)
            }
        
        return {
            "overall_status": "healthy" if all(r.get("status") == "healthy" for r in results.values()) else "degraded",
            "endpoints": results,
            "timestamp": time.time()
        }


# Global instance
binance_smart_router = BinanceSmartRouter()