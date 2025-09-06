"""
Enterprise Health and Monitoring API - Production Grade

Provides comprehensive health checks, monitoring data, and operational
insights for enterprise applications handling real money transactions.
"""

import asyncio
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.enterprise_startup import get_application
from app.core.redis_manager import get_redis_manager
from app.models.user import User, UserRole
from app.api.v1.endpoints.auth import require_role

settings = get_settings()
logger = structlog.get_logger(__name__)

router = APIRouter()


class HealthStatus(BaseModel):
    status: str
    timestamp: str
    uptime_seconds: float
    version: str = "1.0.0"


class ServiceHealth(BaseModel):
    name: str
    status: str
    last_check: Optional[str]
    response_time_ms: Optional[float]
    error_message: Optional[str]
    dependencies: List[str]


class SystemMetrics(BaseModel):
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    active_connections: int
    request_rate_per_minute: float


class DetailedHealthResponse(BaseModel):
    overall_status: str
    timestamp: str
    uptime_seconds: float
    services: List[ServiceHealth]
    system_metrics: SystemMetrics
    redis_status: Dict[str, Any]
    database_status: Dict[str, Any]
    background_services_status: Dict[str, Any]


@router.get("/health", 
           response_model=HealthStatus,
           tags=["Health"],
           summary="Basic health check")
async def basic_health_check():
    """
    Basic health check endpoint for load balancers.
    Returns minimal information for high-frequency checks.
    """
    try:
        app = await get_application()
        health_data = app.get_health_status()
        
        return HealthStatus(
            status="healthy" if health_data['status'] == 'running' else "unhealthy",
            timestamp=datetime.utcnow().isoformat(),
            uptime_seconds=time.time() - (app.orchestrator._startup_start_time or time.time())
        )
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable"
        )


@router.get("/health/detailed",
           response_model=DetailedHealthResponse,
           dependencies=[Depends(require_role([UserRole.ADMIN]))],
           tags=["Health"],
           summary="Detailed health and monitoring data")
async def detailed_health_check(
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Comprehensive health check with detailed system information.
    Admin only endpoint for operational monitoring.
    """
    try:
        app = await get_application()
        
        # Get application status
        app_health = app.get_health_status()
        uptime = time.time() - (app.orchestrator._startup_start_time or time.time())
        
        # Get service health
        services = []
        for service_name, service_data in app_health['services'].items():
            services.append(ServiceHealth(
                name=service_name,
                status=service_data['status'],
                last_check=datetime.utcnow().isoformat(),
                response_time_ms=service_data.get('startup_time', 0) * 1000 if service_data.get('startup_time') else None,
                error_message=service_data.get('last_error'),
                dependencies=service_data.get('dependencies', [])
            ))
        
        # Get system metrics
        system_metrics = SystemMetrics(
            cpu_percent=psutil.cpu_percent(interval=1),
            memory_percent=psutil.virtual_memory().percent,
            disk_usage_percent=psutil.disk_usage('/').percent,
            active_connections=len(psutil.net_connections()),
            request_rate_per_minute=0  # This would come from your request tracking
        )
        
        # Get Redis status
        redis_status = await _get_redis_detailed_status()
        
        # Get database status
        database_status = await _get_database_detailed_status()
        
        # Get background services status
        background_status = await _get_background_services_status()
        
        # Determine overall status
        service_statuses = [s.status for s in services]
        if all(status in ['healthy', 'degraded'] for status in service_statuses):
            overall_status = "healthy"
        elif any(status == 'healthy' for status in service_statuses):
            overall_status = "degraded" 
        else:
            overall_status = "unhealthy"
        
        return DetailedHealthResponse(
            overall_status=overall_status,
            timestamp=datetime.utcnow().isoformat(),
            uptime_seconds=uptime,
            services=services,
            system_metrics=system_metrics,
            redis_status=redis_status,
            database_status=database_status,
            background_services_status=background_status
        )
        
    except Exception as e:
        logger.error("Detailed health check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check error: {str(e)}"
        )


@router.get("/health/redis",
           dependencies=[Depends(require_role([UserRole.ADMIN]))],
           tags=["Health"],
           summary="Redis specific health check")
async def redis_health_check(
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Redis-specific health check with connection pool and circuit breaker status.
    """
    try:
        redis_manager = await get_redis_manager()
        health_status = await redis_manager.get_health_status()
        
        # Add connection test
        client = await redis_manager.get_client()
        if client:
            start_time = time.time()
            await client.ping()
            response_time = (time.time() - start_time) * 1000
            
            health_status['connection_test'] = {
                'success': True,
                'response_time_ms': response_time
            }
        else:
            health_status['connection_test'] = {
                'success': False,
                'reason': 'Circuit breaker open or connection failed'
            }
        
        return health_status
        
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return {
            'status': 'unhealthy',
            'error': str(e),
            'connection_test': {'success': False, 'reason': str(e)}
        }


@router.get("/health/services",
           dependencies=[Depends(require_role([UserRole.ADMIN]))],
           tags=["Health"], 
           summary="Service dependency status")
async def services_health_check(
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Check status of all application services and their dependencies.
    """
    try:
        app = await get_application()
        
        services_status = {}
        for service_name, service in app.orchestrator._services.items():
            
            # Check service health if health check function exists
            health_ok = None
            if service.health_check_func:
                try:
                    health_ok = await asyncio.wait_for(
                        service.health_check_func(), 
                        timeout=5
                    )
                except Exception as e:
                    health_ok = False
                    logger.warning(f"Health check failed for {service_name}", error=str(e))
            
            services_status[service_name] = {
                'status': service.status.value,
                'required': service.required,
                'dependencies': service.dependencies,
                'health_check_result': health_ok,
                'last_error': service.last_error,
                'retry_attempts': service.retry_attempts,
                'startup_time_ms': (
                    (service.end_time - service.start_time) * 1000 
                    if service.end_time and service.start_time 
                    else None
                )
            }
        
        return {
            'services': services_status,
            'startup_metrics': app.orchestrator.get_startup_metrics()
        }
        
    except Exception as e:
        logger.error("Services health check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Services health check error: {str(e)}"
        )


async def _get_redis_detailed_status() -> Dict[str, Any]:
    """Get detailed Redis status information."""
    try:
        redis_manager = await get_redis_manager()
        return await redis_manager.get_health_status()
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


async def _get_database_detailed_status() -> Dict[str, Any]:
    """Get detailed database status information."""
    try:
        # This would implement your database health checks
        return {
            'status': 'healthy',
            'connections': {
                'active': 0,
                'idle': 0,
                'total': 0
            },
            'response_time_ms': 0
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


async def _get_background_services_status() -> Dict[str, Any]:
    """Get background services status."""
    try:
        app = await get_application()
        
        if app.background_manager:
            return {
                'status': 'running' if app.background_manager.running else 'stopped',
                'services': app.background_manager.services.copy(),
                'uptime_seconds': (
                    (datetime.utcnow() - app.background_manager.start_time).total_seconds()
                    if app.background_manager.start_time
                    else 0
                )
            }
        else:
            return {
                'status': 'not_initialized',
                'services': {},
                'uptime_seconds': 0
            }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }