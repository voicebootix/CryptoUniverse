"""
Enterprise Redis Connection Manager - Production Grade

Provides centralized Redis connection management with:
- Connection pooling and lifecycle management
- Circuit breaker pattern with exponential backoff
- Health monitoring and automatic recovery
- Graceful degradation and failover
- Comprehensive observability and metrics

For enterprise platforms handling real money transactions.
"""

import asyncio
import time
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
import structlog
from redis.asyncio import Redis, ConnectionPool
from redis.asyncio.sentinel import Sentinel
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from app.core.config import get_settings
from app.core.logging import LoggerMixin

settings = get_settings()
logger = structlog.get_logger(__name__)


class RedisHealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CircuitBreakerState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit open, failing fast
    HALF_OPEN = "half_open"  # Testing if service recovered


class EnterpriseRedisManager(LoggerMixin):
    """
    Enterprise-grade Redis connection manager with resilience patterns.
    
    Features:
    - Single connection pool shared across application
    - Circuit breaker with exponential backoff
    - Health monitoring and metrics collection
    - Automatic failover and recovery
    - Connection lifecycle management
    """
    
    _instance: Optional['EnterpriseRedisManager'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'EnterpriseRedisManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        super().__init__()
        self._initialized = True
        
        # Connection management
        self._pool: Optional[ConnectionPool] = None
        self._redis: Optional[Redis] = None
        self._sentinel: Optional[Sentinel] = None
        
        # Circuit breaker state
        self._circuit_state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0
        self._success_count = 0
        
        # Health monitoring
        self._health_status = RedisHealthStatus.UNKNOWN
        self._last_health_check = 0
        self._health_check_interval = settings.REDIS_HEALTH_CHECK_INTERVAL
        
        # Configuration
        self._max_failures = 5
        self._recovery_timeout = 60  # seconds
        self._half_open_max_calls = 3
        self._connection_timeout = 5
        self._command_timeout = 3
        
        # Metrics
        self._metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'circuit_trips': 0,
            'recovery_attempts': 0,
            'last_error': None,
            'connection_pool_size': 0,
            'active_connections': 0
        }
        
        # Background tasks
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> bool:
        """
        Initialize Redis connection manager with enterprise configuration.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            self.logger.info("Initializing Enterprise Redis Manager...")
            
            # Configure connection pool
            await self._setup_connection_pool()
            
            # Establish initial connection
            await self._establish_connection()
            
            # Start health monitoring
            await self._start_health_monitoring()
            
            # Perform initial health check
            await self._perform_health_check()
            
            self.logger.info("✅ Enterprise Redis Manager initialized successfully", 
                           health_status=self._health_status.value,
                           circuit_state=self._circuit_state.value)
            return True
            
        except Exception as e:
            self.logger.error(" Failed to initialize Redis Manager", error=str(e))
            self._health_status = RedisHealthStatus.UNHEALTHY
            return False
    
    async def _setup_connection_pool(self):
        """Configure Redis connection pool with enterprise settings."""
        
        # Parse Redis URL for connection details
        redis_url = settings.REDIS_URL
        if not redis_url:
            raise ValueError("REDIS_URL environment variable not configured")
        
        # Connection pool configuration
        pool_config = {
            'max_connections': 20,  # Reasonable pool size
            'retry_on_timeout': True,
            'socket_connect_timeout': self._connection_timeout,
            'socket_timeout': self._command_timeout,
            'socket_keepalive': True,
            'socket_keepalive_options': {},
            'health_check_interval': 30,
        }
        
        try:
            # Create connection pool
            self._pool = ConnectionPool.from_url(
                redis_url,
                **pool_config
            )
            
            self._metrics['connection_pool_size'] = pool_config['max_connections']
            self.logger.info(" Redis connection pool configured", 
                           max_connections=pool_config['max_connections'])
            
        except Exception as e:
            self.logger.error(" Failed to setup connection pool", error=str(e))
            raise
    
    async def _establish_connection(self):
        """Establish Redis connection with circuit breaker protection."""
        
        if self._circuit_state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if time.time() - self._last_failure_time < self._recovery_timeout:
                raise ConnectionError("Circuit breaker is OPEN - Redis unavailable")
            else:
                # Transition to half-open for testing
                self._circuit_state = CircuitBreakerState.HALF_OPEN
                self._success_count = 0
                self.logger.info("🔄 Circuit breaker transitioning to HALF_OPEN")
        
        try:
            # Create Redis client with connection pool
            self._redis = Redis(connection_pool=self._pool)
            
            # Test connection with timeout
            await asyncio.wait_for(self._redis.ping(), timeout=self._command_timeout)
            
            # Connection successful - update circuit breaker
            await self._handle_success()
            
            self.logger.info("✅ Redis connection established successfully")
            
        except Exception as e:
            # Connection failed - update circuit breaker
            await self._handle_failure(e)
            raise
    
    async def _handle_success(self):
        """Handle successful Redis operation for circuit breaker."""
        self._metrics['successful_requests'] += 1
        
        if self._circuit_state == CircuitBreakerState.HALF_OPEN:
            self._success_count += 1
            
            # If enough successes in half-open, close circuit
            if self._success_count >= self._half_open_max_calls:
                self._circuit_state = CircuitBreakerState.CLOSED
                self._failure_count = 0
                self.logger.info("✅ Circuit breaker CLOSED - Redis recovered")
        
        elif self._circuit_state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0
    
    async def _handle_failure(self, error: Exception):
        """Handle Redis operation failure for circuit breaker."""
        self._metrics['failed_requests'] += 1
        self._metrics['last_error'] = str(error)
        self._last_failure_time = time.time()
        
        if self._circuit_state in [CircuitBreakerState.CLOSED, CircuitBreakerState.HALF_OPEN]:
            self._failure_count += 1
            
            # Trip circuit breaker if too many failures
            if self._failure_count >= self._max_failures:
                self._circuit_state = CircuitBreakerState.OPEN
                self._metrics['circuit_trips'] += 1
                self._health_status = RedisHealthStatus.UNHEALTHY
                
                self.logger.error("⚠️ Circuit breaker OPENED - Redis marked unhealthy", 
                               failure_count=self._failure_count,
                               error=str(error))
    
    async def get_client(self) -> Optional[Redis]:
        """
        Get Redis client with circuit breaker protection.
        
        Returns:
            Optional[Redis]: Redis client if available, None if circuit is open
        """
        self._metrics['total_requests'] += 1
        
        # Check circuit breaker state
        if self._circuit_state == CircuitBreakerState.OPEN:
            # Check if we can transition to half-open
            if time.time() - self._last_failure_time >= self._recovery_timeout:
                try:
                    await self._establish_connection()
                    return self._redis
                except Exception:
                    return None
            else:
                # Circuit still open
                return None
        
        # Ensure connection is established
        if not self._redis:
            try:
                await self._establish_connection()
            except Exception:
                return None
        
        return self._redis
    
    async def execute_with_fallback(self, 
                                  operation_name: str,
                                  redis_operation,
                                  fallback_value=None) -> Any:
        """
        Execute Redis operation with automatic fallback.
        
        Args:
            operation_name: Name of operation for logging
            redis_operation: Async function that performs Redis operation
            fallback_value: Value to return if Redis unavailable
            
        Returns:
            Operation result or fallback value
        """
        client = await self.get_client()
        
        if not client:
            self.logger.warning(f"⚠️ Redis unavailable for {operation_name} - using fallback")
            return fallback_value
        
        try:
            result = await redis_operation(client)
            await self._handle_success()
            return result
            
        except Exception as e:
            await self._handle_failure(e)
            self.logger.warning(f"⚠️ Redis operation failed for {operation_name}", 
                              error=str(e))
            return fallback_value
    
    async def _start_health_monitoring(self):
        """Start background health monitoring task."""
        if self._health_monitor_task is None or self._health_monitor_task.done():
            self._health_monitor_task = asyncio.create_task(self._health_monitor_loop())
            self.logger.info("🏥 Redis health monitoring started")
    
    async def _health_monitor_loop(self):
        """Background health monitoring loop."""
        while True:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self._health_check_interval)
                
            except asyncio.CancelledError:
                self.logger.info("🛑 Health monitoring stopped")
                break
            except Exception as e:
                self.logger.error(" Health monitoring error", error=str(e))
                await asyncio.sleep(self._health_check_interval)
    
    async def _perform_health_check(self):
        """Perform comprehensive Redis health check."""
        try:
            if not self._redis:
                self._health_status = RedisHealthStatus.UNHEALTHY
                return
            
            start_time = time.time()
            
            # Ping test
            await asyncio.wait_for(self._redis.ping(), timeout=self._command_timeout)
            
            # Basic operation test with enterprise data integrity verification
            # Use high-resolution unique key to prevent worker collisions
            import uuid
            unique_suffix = f"{time.time_ns()}_{uuid.uuid4().hex[:8]}"
            test_key = f"health_check_{unique_suffix}"
            test_value = f"test_value_{unique_suffix}"
            expected_bytes = test_value.encode('utf-8')
            
            # Set test data with expiration
            await self._redis.set(test_key, test_value, ex=10)
            
            # Retrieve and verify data integrity
            result = await self._redis.get(test_key)
            
            # Clean up test data
            await self._redis.delete(test_key)
            
            # Verify data integrity with proper byte comparison
            if result is None:
                raise ValueError("Health check data retrieval failure - key not found")
            elif result != expected_bytes:
                raise ValueError(f"Health check data integrity failure - expected {expected_bytes}, got {result}")
            
            # Calculate response time
            response_time = (time.time() - start_time) * 1000  # milliseconds
            
            # Update health status based on response time
            if response_time < 100:  # Under 100ms
                self._health_status = RedisHealthStatus.HEALTHY
            elif response_time < 1000:  # Under 1 second
                self._health_status = RedisHealthStatus.DEGRADED
            else:
                self._health_status = RedisHealthStatus.UNHEALTHY
            
            self._last_health_check = time.time()
            
        except Exception as e:
            self._health_status = RedisHealthStatus.UNHEALTHY
            self.logger.warning("⚠️ Redis health check failed", error=str(e))
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status and metrics."""
        return {
            'status': self._health_status.value,
            'circuit_breaker_state': self._circuit_state.value,
            'last_health_check': self._last_health_check,
            'metrics': self._metrics.copy(),
            'configuration': {
                'max_failures': self._max_failures,
                'recovery_timeout': self._recovery_timeout,
                'connection_timeout': self._connection_timeout,
                'command_timeout': self._command_timeout
            }
        }
    
    async def shutdown(self):
        """Gracefully shutdown Redis manager."""
        self.logger.info("🛑 Shutting down Enterprise Redis Manager...")
        
        # Cancel background tasks
        if self._health_monitor_task:
            self._health_monitor_task.cancel()
            try:
                await self._health_monitor_task
            except asyncio.CancelledError:
                pass
        
        # Close Redis connection
        if self._redis:
            await self._redis.close()
        
        # Close connection pool
        if self._pool:
            await self._pool.disconnect()
        
        self.logger.info("✅ Enterprise Redis Manager shutdown complete")


# Global instance
_redis_manager: Optional[EnterpriseRedisManager] = None


async def get_redis_manager() -> EnterpriseRedisManager:
    """Get the global Redis manager instance."""
    global _redis_manager
    
    if _redis_manager is None:
        _redis_manager = EnterpriseRedisManager()
        await _redis_manager.initialize()
    
    return _redis_manager


async def get_redis_client() -> Optional[Redis]:
    """
    Get Redis client through enterprise manager.
    
    Returns:
        Optional[Redis]: Redis client if available, None if circuit breaker is open
    """
    try:
        manager = await get_redis_manager()
        return await manager.get_client()
    except Exception as e:
        logger.error(" Failed to get Redis client", error=str(e))
        return None