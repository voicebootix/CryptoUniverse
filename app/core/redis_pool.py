"""
Production-ready Redis connection pool manager.
Handles connection pooling, health checks, and graceful degradation.
"""

import asyncio
from typing import Optional, Any
from contextlib import asynccontextmanager
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError, ConnectionError, TimeoutError
import structlog

from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger(__name__)


class RedisPoolManager:
    """
    Production Redis connection pool manager with:
    - Connection pooling
    - Health monitoring
    - Automatic reconnection
    - Graceful degradation
    """
    
    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._healthy: bool = False
        self._last_health_check: float = 0
        self._health_check_interval: int = 30  # seconds
        self._connection_retries: int = 0
        self._max_retries: int = 3
        
    async def initialize(self) -> bool:
        """
        Initialize Redis connection pool.
        Returns True if successful, False if Redis is unavailable.
        """
        try:
            if not settings.REDIS_URL:
                logger.warning("Redis URL not configured - running without Redis")
                self._healthy = False
                return False
            
            # Create connection pool with production settings
            self._pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=20,  # Reasonable pool size
                socket_connect_timeout=5,  # 5 second connection timeout
                socket_timeout=5,  # 5 second operation timeout
                retry_on_timeout=True,
                retry_on_error=[ConnectionError, TimeoutError],
                health_check_interval=30,  # Built-in health checking
                decode_responses=False  # Don't decode for better performance
            )
            
            # Create client from pool
            self._client = redis.Redis(connection_pool=self._pool)
            
            # Test connection
            await self._client.ping()
            
            self._healthy = True
            self._connection_retries = 0
            logger.info("Redis connection pool initialized successfully", 
                       max_connections=20,
                       url=settings.REDIS_URL[:30] + "...")  # Log partial URL for security
            return True
            
        except Exception as e:
            logger.error("Failed to initialize Redis connection pool", 
                        error=str(e),
                        type=type(e).__name__)
            self._healthy = False
            self._connection_retries += 1
            
            # If we've exceeded max retries, give up on Redis
            if self._connection_retries >= self._max_retries:
                logger.warning("Redis initialization failed after max retries - running in degraded mode",
                             retries=self._connection_retries)
            
            return False
    
    async def get_client(self) -> Optional[redis.Redis]:
        """
        Get Redis client from pool.
        Returns None if Redis is unavailable (graceful degradation).
        """
        # If not healthy and exceeded retries, return None immediately
        if not self._healthy and self._connection_retries >= self._max_retries:
            return None
        
        # If not initialized or unhealthy, try to initialize
        if not self._client or not self._healthy:
            initialized = await self.initialize()
            if not initialized:
                return None
        
        # Perform periodic health check
        import time
        current_time = time.time()
        if current_time - self._last_health_check > self._health_check_interval:
            self._last_health_check = current_time
            asyncio.create_task(self._health_check())
        
        return self._client
    
    async def _health_check(self):
        """Perform background health check."""
        try:
            if self._client:
                await self._client.ping()
                if not self._healthy:
                    logger.info("Redis connection restored")
                    self._healthy = True
                    self._connection_retries = 0
        except Exception as e:
            if self._healthy:
                logger.warning("Redis health check failed", error=str(e))
                self._healthy = False
    
    async def execute_with_fallback(self, operation: str, *args, **kwargs) -> Optional[Any]:
        """
        Execute Redis operation with automatic fallback.
        Returns None if Redis is unavailable.
        """
        client = await self.get_client()
        if not client:
            logger.debug(f"Redis operation {operation} skipped - Redis unavailable")
            return None
        
        try:
            # Get the operation method
            method = getattr(client, operation)
            # Execute it
            result = await method(*args, **kwargs)
            return result
        except Exception as e:
            logger.error(f"Redis operation {operation} failed", 
                        error=str(e),
                        args=args,
                        kwargs=kwargs)
            # Mark as unhealthy for next health check
            self._healthy = False
            return None
    
    @asynccontextmanager
    async def pipeline(self):
        """
        Get a Redis pipeline with automatic fallback.
        Yields None if Redis is unavailable.
        """
        client = await self.get_client()
        if not client:
            yield None
        else:
            try:
                async with client.pipeline() as pipe:
                    yield pipe
            except Exception as e:
                logger.error("Redis pipeline failed", error=str(e))
                self._healthy = False
                yield None
    
    async def close(self):
        """Close Redis connection pool gracefully."""
        try:
            if self._client:
                await self._client.close()
                self._client = None
            if self._pool:
                await self._pool.disconnect()
                self._pool = None
            self._healthy = False
            logger.info("Redis connection pool closed")
        except Exception as e:
            logger.error("Error closing Redis connection pool", error=str(e))
    
    @property
    def is_healthy(self) -> bool:
        """Check if Redis connection is healthy."""
        return self._healthy
    
    @property
    def status(self) -> dict:
        """Get current Redis connection status."""
        return {
            "healthy": self._healthy,
            "retries": self._connection_retries,
            "max_retries": self._max_retries,
            "pool_created": self._pool is not None,
            "client_created": self._client is not None
        }


# Create singleton instance
redis_pool_manager = RedisPoolManager()


async def get_redis_pool_client() -> Optional[redis.Redis]:
    """Get Redis client from managed pool."""
    return await redis_pool_manager.get_client()


async def initialize_redis_pool() -> bool:
    """Initialize Redis connection pool on startup."""
    return await redis_pool_manager.initialize()


async def close_redis_pool():
    """Close Redis connection pool on shutdown."""
    await redis_pool_manager.close()


def get_redis_status() -> dict:
    """Get current Redis connection status."""
    return redis_pool_manager.status