"""
Redis configuration and client management.

Handles Redis connection, caching, session storage, and pub/sub
for real-time features in the cryptocurrency trading platform.
"""

import json
import asyncio
import time
import socket
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager
import redis.asyncio as redis
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError, RedisError
import structlog

from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger()

# Redis client instance
redis_client: Optional[Redis] = None
connection_pool: Optional[ConnectionPool] = None

# ENTERPRISE CONNECTION RESILIENCE
class RedisConnectionManager:
    """Enterprise-grade Redis connection manager with automatic recovery."""
    
    def __init__(self):
        self.pool: Optional[ConnectionPool] = None
        self.client: Optional[Redis] = None
        self.last_health_check = 0
        self.health_check_interval = 30  # 30 seconds
        self.connection_failures = 0
        self.max_failures = 5
        self.circuit_breaker_timeout = 300  # 5 minutes
        self.circuit_breaker_open_until = 0
        self.is_healthy = True
        self._recreate_lock = asyncio.Lock()  # Concurrency safety for client recreation
    
    async def get_connection_pool(self) -> Optional[ConnectionPool]:
        """Get or create Redis connection pool with enterprise settings."""
        if self.pool is None:
            try:
                # Build socket keepalive options conditionally for cross-platform compatibility
                keepalive_options = {}
                if hasattr(socket, 'TCP_KEEPIDLE'):
                    keepalive_options[socket.TCP_KEEPIDLE] = 1
                if hasattr(socket, 'TCP_KEEPINTVL'):
                    keepalive_options[socket.TCP_KEEPINTVL] = 3
                if hasattr(socket, 'TCP_KEEPCNT'):
                    keepalive_options[socket.TCP_KEEPCNT] = 5
                
                pool_kwargs = {
                    "max_connections": 50,  # Increased for enterprise
                    "retry_on_timeout": True,
                    "retry_on_error": [ConnectionError, TimeoutError],
                    "health_check_interval": 30,
                    "socket_keepalive": True,
                    "connection_class": redis.Connection,
                    "decode_responses": True
                }
                
                # Only add socket_keepalive_options if we have any valid options
                if keepalive_options:
                    pool_kwargs["socket_keepalive_options"] = keepalive_options
                
                self.pool = ConnectionPool.from_url(settings.REDIS_URL, **pool_kwargs)
                logger.info("Redis connection pool created with enterprise settings")
            except Exception as e:
                logger.error("Failed to create Redis connection pool", error=str(e))
                self.pool = None
        return self.pool
    
    async def get_client(self) -> Optional[Redis]:
        """Get Redis client with automatic health checking and recovery."""
        current_time = time.time()
        
        # Circuit breaker check
        if current_time < self.circuit_breaker_open_until:
            logger.debug("Redis circuit breaker is OPEN, returning None")
            return None
        
        # Health check
        if current_time - self.last_health_check > self.health_check_interval:
            await self._health_check()
            self.last_health_check = current_time
        
        # Return existing healthy client
        if self.client and self.is_healthy:
            return self.client
        
        # Create new client if needed
        if self.client is None:
            await self._create_client()
        
        return self.client if self.is_healthy else None
    
    async def _create_client(self):
        """Create new Redis client."""
        try:
            pool = await self.get_connection_pool()
            if pool:
                self.client = Redis(connection_pool=pool)
                logger.info("Redis client created successfully")
            else:
                self.client = None
        except Exception as e:
            logger.error("Failed to create Redis client", error=str(e))
            self.client = None
            await self._handle_connection_failure()
    
    async def _health_check(self):
        """Perform Redis health check."""
        if not self.client:
            self.is_healthy = False
            return
        
        try:
            # ENTERPRISE: Enhanced ping with parser error handling
            if self.client:
                try:
                    # Use asyncio timeout for the ping to avoid hanging
                    ping_result = await asyncio.wait_for(self.client.ping(), timeout=5.0)
                    
                    # Validate ping response properly
                    if ping_result == True or ping_result == "PONG" or ping_result == b"PONG":
                        self.is_healthy = True
                        self.connection_failures = 0
                        if self.circuit_breaker_open_until > 0:
                            logger.info("Redis circuit breaker CLOSED - connection restored")
                            self.circuit_breaker_open_until = 0
                    else:
                        logger.warning("Redis ping returned unexpected result", result=ping_result)
                        self.is_healthy = False
                        await self._handle_connection_failure()
                        
                except asyncio.TimeoutError:
                    logger.warning("Redis ping timeout - connection may be stale")
                    self.is_healthy = False
                    await self._recreate_client_on_error()
                    
                except Exception as ping_error:
                    # Handle specific Redis parser errors
                    error_str = str(ping_error)
                    if "_AsyncRESP2Parser" in error_str or "_connected" in error_str:
                        logger.warning("Redis parser connection state error - recreating client")
                        await self._recreate_client_on_error()
                    else:
                        logger.warning("Redis ping failed", error=error_str)
                        self.is_healthy = False
                        await self._handle_connection_failure()
            else:
                self.is_healthy = False
                await self._handle_connection_failure()
        except Exception as e:
            logger.warning("Redis health check failed", error=str(e))
            self.is_healthy = False
            await self._handle_connection_failure()
    
    async def _recreate_client_on_error(self):
        """Recreate Redis client when parser errors occur - concurrency safe."""
        async with self._recreate_lock:
            try:
                # Close current client safely
                if self.client:
                    try:
                        await self.client.aclose()
                    except Exception as e:
                        logger.error("Error closing Redis client during recreation", error=str(e), exc_info=True)
                    self.client = None
                
                # Reset connection pool to force fresh connections
                if self.pool:
                    try:
                        await self.pool.aclose()
                    except Exception as e:
                        logger.error("Error closing Redis pool during recreation", error=str(e), exc_info=True)
                    self.pool = None
                
                # Create new client
                await self._create_client()
                
                # Perform immediate health check
                if self.client:
                    try:
                        ping_result = await asyncio.wait_for(self.client.ping(), timeout=3.0)
                        if ping_result == True or ping_result == "PONG" or ping_result == b"PONG":
                            # Successful recreation - reset all failure states
                            self.is_healthy = True
                            self.connection_failures = 0
                            self.circuit_breaker_open_until = 0
                            logger.info("Redis client successfully recreated and healthy")
                            return
                    except Exception as e:
                        logger.error("Health check failed after Redis client recreation", error=str(e), exc_info=True)
                
                # If recreation failed, handle as connection failure
                await self._handle_connection_failure()
                
            except Exception as e:
                logger.exception("Failed to recreate Redis client")
                await self._handle_connection_failure()

    async def _handle_connection_failure(self):
        """Handle connection failures with circuit breaker pattern."""
        self.connection_failures += 1
        self.is_healthy = False
        
        if self.connection_failures >= self.max_failures:
            self.circuit_breaker_open_until = time.time() + self.circuit_breaker_timeout
            logger.error(f"Redis circuit breaker OPENED after {self.connection_failures} failures")
            
            # Close current client
            if self.client:
                try:
                    await self.client.aclose()
                except Exception:
                    pass
                self.client = None
    
    async def close(self):
        """Close Redis connections gracefully."""
        if self.client:
            try:
                await self.client.aclose()
            except Exception as e:
                logger.error("Error closing Redis client", error=str(e))
        
        if self.pool:
            try:
                await self.pool.aclose()
            except Exception as e:
                logger.error("Error closing Redis pool", error=str(e))
        
        self.client = None
        self.pool = None

# Global connection manager
redis_connection_manager = RedisConnectionManager()


async def get_redis_client() -> Optional[Redis]:
    """
    Get Redis client instance with ENTERPRISE connection management and retry logic.
    
    Returns:
        Redis: Redis client instance or None if unavailable
    """
    # PRODUCTION: Add retry logic for connection establishment
    max_retries = 3
    base_delay = 0.1
    
    for attempt in range(max_retries):
        try:
            client = await redis_connection_manager.get_client()
            if client:
                # Validate connection with ping test
                await asyncio.wait_for(client.ping(), timeout=2.0)
                return client
            return None
        except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
            if attempt == max_retries - 1:
                logger.warning(f"Redis connection failed after {max_retries} attempts", error=str(e))
                return None
            
            # Exponential backoff with jitter
            delay = base_delay * (2 ** attempt) + (time.time() % 0.1)
            logger.debug(f"Redis connection attempt {attempt + 1} failed, retrying in {delay:.2f}s")
            await asyncio.sleep(delay)
        except Exception as e:
            logger.warning(f"Redis connection error on attempt {attempt + 1}", error=str(e))
            if attempt == max_retries - 1:
                return None
            await asyncio.sleep(base_delay)
    
    return None


async def close_redis_client():
    """Close Redis client connection with enterprise cleanup."""
    global redis_client
    await redis_connection_manager.close()
    redis_client = None


class RedisManager:
    """Redis operations manager with serialization and error handling."""
    
    def __init__(self):
        self.client: Optional[Redis] = None
    
    async def get_client(self) -> Optional[Redis]:
        """Get Redis client instance with graceful degradation."""
        if self.client is None:
            self.client = await get_redis_client()
        return self.client
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire: Optional[int] = None,
        serialize: bool = True
    ) -> bool:
        """
        Set a value in Redis with optional expiration.
        
        Args:
            key: Redis key
            value: Value to store
            expire: Expiration in seconds
            serialize: Whether to JSON serialize the value
            
        Returns:
            bool: True if successful
        """
        try:
            client = await self.get_client()
            if client is None:  # ENTERPRISE GRACEFUL DEGRADATION
                logger.debug("Redis unavailable for SET operation", key=key)
                return False
            
            if serialize and not isinstance(value, (str, int, float)):
                value = json.dumps(value, default=str)
            
            result = await client.set(
                key, 
                value, 
                ex=expire or settings.REDIS_EXPIRE_SECONDS
            )
            return bool(result)
        except Exception as e:
            logger.error("Redis SET failed", key=key, error=str(e))
            return False
    
    async def get(
        self, 
        key: str, 
        deserialize: bool = True,
        default: Any = None
    ) -> Any:
        """
        Get a value from Redis with optional deserialization.
        
        Args:
            key: Redis key
            deserialize: Whether to JSON deserialize the value
            default: Default value if key doesn't exist
            
        Returns:
            Any: Retrieved value or default
        """
        try:
            client = await self.get_client()
            if client is None:  # ENTERPRISE GRACEFUL DEGRADATION
                logger.debug("Redis unavailable for GET operation", key=key)
                return default
                
            value = await client.get(key)
            
            if value is None:
                return default
            
            if deserialize and isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            
            return value
        except Exception as e:
            logger.error("Redis GET failed", key=key, error=str(e))
            return default
    
    async def delete(self, *keys: str) -> int:
        """
        Delete keys from Redis.
        
        Args:
            keys: Keys to delete
            
        Returns:
            int: Number of keys deleted
        """
        try:
            client = await self.get_client()
            return await client.delete(*keys)
        except Exception as e:
            logger.error("Redis DELETE failed", keys=keys, error=str(e))
            return 0
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in Redis.
        
        Args:
            key: Redis key
            
        Returns:
            bool: True if key exists
        """
        try:
            client = await self.get_client()
            return bool(await client.exists(key))
        except Exception as e:
            logger.error("Redis EXISTS failed", key=key, error=str(e))
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration for a key.
        
        Args:
            key: Redis key
            seconds: Expiration time in seconds
            
        Returns:
            bool: True if successful
        """
        try:
            client = await self.get_client()
            return bool(await client.expire(key, seconds))
        except Exception as e:
            logger.error("Redis EXPIRE failed", key=key, error=str(e))
            return False
    
    async def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment a key's value.
        
        Args:
            key: Redis key
            amount: Amount to increment by
            
        Returns:
            int: New value after increment
        """
        try:
            client = await self.get_client()
            return await client.incrby(key, amount)
        except Exception as e:
            logger.error("Redis INCR failed", key=key, error=str(e))
            return None
    
    async def push_list(self, key: str, *values: Any, serialize: bool = True) -> int:
        """
        Push values to a Redis list.
        
        Args:
            key: Redis key
            values: Values to push
            serialize: Whether to serialize values
            
        Returns:
            int: New list length
        """
        try:
            client = await self.get_client()
            
            if serialize:
                values = [json.dumps(v, default=str) for v in values]
            
            return await client.lpush(key, *values)
        except Exception as e:
            logger.error("Redis LPUSH failed", key=key, error=str(e))
            return 0
    
    async def pop_list(self, key: str, deserialize: bool = True) -> Any:
        """
        Pop value from a Redis list.
        
        Args:
            key: Redis key
            deserialize: Whether to deserialize value
            
        Returns:
            Any: Popped value
        """
        try:
            client = await self.get_client()
            value = await client.rpop(key)
            
            if value is None:
                return None
            
            if deserialize and isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            
            return value
        except Exception as e:
            logger.error("Redis RPOP failed", key=key, error=str(e))
            return None
    
    async def get_list(self, key: str, start: int = 0, end: int = -1, deserialize: bool = True) -> List[Any]:
        """
        Get list items from Redis.
        
        Args:
            key: Redis key
            start: Start index
            end: End index (-1 for all)
            deserialize: Whether to deserialize values
            
        Returns:
            List[Any]: List items
        """
        try:
            client = await self.get_client()
            values = await client.lrange(key, start, end)
            
            if not values:
                return []
            
            if deserialize:
                result = []
                for value in values:
                    try:
                        result.append(json.loads(value))
                    except json.JSONDecodeError:
                        result.append(value)
                return result
            
            return values
        except Exception as e:
            logger.error("Redis LRANGE failed", key=key, error=str(e))
            return []
    
    async def set_hash(self, key: str, mapping: Dict[str, Any], serialize: bool = True) -> bool:
        """
        Set hash fields in Redis.
        
        Args:
            key: Redis key
            mapping: Field-value mapping
            serialize: Whether to serialize values
            
        Returns:
            bool: True if successful
        """
        try:
            client = await self.get_client()
            
            if serialize:
                mapping = {k: json.dumps(v, default=str) for k, v in mapping.items()}
            
            result = await client.hset(key, mapping=mapping)
            return result is not None
        except Exception as e:
            logger.error("Redis HSET failed", key=key, error=str(e))
            return False
    
    async def get_hash(self, key: str, deserialize: bool = True) -> Dict[str, Any]:
        """
        Get hash from Redis.
        
        Args:
            key: Redis key
            deserialize: Whether to deserialize values
            
        Returns:
            Dict[str, Any]: Hash data
        """
        try:
            client = await self.get_client()
            data = await client.hgetall(key)
            
            if not data:
                return {}
            
            if deserialize:
                result = {}
                for k, v in data.items():
                    try:
                        result[k] = json.loads(v)
                    except json.JSONDecodeError:
                        result[k] = v
                return result
            
            return data
        except Exception as e:
            logger.error("Redis HGETALL failed", key=key, error=str(e))
            return {}
    
    async def publish(self, channel: str, message: Any, serialize: bool = True) -> int:
        """
        Publish message to Redis channel.
        
        Args:
            channel: Redis channel
            message: Message to publish
            serialize: Whether to serialize message
            
        Returns:
            int: Number of subscribers that received the message
        """
        try:
            client = await self.get_client()
            
            if serialize and not isinstance(message, (str, int, float)):
                message = json.dumps(message, default=str)
            
            return await client.publish(channel, message)
        except Exception as e:
            logger.error("Redis PUBLISH failed", channel=channel, error=str(e))
            return 0
    
    async def ping(self) -> bool:
        """
        Ping Redis server with enterprise health checking.
        
        Returns:
            bool: True if Redis is responding
        """
        try:
            client = await self.get_client()
            if client is None:  # ENTERPRISE GRACEFUL DEGRADATION
                return False
                
            ping_result = await client.ping()
            # ENTERPRISE: Handle different ping response types
            return ping_result == True or ping_result == "PONG" or ping_result == b"PONG"
        except Exception as e:
            logger.error("Redis PING failed", error=str(e))
            return False


# Global Redis manager instance
redis_manager = RedisManager()


class CacheManager:
    """High-level caching operations."""
    
    def __init__(self, redis_manager: RedisManager):
        self.redis = redis_manager
    
    async def cache_user_session(self, user_id: str, session_data: Dict[str, Any], expire: int = 3600) -> bool:
        """Cache user session data."""
        key = f"session:user:{user_id}"
        return await self.redis.set(key, session_data, expire=expire)
    
    async def get_user_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user session data."""
        key = f"session:user:{user_id}"
        return await self.redis.get(key)
    
    async def invalidate_user_session(self, user_id: str) -> bool:
        """Invalidate user session."""
        key = f"session:user:{user_id}"
        return bool(await self.redis.delete(key))
    
    async def cache_portfolio_data(self, user_id: str, portfolio_data: Dict[str, Any], expire: int = 300) -> bool:
        """Cache portfolio data with 5-minute expiration."""
        key = f"portfolio:user:{user_id}"
        return await self.redis.set(key, portfolio_data, expire=expire)
    
    async def get_portfolio_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached portfolio data."""
        key = f"portfolio:user:{user_id}"
        return await self.redis.get(key)
    
    async def cache_market_data(self, symbol: str, data: Dict[str, Any], expire: int = 60) -> bool:
        """Cache market data with 1-minute expiration."""
        key = f"market:{symbol.lower()}"
        return await self.redis.set(key, data, expire=expire)
    
    async def get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached market data."""
        key = f"market:{symbol.lower()}"
        return await self.redis.get(key)
    
    async def track_rate_limit(self, user_id: str, endpoint: str, window: int = 60) -> Dict[str, Any]:
        """Track rate limiting for user and endpoint."""
        key = f"rate_limit:{user_id}:{endpoint}"
        current_count = await self.redis.incr(key)
        
        if current_count == 1:
            await self.redis.expire(key, window)
        
        return {
            "current_count": current_count,
            "window": window,
            "exceeded": current_count > settings.RATE_LIMIT_REQUESTS
        }


# Global cache manager instance
cache_manager = CacheManager(redis_manager)


# Initialize Redis client on import
redis_client = None
