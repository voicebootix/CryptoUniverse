"""Request logging middleware for CryptoUniverse Enterprise."""

import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Production-grade request logging middleware with performance tracking."""
    
    # Skip logging for these paths to reduce noise
    SKIP_PATHS = {"/health", "/ping", "/favicon.ico", "/metrics"}
    
    async def dispatch(self, request: Request, call_next):
        """Log requests and responses with production enhancements."""
        # Skip logging for health checks and metrics
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)
        
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        
        start_time = time.time()
        
        # Only log in production for non-GET requests or errors
        should_log_request = request.method != "GET" or logger.isEnabledFor(10)  # DEBUG level
        
        if should_log_request:
            logger.info(
                "Request started",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                query=str(request.url.query) if request.url.query else None,
                client=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", "unknown")[:100]  # Truncate long UAs
            )
        
        # Process request with error handling
        response = None
        error_occurred = False
        
        try:
            response = await call_next(request)
        except Exception as e:
            error_occurred = True
            process_time = time.time() - start_time
            
            logger.error(
                "Request failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                error=str(e),
                process_time=f"{process_time:.3f}s"
            )
            raise
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Add request ID to response headers for tracing
        response.headers["X-Request-ID"] = request_id
        
        # Log based on status code and processing time
        if response.status_code >= 500:
            logger.error(
                "Request completed with server error",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                process_time=f"{process_time:.3f}s"
            )
        elif response.status_code >= 400:
            logger.warning(
                "Request completed with client error",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                process_time=f"{process_time:.3f}s"
            )
        elif process_time > 2.0:  # Slow request threshold
            logger.warning(
                "Slow request detected",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                process_time=f"{process_time:.3f}s"
            )
        elif should_log_request:
            logger.info(
                "Request completed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                process_time=f"{process_time:.3f}s"
            )
        
        # Record metrics if monitoring is available
        try:
            from app.services.system_monitoring import system_monitoring_service
            if system_monitoring_service.monitoring_active:
                system_monitoring_service.metrics_collector.record_metric(
                    "http_request_duration_ms",
                    process_time * 1000,
                    {
                        "method": request.method,
                        "status": str(response.status_code),
                        "path": request.url.path
                    }
                )
        except Exception:
            pass  # Don't fail requests if monitoring is unavailable
        
        return response
