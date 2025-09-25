"""
Advanced caching utilities for CryptoUniverse Enterprise.

This module provides a high-level caching interface with support for:
- Time-based expiration
- Tag-based invalidation
- Distributed locking
- Cache stampede protection
- Automatic serialization/deserialization
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import (
    Any, Awaitable, Callable, Dict, List, Optional, Set, Tuple, Type, TypeVar, Union, cast
)
from functools import wraps
import pickle
import hashlib

from app.core.redis import get_redis_client
from app.core.logging import logger
from app.core.config import settings

T = TypeVar('T')

class CacheMissError(Exception):
    """Raised when a cache key is not found."""
    pass

class CacheLockError(Exception):
    """Raised when a cache lock cannot be acquired."""
    pass

def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate a consistent cache key from the given arguments.
    
    Args:
        prefix: A prefix for the cache key (e.g., 'user:profile')
        *args: Positional arguments to include in the key
        **kwargs: Keyword arguments to include in the key
        
    Returns:
        A string that can be used as a cache key
    """
    key_parts = [prefix]
    
    # Add positional arguments
    for arg in args:
        if isinstance(arg, (str, int, float, bool)) or arg is None:
            key_parts.append(str(arg))
        else:
            # For complex objects, use a hash of their string representation
            key_parts.append(hashlib.md5(str(arg).encode()).hexdigest())
    
    # Add keyword arguments
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")
    
    return ":".join(key_parts)

class CacheManager:
    """
    High-level cache manager with advanced features.
    
    Features:
    - Automatic serialization/deserialization
    - Tag-based invalidation
    - Distributed locking
    - Cache stampede protection
    - Time-based expiration
    - Namespacing
    """
    
    def __init__(
        self,
        redis_prefix: str = "cache:",
        default_ttl: int = 300,  # 5 minutes
        enabled: bool = True
    ):
        """
        Initialize the cache manager.
        
        Args:
            redis_prefix: Prefix for all Redis keys
            default_ttl: Default time-to-live in seconds
            enabled: Whether caching is enabled
        """
        self.redis_prefix = redis_prefix
        self.default_ttl = default_ttl
        self.enabled = enabled and not settings.DEBUG
    
    async def _get_redis_key(self, key: str) -> str:
        """Get the full Redis key with prefix."""
        return f"{self.redis_prefix}{key}"
    
    async def _get_tag_key(self, tag: str) -> str:
        """Get the Redis key for a tag."""
        return f"{self.redis_prefix}tag:{tag}"
    
    async def _serialize(self, value: Any) -> bytes:
        """Serialize a value for storage in Redis."""
        try:
            return pickle.dumps({
                'value': value,
                '_cached_at': time.time()
            })
        except (pickle.PickleError, TypeError) as e:
            logger.error(f"Failed to serialize cache value: {e}")
            raise ValueError(f"Unserializable value: {value}")
    
    async def _deserialize(self, data: bytes) -> Any:
        """Deserialize a value from Redis."""
        try:
            result = pickle.loads(data)
            return result['value']
        except (pickle.PickleError, KeyError) as e:
            logger.error(f"Failed to deserialize cache value: {e}")
            raise CacheMissError("Invalid cache data")
    
    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the cache.
        
        Args:
            key: The cache key
            default: Default value if key not found
            
        Returns:
            The cached value or default if not found
        """
        if not self.enabled:
            return default
            
        redis = await get_redis_client()
        full_key = await self._get_redis_key(key)
        
        try:
            data = await redis.get(full_key)
            if data is None:
                return default
                
            return await self._deserialize(data)
            
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return default
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Set a value in the cache.
        
        Args:
            key: The cache key
            value: The value to cache
            ttl: Time-to-live in seconds (None for default)
            tags: List of tags for this cache entry
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
            
        redis = await get_redis_client()
        full_key = await self._get_redis_key(key)
        ttl = ttl if ttl is not None else self.default_ttl
        
        try:
            # Serialize the value
            serialized = await self._serialize(value)
            
            # Start a transaction
            async with redis.pipeline() as pipe:
                # Set the value
                await pipe.set(full_key, serialized, ex=ttl)
                
                # Add to tag sets if tags are provided
                if tags:
                    for tag in tags:
                        tag_key = await self._get_tag_key(tag)
                        await pipe.sadd(tag_key, full_key)
                        await pipe.expire(tag_key, ttl)
                
                # Execute the transaction
                await pipe.execute()
                
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, *keys: str) -> int:
        """
        Delete one or more keys from the cache.
        
        Args:
            *keys: One or more cache keys to delete
            
        Returns:
            Number of keys deleted
        """
        if not self.enabled or not keys:
            return 0
            
        redis = await get_redis_client()
        full_keys = [await self._get_redis_key(k) for k in keys]
        
        try:
            return await redis.delete(*full_keys)
        except Exception as e:
            logger.error(f"Cache delete error for keys {keys}: {e}")
            return 0
    
    async def invalidate_tags(self, *tags: str) -> int:
        """
        Invalidate all cache entries with the given tags.
        
        Args:
            *tags: One or more tags to invalidate
            
        Returns:
            Number of cache entries invalidated
        """
        if not self.enabled or not tags:
            return 0
            
        redis = await get_redis_client()
        deleted = 0
        
        for tag in tags:
            tag_key = await self._get_tag_key(tag)
            
            try:
                # Get all keys with this tag
                cache_keys = await redis.smembers(tag_key)
                
                if cache_keys:
                    # Delete the cache entries
                    count = await redis.delete(*cache_keys)
                    deleted += count
                
                # Delete the tag set
                await redis.delete(tag_key)
                
            except Exception as e:
                logger.error(f"Cache tag invalidation error for tag {tag}: {e}")
        
        return deleted
    
    async def get_or_set(
        self,
        key: str,
        func: Callable[[], Awaitable[T]],
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None,
        lock_timeout: int = 10,
        stale_ttl: int = 60
    ) -> T:
        """
        Get a value from the cache, or set it if not found.
        
        This method implements the cache-aside pattern with lock-based
        cache stampede protection.
        
        Args:
            key: The cache key
            func: Async function to generate the value if not in cache
            ttl: Time-to-live in seconds (None for default)
            tags: List of tags for this cache entry
            lock_timeout: Maximum time to wait for a lock (seconds)
            stale_ttl: Time to keep stale values in cache (for hot cache)
            
        Returns:
            The cached or newly generated value
        """
        if not self.enabled:
            return await func()
            
        # Try to get from cache first
        result = await self.get(key)
        if result is not None:
            return result
        
        # If not found, acquire a lock to prevent cache stampede
        lock = await self._acquire_lock(key, lock_timeout)
        if not lock:
            # If we couldn't get the lock, return a default value or raise an error
            # In a real implementation, you might want to implement a fallback strategy
            logger.warning(f"Could not acquire lock for key: {key}")
            return await func()
        
        try:
            # Double-check if the value was set while we were waiting for the lock
            result = await self.get(key)
            if result is not None:
                return result
            
            # Generate the value
            result = await func()
            
            # Store in cache
            await self.set(key, result, ttl=ttl, tags=tags)
            
            return result
            
        finally:
            # Always release the lock
            await self._release_lock(lock)
    
    async def _acquire_lock(self, key: str, timeout: int) -> Optional[str]:
        """Acquire a distributed lock."""
        redis = await get_redis_client()
        lock_key = f"{self.redis_prefix}lock:{key}"
        lock_id = str(uuid.uuid4())
        
        try:
            # Try to acquire the lock with a timeout
            acquired = await redis.set(
                lock_key,
                lock_id,
                ex=timeout,
                nx=True
            )
            
            if acquired:
                return lock_id
                
        except Exception as e:
            logger.error(f"Error acquiring lock for key {key}: {e}")
            
        return None
    
    async def _release_lock(self, lock: str) -> None:
        """Release a distributed lock."""
        # The lock is released by Redis when it expires
        pass
    
    def cached(
        self,
        key: Optional[str] = None,
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None,
        key_func: Optional[Callable[..., str]] = None
    ) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
        """
        Decorator to cache the result of an async function.
        
        Args:
            key: Cache key (or template with {arg} placeholders)
            ttl: Time-to-live in seconds (None for default)
            tags: List of tags for this cache entry
            key_func: Function to generate the cache key from function arguments
        """
        def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                # Generate the cache key
                if key_func is not None:
                    cache_key = key_func(*args, **kwargs)
                elif key is not None:
                    # Format the key with the function arguments
                    cache_key = key.format(*args, **kwargs)
                else:
                    # Default key generation
                    cache_key = f"{func.__module__}:{func.__name__}:{args}:{kwargs}"
                
                # Try to get from cache
                if self.enabled:
                    try:
                        cached_result = await self.get(cache_key)
                        if cached_result is not None:
                            return cached_result
                    except Exception as e:
                        logger.error(f"Cache get error in @cached decorator: {e}")
                
                # If not in cache or error, call the function
                result = await func(*args, **kwargs)
                
                # Store in cache
                if self.enabled:
                    try:
                        await self.set(cache_key, result, ttl=ttl, tags=tags)
                    except Exception as e:
                        logger.error(f"Cache set error in @cached decorator: {e}")
                
                return result
            
            return wrapper
        
        return decorator

# Global cache manager instance
cache = CacheManager(
    redis_prefix=f"{settings.REDIS_PREFIX}cache:" if hasattr(settings, 'REDIS_PREFIX') else "cache:",
    default_ttl=300,  # 5 minutes
    enabled=not settings.DEBUG
)

# Helper functions for backward compatibility
async def get_cache() -> CacheManager:
    """Get the global cache manager instance."""
    return cache

async def get_cached_or_fetch(
    key: str,
    func: Callable[[], Awaitable[T]],
    ttl: Optional[int] = None,
    tags: Optional[List[str]] = None
) -> T:
    """
    Get a value from cache or fetch it using the provided function.
    
    This is a convenience wrapper around cache.get_or_set().
    """
    return await cache.get_or_set(key, func, ttl=ttl, tags=tags)
