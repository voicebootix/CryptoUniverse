"""
Advanced rate limiting middleware for CryptoUniverse Enterprise.
Implements sliding window rate limiting using Redis for distributed systems.
"""

import time
import json
from typing import Optional, Dict, Any, Tuple, Callable, Awaitable
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response, JSONResponse

from app.core.redis import get_redis_client
from app.core.logging import logger
from app.core.config import settings

class RateLimitExceeded(HTTPException):
    """Custom exception for rate limit exceeded."""
    def __init__(self, retry_after: int):
        headers = {"Retry-After": str(retry_after)},
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": f"Too many requests. Please try again in {retry_after} seconds.",
                "retry_after": retry_after
            },
            headers={"Retry-After": str(retry_after)}
        )

class RateLimitConfig:
    """Configuration for rate limiting rules."""
    
    def __init__(
        self,
        limit: int,
        window: int,  # in seconds
        scope: str = "global",
        key_func: Optional[Callable[[Request], str]] = None,
        cost_func: Optional[Callable[[Request], int]] = None
    ):
        """
        Initialize rate limit configuration.
        
        Args:
            limit: Maximum number of requests allowed in the time window
            window: Time window in seconds
            scope: Scope of the rate limit (global, user, ip, etc.)
            key_func: Function to generate the rate limit key
            cost_func: Function to calculate the cost of a request
        """
        self.limit = limit
        self.window = window
        self.scope = scope
        self.key_func = key_func or (lambda r: "global")
        self.cost_func = cost_func or (lambda r: 1)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Advanced rate limiting middleware using Redis.
    
    Features:
    - Sliding window algorithm for accurate rate limiting
    - Support for different rate limits per endpoint
    - Custom key and cost functions
    - Distributed rate limiting using Redis
    - Automatic retry-after header
    """
    
    def __init__(
        self,
        app,
        default_limit: int = 100,
        default_window: int = 60,  # 1 minute
        redis_prefix: str = "rate_limit:",
        enabled: bool = True
    ):
        super().__init__(app)
        self.default_limit = default_limit
        self.default_window = default_window
        self.redis_prefix = redis_prefix
        self.enabled = enabled and not settings.DEBUG
        self.rules: Dict[str, RateLimitConfig] = {}
        
        # Add default rules
        self.add_rule("default", limit=default_limit, window=default_window)
        
        # Add more specific rules
        self.add_rule(
            "auth",
            limit=5,
            window=300,  # 5 minutes
            key_func=lambda r: f"ip:{r.client.host}",
            scope="ip"
        )
        
        self.add_rule(
            "api",
            limit=1000,
            window=3600,  # 1 hour
            key_func=lambda r: f"api_key:{r.headers.get('X-API-Key', 'anonymous')}",
            scope="api_key"
        )
    
    def add_rule(
        self,
        path: str,
        limit: int,
        window: int,
        scope: str = "ip",
        key_func: Optional[Callable[[Request], str]] = None,
        cost_func: Optional[Callable[[Request], int]] = None
    ) -> None:
        """Add a rate limit rule for a specific path pattern."""
        self.rules[path] = RateLimitConfig(
            limit=limit,
            window=window,
            scope=scope,
            key_func=key_func or (lambda r: f"ip:{r.client.host}"),
            cost_func=cost_func or (lambda r: 1)
        )
    
    def get_rule(self, request: Request) -> RateLimitConfig:
        """Get the most specific rule for the request path."""
        path = request.url.path
        
        # Check for exact matches first
        for rule_path, rule in self.rules.items():
            if path == rule_path or path.startswith(f"{rule_path}/"):
                return rule
        
        # Default to global rule
        return self.rules["default"]
    
    async def get_redis_key(self, request: Request, rule: RateLimitConfig) -> str:
        """Generate the Redis key for rate limiting."""
        key = rule.key_func(request)
        return f"{self.redis_prefix}{rule.scope}:{key}:{request.url.path}"
    
    async def check_rate_limit(self, request: Request) -> Tuple[bool, int]:
        """Check if the request is within rate limits."""
        if not self.enabled:
            return True, 0
        
        rule = self.get_rule(request)
        redis = await get_redis_client()
        
        # If Redis is unavailable, allow the request (fail open)
        if not redis:
            logger.debug("Redis unavailable for rate limiting - allowing request")
            return True, 0
        
        # Generate the Redis key
        key = await self.get_redis_key(request, rule)
        now = int(time.time())
        
        try:
            # Use Redis pipeline for atomic operations
            async with redis.pipeline() as pipe:
                # Remove old timestamps outside the window
                pipe.zremrangebyscore(key, 0, now - rule.window)
                
                # Get current count
                pipe.zcard(key)
                
                # Add current timestamp
                pipe.zadd(key, {str(now): now})
                
                # Set expiry
                pipe.expire(key, rule.window)
                
                # Execute pipeline
                _, count, _, _ = await pipe.execute()
                
                # Calculate remaining requests
                remaining = max(0, rule.limit - count)
                
                # Check if rate limit exceeded
                if count > rule.limit:
                    # Get the oldest timestamp to calculate retry after
                    oldest = await redis.zrange(key, 0, 0, withscores=True)
                    if oldest:
                        retry_after = int(oldest[0][1] + rule.window - now)
                    else:
                        retry_after = rule.window
                    
                    return False, retry_after
                
                return True, remaining
                
        except Exception as e:
            logger.error(f"Rate limit error: {str(e)}")
            # Fail open in case of Redis errors
            return True, 0
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request with rate limiting."""
        # Always allow CORS preflight to pass through unimpeded
        if request.method == "OPTIONS":
            return await call_next(request)
        # Skip rate limiting for certain paths
        if any(request.url.path.startswith(p) for p in [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]):
            return await call_next(request)
        
        # Check rate limit
        allowed, retry_after = await self.check_rate_limit(request)
        
        if not allowed:
            raise RateLimitExceeded(retry_after=retry_after)
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.default_limit)
        response.headers["X-RateLimit-Remaining"] = str(retry_after - 1)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + retry_after)
        
        return response
