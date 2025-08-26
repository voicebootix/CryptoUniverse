"""Request logging middleware for CryptoUniverse Enterprise."""

import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Request logging middleware."""
    
    async def dispatch(self, request: Request, call_next):
        """Log requests and responses."""
        start_time = time.time()
        
        # Log request
        logger.info(
            "Request started",
            method=request.method,
            url=str(request.url),
            client=request.client.host if request.client else "unknown"
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            "Request completed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            process_time=f"{process_time:.3f}s"
        )
        
        return response
