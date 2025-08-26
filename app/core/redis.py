"""
Redis configuration and client management.

Handles Redis connection, caching, session storage, and pub/sub
for real-time features in the cryptocurrency trading platform.
"""

import json
from typing import Any, Dict, List, Optional, Union
import aioredis
from aioredis import Redis
import structlog

from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger()

# Redis client instance
redis_client: Optional[Redis] = None


async def get_redis_client() -> Redis:
    """
    Get Redis client instance with connection pooling.
    
    Returns:
        Redis: Redis client instance
    """
    global redis_client
    if redis_client is None:
        redis_client = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
            retry_on_timeout=True
        )
    return redis_client


async def close_redis_client():
    """Close Redis client connection."""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


class RedisManager:
    """Redis operations manager with serialization and error handling."""
    
    def __init__(self):
        self.client: Optional[Redis] = None
    
    async def get_client(self) -> Redis:
        """Get Redis client instance."""
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
        Ping Redis server.
        
        Returns:
            bool: True if Redis is responding
        """
        try:
            client = await self.get_client()
            result = await client.ping()
            return result == "PONG"
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
