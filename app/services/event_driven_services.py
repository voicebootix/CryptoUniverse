"""
Event-Driven Services Architecture for CryptoUniverse
Replaces polling-based background services with Redis Streams for real-time event processing.
Based on production crypto trading system patterns.
"""

import asyncio
import json
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum

import structlog
from app.core.config import get_settings
from app.core.redis import get_redis_client
from app.core.logging import LoggerMixin

settings = get_settings()
logger = structlog.get_logger(__name__)


class ServicePriority(Enum):
    CRITICAL = "critical"       # Trading execution, risk monitoring
    IMPORTANT = "important"     # Portfolio sync, balance updates
    BACKGROUND = "background"   # Analytics, cleanup


class EventType(Enum):
    PRICE_UPDATE = "price_update"
    TRADE_SIGNAL = "trade_signal"
    PORTFOLIO_CHANGE = "portfolio_change"
    RISK_ALERT = "risk_alert"
    SYSTEM_HEALTH = "system_health"
    BALANCE_UPDATE = "balance_update"


class EventDrivenServiceManager(LoggerMixin):
    """Production-grade event-driven service manager using Redis Streams."""
    
    def __init__(self):
        self.redis = None
        self.running = False
        self.consumer_tasks = {}
        self.service_configs = {}
        self.resource_monitor = ResourceMonitor()
        
        # Redis Streams configuration
        self.streams = {
            # Critical real-time streams
            "trade_signals": {
                "max_len": 50000,
                "ttl": 1800,  # 30 minutes
                "consumer_group": "trading_services",
                "priority": ServicePriority.CRITICAL
            },
            "risk_alerts": {
                "max_len": 10000,
                "ttl": 900,   # 15 minutes
                "consumer_group": "risk_services",
                "priority": ServicePriority.CRITICAL
            },
            
            # Important business logic streams
            "market_updates": {
                "max_len": 100000,
                "ttl": 3600,  # 1 hour
                "consumer_group": "market_services",
                "priority": ServicePriority.IMPORTANT
            },
            "portfolio_changes": {
                "max_len": 25000,
                "ttl": 1800,  # 30 minutes
                "consumer_group": "portfolio_services",
                "priority": ServicePriority.IMPORTANT
            },
            "balance_updates": {
                "max_len": 20000,
                "ttl": 1800,  # 30 minutes
                "consumer_group": "balance_services",
                "priority": ServicePriority.IMPORTANT
            },
            
            # Background processing streams
            "system_events": {
                "max_len": 15000,
                "ttl": 7200,  # 2 hours
                "consumer_group": "system_services",
                "priority": ServicePriority.BACKGROUND
            },
            "cleanup_events": {
                "max_len": 5000,
                "ttl": 14400, # 4 hours
                "consumer_group": "cleanup_services", 
                "priority": ServicePriority.BACKGROUND
            }
        }
        
        # Service definitions with adaptive intervals
        self.services = {
            # Critical services - primarily event-driven
            "trade_execution": {
                "stream": "trade_signals",
                "handler": self._handle_trade_execution,
                "priority": ServicePriority.CRITICAL,
                "fallback_interval": 1,  # 1 second emergency fallback
                "batch_size": 1,         # Process immediately
                "timeout": 100           # 100ms processing timeout
            },
            "risk_monitor": {
                "stream": "portfolio_changes",
                "handler": self._handle_risk_monitoring,
                "priority": ServicePriority.CRITICAL,
                "fallback_interval": 5,  # 5 second fallback
                "batch_size": 5,
                "timeout": 500
            },
            
            # Important services - hybrid event/polling
            "portfolio_sync": {
                "stream": "market_updates",
                "handler": self._handle_portfolio_sync,
                "priority": ServicePriority.IMPORTANT,
                "fallback_interval": 120,  # 2 minute fallback
                "batch_size": 10,
                "timeout": 2000
            },
            "balance_sync": {
                "stream": "balance_updates",
                "handler": self._handle_balance_sync,
                "priority": ServicePriority.IMPORTANT,
                "fallback_interval": 300,  # 5 minute fallback
                "batch_size": 15,
                "timeout": 3000
            },
            "market_data_processor": {
                "stream": "market_updates",
                "handler": self._handle_market_data,
                "priority": ServicePriority.IMPORTANT,
                "fallback_interval": 60,   # 1 minute fallback
                "batch_size": 25,
                "timeout": 1500
            },
            
            # Background services - adaptive polling with event triggers
            "health_monitor": {
                "stream": "system_events",
                "handler": self._handle_health_monitoring,
                "priority": ServicePriority.BACKGROUND,
                "fallback_interval": 300,  # 5 minute fallback (vs 60s polling)
                "batch_size": 20,
                "timeout": 5000
            },
            "cleanup_service": {
                "stream": "cleanup_events",
                "handler": self._handle_cleanup,
                "priority": ServicePriority.BACKGROUND,
                "fallback_interval": 3600, # 1 hour fallback (vs polling every hour)
                "batch_size": 50,
                "timeout": 10000
            },
            "metrics_collector": {
                "stream": "system_events", 
                "handler": self._handle_metrics_collection,
                "priority": ServicePriority.BACKGROUND,
                "fallback_interval": 600,  # 10 minute fallback (vs 5min polling)
                "batch_size": 30,
                "timeout": 8000
            }
        }
    
    async def initialize(self):
        """Initialize Redis connection and setup consumer groups."""
        try:
            self.redis = await get_redis_client()
            if not self.redis:
                raise Exception("Redis client unavailable")
            
            # Setup consumer groups for each stream
            await self._setup_consumer_groups()
            
            # Initialize resource monitoring
            await self.resource_monitor.initialize()
            
            logger.info("Event-driven service manager initialized", 
                       streams=len(self.streams),
                       services=len(self.services))
            
        except Exception as e:
            logger.error("Failed to initialize event-driven services", error=str(e))
            raise
    
    async def _setup_consumer_groups(self):
        """Setup Redis consumer groups for each stream."""
        for stream_name, config in self.streams.items():
            try:
                await self.redis.xgroup_create(
                    stream_name, 
                    config["consumer_group"], 
                    id="0", 
                    mkstream=True
                )
                logger.debug(f"Created consumer group for {stream_name}")
                
            except Exception as e:
                if "BUSYGROUP" in str(e):
                    logger.debug(f"Consumer group already exists for {stream_name}")
                else:
                    logger.warning(f"Failed to create consumer group for {stream_name}", error=str(e))
    
    async def start_all_services(self):
        """Start all event-driven services with adaptive intervals."""
        if self.running:
            logger.warning("Services already running")
            return
        
        self.running = True
        logger.info("Starting event-driven services")
        
        # Start resource monitoring first
        resource_task = asyncio.create_task(
            self.resource_monitor.start_monitoring()
        )
        self.consumer_tasks["resource_monitor"] = resource_task
        
        # Start services by priority
        priority_order = [ServicePriority.CRITICAL, ServicePriority.IMPORTANT, ServicePriority.BACKGROUND]
        
        for priority in priority_order:
            services_for_priority = {
                name: config for name, config in self.services.items() 
                if config["priority"] == priority
            }
            
            for service_name, service_config in services_for_priority.items():
                try:
                    # Start event consumer
                    consumer_task = asyncio.create_task(
                        self._run_event_consumer(service_name, service_config)
                    )
                    self.consumer_tasks[service_name] = consumer_task
                    
                    # Start adaptive fallback poller
                    fallback_task = asyncio.create_task(
                        self._run_adaptive_fallback(service_name, service_config)
                    )
                    self.consumer_tasks[f"{service_name}_fallback"] = fallback_task
                    
                    logger.info(f"Started {service_name} service", priority=priority.value)
                    
                    # Stagger service starts to avoid resource spikes
                    if priority == ServicePriority.CRITICAL:
                        await asyncio.sleep(0.1)  # 100ms stagger for critical
                    else:
                        await asyncio.sleep(0.5)  # 500ms stagger for others
                        
                except Exception as e:
                    logger.error(f"Failed to start {service_name}", error=str(e))
        
        logger.info("All event-driven services started", 
                   active_tasks=len(self.consumer_tasks))
    
    async def _run_event_consumer(self, service_name: str, config: Dict):
        """Run event consumer for a specific service."""
        stream_name = config["stream"]
        consumer_group = self.streams[stream_name]["consumer_group"]
        consumer_name = f"{service_name}_{int(time.time())}"
        
        logger.info(f"Starting event consumer for {service_name}", 
                   stream=stream_name, consumer_group=consumer_group)
        
        while self.running:
            try:
                # Check system resources before processing
                if not await self._can_process_events(config["priority"]):
                    await asyncio.sleep(1)
                    continue
                
                # Read events from stream
                messages = await self.redis.xreadgroup(
                    consumer_group,
                    consumer_name,
                    {stream_name: ">"},
                    count=config["batch_size"],
                    block=1000  # 1 second timeout
                )
                
                if messages:
                    await self._process_stream_messages(
                        service_name, 
                        config,
                        messages[0][1]  # Get messages for our stream
                    )
                
            except asyncio.TimeoutError:
                # Normal timeout, continue
                continue
                
            except Exception as e:
                logger.warning(f"Event consumer error for {service_name}", error=str(e))
                await asyncio.sleep(1)
    
    async def _run_adaptive_fallback(self, service_name: str, config: Dict):
        """Run adaptive fallback polling when events are not flowing."""
        base_interval = config["fallback_interval"]
        
        while self.running:
            try:
                # Calculate adaptive interval based on system load
                interval = await self._calculate_adaptive_interval(service_name, base_interval)
                
                # Check if events are flowing (if not, trigger fallback)
                if await self._should_run_fallback(service_name):
                    logger.debug(f"Running fallback for {service_name}")
                    
                    # Check resources before fallback processing  
                    if await self._can_process_events(config["priority"]):
                        await config["handler"](None, "fallback")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.warning(f"Adaptive fallback error for {service_name}", error=str(e))
                await asyncio.sleep(base_interval)
    
    async def _process_stream_messages(self, service_name: str, config: Dict, messages: List):
        """Process messages from Redis Stream."""
        if not messages:
            return
        
        start_time = time.time()
        
        try:
            # Process messages with timeout
            await asyncio.wait_for(
                self._batch_process_messages(service_name, config, messages),
                timeout=config["timeout"] / 1000  # Convert to seconds
            )
            
            # Acknowledge processed messages
            stream_name = config["stream"]
            consumer_group = self.streams[stream_name]["consumer_group"]
            
            message_ids = [msg[0] for msg in messages]
            await self.redis.xack(stream_name, consumer_group, *message_ids)
            
            # Log performance metrics
            processing_time = (time.time() - start_time) * 1000
            logger.debug(f"Processed {len(messages)} events for {service_name}",
                        processing_time_ms=processing_time,
                        throughput=len(messages) / (processing_time / 1000))
            
        except asyncio.TimeoutError:
            logger.warning(f"Processing timeout for {service_name}",
                         timeout_ms=config["timeout"],
                         batch_size=len(messages))
            
        except Exception as e:
            logger.error(f"Failed to process events for {service_name}", error=str(e))
    
    async def _batch_process_messages(self, service_name: str, config: Dict, messages: List):
        """Process a batch of messages efficiently."""
        handler = config["handler"]
        
        # Process messages in parallel for better throughput
        tasks = []
        for message_id, fields in messages:
            task = asyncio.create_task(
                handler(fields, "event", message_id)
            )
            tasks.append(task)
        
        # Wait for all messages to process
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _calculate_adaptive_interval(self, service_name: str, base_interval: int) -> int:
        """Calculate adaptive interval based on system resources and service priority."""
        resource_stats = await self.resource_monitor.get_current_stats()
        service_config = self.services[service_name]
        
        # Base multiplier from resource usage
        memory_factor = 1.0
        cpu_factor = 1.0
        
        if resource_stats["memory_percent"] > 85:
            memory_factor = 2.0  # Slow down significantly under memory pressure
        elif resource_stats["memory_percent"] > 70:
            memory_factor = 1.5
        elif resource_stats["memory_percent"] < 50:
            memory_factor = 0.75  # Speed up when plenty of memory
        
        if resource_stats["cpu_percent"] > 90:
            cpu_factor = 3.0    # Slow down dramatically under CPU pressure
        elif resource_stats["cpu_percent"] > 75:
            cpu_factor = 2.0
        elif resource_stats["cpu_percent"] < 40:
            cpu_factor = 0.8
        
        # Priority adjustments
        priority_factor = 1.0
        if service_config["priority"] == ServicePriority.CRITICAL:
            priority_factor = 0.5   # Critical services run more frequently
        elif service_config["priority"] == ServicePriority.BACKGROUND:
            priority_factor = 2.0   # Background services run less frequently
        
        # Calculate final interval
        adaptive_interval = int(base_interval * memory_factor * cpu_factor * priority_factor)
        
        # Ensure minimum intervals based on priority
        min_intervals = {
            ServicePriority.CRITICAL: 1,
            ServicePriority.IMPORTANT: 30, 
            ServicePriority.BACKGROUND: 300
        }
        
        return max(adaptive_interval, min_intervals[service_config["priority"]])
    
    async def _can_process_events(self, priority: ServicePriority) -> bool:
        """Check if system can handle event processing based on priority."""
        stats = await self.resource_monitor.get_current_stats()
        
        # Always allow critical services
        if priority == ServicePriority.CRITICAL:
            return stats["cpu_percent"] < 95 and stats["memory_percent"] < 95
        
        # Throttle important services under load
        if priority == ServicePriority.IMPORTANT:
            return stats["cpu_percent"] < 85 and stats["memory_percent"] < 85
        
        # Heavily throttle background services under load
        return stats["cpu_percent"] < 70 and stats["memory_percent"] < 70
    
    async def _should_run_fallback(self, service_name: str) -> bool:
        """Determine if fallback should run (when events are not flowing)."""
        stream_name = self.services[service_name]["stream"]
        
        try:
            # Check if stream has recent activity
            info = await self.redis.xinfo_stream(stream_name)
            last_generated_id = info.get("last-generated-id", "0-0")
            
            # Parse timestamp from Redis stream ID (format: timestamp-sequence)
            if last_generated_id and last_generated_id != "0-0":
                timestamp = int(last_generated_id.split("-")[0])
                age = time.time() * 1000 - timestamp  # Convert to milliseconds
                
                # If no events in last 30 seconds, run fallback
                return age > 30000
            
            return True  # No events at all, run fallback
            
        except Exception:
            return True  # Error checking stream, run fallback
    
    async def publish_event(self, event_type: EventType, data: Dict, stream_override: Optional[str] = None):
        """Publish event to appropriate Redis Stream."""
        if not self.redis:
            logger.warning("Cannot publish event - Redis unavailable", event_type=event_type.value)
            return
        
        # Determine target stream
        stream_mapping = {
            EventType.PRICE_UPDATE: "market_updates",
            EventType.TRADE_SIGNAL: "trade_signals", 
            EventType.PORTFOLIO_CHANGE: "portfolio_changes",
            EventType.RISK_ALERT: "risk_alerts",
            EventType.SYSTEM_HEALTH: "system_events",
            EventType.BALANCE_UPDATE: "balance_updates"
        }
        
        stream_name = stream_override or stream_mapping.get(event_type, "system_events")
        
        # Add metadata
        event_data = {
            "event_type": event_type.value,
            "timestamp": int(time.time() * 1000),
            **data
        }
        
        try:
            # Publish with automatic cleanup
            stream_config = self.streams[stream_name]
            await self.redis.xadd(
                stream_name,
                event_data,
                maxlen=stream_config["max_len"],
                approximate=True
            )
            
            logger.debug(f"Published event to {stream_name}", event_type=event_type.value)
            
        except Exception as e:
            logger.error(f"Failed to publish event", 
                        event_type=event_type.value,
                        stream=stream_name,
                        error=str(e))
    
    # Service Handlers - These will be called by the event consumers
    
    async def _handle_trade_execution(self, data: Optional[Dict], source: str, message_id: Optional[str] = None):
        """Handle trade execution events (critical priority)."""
        if source == "event" and data:
            logger.info("Processing trade signal", signal_type=data.get("signal_type"))
            # TODO: Implement actual trade execution logic
        elif source == "fallback":
            logger.debug("Trade execution fallback check")
            # TODO: Check for pending trades that need execution
    
    async def _handle_risk_monitoring(self, data: Optional[Dict], source: str, message_id: Optional[str] = None):
        """Handle risk monitoring events (critical priority).""" 
        if source == "event" and data:
            logger.info("Processing risk check", risk_type=data.get("risk_type"))
            # TODO: Implement risk assessment logic
        elif source == "fallback":
            logger.debug("Risk monitoring fallback check")
            # TODO: Periodic risk assessment
    
    async def _handle_portfolio_sync(self, data: Optional[Dict], source: str, message_id: Optional[str] = None):
        """Handle portfolio synchronization (important priority)."""
        if source == "event" and data:
            logger.debug("Processing portfolio update", symbol=data.get("symbol"))
            # TODO: Update portfolio based on market data
        elif source == "fallback":
            logger.debug("Portfolio sync fallback")
            # TODO: Full portfolio reconciliation
    
    async def _handle_balance_sync(self, data: Optional[Dict], source: str, message_id: Optional[str] = None):
        """Handle balance synchronization (important priority)."""
        if source == "event" and data:
            logger.debug("Processing balance update", exchange=data.get("exchange"))
            # TODO: Sync specific exchange balance
        elif source == "fallback":
            logger.debug("Balance sync fallback")
            # TODO: Sync all exchange balances
    
    async def _handle_market_data(self, data: Optional[Dict], source: str, message_id: Optional[str] = None):
        """Handle market data processing (important priority)."""
        if source == "event" and data:
            # This connects to the WebSocket market data system
            symbol = data.get("symbol")
            price = data.get("price")
            if symbol and price:
                logger.debug(f"Processing market update: {symbol} = ${price}")
                
                # Trigger portfolio recalculation if significant price change
                if await self._is_significant_price_change(symbol, price):
                    await self.publish_event(
                        EventType.PORTFOLIO_CHANGE,
                        {"symbol": symbol, "price": price, "trigger": "price_change"}
                    )
        
        elif source == "fallback":
            logger.debug("Market data processing fallback")
            # TODO: Process any missed market data
    
    async def _handle_health_monitoring(self, data: Optional[Dict], source: str, message_id: Optional[str] = None):
        """Handle system health monitoring (background priority)."""
        if source == "fallback":  # Health monitoring is primarily fallback-driven
            try:
                # Use non-blocking CPU check to avoid the previous issue
                cpu_percent = psutil.cpu_percent(interval=0)  # Non-blocking
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                health_data = {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": disk.percent,
                    "timestamp": time.time()
                }
                
                # Publish health events if thresholds exceeded
                if cpu_percent > 85 or memory.percent > 85:
                    await self.publish_event(
                        EventType.SYSTEM_HEALTH,
                        {**health_data, "alert": "high_resource_usage"}
                    )
                
                logger.debug("Health monitoring complete", **health_data)
                
            except Exception as e:
                logger.warning("Health monitoring failed", error=str(e))
    
    async def _handle_cleanup(self, data: Optional[Dict], source: str, message_id: Optional[str] = None):
        """Handle cleanup operations (background priority)."""
        if source == "fallback":
            try:
                # Cleanup old Redis keys
                if self.redis:
                    # Clean up expired stream entries (already handled by TTL, but double-check)
                    for stream_name, config in self.streams.items():
                        try:
                            # Trim streams to max length
                            await self.redis.xtrim(stream_name, maxlen=config["max_len"], approximate=True)
                        except Exception as e:
                            logger.warning(f"Failed to trim stream {stream_name}", error=str(e))
                
                logger.debug("Cleanup cycle completed")
                
            except Exception as e:
                logger.warning("Cleanup failed", error=str(e))
    
    async def _handle_metrics_collection(self, data: Optional[Dict], source: str, message_id: Optional[str] = None):
        """Handle metrics collection (background priority)."""
        if source == "fallback":
            try:
                # Collect service metrics
                metrics = {
                    "active_services": len([t for t in self.consumer_tasks.values() if not t.done()]),
                    "redis_connected": self.redis is not None,
                    "timestamp": time.time()
                }
                
                # Add resource metrics
                resource_stats = await self.resource_monitor.get_current_stats()
                metrics.update(resource_stats)
                
                logger.debug("Metrics collected", **metrics)
                
            except Exception as e:
                logger.warning("Metrics collection failed", error=str(e))
    
    async def _is_significant_price_change(self, symbol: str, current_price: float) -> bool:
        """Check if price change is significant enough to trigger events."""
        if not self.redis:
            return True  # Without Redis, assume all changes are significant
        
        try:
            last_price_key = f"last_price:{symbol}"
            last_price = await self.redis.get(last_price_key)
            
            if last_price:
                last_price = float(last_price)
                change_percent = abs((current_price - last_price) / last_price) * 100
                
                # Trigger if change > 0.5% for major coins, 1% for others  
                threshold = 0.5 if symbol in ["BTCUSDT", "ETHUSDT"] else 1.0
                
                if change_percent > threshold:
                    await self.redis.setex(last_price_key, 300, current_price)  # Cache for 5 minutes
                    return True
                    
                return False
            else:
                # No previous price, save current and don't trigger
                await self.redis.setex(last_price_key, 300, current_price)
                return False
                
        except Exception as e:
            logger.warning("Failed to check price change significance", error=str(e))
            return True  # Default to significant on error
    
    async def get_service_status(self) -> Dict:
        """Get comprehensive status of all services."""
        status = {
            "running": self.running,
            "redis_connected": self.redis is not None,
            "active_services": {},
            "resource_stats": await self.resource_monitor.get_current_stats(),
            "stream_info": {}
        }
        
        # Service status
        for name, task in self.consumer_tasks.items():
            status["active_services"][name] = {
                "running": not task.done(),
                "cancelled": task.cancelled() if task.done() else False
            }
        
        # Stream info
        if self.redis:
            for stream_name in self.streams.keys():
                try:
                    info = await self.redis.xinfo_stream(stream_name)
                    status["stream_info"][stream_name] = {
                        "length": info.get("length", 0),
                        "groups": info.get("groups", 0),
                        "last_generated_id": info.get("last-generated-id")
                    }
                except Exception:
                    status["stream_info"][stream_name] = {"error": "Unable to get info"}
        
        return status
    
    async def shutdown(self):
        """Graceful shutdown of all services."""
        logger.info("Shutting down event-driven services")
        self.running = False
        
        # Cancel all tasks
        for name, task in self.consumer_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Shutdown resource monitor
        await self.resource_monitor.shutdown()
        
        logger.info("Event-driven services shutdown complete")


class ResourceMonitor:
    """Monitor system resources for adaptive service intervals."""
    
    def __init__(self):
        self.stats = {
            "cpu_percent": 0,
            "memory_percent": 0,
            "disk_percent": 0,
            "last_update": 0
        }
        self.monitoring = False
        self.update_interval = 10  # Update every 10 seconds
    
    async def initialize(self):
        """Initialize resource monitoring."""
        # Get initial stats
        await self._update_stats()
        logger.info("Resource monitor initialized", **self.stats)
    
    async def start_monitoring(self):
        """Start continuous resource monitoring."""
        self.monitoring = True
        
        while self.monitoring:
            try:
                await self._update_stats()
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.warning("Resource monitoring error", error=str(e))
                await asyncio.sleep(self.update_interval)
    
    async def _update_stats(self):
        """Update resource statistics."""
        # Non-blocking calls to avoid CPU spikes
        cpu_percent = psutil.cpu_percent(interval=0)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        self.stats = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
            "last_update": time.time()
        }
    
    async def get_current_stats(self) -> Dict:
        """Get current resource statistics."""
        # Update if stats are stale
        if time.time() - self.stats["last_update"] > self.update_interval * 2:
            await self._update_stats()
        
        return self.stats.copy()
    
    async def shutdown(self):
        """Stop resource monitoring."""
        self.monitoring = False


# Global instance
event_driven_manager = EventDrivenServiceManager()