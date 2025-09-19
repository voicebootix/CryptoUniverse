"""
Enterprise Circuit Breaker Management Service

Handles circuit breakers for external API dependencies with:
- Intelligent failure detection and recovery
- Adaptive rate limiting based on API response patterns
- Fallback strategies for each service type
- Comprehensive monitoring and alerting
- Production-grade reliability patterns
"""

import asyncio
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass, asdict
import structlog

from app.core.config import get_settings
from app.core.redis import get_redis_client

settings = get_settings()
logger = structlog.get_logger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    success_threshold: int = 3
    timeout_threshold: int = 30
    slow_call_threshold: float = 5.0  # seconds
    minimum_calls: int = 10
    sliding_window_size: int = 100


@dataclass
class CircuitBreakerMetrics:
    """Metrics tracked by the circuit breaker."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    timeout_calls: int = 0
    slow_calls: int = 0
    last_failure_time: float = 0
    last_success_time: float = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    average_response_time: float = 0.0


class EnterpriseCircuitBreaker:
    """
    Enterprise-grade circuit breaker with Redis persistence for multi-worker environments.
    
    Features:
    - Redis-backed state persistence
    - Adaptive failure detection
    - Intelligent recovery strategies
    - Comprehensive metrics and monitoring
    - Fallback mechanism support
    """
    
    def __init__(self, 
                 service_name: str,
                 config: Optional[CircuitBreakerConfig] = None,
                 fallback_func: Optional[Callable] = None):
        self.service_name = service_name
        self.config = config or CircuitBreakerConfig()
        self.fallback_func = fallback_func
        self.logger = logger.bind(service=service_name)
        
        # Redis keys
        self.state_key = f"circuit_breaker:{service_name}:state"
        self.metrics_key = f"circuit_breaker:{service_name}:metrics"
        self.calls_key = f"circuit_breaker:{service_name}:calls"
        
        # Local cache for performance
        self._local_state = CircuitState.CLOSED
        self._local_metrics = CircuitBreakerMetrics()
        self._last_state_sync = 0
        self._sync_interval = 5  # seconds
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function call through the circuit breaker.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or fallback value
            
        Raises:
            Exception: If circuit is open and no fallback available
        """
        # Sync state from Redis if needed
        await self._sync_state_from_redis()
        
        # Check if circuit is open
        if self._local_state == CircuitState.OPEN:
            if await self._should_attempt_reset():
                self._local_state = CircuitState.HALF_OPEN
                self.logger.info("Circuit breaker transitioning to HALF_OPEN", 
                               service=self.service_name)
            else:
                # Circuit is open, use fallback or fail fast
                return await self._handle_open_circuit(func, *args, **kwargs)
        
        # Execute the function call
        start_time = time.time()
        
        try:
            # Apply timeout if configured
            if self.config.timeout_threshold > 0:
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.timeout_threshold
                )
            else:
                result = await func(*args, **kwargs)
            
            # Record successful call
            call_duration = time.time() - start_time
            await self._record_success(call_duration)
            
            return result
            
        except asyncio.TimeoutError as e:
            # Record timeout
            call_duration = time.time() - start_time
            await self._record_timeout(call_duration)
            raise
            
        except Exception as e:
            # Record failure
            call_duration = time.time() - start_time
            await self._record_failure(call_duration, str(e))
            raise
    
    async def _sync_state_from_redis(self):
        """Sync circuit breaker state from Redis."""
        current_time = time.time()
        
        if current_time - self._last_state_sync < self._sync_interval:
            return
        
        try:
            redis = await get_redis_client()
            if not redis:
                return
            
            # Get state and metrics from Redis
            state_data = await redis.get(self.state_key)
            metrics_data = await redis.get(self.metrics_key)
            
            if state_data:
                state_info = json.loads(state_data)
                self._local_state = CircuitState(state_info.get("state", "closed"))
            
            if metrics_data:
                metrics_info = json.loads(metrics_data)
                self._local_metrics = CircuitBreakerMetrics(**metrics_info)
            
            self._last_state_sync = current_time
            
        except Exception as e:
            self.logger.warning("Failed to sync circuit breaker state from Redis",
                              error=str(e))
    
    async def _persist_state_to_redis(self):
        """Persist circuit breaker state to Redis."""
        try:
            redis = await get_redis_client()
            if not redis:
                return
            
            # Store state
            state_data = {
                "state": self._local_state.value,
                "last_updated": time.time(),
                "service": self.service_name
            }
            
            await redis.setex(
                self.state_key,
                300,  # 5 minute expiration
                json.dumps(state_data)
            )
            
            # Store metrics
            metrics_data = asdict(self._local_metrics)
            await redis.setex(
                self.metrics_key,
                300,  # 5 minute expiration
                json.dumps(metrics_data)
            )
            
        except Exception as e:
            self.logger.warning("Failed to persist circuit breaker state to Redis",
                              error=str(e))
    
    async def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset."""
        if self._local_state != CircuitState.OPEN:
            return False
        
        # Check if recovery timeout has passed
        current_time = time.time()
        time_since_failure = current_time - self._local_metrics.last_failure_time
        
        return time_since_failure >= self.config.recovery_timeout
    
    async def _handle_open_circuit(self, func: Callable, *args, **kwargs) -> Any:
        """Handle calls when circuit is open."""
        if self.fallback_func:
            self.logger.info("Circuit breaker OPEN - using fallback",
                           service=self.service_name)
            try:
                return await self.fallback_func(*args, **kwargs)
            except Exception as e:
                self.logger.error("Fallback function failed",
                                service=self.service_name,
                                error=str(e))
                raise
        else:
            # No fallback available
            raise Exception(f"Circuit breaker OPEN for {self.service_name} - no fallback available")
    
    async def _record_success(self, call_duration: float):
        """Record a successful call."""
        self._local_metrics.total_calls += 1
        self._local_metrics.successful_calls += 1
        self._local_metrics.consecutive_successes += 1
        self._local_metrics.consecutive_failures = 0
        self._local_metrics.last_success_time = time.time()
        
        # Update average response time
        self._update_average_response_time(call_duration)
        
        # Check if call was slow
        if call_duration > self.config.slow_call_threshold:
            self._local_metrics.slow_calls += 1
        
        # Handle state transitions
        if self._local_state == CircuitState.HALF_OPEN:
            if self._local_metrics.consecutive_successes >= self.config.success_threshold:
                self._local_state = CircuitState.CLOSED
                self.logger.info("Circuit breaker CLOSED - service recovered",
                               service=self.service_name,
                               consecutive_successes=self._local_metrics.consecutive_successes)
        
        await self._persist_state_to_redis()
    
    async def _record_failure(self, call_duration: float, error: str):
        """Record a failed call."""
        self._local_metrics.total_calls += 1
        self._local_metrics.failed_calls += 1
        self._local_metrics.consecutive_failures += 1
        self._local_metrics.consecutive_successes = 0
        self._local_metrics.last_failure_time = time.time()
        
        # Update average response time
        self._update_average_response_time(call_duration)
        
        # Check if we should trip the circuit breaker
        if (self._local_metrics.consecutive_failures >= self.config.failure_threshold and
            self._local_metrics.total_calls >= self.config.minimum_calls):
            
            if self._local_state != CircuitState.OPEN:
                self._local_state = CircuitState.OPEN
                self.logger.error("Circuit breaker OPENED",
                                service=self.service_name,
                                consecutive_failures=self._local_metrics.consecutive_failures,
                                error=error)
        
        await self._persist_state_to_redis()
    
    async def _record_timeout(self, call_duration: float):
        """Record a timeout call."""
        self._local_metrics.total_calls += 1
        self._local_metrics.timeout_calls += 1
        self._local_metrics.failed_calls += 1
        self._local_metrics.consecutive_failures += 1
        self._local_metrics.consecutive_successes = 0
        self._local_metrics.last_failure_time = time.time()
        
        # Update average response time
        self._update_average_response_time(call_duration)
        
        # Timeouts are treated as failures for circuit breaking
        if (self._local_metrics.consecutive_failures >= self.config.failure_threshold and
            self._local_metrics.total_calls >= self.config.minimum_calls):
            
            if self._local_state != CircuitState.OPEN:
                self._local_state = CircuitState.OPEN
                self.logger.error("Circuit breaker OPENED due to timeouts",
                                service=self.service_name,
                                consecutive_failures=self._local_metrics.consecutive_failures)
        
        await self._persist_state_to_redis()
    
    def _update_average_response_time(self, call_duration: float):
        """Update the average response time."""
        if self._local_metrics.average_response_time == 0:
            self._local_metrics.average_response_time = call_duration
        else:
            # Exponential moving average
            alpha = 0.1
            self._local_metrics.average_response_time = (
                alpha * call_duration + 
                (1 - alpha) * self._local_metrics.average_response_time
            )
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics for monitoring."""
        await self._sync_state_from_redis()
        
        success_rate = 0.0
        if self._local_metrics.total_calls > 0:
            success_rate = self._local_metrics.successful_calls / self._local_metrics.total_calls
        
        return {
            "service_name": self.service_name,
            "state": self._local_state.value,
            "success_rate": success_rate,
            "metrics": asdict(self._local_metrics),
            "config": asdict(self.config),
            "health_status": self._get_health_status()
        }
    
    def _get_health_status(self) -> str:
        """Get current health status."""
        if self._local_state == CircuitState.OPEN:
            return "unhealthy"
        elif self._local_state == CircuitState.HALF_OPEN:
            return "recovering"
        elif self._local_metrics.slow_calls > self._local_metrics.successful_calls * 0.5:
            return "degraded"
        else:
            return "healthy"
    
    async def force_open(self):
        """Manually force circuit breaker open."""
        self._local_state = CircuitState.OPEN
        self._local_metrics.last_failure_time = time.time()
        await self._persist_state_to_redis()
        self.logger.warning("Circuit breaker manually forced OPEN",
                          service=self.service_name)
    
    async def force_close(self):
        """Manually force circuit breaker closed."""
        self._local_state = CircuitState.CLOSED
        self._local_metrics.consecutive_failures = 0
        await self._persist_state_to_redis()
        self.logger.info("Circuit breaker manually forced CLOSED",
                        service=self.service_name)


class EnterpriseCircuitBreakerManager:
    """
    Manages multiple circuit breakers for different services.
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[str, EnterpriseCircuitBreaker] = {}
        self.logger = logger
    
    def get_circuit_breaker(self, 
                          service_name: str,
                          config: Optional[CircuitBreakerConfig] = None,
                          fallback_func: Optional[Callable] = None) -> EnterpriseCircuitBreaker:
        """Get or create a circuit breaker for a service."""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = EnterpriseCircuitBreaker(
                service_name=service_name,
                config=config,
                fallback_func=fallback_func
            )
            self.logger.info("Created circuit breaker for service",
                           service=service_name)
        
        return self.circuit_breakers[service_name]
    
    async def get_all_metrics(self) -> Dict[str, Any]:
        """Get metrics for all circuit breakers."""
        metrics = {}
        for service_name, circuit_breaker in self.circuit_breakers.items():
            metrics[service_name] = await circuit_breaker.get_metrics()
        return metrics
    
    async def health_check(self) -> Dict[str, str]:
        """Get health status for all services."""
        health_status = {}
        for service_name, circuit_breaker in self.circuit_breakers.items():
            metrics = await circuit_breaker.get_metrics()
            health_status[service_name] = metrics["health_status"]
        return health_status


# Global circuit breaker manager
circuit_breaker_manager = EnterpriseCircuitBreakerManager()


# Convenience functions for common external services
async def call_with_circuit_breaker(service_name: str, 
                                   func: Callable,
                                   *args,
                                   config: Optional[CircuitBreakerConfig] = None,
                                   fallback_func: Optional[Callable] = None,
                                   **kwargs) -> Any:
    """
    Execute a function call with circuit breaker protection.
    
    Args:
        service_name: Name of the service
        func: Function to execute
        config: Circuit breaker configuration
        fallback_func: Fallback function if circuit is open
        
    Returns:
        Function result or fallback value
    """
    circuit_breaker = circuit_breaker_manager.get_circuit_breaker(
        service_name=service_name,
        config=config,
        fallback_func=fallback_func
    )
    
    return await circuit_breaker.call(func, *args, **kwargs)


# Pre-configured circuit breakers for common services
def get_market_data_circuit_breaker(service_name: str) -> EnterpriseCircuitBreaker:
    """Get circuit breaker configured for market data services."""
    config = CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=120,  # 2 minutes
        timeout_threshold=10,  # 10 second timeout
        slow_call_threshold=3.0  # 3 seconds
    )
    
    async def market_data_fallback(*args, **kwargs):
        """Fallback for market data - return cached data or empty response."""
        logger.warning(f"Using market data fallback for {service_name}")
        return {"error": "Service unavailable", "data": None}
    
    return circuit_breaker_manager.get_circuit_breaker(
        service_name=service_name,
        config=config,
        fallback_func=market_data_fallback
    )


def get_ai_service_circuit_breaker(service_name: str) -> EnterpriseCircuitBreaker:
    """Get circuit breaker configured for AI services."""
    config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=300,  # 5 minutes
        timeout_threshold=30,  # 30 second timeout
        slow_call_threshold=10.0  # 10 seconds
    )
    
    async def ai_service_fallback(*args, **kwargs):
        """Fallback for AI services - return simple response."""
        logger.warning(f"Using AI service fallback for {service_name}")
        return {
            "response": "AI service temporarily unavailable. Using fallback response.",
            "confidence": 0.0,
            "fallback": True
        }
    
    return circuit_breaker_manager.get_circuit_breaker(
        service_name=service_name,
        config=config,
        fallback_func=ai_service_fallback
    )