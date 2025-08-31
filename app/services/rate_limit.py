"""
Rate Limiting Service - Enterprise Grade

Implements sophisticated rate limiting with Redis backend for API protection,
user-specific limits, and exchange API rate limit management.
"""

import asyncio
import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

import structlog
from fastapi import HTTPException, status

from app.core.redis import get_redis_client
from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger(__name__)


class RateLimitService:
    """Enterprise rate limiting service with Redis backend."""
    
    def __init__(self):
        self.redis = None
        
        # Default rate limits for different endpoint types
        self.default_limits = {
            "auth": {"limit": 5, "window": 300},      # 5 per 5 minutes
            "trading": {"limit": 100, "window": 60},   # 100 per minute
            "portfolio": {"limit": 200, "window": 60}, # 200 per minute
            "market_data": {"limit": 1000, "window": 60}, # 1000 per minute
            "admin": {"limit": 50, "window": 60}       # 50 per minute
        }
        
        # ENTERPRISE Exchange-specific rate limits (conservative to avoid bans)
        self.exchange_limits = {
            "binance": {
                "spot": {"limit": 1200, "window": 60},     # 1200/min (actual limit 2400)
                "futures": {"limit": 2400, "window": 60},  # 2400/min (actual limit 4800)
                "private": {"limit": 200, "window": 60},   # ENTERPRISE: Private API endpoints
                "public": {"limit": 1200, "window": 60},   # ENTERPRISE: Public API endpoints
                "api_key": {"limit": 100, "window": 60}    # Per API key
            },
            "kraken": {
                "public": {"limit": 60, "window": 60},     # 1/sec
                "private": {"limit": 15, "window": 60},    # Conservative for private
                "api_key": {"limit": 60, "window": 60}
            },
            "kucoin": {
                "public": {"limit": 100, "window": 10},    # 100/10sec
                "private": {"limit": 45, "window": 10},    # 45/10sec
                "api_key": {"limit": 100, "window": 60}
            },
            "coinbase": {
                "public": {"limit": 100, "window": 60},    # ENTERPRISE: Coinbase public
                "private": {"limit": 50, "window": 60},    # ENTERPRISE: Coinbase private
                "api_key": {"limit": 50, "window": 60}
            },
            "bybit": {
                "public": {"limit": 120, "window": 60},    # ENTERPRISE: Bybit public
                "private": {"limit": 60, "window": 60},    # ENTERPRISE: Bybit private
                "api_key": {"limit": 60, "window": 60}
            }
        }
    
    async def async_init(self):
        try:
            self.redis = await get_redis_client()
            if self.redis:
                logger.info("Rate limiter initialized with Redis backend")
            else:
                logger.warning("Rate limiter initialized WITHOUT Redis - will fail open")
        except Exception as e:
            logger.warning("Rate limiter Redis initialization failed", error=str(e))
            self.redis = None
    
    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window: int,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Check if request is within rate limit using sliding window algorithm.
        
        Args:
            key: Unique identifier for the rate limit
            limit: Maximum number of requests allowed
            window: Time window in seconds
            user_id: Optional user ID for user-specific limits
            
        Returns:
            True if within limit, raises HTTPException if exceeded
        """
        now = time.time()
        window_start = now - window
        
        # Create Redis key
        redis_key = f"rate_limit:{key}"
        if user_id:
            redis_key = f"rate_limit:user:{user_id}:{key}"
        
        try:
            # ENTERPRISE REDIS RESILIENCE - Fail open if Redis unavailable
            if not self.redis:
                logger.debug("Rate limit check bypassed - Redis unavailable", key=key)
                return True
            
            # Use Redis pipeline for atomic operations
            pipe = self.redis.pipeline()
            
            # Remove expired entries
            pipe.zremrangebyscore(redis_key, 0, window_start)
            
            # Count current requests
            pipe.zcard(redis_key)
            
            # Add current request
            pipe.zadd(redis_key, {str(now): now})
            
            # Set expiration
            pipe.expire(redis_key, window + 1)
            
            # Execute pipeline
            results = await pipe.execute()
            current_count = results[1]
            
            # Check if limit exceeded
            if current_count >= limit:
                logger.warning(
                    "Rate limit exceeded",
                    key=key,
                    limit=limit,
                    current=current_count,
                    window=window,
                    user_id=user_id
                )
                
                # Calculate retry after time
                retry_after = window
                
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. {current_count}/{limit} requests in {window}s window",
                    headers={"Retry-After": str(retry_after)}
                )
            
            logger.debug(
                "Rate limit check passed",
                key=key,
                current=current_count,
                limit=limit,
                window=window
            )
            
            return True
            
        except Exception as e:
            logger.error("Rate limit check failed", error=str(e), key=key)
            # On error, allow request to proceed (fail open)
            return True
    
    async def check_exchange_rate_limit(
        self,
        exchange: str,
        endpoint_type: str,
        api_key: Optional[str] = None
    ) -> bool:
        """Check exchange-specific rate limits."""
        
        if exchange not in self.exchange_limits:
            logger.warning(f"Unknown exchange for rate limiting: {exchange}")
            return True
        
        exchange_config = self.exchange_limits[exchange]
        
        if endpoint_type not in exchange_config:
            logger.warning(f"Unknown endpoint type for {exchange}: {endpoint_type}")
            return True
        
        limit_config = exchange_config[endpoint_type]
        
        # Global exchange limit
        await self.check_rate_limit(
            key=f"exchange:{exchange}:{endpoint_type}",
            limit=limit_config["limit"],
            window=limit_config["window"]
        )
        
        # Per API key limit if provided
        if api_key:
            api_key_hash = hash(api_key) % 10000  # Hash for privacy
            await self.check_rate_limit(
                key=f"exchange:{exchange}:api_key:{api_key_hash}",
                limit=exchange_config.get("api_key", {}).get("limit", 100),
                window=exchange_config.get("api_key", {}).get("window", 60)
            )
        
        return True
    
    async def get_rate_limit_status(self, key: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get current rate limit status for a key."""
        
        redis_key = f"rate_limit:{key}"
        if user_id:
            redis_key = f"rate_limit:user:{user_id}:{key}"
        
        try:
            # ENTERPRISE REDIS RESILIENCE
            if not self.redis:
                return {
                    "key": key,
                    "error": "Redis unavailable",
                    "status": "degraded_mode"
                }
            
            now = time.time()
            window = 60  # Default window
            
            # Get current count
            current_count = await self.redis.zcard(redis_key)
            
            # Get oldest entry to calculate window
            oldest_entries = await self.redis.zrange(redis_key, 0, 0, withscores=True)
            if oldest_entries:
                oldest_time = oldest_entries[0][1]
                time_since_oldest = now - oldest_time
                window = min(window, time_since_oldest)
            
            return {
                "key": key,
                "current_count": current_count,
                "window_seconds": window,
                "requests_per_second": current_count / window if window > 0 else 0,
                "timestamp": now
            }
            
        except Exception as e:
            logger.error("Failed to get rate limit status", error=str(e), key=key)
            return {"error": str(e)}
    
    async def reset_rate_limit(self, key: str, user_id: Optional[str] = None) -> bool:
        """Reset rate limit for a specific key (admin function)."""
        
        redis_key = f"rate_limit:{key}"
        if user_id:
            redis_key = f"rate_limit:user:{user_id}:{key}"
        
        try:
            # ENTERPRISE REDIS RESILIENCE
            if not self.redis:
                logger.warning("Rate limit reset skipped - Redis unavailable", key=key)
                return False
            
            await self.redis.delete(redis_key)
            logger.info("Rate limit reset", key=key, user_id=user_id)
            return True
        except Exception as e:
            logger.error("Failed to reset rate limit", error=str(e), key=key)
            return False
    
    async def set_custom_limit(
        self,
        key: str,
        limit: int,
        window: int,
        user_id: Optional[str] = None
    ) -> bool:
        """Set custom rate limit for specific key."""
        
        config_key = f"rate_limit_config:{key}"
        if user_id:
            config_key = f"rate_limit_config:user:{user_id}:{key}"
        
        try:
            # ENTERPRISE REDIS RESILIENCE
            if not self.redis:
                logger.warning("Custom rate limit set skipped - Redis unavailable", key=key)
                return False
            
            config = {"limit": limit, "window": window, "set_at": time.time()}
            await self.redis.setex(
                config_key,
                86400,  # 24 hours
                str(config)
            )
            logger.info("Custom rate limit set", key=key, limit=limit, window=window)
            return True
        except Exception as e:
            logger.error("Failed to set custom rate limit", error=str(e))
            return False
    
    async def get_exchange_status(self) -> Dict[str, Any]:
        """Get status of all exchange rate limits."""
        
        status = {}
        
        # ENTERPRISE REDIS RESILIENCE
        if not self.redis:
            return {"error": "Redis unavailable", "status": "degraded_mode"}
        
        for exchange, config in self.exchange_limits.items():
            exchange_status = {}
            
            for endpoint_type, limits in config.items():
                if endpoint_type == "api_key":
                    continue
                
                try:
                    redis_key = f"rate_limit:exchange:{exchange}:{endpoint_type}"
                    current_count = await self.redis.zcard(redis_key)
                    
                    exchange_status[endpoint_type] = {
                        "current": current_count,
                        "limit": limits["limit"],
                        "window": limits["window"],
                        "usage_pct": (current_count / limits["limit"]) * 100,
                        "available": limits["limit"] - current_count
                    }
                except Exception as e:
                    exchange_status[endpoint_type] = {"error": str(e)}
            
            status[exchange] = exchange_status
        
        return status
    
    async def cleanup_expired_entries(self) -> int:
        """Cleanup expired rate limit entries (background task)."""
        
        cleaned_count = 0
        now = time.time()
        
        try:
            # ENTERPRISE REDIS RESILIENCE
            if not self.redis:
                logger.debug("Rate limit cleanup skipped - Redis unavailable")
                return 0
            
            # Get all rate limit keys
            keys = await self.redis.keys("rate_limit:*")
            
            for key in keys:
                try:
                    # Remove entries older than 1 hour
                    removed = await self.redis.zremrangebyscore(key, 0, now - 3600)
                    cleaned_count += removed
                    
                    # Remove empty keys
                    if await self.redis.zcard(key) == 0:
                        await self.redis.delete(key)
                        
                except Exception as e:
                    logger.warning(f"Failed to cleanup key {key}: {e}")
            
            logger.info(f"Rate limit cleanup completed", cleaned_entries=cleaned_count)
            
        except Exception as e:
            logger.error("Rate limit cleanup failed", error=str(e))
        
        return cleaned_count


# Global rate limiter instance
rate_limiter = RateLimitService()
