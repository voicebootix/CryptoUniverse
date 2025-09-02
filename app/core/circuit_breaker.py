"""
Circuit Breaker pattern implementation for resilient external service calls.

This module provides a CircuitBreaker class that can be used to wrap calls to external
services, automatically opening the circuit when failures exceed a threshold.
"""

import asyncio
import time
from typing import Any, Callable, Optional, TypeVar, Dict, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
import logging

from app.core.redis import get_redis_client
from app.core.logging import logger
from app.core.config import settings

T = TypeVar('T')

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = auto()      # Normal operation, all requests allowed
    OPEN = auto()        # Circuit is open, all requests fail fast
    HALF_OPEN = auto()   # Testing if service has recovered

@dataclass
class CircuitMetrics:
    """Metrics for circuit breaker state."""
    failures: int = 0
    successes: int = 0
    last_failure: Optional[datetime] = None
    last_success: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0

@dataclass
class CircuitConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5           # Number of failures before opening the circuit
    recovery_timeout: int = 30           # Seconds before trying to close the circuit
    success_threshold: int = 3           # Number of successful calls to close the circuit
    failure_timeout: int = 60            # Time window for counting failures (seconds)
    excluded_exceptions: Tuple[Exception, ...] = ()

class CircuitBreakerError(Exception):
    """Raised when the circuit is open."""
    def __init__(self, circuit_name: str, retry_after: float):
        self.circuit_name = circuit_name
        self.retry_after = retry_after
        super().__init__(
            f"Circuit '{circuit_name}' is open. Retry after {retry_after:.1f} seconds"
        )

class CircuitBreaker:
    """
    Circuit breaker implementation with Redis backend for distributed systems.
    
    Features:
    - Automatic circuit state management
    - Distributed state using Redis
    - Configurable thresholds and timeouts
    - Metrics collection
    - Graceful degradation
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitConfig] = None,
        redis_prefix: str = "circuit:",
        enabled: bool = True
    ):
        """
        Initialize the circuit breaker.
        
        Args:
            name: Unique name for the circuit
            config: Configuration for the circuit breaker
            redis_prefix: Prefix for Redis keys
            enabled: Whether the circuit breaker is enabled
        """
        self.name = name
        self.config = config or CircuitConfig()
        self.redis_prefix = redis_prefix
        self.enabled = enabled and not settings.DEBUG
        self._state = CircuitState.CLOSED
        self._last_state_change = time.monotonic()
        self._lock = asyncio.Lock()
        self._metrics = CircuitMetrics()
        
    async def _get_redis_key(self, suffix: str) -> str:
        """Generate a Redis key with the given suffix."""
        return f"{self.redis_prefix}{self.name}:{suffix}"
    
    async def _load_state(self) -> None:
        """Load the circuit state from Redis."""
        if not self.enabled:
            self._state = CircuitState.CLOSED
            return
            
        redis = await get_redis_client()
        
        async with self._lock:
            try:
                # Get the current state from Redis
                state_key = await self._get_redis_key("state")
                state_data = await redis.hgetall(state_key)
                
                if state_data:
                    self._state = CircuitState[state_data[b'state'].decode()]
                    self._last_state_change = float(state_data[b'last_change'])
                    
                    # Load metrics
                    metrics_key = await self._get_redis_key("metrics")
                    metrics_data = await redis.hgetall(metrics_key)
                    
                    if metrics_data:
                        self._metrics = CircuitMetrics(
                            failures=int(metrics_data.get(b'failures', 0)),
                            successes=int(metrics_data.get(b'successes', 0)),
                            consecutive_failures=int(metrics_data.get(b'consecutive_failures', 0)),
                            consecutive_successes=int(metrics_data.get(b'consecutive_successes', 0)),
                            last_failure=(
                                datetime.fromisoformat(metrics_data[b'last_failure'].decode())
                                if b'last_failure' in metrics_data else None
                            ),
                            last_success=(
                                datetime.fromisoformat(metrics_data[b'last_success'].decode())
                                if b'last_success' in metrics_data else None
                            )
                        )
            except Exception as e:
                logger.error(f"Failed to load circuit state: {e}")
                # Fail closed (allow requests to proceed)
                self._state = CircuitState.CLOSED
    
    async def _save_state(self) -> None:
        """Save the circuit state to Redis."""
        if not self.enabled:
            return
            
        redis = await get_redis_client()
        
        async with self._lock:
            try:
                # Save the current state
                state_key = await self._get_redis_key("state")
                await redis.hset(
                    state_key,
                    mapping={
                        'state': self._state.name,
                        'last_change': str(self._last_state_change)
                    }
                )
                
                # Set expiry on the state key
                await redis.expire(state_key, max(
                    self.config.failure_timeout,
                    self.config.recovery_timeout
                ) * 2)
                
                # Save metrics
                metrics_key = await self._get_redis_key("metrics")
                metrics_data = {
                    'failures': str(self._metrics.failures),
                    'successes': str(self._metrics.successes),
                    'consecutive_failures': str(self._metrics.consecutive_failures),
                    'consecutive_successes': str(self._metrics.consecutive_successes),
                }
                
                if self._metrics.last_failure:
                    metrics_data['last_failure'] = self._metrics.last_failure.isoformat()
                if self._metrics.last_success:
                    metrics_data['last_success'] = self._metrics.last_success.isoformat()
                
                await redis.hset(metrics_key, mapping=metrics_data)
                
            except Exception as e:
                logger.error(f"Failed to save circuit state: {e}")
    
    async def _record_success(self) -> None:
        """Record a successful operation."""
        async with self._lock:
            now = datetime.utcnow()
            self._metrics.successes += 1
            self._metrics.consecutive_successes += 1
            self._metrics.consecutive_failures = 0
            self._metrics.last_success = now
            
            # If we're in half-open state and have enough successes, close the circuit
            if self._state == CircuitState.HALF_OPEN:
                if self._metrics.consecutive_successes >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._last_state_change = time.monotonic()
                    logger.info(f"Circuit '{self.name}' is now CLOSED")
            
            await self._save_state()
    
    async def _record_failure(self) -> None:
        """Record a failed operation."""
        async with self._lock:
            now = datetime.utcnow()
            self._metrics.failures += 1
            self._metrics.consecutive_failures += 1
            self._metrics.consecutive_successes = 0
            self._metrics.last_failure = now
            
            # Check if we should open the circuit
            if (self._state == CircuitState.CLOSED and 
                self._metrics.consecutive_failures >= self.config.failure_threshold):
                self._state = CircuitState.OPEN
                self._last_state_change = time.monotonic()
                logger.warning(f"Circuit '{self.name}' is now OPEN")
            
            await self._save_state()
    
    async def _should_try(self) -> bool:
        """Determine if a request should be allowed based on the circuit state."""
        if not self.enabled:
            return True
            
        await self._load_state()
        
        # If circuit is closed, allow the request
        if self._state == CircuitState.CLOSED:
            return True
            
        # If circuit is open, check if we should try to recover
        if self._state == CircuitState.OPEN:
            time_since_open = time.monotonic() - self._last_state_change
            if time_since_open >= self.config.recovery_timeout:
                # Try to move to half-open state
                async with self._lock:
                    if self._state == CircuitState.OPEN:  # Double-check after acquiring lock
                        self._state = CircuitState.HALF_OPEN
                        self._last_state_change = time.monotonic()
                        logger.info(f"Circuit '{self.name}' is now HALF-OPEN")
                        await self._save_state()
                        return True
            return False
            
        # If circuit is half-open, allow the request (this is the test request)
        return True
    
    async def call(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any
    ) -> T:
        """
        Execute a function with circuit breaker protection.
        
        Args:
            func: The function to call
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the function call
            
        Raises:
            CircuitBreakerError: If the circuit is open
            Exception: Any exception raised by the wrapped function
        """
        if not await self._should_try():
            time_until_retry = max(0, (
                (self._last_state_change + self.config.recovery_timeout) - time.monotonic()
            ))
            raise CircuitBreakerError(self.name, time_until_retry)
        
        try:
            # Call the wrapped function
            result = await func(*args, **kwargs)
            
            # Record success
            await self._record_success()
            return result
            
        except self.config.excluded_exceptions:
            # Re-raise excluded exceptions without affecting the circuit
            raise
            
        except Exception as e:
            # Record failure and re-raise
            await self._record_failure()
            raise
    
    def __call__(
        self,
        func: Callable[..., Awaitable[T]]
    ) -> Callable[..., Awaitable[T]]:
        """Decorator version of the call method."""
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await self.call(func, *args, **kwargs)
        return wrapper

# Global circuit breaker registry
_circuit_breakers: Dict[str, CircuitBreaker] = {}

def get_circuit_breaker(
    name: str,
    config: Optional[CircuitConfig] = None,
    **kwargs: Any
) -> CircuitBreaker:
    """
    Get or create a circuit breaker with the given name and configuration.
    
    Args:
        name: Unique name for the circuit
        config: Configuration for the circuit breaker
        **kwargs: Additional arguments to pass to the CircuitBreaker constructor
        
    Returns:
        CircuitBreaker: The circuit breaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config, **kwargs)
    return _circuit_breakers[name]

# Common circuit breaker configurations
DEFAULT_CIRCUIT_CONFIG = CircuitConfig(
    failure_threshold=5,
    recovery_timeout=30,
    success_threshold=3,
    failure_timeout=60
)

# Example usage:
# @get_circuit_breaker("external_api", DEFAULT_CIRCUIT_CONFIG)
# async def call_external_api():
#     # Your API call here
#     pass
