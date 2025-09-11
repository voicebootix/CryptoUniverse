"""
MarketDataCoordinator - Request Deduplication and Batching Service

Enterprise-grade service for coordinating market data requests across the system.
Prevents duplicate API calls, batches requests, and implements intelligent caching.
"""

import asyncio
import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set, Optional, Any, Tuple, TYPE_CHECKING
from collections import defaultdict
import structlog
import redis
from app.core.config import get_settings

if TYPE_CHECKING:
    from app.services.master_controller import MasterSystemController

settings = get_settings()
logger = structlog.get_logger(__name__)


class MarketDataCoordinator:
    """
    ENTERPRISE MARKET DATA COORDINATION
    
    Features:
    - Request deduplication
    - Intelligent batching
    - Cache management
    - Rate limiting coordination
    - API call optimization
    """
    
    def __init__(self, master_controller: Optional['MasterSystemController'] = None):
        # SSL/TLS configuration for production
        ssl_config = {}
        if getattr(settings, 'redis_use_ssl', False):
            ssl_config.update({
                'ssl': True,
                'ssl_cert_reqs': getattr(settings, 'redis_ssl_cert_reqs', None),
                'ssl_ca_certs': getattr(settings, 'redis_ssl_ca_certs', None),
                'ssl_certfile': getattr(settings, 'redis_ssl_certfile', None),
                'ssl_keyfile': getattr(settings, 'redis_ssl_keyfile', None)
            })
            
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            decode_responses=False,  # Preserve binary data
            **ssl_config
        )
        self.master_controller = master_controller
        
        # Request tracking
        self.active_requests: Dict[str, asyncio.Event] = {}
        self.request_results: Dict[str, Any] = {}
        self.batch_queues: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.batch_timers: Dict[str, asyncio.Task] = {}
        self._cleanup_tasks: Dict[str, asyncio.Task] = {}
        
        # Configuration
        self.cache_ttl = {
            'prices': 30,           # 30 seconds for price data
            'technical': 300,       # 5 minutes for technical analysis
            'sentiment': 600,       # 10 minutes for sentiment
            'arbitrage': 60,        # 1 minute for arbitrage
            'flows': 900,           # 15 minutes for institutional flows
            'overview': 300         # 5 minutes for market overview
        }
        
        self.batch_config = {
            'max_batch_size': 20,
            'batch_timeout': 2.0,   # 2 seconds
            'min_batch_size': 3
        }
        
        # Statistics
        self.stats = {
            'requests_deduplicated': 0,
            'batches_created': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'api_calls_saved': 0,
            'total_requests': 0
        }
        
        logger.info("✅ MarketDataCoordinator initialized with enterprise features")
    
    def _generate_request_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate unique key for request deduplication."""
        
        # Sort parameters for consistent keys
        sorted_params = sorted(params.items()) if params else []
        param_str = json.dumps(sorted_params, sort_keys=True)
        
        # Use cryptographic hash for collision resistance
        param_hash = hashlib.sha256(param_str.encode('utf-8')).hexdigest()[:16]
        return f"req:{endpoint}:{param_hash}"
    
    def _generate_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate cache key for storing results."""
        
        sorted_params = sorted(params.items()) if params else []
        param_str = json.dumps(sorted_params, sort_keys=True)
        
        return f"cache:{endpoint}:{hash(param_str)}"
    
    def _get_cache_ttl(self, endpoint: str) -> int:
        """Get appropriate cache TTL based on endpoint type."""
        
        if 'price' in endpoint or 'realtime' in endpoint:
            return self.cache_ttl['prices']
        elif 'technical' in endpoint:
            return self.cache_ttl['technical']
        elif 'sentiment' in endpoint:
            return self.cache_ttl['sentiment']
        elif 'arbitrage' in endpoint:
            return self.cache_ttl['arbitrage']
        elif 'flow' in endpoint or 'institutional' in endpoint:
            return self.cache_ttl['flows']
        elif 'overview' in endpoint or 'market' in endpoint:
            return self.cache_ttl['overview']
        else:
            return 300  # Default 5 minutes
    
    async def coordinate_request(
        self, 
        endpoint: str, 
        params: Dict[str, Any],
        force_refresh: bool = False,
        batchable: bool = True
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        COORDINATE MARKET DATA REQUEST
        
        Main coordination method that handles:
        - Cache checking
        - Request deduplication
        - Batching optimization
        - Result distribution
        """
        
        self.stats['total_requests'] += 1
        
        request_key = self._generate_request_key(endpoint, params)
        cache_key = self._generate_cache_key(endpoint, params)
        
        # Step 1: Check cache if not forcing refresh
        if not force_refresh:
            cached_result = await self._check_cache(cache_key)
            if cached_result:
                self.stats['cache_hits'] += 1
                return cached_result, {
                    'source': 'cache',
                    'cache_hit': True,
                    'request_key': request_key
                }
        
        self.stats['cache_misses'] += 1
        
        # Step 2: Check for duplicate active requests
        if request_key in self.active_requests:
            logger.debug(f"Duplicate request detected, waiting for result", request_key=request_key)
            self.stats['requests_deduplicated'] += 1
            
            # Wait for the active request to complete
            await self.active_requests[request_key].wait()
            
            # Get the result
            result = self.request_results.get(request_key)
            if result:
                return result, {
                    'source': 'deduplicated',
                    'cache_hit': False,
                    'request_key': request_key
                }
        
        # Step 3: Handle batching for eligible requests
        if batchable and self._is_batchable(endpoint):
            return await self._handle_batched_request(endpoint, params, request_key, cache_key)
        
        # Step 4: Execute individual request
        return await self._execute_individual_request(endpoint, params, request_key, cache_key)
    
    async def _check_cache(self, cache_key: str) -> Optional[Any]:
        """Check Redis cache for existing result."""
        
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                result = json.loads(cached_data)
                
                # Check if cache is still valid
                if 'cached_at' in result:
                    cached_at = datetime.fromisoformat(result['cached_at'])
                    # Ensure cached_at is timezone-aware
                    if cached_at.tzinfo is None:
                        cached_at = cached_at.replace(tzinfo=timezone.utc)
                    
                    current_time = datetime.now(timezone.utc)
                    if current_time - cached_at < timedelta(seconds=result.get('ttl', 300)):
                        logger.debug(f"Cache hit", cache_key=cache_key)
                        return result['data']
                
                # Cache expired, remove it
                self.redis_client.delete(cache_key)
            
        except Exception as e:
            logger.warning(f"Cache check failed", cache_key=cache_key, error=str(e))
        
        return None
    
    async def _store_in_cache(self, cache_key: str, data: Any, ttl: int):
        """Store result in Redis cache."""
        
        try:
            cache_data = {
                'data': data,
                'cached_at': datetime.now(timezone.utc).isoformat(),
                'ttl': ttl
            }
            
            self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(cache_data, default=str)
            )
            
            logger.debug(f"Cached result", cache_key=cache_key, ttl=ttl)
            
        except Exception as e:
            logger.warning(f"Cache storage failed", cache_key=cache_key, error=str(e))
    
    def _is_batchable(self, endpoint: str) -> bool:
        """Determine if endpoint supports batching."""
        
        batchable_endpoints = {
            'realtime-prices',
            'technical-analysis', 
            'sentiment-analysis',
            'volatility-analysis',
            'support-resistance'
        }
        
        return any(batch_endpoint in endpoint for batch_endpoint in batchable_endpoints)
    
    async def _handle_batched_request(
        self, 
        endpoint: str, 
        params: Dict[str, Any], 
        request_key: str, 
        cache_key: str
    ) -> Tuple[Any, Dict[str, Any]]:
        """Handle request that can be batched with others."""
        
        batch_type = self._get_batch_type(endpoint)
        
        # Add request to batch queue
        batch_request = {
            'endpoint': endpoint,
            'params': params,
            'request_key': request_key,
            'cache_key': cache_key,
            'timestamp': time.time()
        }
        
        self.batch_queues[batch_type].append(batch_request)
        
        # Create event for this request
        event = asyncio.Event()
        self.active_requests[request_key] = event
        
        # Start batch timer if not already running
        if batch_type not in self.batch_timers:
            self.batch_timers[batch_type] = asyncio.create_task(
                self._batch_timer(batch_type)
            )
        
        # Check if batch is ready to execute
        if len(self.batch_queues[batch_type]) >= self.batch_config['max_batch_size']:
            await self._execute_batch(batch_type)
        
        # Wait for batch result
        await event.wait()
        
        result = self.request_results.get(request_key)
        return result, {
            'source': 'batched',
            'cache_hit': False,
            'request_key': request_key,
            'batch_type': batch_type
        }
    
    def _get_batch_type(self, endpoint: str) -> str:
        """Get batch type based on endpoint."""
        
        if 'price' in endpoint:
            return 'prices'
        elif 'technical' in endpoint:
            return 'technical'
        elif 'sentiment' in endpoint:
            return 'sentiment'
        elif 'volatility' in endpoint:
            return 'volatility'
        else:
            return 'general'
    
    async def _batch_timer(self, batch_type: str):
        """Timer to execute batch after timeout."""
        
        await asyncio.sleep(self.batch_config['batch_timeout'])
        
        if (batch_type in self.batch_queues and 
            len(self.batch_queues[batch_type]) >= self.batch_config['min_batch_size']):
            await self._execute_batch(batch_type)
        
        # Remove timer
        if batch_type in self.batch_timers:
            del self.batch_timers[batch_type]
    
    async def _execute_batch(self, batch_type: str):
        """Execute a batch of requests."""
        
        if batch_type not in self.batch_queues or not self.batch_queues[batch_type]:
            return
        
        requests = self.batch_queues[batch_type].copy()
        self.batch_queues[batch_type].clear()
        
        # Cancel timer if running (avoid deadlock)
        if batch_type in self.batch_timers:
            timer_task = self.batch_timers[batch_type]
            if not timer_task.done():
                timer_task.cancel()
                try:
                    await asyncio.wait_for(timer_task, timeout=1.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass  # Expected when cancelling
            del self.batch_timers[batch_type]
        
        logger.info(f"Executing batch", batch_type=batch_type, requests=len(requests))
        self.stats['batches_created'] += 1
        
        try:
            # Group requests by endpoint and combine parameters
            endpoint_groups = defaultdict(list)
            for req in requests:
                endpoint_groups[req['endpoint']].append(req)
            
            # Execute each endpoint group
            for endpoint, endpoint_requests in endpoint_groups.items():
                await self._execute_endpoint_batch(endpoint, endpoint_requests)
                
        except Exception as e:
            logger.error(f"Batch execution failed", batch_type=batch_type, error=str(e))
            
            # Set error for all requests in batch
            for req in requests:
                self.request_results[req['request_key']] = {
                    'success': False,
                    'error': str(e),
                    'pipeline_results': {}
                }
                
                if req['request_key'] in self.active_requests:
                    self.active_requests[req['request_key']].set()
    
    async def _execute_endpoint_batch(self, endpoint: str, requests: List[Dict[str, Any]]):
        """Execute a batch of requests for the same endpoint."""
        
        # Use injected master controller or create one
        master_controller = self.master_controller
        if not master_controller:
            from app.services.master_controller import MasterSystemController
            master_controller = MasterSystemController()
        
        # Combine symbols from all requests
        all_symbols = set()
        combined_params = {}
        
        for req in requests:
            params = req['params']
            if 'symbols' in params:
                symbols = params['symbols']
                if isinstance(symbols, str):
                    all_symbols.update(symbols.split(','))
                elif isinstance(symbols, list):
                    all_symbols.update(symbols)
            
            # Merge other parameters (use first request's params as base)
            if not combined_params:
                combined_params = params.copy()
        
        # Update symbols with combined set
        combined_params['symbols'] = ','.join(all_symbols)
        
        try:
            # Execute pipeline request
            result = await master_controller.trigger_pipeline(**combined_params)
            
            self.stats['api_calls_saved'] += len(requests) - 1  # Saved n-1 API calls
            
            # Distribute results to individual requests
            for req in requests:
                individual_result = self._extract_individual_result(result, req['params'])
                
                # Cache individual result
                ttl = self._get_cache_ttl(endpoint)
                await self._store_in_cache(req['cache_key'], individual_result, ttl)
                
                # Store result and notify waiting coroutine
                self.request_results[req['request_key']] = individual_result
                
                if req['request_key'] in self.active_requests:
                    self.active_requests[req['request_key']].set()
            
        except Exception as e:
            logger.error(f"Endpoint batch execution failed", endpoint=endpoint, error=str(e))
            
            # Set error for all requests
            error_result = {
                'success': False,
                'error': str(e),
                'pipeline_results': {}
            }
            
            for req in requests:
                self.request_results[req['request_key']] = error_result
                
                if req['request_key'] in self.active_requests:
                    self.active_requests[req['request_key']].set()
    
    def _extract_individual_result(self, batch_result: Dict[str, Any], individual_params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract individual result from batch result."""
        
        # For now, return the full batch result
        # In a more sophisticated implementation, we would filter based on individual_params
        return batch_result
    
    async def _execute_individual_request(
        self, 
        endpoint: str, 
        params: Dict[str, Any], 
        request_key: str, 
        cache_key: str
    ) -> Tuple[Any, Dict[str, Any]]:
        """Execute individual request (not batched)."""
        
        # Import here to avoid circular imports
        from app.services.master_controller import MasterSystemController
        
        # Create event for this request
        event = asyncio.Event()
        self.active_requests[request_key] = event
        
        try:
            master_controller = MasterSystemController()
            
            # Execute pipeline request
            result = await master_controller.trigger_pipeline(**params)
            
            # Cache result
            ttl = self._get_cache_ttl(endpoint)
            await self._store_in_cache(cache_key, result, ttl)
            
            # Store result and notify
            self.request_results[request_key] = result
            event.set()
            
            return result, {
                'source': 'individual',
                'cache_hit': False,
                'request_key': request_key
            }
            
        except Exception as e:
            logger.error(f"Individual request failed", endpoint=endpoint, error=str(e))
            
            error_result = {
                'success': False,
                'error': str(e),
                'pipeline_results': {}
            }
            
            self.request_results[request_key] = error_result
            event.set()
            
            return error_result, {
                'source': 'individual',
                'cache_hit': False,
                'request_key': request_key,
                'error': str(e)
            }
        
        finally:
            # Clean up
            if request_key in self.active_requests:
                del self.active_requests[request_key]
            if request_key in self.request_results:
                # Keep result for a short time in case of duplicate requests
                cleanup_task = asyncio.create_task(self._cleanup_result(request_key, delay=30))
                self._cleanup_tasks[request_key] = cleanup_task
                cleanup_task.add_done_callback(lambda t, k=request_key: self._cleanup_tasks.pop(k, None))
    
    async def _cleanup_result(self, request_key: str, delay: int = 30):
        """Clean up stored result after delay."""
        
        await asyncio.sleep(delay)
        if request_key in self.request_results:
            del self.request_results[request_key]
    
    async def invalidate_cache(self, pattern: str = None, max_keys: int = 1000, require_confirmation: bool = False):
        """Invalidate cache entries with safety checks and limits."""
        
        try:
            # Validate and sanitize pattern
            if pattern:
                # Reject overly broad or unsafe patterns
                import re
                if not pattern or len(pattern) < 3 or pattern in ['*', '**', 'cache:*']:
                    raise ValueError(f"Pattern too broad or unsafe: {pattern}")
                    
                if not re.match(r'^[A-Za-z0-9_:-]+$', pattern):
                    raise ValueError(f"Pattern contains invalid characters: {pattern}")
                    
                cache_pattern = f"cache:{pattern}*"
            else:
                if not require_confirmation:
                    raise ValueError("Deleting all cache entries requires explicit confirmation")
                cache_pattern = "cache:*"
                
            # Use SCAN to safely count matching keys first
            key_count = 0
            cursor = 0
            
            # Count phase
            while True:
                cursor, keys = self.redis_client.scan(cursor, match=cache_pattern, count=100)
                key_count += len(keys)
                if key_count > max_keys:
                    raise ValueError(f"Too many keys to delete: {key_count} > {max_keys}")
                if cursor == 0:
                    break
            
            if key_count == 0:
                logger.info(f"No cache entries found matching pattern", pattern=cache_pattern)
                return 0
                
            # Deletion phase - delete in small batches
            deleted_count = 0
            cursor = 0
            batch_size = 100
            
            while True:
                cursor, keys = self.redis_client.scan(cursor, match=cache_pattern, count=batch_size)
                if keys:
                    # Delete in smaller batches to avoid blocking Redis
                    for i in range(0, len(keys), batch_size):
                        batch = keys[i:i + batch_size]
                        self.redis_client.delete(*batch)
                        deleted_count += len(batch)
                        
                if cursor == 0:
                    break
                    
            logger.info(f"Cache invalidation completed", 
                       pattern=cache_pattern, 
                       deleted_count=deleted_count,
                       max_keys_limit=max_keys)
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cache invalidation failed", pattern=pattern, error=str(e))
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get coordination statistics."""
        
        return {
            **self.stats,
            'active_requests': len(self.active_requests),
            'cached_results': len(self.request_results),
            'batch_queues': {k: len(v) for k, v in self.batch_queues.items()},
            'cache_hit_rate': (
                self.stats['cache_hits'] / (self.stats['cache_hits'] + self.stats['cache_misses'])
                if (self.stats['cache_hits'] + self.stats['cache_misses']) > 0 else 0
            ),
            'deduplication_rate': (
                self.stats['requests_deduplicated'] / self.stats['total_requests']
                if self.stats['total_requests'] > 0 else 0
            )
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        
        try:
            # Check Redis connectivity (non-blocking async version)
            # Note: This assumes we'll convert to async Redis client later
            # For now, use the synchronous version but in a way that won't block too long
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.redis_client.ping)
            redis_status = 'healthy'
        except Exception as e:
            redis_status = f'error: {str(e)}'
        
        stats = self.get_stats()
        
        return {
            'status': 'healthy' if redis_status == 'healthy' else 'degraded',
            'redis_status': redis_status,
            'statistics': stats,
            'uptime': time.time(),
            'last_updated': datetime.utcnow().isoformat()
        }
    
    async def shutdown(self):
        """Cleanup resources during shutdown."""
        
        # Cancel all batch timers
        for batch_type, timer_task in list(self.batch_timers.items()):
            if not timer_task.done():
                timer_task.cancel()
                try:
                    await asyncio.wait_for(timer_task, timeout=1.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
        self.batch_timers.clear()
        
        # Cancel and await cleanup tasks
        for request_key, cleanup_task in list(self._cleanup_tasks.items()):
            if not cleanup_task.done():
                cleanup_task.cancel()
                try:
                    await asyncio.wait_for(cleanup_task, timeout=1.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
        self._cleanup_tasks.clear()
        
        logger.info("MarketDataCoordinator shutdown complete")


# Global coordinator instance
market_data_coordinator = MarketDataCoordinator()