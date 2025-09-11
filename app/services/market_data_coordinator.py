"""
MarketDataCoordinator - Request Deduplication and Batching Service

Enterprise-grade service for coordinating market data requests across the system.
Prevents duplicate API calls, batches requests, and implements intelligent caching.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any, Tuple
from collections import defaultdict
import structlog
import redis
from app.core.config import get_settings

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
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            decode_responses=True
        )
        
        # Request tracking
        self.active_requests: Dict[str, asyncio.Event] = {}
        self.request_results: Dict[str, Any] = {}
        self.batch_queues: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.batch_timers: Dict[str, asyncio.Task] = {}
        
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
        
        return f"req:{endpoint}:{hash(param_str)}"
    
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
                    if datetime.utcnow() - cached_at < timedelta(seconds=result.get('ttl', 300)):
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
                'cached_at': datetime.utcnow().isoformat(),
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
        
        # Cancel timer if running
        if batch_type in self.batch_timers:
            self.batch_timers[batch_type].cancel()
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
        
        # Import here to avoid circular imports
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
                asyncio.create_task(self._cleanup_result(request_key, delay=30))
    
    async def _cleanup_result(self, request_key: str, delay: int = 30):
        """Clean up stored result after delay."""
        
        await asyncio.sleep(delay)
        if request_key in self.request_results:
            del self.request_results[request_key]
    
    async def invalidate_cache(self, pattern: str = None):
        """Invalidate cache entries."""
        
        try:
            if pattern:
                keys = self.redis_client.keys(f"cache:{pattern}*")
            else:
                keys = self.redis_client.keys("cache:*")
            
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Invalidated cache entries", count=len(keys), pattern=pattern)
            
        except Exception as e:
            logger.error(f"Cache invalidation failed", error=str(e))
    
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
            # Check Redis connectivity
            self.redis_client.ping()
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


# Global coordinator instance
market_data_coordinator = MarketDataCoordinator()