"""
Enterprise Startup Orchestration - Production Grade

Manages application startup with proper dependency resolution, health checks,
and graceful degradation. Prevents thundering herd problems and ensures
reliable service initialization in enterprise environments.

For platforms handling real money transactions.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Set
from enum import Enum
import structlog
from dataclasses import dataclass, field

from app.core.logging import LoggerMixin

logger = structlog.get_logger(__name__)


class ServiceStatus(Enum):
    PENDING = "pending"
    INITIALIZING = "initializing"  
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    SHUTDOWN = "shutdown"


class DependencyStatus(Enum):
    SATISFIED = "satisfied"
    WAITING = "waiting"
    FAILED = "failed"


@dataclass
class ServiceDefinition:
    """Definition of a service with dependencies and initialization logic."""
    name: str
    initialize_func: Callable
    dependencies: List[str] = field(default_factory=list)
    required: bool = True  # If False, service failure won't stop startup
    timeout: int = 30  # seconds
    retry_count: int = 3
    retry_delay: int = 5  # seconds
    health_check_func: Optional[Callable] = None
    shutdown_func: Optional[Callable] = None
    
    # Runtime state
    status: ServiceStatus = ServiceStatus.PENDING
    last_error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    retry_attempts: int = 0


class EnterpriseStartupOrchestrator(LoggerMixin):
    """
    Enterprise startup orchestrator with dependency management.
    
    Features:
    - Dependency graph resolution
    - Parallel initialization where possible
    - Graceful degradation on failures
    - Comprehensive monitoring and logging
    - Rollback capabilities
    """
    
    def __init__(self):
        super().__init__()
        self._services: Dict[str, ServiceDefinition] = {}
        self._startup_start_time: Optional[float] = None
        self._startup_complete: bool = False
        self._shutdown_initiated: bool = False
        
        # Monitoring
        self._startup_metrics = {
            'total_services': 0,
            'successful_services': 0,
            'failed_services': 0,
            'degraded_services': 0,
            'total_startup_time': 0,
            'dependency_resolution_time': 0,
            'critical_path_time': 0
        }
    
    def register_service(self, service: ServiceDefinition):
        """Register a service with the orchestrator."""
        if service.name in self._services:
            raise ValueError(f"Service '{service.name}' already registered")
        
        self._services[service.name] = service
        self.logger.info(f"📝 Registered service: {service.name}", 
                        dependencies=service.dependencies,
                        required=service.required)
    
    async def start_all(self) -> bool:
        """
        Start all services with proper dependency resolution.
        
        Returns:
            bool: True if all critical services started successfully
        """
        self.logger.info("🚀 Starting Enterprise Service Orchestration...")
        self._startup_start_time = time.time()
        
        try:
            # Validate dependency graph
            await self._validate_dependencies()
            
            # Calculate startup order
            startup_order = await self._resolve_startup_order()
            
            # Execute startup in phases
            success = await self._execute_startup_phases(startup_order)
            
            # Update metrics
            self._update_startup_metrics()
            
            # Log final status
            await self._log_startup_summary()
            
            self._startup_complete = True
            return success
            
        except Exception as e:
            self.logger.error("❌ Startup orchestration failed", error=str(e))
            await self._emergency_shutdown()
            return False
    
    async def _validate_dependencies(self):
        """Validate that all dependencies are registered and form a valid DAG."""
        
        # Check all dependencies exist
        for service_name, service in self._services.items():
            for dep_name in service.dependencies:
                if dep_name not in self._services:
                    raise ValueError(f"Service '{service_name}' depends on unregistered service '{dep_name}'")
        
        # Check for circular dependencies
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for dep in self._services[node].dependencies:
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for service_name in self._services:
            if service_name not in visited:
                if has_cycle(service_name):
                    raise ValueError("Circular dependency detected in service graph")
        
        self.logger.info("✅ Service dependency graph validated")
    
    async def _resolve_startup_order(self) -> List[List[str]]:
        """
        Resolve startup order using topological sort.
        Returns phases where services in same phase can start in parallel.
        """
        
        # Calculate in-degree for each service
        in_degree = {name: 0 for name in self._services}
        for service in self._services.values():
            for dep in service.dependencies:
                in_degree[service.name] += 1
        
        # Topological sort in phases
        phases = []
        remaining = set(self._services.keys())
        
        while remaining:
            # Find services with no dependencies in current iteration
            ready = [name for name in remaining if in_degree[name] == 0]
            
            if not ready:
                raise ValueError("Dependency cycle detected during resolution")
            
            phases.append(ready)
            
            # Remove ready services and update in-degrees
            for service_name in ready:
                remaining.remove(service_name)
                for dependent in self._services:
                    if service_name in self._services[dependent].dependencies:
                        in_degree[dependent] -= 1
        
        self.logger.info("📊 Startup phases calculated", 
                        phases=[(i, phase) for i, phase in enumerate(phases)])
        return phases
    
    async def _execute_startup_phases(self, phases: List[List[str]]) -> bool:
        """Execute startup phases with parallel execution within phases."""
        
        critical_failures = []
        
        for phase_index, phase_services in enumerate(phases):
            self.logger.info(f"🔄 Starting phase {phase_index + 1}/{len(phases)}", 
                           services=phase_services)
            
            # Start all services in phase concurrently
            phase_tasks = []
            for service_name in phase_services:
                task = asyncio.create_task(
                    self._start_service(service_name),
                    name=f"startup-{service_name}"
                )
                phase_tasks.append((service_name, task))
            
            # Wait for phase completion
            phase_results = await asyncio.gather(
                *[task for _, task in phase_tasks], 
                return_exceptions=True
            )
            
            # Process phase results
            for i, (service_name, result) in enumerate(zip(phase_services, phase_results)):
                service = self._services[service_name]
                
                if isinstance(result, Exception):
                    service.status = ServiceStatus.FAILED
                    service.last_error = str(result)
                    
                    if service.required:
                        critical_failures.append(service_name)
                        self.logger.error(f"❌ Critical service failed: {service_name}", 
                                        error=str(result))
                    else:
                        self.logger.warning(f"⚠️ Optional service failed: {service_name}", 
                                          error=str(result))
                
                elif result:
                    service.status = ServiceStatus.HEALTHY
                    self.logger.info(f"✅ Service started: {service_name}")
                else:
                    service.status = ServiceStatus.DEGRADED
                    self.logger.warning(f"⚠️ Service degraded: {service_name}")
            
            # Check if we should continue
            if critical_failures:
                self.logger.error("❌ Critical services failed - stopping startup", 
                                failed_services=critical_failures)
                return False
            
            self.logger.info(f"✅ Phase {phase_index + 1} completed successfully")
        
        return len(critical_failures) == 0
    
    async def _start_service(self, service_name: str) -> bool:
        """Start a single service with retry logic and timeout."""
        
        service = self._services[service_name]
        service.status = ServiceStatus.INITIALIZING
        service.start_time = time.time()
        service.retry_attempts = 0
        
        self.logger.info(f"🚀 Starting service: {service_name}")
        
        # Check dependencies are satisfied
        for dep_name in service.dependencies:
            dep_service = self._services[dep_name]
            if dep_service.status not in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]:
                service.status = ServiceStatus.FAILED
                service.last_error = f"Dependency '{dep_name}' not available"
                return False
        
        # Retry loop
        last_error = None
        for attempt in range(service.retry_count + 1):
            try:
                service.retry_attempts = attempt
                
                # Execute service initialization with timeout
                await asyncio.wait_for(
                    service.initialize_func(),
                    timeout=service.timeout
                )
                
                # Run health check if provided
                if service.health_check_func:
                    health_ok = await asyncio.wait_for(
                        service.health_check_func(),
                        timeout=10  # Health check timeout
                    )
                    
                    if not health_ok:
                        raise RuntimeError("Health check failed")
                
                # Service started successfully
                service.end_time = time.time()
                service.status = ServiceStatus.HEALTHY
                
                startup_time = service.end_time - service.start_time
                self.logger.info(f"✅ Service started successfully: {service_name}", 
                               startup_time_ms=int(startup_time * 1000),
                               attempts=attempt + 1)
                return True
                
            except asyncio.TimeoutError:
                last_error = f"Service initialization timed out after {service.timeout}s"
                self.logger.warning(f"⏱️ Service timeout: {service_name}", 
                                  attempt=attempt + 1, 
                                  max_attempts=service.retry_count + 1)
                
            except Exception as e:
                last_error = str(e)
                self.logger.warning(f"⚠️ Service start failed: {service_name}", 
                                  attempt=attempt + 1,
                                  max_attempts=service.retry_count + 1,
                                  error=str(e))
            
            # Wait before retry (except on last attempt)
            if attempt < service.retry_count:
                retry_delay = service.retry_delay * (2 ** attempt)  # Exponential backoff
                await asyncio.sleep(retry_delay)
        
        # All attempts failed
        service.end_time = time.time()
        service.status = ServiceStatus.FAILED
        service.last_error = last_error
        
        self.logger.error(f"❌ Service failed to start: {service_name}", 
                         final_error=last_error,
                         total_attempts=service.retry_count + 1)
        return False
    
    async def _update_startup_metrics(self):
        """Update startup metrics for monitoring."""
        
        total_time = time.time() - self._startup_start_time
        
        self._startup_metrics.update({
            'total_services': len(self._services),
            'successful_services': sum(1 for s in self._services.values() 
                                     if s.status == ServiceStatus.HEALTHY),
            'failed_services': sum(1 for s in self._services.values() 
                                 if s.status == ServiceStatus.FAILED),
            'degraded_services': sum(1 for s in self._services.values() 
                                   if s.status == ServiceStatus.DEGRADED),
            'total_startup_time': total_time
        })
    
    async def _log_startup_summary(self):
        """Log comprehensive startup summary."""
        
        summary = {
            'total_services': len(self._services),
            'successful': [],
            'failed': [],
            'degraded': [],
            'startup_time': self._startup_metrics['total_startup_time']
        }
        
        for name, service in self._services.items():
            service_info = {
                'name': name,
                'startup_time': (service.end_time - service.start_time) if service.end_time else 0,
                'attempts': service.retry_attempts + 1
            }
            
            if service.status == ServiceStatus.HEALTHY:
                summary['successful'].append(service_info)
            elif service.status == ServiceStatus.FAILED:
                service_info['error'] = service.last_error
                summary['failed'].append(service_info)
            elif service.status == ServiceStatus.DEGRADED:
                service_info['error'] = service.last_error
                summary['degraded'].append(service_info)
        
        self.logger.info("📊 Startup Summary", **summary)
    
    async def shutdown_all(self):
        """Gracefully shutdown all services in reverse dependency order."""
        
        if self._shutdown_initiated:
            return
        
        self._shutdown_initiated = True
        self.logger.info("🛑 Starting graceful service shutdown...")
        
        # Calculate shutdown order (reverse of startup)
        try:
            startup_phases = await self._resolve_startup_order()
            shutdown_phases = list(reversed(startup_phases))
            
            for phase in shutdown_phases:
                # Shutdown services in phase
                shutdown_tasks = []
                for service_name in phase:
                    service = self._services[service_name]
                    if service.shutdown_func and service.status in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]:
                        task = asyncio.create_task(
                            self._shutdown_service(service_name),
                            name=f"shutdown-{service_name}"
                        )
                        shutdown_tasks.append(task)
                
                # Wait for phase shutdown
                if shutdown_tasks:
                    await asyncio.gather(*shutdown_tasks, return_exceptions=True)
            
            self.logger.info("✅ Graceful shutdown completed")
            
        except Exception as e:
            self.logger.error("❌ Error during graceful shutdown", error=str(e))
    
    async def _shutdown_service(self, service_name: str):
        """Shutdown a single service."""
        service = self._services[service_name]
        
        try:
            await asyncio.wait_for(service.shutdown_func(), timeout=30)
            service.status = ServiceStatus.SHUTDOWN
            self.logger.info(f"✅ Service shutdown: {service_name}")
            
        except Exception as e:
            self.logger.error(f"❌ Service shutdown failed: {service_name}", error=str(e))
    
    async def _emergency_shutdown(self):
        """Emergency shutdown when startup fails."""
        self.logger.warning("⚠️ Initiating emergency shutdown...")
        
        # Force shutdown all initialized services
        shutdown_tasks = []
        for service_name, service in self._services.items():
            if (service.status in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED] 
                and service.shutdown_func):
                
                task = asyncio.create_task(
                    asyncio.wait_for(service.shutdown_func(), timeout=10),
                    name=f"emergency-shutdown-{service_name}"
                )
                shutdown_tasks.append(task)
        
        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)
        
        self.logger.info("✅ Emergency shutdown completed")
    
    def get_service_status(self, service_name: str) -> Optional[ServiceDefinition]:
        """Get status of a specific service."""
        return self._services.get(service_name)
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all services."""
        return {
            name: {
                'status': service.status.value,
                'required': service.required,
                'dependencies': service.dependencies,
                'last_error': service.last_error,
                'startup_time': (service.end_time - service.start_time) if service.end_time and service.start_time else None,
                'retry_attempts': service.retry_attempts
            }
            for name, service in self._services.items()
        }
    
    def get_startup_metrics(self) -> Dict[str, Any]:
        """Get startup metrics for monitoring."""
        return self._startup_metrics.copy()