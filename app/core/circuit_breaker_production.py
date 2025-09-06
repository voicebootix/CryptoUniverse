"""
Production-Grade Circuit Breaker and Backpressure Management for CryptoUniverse
Multi-layer circuit breakers with priority-based throttling and resource-aware backpressure.
Based on production crypto trading system patterns.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
from collections import deque

import structlog
from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"        # Normal operation
    OPEN = "open"           # Failing, rejecting requests
    HALF_OPEN = "half_open" # Testing if service recovered


class Priority(Enum):
    CRITICAL = 1    # Trading execution, risk alerts
    HIGH = 2        # Market data, portfolio sync  
    MEDIUM = 3      # Balance updates, user requests
    LOW = 4         # Analytics, background tasks


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5          # Failures before opening
    success_threshold: int = 3          # Successes to close from half-open
    timeout_seconds: int = 60          # Time before trying half-open
    max_timeout_seconds: int = 300     # Maximum timeout (exponential backoff)
    failure_window_seconds: int = 60   # Time window for failure counting
    slow_request_threshold_ms: int = 5000  # Requests slower than this count as failures
    

@dataclass
class BackpressureConfig:
    """Configuration for backpressure management."""
    max_concurrent_requests: int = 100
    queue_size_limit: int = 1000
    memory_threshold_percent: int = 85
    cpu_threshold_percent: int = 90
    disk_threshold_percent: int = 95
    priority_queue_sizes: Dict[Priority, int] = field(default_factory=lambda: {
        Priority.CRITICAL: 200,
        Priority.HIGH: 150,
        Priority.MEDIUM: 100,
        Priority.LOW: 50
    })


class CircuitBreaker:
    """Production-grade circuit breaker with exponential backoff and metrics."""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.state_change_time = time.time()
        self.timeout_multiplier = 1
        
        # Metrics tracking
        self.request_count = 0
        self.failure_history = deque(maxlen=1000)
        self.latency_history = deque(maxlen=1000)
        self.state_changes = []
        
        # Failure tracking within time window
        self.failure_times = deque()
    
    async def call(self, func: Callable, *args, priority: Priority = Priority.MEDIUM, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        self.request_count += 1
        
        # Check if circuit is open
        if self.state == CircuitState.OPEN:
            if not self._should_attempt_reset():
                raise CircuitBreakerOpenError(
                    f"Circuit breaker {self.name} is OPEN. "
                    f"Retry after {self._get_retry_after_seconds()}s"
                )
            else:
                self._transition_to_half_open()
        
        # Record request start time
        start_time = time.time()
        
        try:
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                # Offload synchronous function to thread pool to avoid blocking event loop
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, func, *args, **kwargs)
            
            # Record success
            execution_time_ms = (time.time() - start_time) * 1000
            await self._record_success(execution_time_ms, priority)
            
            return result
            
        except Exception as e:
            # Record failure
            execution_time_ms = (time.time() - start_time) * 1000
            await self._record_failure(e, execution_time_ms, priority)
            raise
    
    async def _record_success(self, execution_time_ms: float, priority: Priority):
        """Record successful execution."""
        self.latency_history.append(execution_time_ms)
        
        # Check if request was too slow (counts as partial failure)
        if execution_time_ms > self.config.slow_request_threshold_ms:
            logger.warning(f"Slow request in {self.name}",
                         execution_time_ms=execution_time_ms,
                         threshold_ms=self.config.slow_request_threshold_ms,
                         priority=priority.name)
            # Don't increment failure count for slow requests, but log them
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.debug(f"Circuit breaker {self.name} success in HALF_OPEN",
                        success_count=self.success_count,
                        needed=self.config.success_threshold)
            
            if self.success_count >= self.config.success_threshold:
                self._transition_to_closed()
        
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = max(0, self.failure_count - 1)
    
    async def _record_failure(self, error: Exception, execution_time_ms: float, priority: Priority):
        """Record failed execution."""
        current_time = time.time()
        
        self.failure_count += 1
        self.last_failure_time = current_time
        self.failure_times.append(current_time)
        self.failure_history.append({
            "time": current_time,
            "error": str(error),
            "execution_time_ms": execution_time_ms,
            "priority": priority.name
        })
        
        # Clean old failures outside the window
        self._clean_old_failures()
        
        logger.warning(f"Circuit breaker {self.name} recorded failure",
                      error=str(error),
                      failure_count=self.failure_count,
                      execution_time_ms=execution_time_ms,
                      priority=priority.name,
                      state=self.state.value)
        
        # Check if we should open the circuit
        if self.state == CircuitState.CLOSED and self._should_open_circuit():
            self._transition_to_open()
        
        elif self.state == CircuitState.HALF_OPEN:
            # Any failure in half-open immediately goes back to open
            self._transition_to_open()
    
    def _clean_old_failures(self):
        """Remove failures outside the failure window."""
        cutoff_time = time.time() - self.config.failure_window_seconds
        
        while self.failure_times and self.failure_times[0] < cutoff_time:
            self.failure_times.popleft()
    
    def _should_open_circuit(self) -> bool:
        """Check if circuit should be opened."""
        # Clean old failures first
        self._clean_old_failures()
        
        # Check if we have enough recent failures
        recent_failures = len(self.failure_times)
        
        return recent_failures >= self.config.failure_threshold
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset (transition to half-open)."""
        if self.state != CircuitState.OPEN:
            return False
        
        time_since_open = time.time() - self.state_change_time
        timeout_with_backoff = self.config.timeout_seconds * self.timeout_multiplier
        
        return time_since_open >= min(timeout_with_backoff, self.config.max_timeout_seconds)
    
    def _get_retry_after_seconds(self) -> int:
        """Get seconds until retry is possible."""
        if self.state != CircuitState.OPEN:
            return 0
        
        time_since_open = time.time() - self.state_change_time
        timeout_with_backoff = self.config.timeout_seconds * self.timeout_multiplier
        max_timeout = min(timeout_with_backoff, self.config.max_timeout_seconds)
        
        return max(0, int(max_timeout - time_since_open))
    
    def _transition_to_open(self):
        """Transition circuit breaker to OPEN state."""
        old_state = self.state
        self.state = CircuitState.OPEN
        self.state_change_time = time.time()
        self.success_count = 0
        
        # Exponential backoff on repeated failures
        if old_state == CircuitState.HALF_OPEN:
            self.timeout_multiplier = min(self.timeout_multiplier * 2, 8)  # Max 8x timeout
        
        self._log_state_change(old_state, CircuitState.OPEN)
    
    def _transition_to_half_open(self):
        """Transition circuit breaker to HALF_OPEN state."""
        old_state = self.state
        self.state = CircuitState.HALF_OPEN
        self.state_change_time = time.time()
        self.success_count = 0
        
        self._log_state_change(old_state, CircuitState.HALF_OPEN)
    
    def _transition_to_closed(self):
        """Transition circuit breaker to CLOSED state."""
        old_state = self.state
        self.state = CircuitState.CLOSED
        self.state_change_time = time.time()
        self.failure_count = 0
        self.success_count = 0
        self.timeout_multiplier = 1  # Reset backoff multiplier
        
        self._log_state_change(old_state, CircuitState.CLOSED)
    
    def _log_state_change(self, from_state: CircuitState, to_state: CircuitState):
        """Log circuit breaker state changes."""
        change_info = {
            "circuit_breaker": self.name,
            "from_state": from_state.value,
            "to_state": to_state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "timeout_multiplier": self.timeout_multiplier
        }
        
        self.state_changes.append({
            "time": time.time(),
            **change_info
        })
        
        if to_state == CircuitState.OPEN:
            logger.error("Circuit breaker opened", **change_info)
        elif to_state == CircuitState.CLOSED:
            logger.info("Circuit breaker closed", **change_info)
        else:
            logger.info("Circuit breaker half-opened", **change_info)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive circuit breaker statistics."""
        current_time = time.time()
        self._clean_old_failures()
        
        # Calculate latency percentiles
        latencies = list(self.latency_history)
        latency_stats = {}
        if latencies:
            latencies.sort()
            latency_stats = {
                "p50": latencies[int(len(latencies) * 0.5)] if latencies else 0,
                "p95": latencies[int(len(latencies) * 0.95)] if len(latencies) > 20 else 0,
                "p99": latencies[int(len(latencies) * 0.99)] if len(latencies) > 100 else 0,
                "avg": sum(latencies) / len(latencies),
                "max": max(latencies)
            }
        
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "recent_failures": len(self.failure_times),
            "request_count": self.request_count,
            "time_in_current_state": current_time - self.state_change_time,
            "retry_after_seconds": self._get_retry_after_seconds(),
            "timeout_multiplier": self.timeout_multiplier,
            "latency_stats": latency_stats,
            "failure_rate": len(self.failure_times) / max(self.request_count, 1),
            "state_changes": len(self.state_changes)
        }


class BackpressureManager:
    """Production-grade backpressure management with priority queues."""
    
    def __init__(self, config: BackpressureConfig):
        self.config = config
        self.active_requests = 0
        self.priority_queues = {
            priority: asyncio.Queue(maxsize=size) 
            for priority, size in config.priority_queue_sizes.items()
        }
        
        # Resource monitoring
        self.resource_stats = {
            "memory_percent": 0,
            "cpu_percent": 0,
            "disk_percent": 0,
            "last_update": 0
        }
        
        # CPU monitoring initialization
        self._cpu_initialized = False
        
        # Metrics
        self.metrics = {
            "requests_queued": 0,
            "requests_rejected": 0,
            "requests_completed": 0,
            "queue_wait_times": deque(maxlen=1000),
            "resource_pressure_events": 0
        }
        
        # Start resource monitoring
        self._monitoring_task = None
        self._start_resource_monitoring()
    
    def _start_resource_monitoring(self):
        """Start background resource monitoring."""
        if not self._monitoring_task:
            self._monitoring_task = asyncio.create_task(self._monitor_resources())
    
    async def _monitor_resources(self):
        """Monitor system resources continuously."""
        while True:
            try:
                import psutil
                
                # Initialize CPU monitoring on first call
                if not self._cpu_initialized:
                    psutil.cpu_percent(interval=None)  # Initialize CPU monitoring
                    self._cpu_initialized = True
                    await asyncio.sleep(1)  # Wait for initial measurement
                    continue
                
                # Get accurate CPU reading with small blocking interval
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                self.resource_stats = {
                    "memory_percent": memory.percent,
                    "cpu_percent": cpu_percent,
                    "disk_percent": disk.percent,
                    "last_update": time.time()
                }
                
                # Check for resource pressure
                if (memory.percent > self.config.memory_threshold_percent or 
                    cpu_percent > self.config.cpu_threshold_percent or
                    disk.percent > self.config.disk_threshold_percent):
                    
                    self.metrics["resource_pressure_events"] += 1
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.warning("Resource monitoring error", error=str(e))
                await asyncio.sleep(10)
    
    async def execute_with_backpressure(
        self, 
        func: Callable, 
        priority: Priority = Priority.MEDIUM,
        timeout_seconds: int = 30,
        *args, 
        **kwargs
    ) -> Any:
        """Execute function with backpressure protection."""
        
        # Check if system is under severe pressure
        if self._is_under_severe_pressure():
            if priority not in [Priority.CRITICAL, Priority.HIGH]:
                self.metrics["requests_rejected"] += 1
                raise BackpressureError(
                    "System under severe pressure, rejecting non-critical requests"
                )
        
        # Check concurrent request limits
        if self.active_requests >= self.config.max_concurrent_requests:
            if priority == Priority.CRITICAL:
                # Allow critical requests to bypass limits (but log warning)
                logger.warning("Critical request bypassing concurrent limit",
                             active_requests=self.active_requests,
                             limit=self.config.max_concurrent_requests)
            else:
                # Queue non-critical requests
                queue_start_time = time.time()
                try:
                    await asyncio.wait_for(
                        self.priority_queues[priority].put(None),
                        timeout=timeout_seconds / 2  # Use half timeout for queueing
                    )
                    
                    queue_wait_time = time.time() - queue_start_time
                    self.metrics["queue_wait_times"].append(queue_wait_time)
                    self.metrics["requests_queued"] += 1
                    
                except asyncio.TimeoutError:
                    self.metrics["requests_rejected"] += 1
                    raise BackpressureError(
                        f"Request queue timeout after {timeout_seconds/2}s"
                    )
        
        # Execute the function with resource tracking
        self.active_requests += 1
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                self._execute_function(func, *args, **kwargs),
                timeout=timeout_seconds
            )
            
            self.metrics["requests_completed"] += 1
            return result
            
        except asyncio.TimeoutError:
            logger.warning("Function execution timeout",
                         function=getattr(func, '__name__', 'unknown'),
                         timeout_seconds=timeout_seconds,
                         priority=priority.name)
            raise
            
        except Exception as e:
            logger.warning("Function execution error",
                         function=getattr(func, '__name__', 'unknown'),
                         error=str(e),
                         priority=priority.name)
            raise
            
        finally:
            self.active_requests -= 1
            
            # Release queued request of same or lower priority
            await self._release_queued_request(priority)
    
    async def _execute_function(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function (async or sync)."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            # Run synchronous function in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, func, *args, **kwargs)
    
    async def _release_queued_request(self, completed_priority: Priority):
        """Release a queued request, prioritizing higher priority requests."""
        # Try to release higher or equal priority requests first
        priority_order = [Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM, Priority.LOW]
        
        for priority in priority_order:
            if priority.value <= completed_priority.value:  # Higher priority = lower number
                try:
                    self.priority_queues[priority].get_nowait()
                    return
                except asyncio.QueueEmpty:
                    continue
    
    def _is_under_severe_pressure(self) -> bool:
        """Check if system is under severe resource pressure."""
        stats = self.resource_stats
        
        return (
            stats["memory_percent"] > self.config.memory_threshold_percent or
            stats["cpu_percent"] > self.config.cpu_threshold_percent or
            stats["disk_percent"] > self.config.disk_threshold_percent
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive backpressure statistics."""
        queue_lengths = {
            priority.name: queue.qsize() 
            for priority, queue in self.priority_queues.items()
        }
        
        wait_times = list(self.metrics["queue_wait_times"])
        wait_time_stats = {}
        if wait_times:
            wait_times.sort()
            wait_time_stats = {
                "p50": wait_times[int(len(wait_times) * 0.5)] if wait_times else 0,
                "p95": wait_times[int(len(wait_times) * 0.95)] if len(wait_times) > 20 else 0,
                "avg": sum(wait_times) / len(wait_times),
                "max": max(wait_times)
            }
        
        return {
            "active_requests": self.active_requests,
            "max_concurrent": self.config.max_concurrent_requests,
            "queue_lengths": queue_lengths,
            "resource_stats": self.resource_stats,
            "is_under_pressure": self._is_under_severe_pressure(),
            "metrics": {
                **self.metrics,
                "queue_wait_times": wait_time_stats
            }
        }
    
    async def shutdown(self):
        """Shutdown backpressure manager."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass


class ProductionCircuitBreakerManager:
    """Manages multiple circuit breakers with different configurations."""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.backpressure_manager: Optional[BackpressureManager] = None
        self._initialize_default_breakers()
    
    def _initialize_default_breakers(self):
        """Initialize circuit breakers for different service types."""
        
        # Redis operations - critical for caching and streams
        self.add_circuit_breaker(
            "redis_operations",
            CircuitBreakerConfig(
                failure_threshold=10,      # More tolerant since Redis is critical
                timeout_seconds=30,        # Shorter timeout for Redis
                max_timeout_seconds=120,   # Max 2 minutes
                failure_window_seconds=60
            )
        )
        
        # Database operations 
        self.add_circuit_breaker(
            "database_operations",
            CircuitBreakerConfig(
                failure_threshold=5,
                timeout_seconds=60,
                max_timeout_seconds=300,   # Max 5 minutes
                failure_window_seconds=120
            )
        )
        
        # External API calls (market data, exchanges)
        self.add_circuit_breaker(
            "external_apis",
            CircuitBreakerConfig(
                failure_threshold=3,       # Less tolerant for external APIs
                timeout_seconds=120,       # Longer timeout for external APIs
                max_timeout_seconds=600,   # Max 10 minutes
                failure_window_seconds=300,
                slow_request_threshold_ms=3000  # 3 seconds for external APIs
            )
        )
        
        # WebSocket connections
        self.add_circuit_breaker(
            "websocket_connections",
            CircuitBreakerConfig(
                failure_threshold=5,
                timeout_seconds=30,
                max_timeout_seconds=180,   # Max 3 minutes
                failure_window_seconds=60
            )
        )
        
        # Trading execution (most critical)
        self.add_circuit_breaker(
            "trading_execution", 
            CircuitBreakerConfig(
                failure_threshold=2,       # Very sensitive to failures
                timeout_seconds=10,        # Quick recovery attempts
                max_timeout_seconds=60,    # Max 1 minute downtime
                failure_window_seconds=30,
                slow_request_threshold_ms=1000  # 1 second for trading
            )
        )
        
        # Initialize backpressure manager
        self.backpressure_manager = BackpressureManager(
            BackpressureConfig(
                max_concurrent_requests=50,  # Conservative for Render
                memory_threshold_percent=80,  # Conservative thresholds
                cpu_threshold_percent=85,
                disk_threshold_percent=90
            )
        )
    
    def add_circuit_breaker(self, name: str, config: CircuitBreakerConfig):
        """Add a new circuit breaker."""
        self.circuit_breakers[name] = CircuitBreaker(name, config)
        logger.info(f"Circuit breaker added: {name}", config=config.__dict__)
    
    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """Get circuit breaker by name."""
        if name not in self.circuit_breakers:
            logger.warning(f"Circuit breaker {name} not found, using default")
            # Create default circuit breaker
            self.add_circuit_breaker(name, CircuitBreakerConfig())
        
        return self.circuit_breakers[name]
    
    async def call_with_circuit_breaker(
        self,
        circuit_name: str,
        func: Callable,
        priority: Priority = Priority.MEDIUM,
        use_backpressure: bool = True,
        *args,
        **kwargs
    ) -> Any:
        """Execute function with circuit breaker and optional backpressure."""
        circuit_breaker = self.get_circuit_breaker(circuit_name)
        
        if use_backpressure and self.backpressure_manager:
            # Use both circuit breaker and backpressure
            # Create a synchronous wrapper that returns a task instead of a coroutine
            def circuit_breaker_wrapper():
                return asyncio.create_task(
                    circuit_breaker.call(func, *args, priority=priority, **kwargs)
                )
            
            return await self.backpressure_manager.execute_with_backpressure(
                circuit_breaker_wrapper,
                priority=priority
            )
        else:
            # Use only circuit breaker
            return await circuit_breaker.call(func, *args, priority=priority, **kwargs)
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get comprehensive stats for all circuit breakers."""
        stats = {
            "circuit_breakers": {
                name: breaker.get_stats() 
                for name, breaker in self.circuit_breakers.items()
            }
        }
        
        if self.backpressure_manager:
            stats["backpressure"] = self.backpressure_manager.get_stats()
        
        # Summary stats
        stats["summary"] = {
            "total_breakers": len(self.circuit_breakers),
            "open_breakers": [
                name for name, breaker in self.circuit_breakers.items() 
                if breaker.state == CircuitState.OPEN
            ],
            "half_open_breakers": [
                name for name, breaker in self.circuit_breakers.items()
                if breaker.state == CircuitState.HALF_OPEN
            ]
        }
        
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check of all circuit breakers."""
        health = {
            "healthy": True,
            "issues": [],
            "circuit_breakers": {},
            "backpressure": None
        }
        
        # Check each circuit breaker
        for name, breaker in self.circuit_breakers.items():
            stats = breaker.get_stats()
            cb_health = {
                "state": stats["state"],
                "healthy": stats["state"] != CircuitState.OPEN.value,
                "failure_rate": stats["failure_rate"],
                "recent_failures": stats["recent_failures"]
            }
            
            if not cb_health["healthy"]:
                health["healthy"] = False
                health["issues"].append(f"Circuit breaker {name} is OPEN")
            
            health["circuit_breakers"][name] = cb_health
        
        # Check backpressure manager
        if self.backpressure_manager:
            bp_stats = self.backpressure_manager.get_stats()
            health["backpressure"] = {
                "under_pressure": bp_stats["is_under_pressure"],
                "active_requests": bp_stats["active_requests"],
                "resource_stats": bp_stats["resource_stats"]
            }
            
            if bp_stats["is_under_pressure"]:
                health["healthy"] = False
                health["issues"].append("System under resource pressure")
        
        return health
    
    async def shutdown(self):
        """Shutdown all circuit breakers and backpressure manager."""
        logger.info("Shutting down circuit breaker manager")
        
        if self.backpressure_manager:
            await self.backpressure_manager.shutdown()
        
        logger.info("Circuit breaker manager shutdown complete")


# Custom exceptions
class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class BackpressureError(Exception):
    """Exception raised when backpressure limits are exceeded."""
    pass


# Global instance
circuit_breaker_manager = ProductionCircuitBreakerManager()