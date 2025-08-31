"""
CryptoUniverse Enterprise - Main Application

Multi-tenant AI-powered cryptocurrency trading platform with enterprise features.
This application migrates and enhances the existing Flowise-based trading system
with native Python implementation and enterprise-grade features.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

# Core imports
from app.core.config import get_settings
from app.core.database import engine, db_manager
from app.core.redis import get_redis_client, close_redis_client
from app.core.logging import configure_logging

# API routes
from app.api.v1.router import api_router

# Middleware
from app.middleware.auth import AuthMiddleware
from app.middleware.tenant import TenantMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.logging import RequestLoggingMiddleware

# Background services
from app.services.background import BackgroundServiceManager
from app.services.production_monitoring import production_monitoring

# Initialize settings and logging
settings = get_settings()
configure_logging(settings.LOG_LEVEL, settings.ENVIRONMENT)
logger = structlog.get_logger()

# Background service manager
background_manager = BackgroundServiceManager()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info(
        "🚀 CryptoUniverse Enterprise starting up...",
        version="2.0.0",
        environment=settings.ENVIRONMENT,
    )

    try:
        # Connect to database
        await db_manager.connect()
        logger.info("✅ Database connected")

        # Connect to Redis
        try:
            redis = await get_redis_client()
            await redis.ping()
            logger.info("✅ Redis connected")
        except Exception as e:
            logger.warning("⚠️ Redis connection failed - running in degraded mode", error=str(e))

        # Start background services
        await background_manager.start_all()
        logger.info("✅ Background services started")

        logger.info(
            "🎉 CryptoUniverse Enterprise is ready!",
            api_docs=f"{settings.BASE_URL}/api/docs" if settings.ENVIRONMENT == "development" else "Contact admin",
        )

    except Exception as e:
        logger.error("❌ Failed to start application", error=str(e))
        raise

    yield

    # Shutdown
    logger.info("🔄 CryptoUniverse Enterprise shutting down...")

    try:
        # Stop background services
        await background_manager.stop_all()
        logger.info("✅ Background services stopped")

        # Disconnect from database
        await db_manager.disconnect()
        logger.info("✅ Database disconnected")

        # Close Redis connection
        await close_redis_client()
        logger.info("✅ Redis disconnected")

    except Exception as e:
        logger.error("❌ Error during shutdown", error=str(e))

    logger.info("👋 Shutdown complete")


# Create FastAPI application
def create_application() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan
    )

    # CORS FIRST - must be added before other middleware
    cors_origins = settings.cors_origins
    
    # Add localhost for development
    if settings.ENVIRONMENT == "development":
        dev_origins = [
            "http://localhost:3000",
            "http://localhost:8000", 
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000"
        ]
        cors_origins.extend(dev_origins)
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=86400,  # Cache preflight for 24 hours
    )

    # Add SessionMiddleware for OAuth
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

    # Security middleware
    if settings.ALLOWED_HOSTS:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

    # Custom middleware (order matters!)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(TenantMiddleware)
    app.add_middleware(AuthMiddleware)

    # Include API routes
    app.include_router(api_router, prefix="/api/v1")

    # Exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with structured logging."""
        logger.warning(
            "HTTP exception",
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "path": request.url.path,
                "timestamp": asyncio.get_event_loop().time(),
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(
            "Unhandled exception",
            error=str(exc),
            path=request.url.path,
            method=request.method,
            exc_info=True,
        )

        if settings.ENVIRONMENT == "development":
            return JSONResponse(
                status_code=500,
                content={
                    "error": str(exc),
                    "type": type(exc).__name__,
                    "status_code": 500,
                    "path": request.url.path,
                },
            )
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error. Please contact support.",
                    "status_code": 500,
                    "support": "support@cryptouniverse.com",
                },
            )

    return app


# Create application instance
app = create_application()


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """
    Comprehensive health check endpoint for load balancers and monitoring.
    
    Checks connectivity to all critical services and returns detailed status.
    """
    health_status = {"status": "healthy", "checks": {}, "timestamp": asyncio.get_event_loop().time()}

    try:
        # Check database
        await db_manager.execute("SELECT 1")
        health_status["checks"]["database"] = "connected"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"

    try:
        # Check Redis
        redis = await get_redis_client()
        await redis.ping()
        health_status["checks"]["redis"] = "connected"
    except Exception as e:
        health_status["checks"]["redis"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"

    try:
        # Check background services
        service_status = await background_manager.health_check()
        health_status["checks"]["background_services"] = service_status
        if not all(status == "running" for status in service_status.values()):
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["background_services"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"

    try:
        # Get comprehensive production monitoring data
        production_health = await production_monitoring.get_system_health()
        health_status["checks"]["production_monitoring"] = {
            "status": production_health.get("status"),
            "health_score": production_health.get("health_score"),
            "uptime_hours": production_health.get("uptime_hours")
        }
        
        # Update overall status based on production monitoring
        if production_health.get("status") == "critical":
            health_status["status"] = "unhealthy"
        elif production_health.get("status") == "warning" and health_status["status"] == "healthy":
            health_status["status"] = "degraded"
            
    except Exception as e:
        health_status["checks"]["production_monitoring"] = f"error: {str(e)}"

    # Add system information
    health_status.update(
        {
            "version": "2.0.0",
            "environment": settings.ENVIRONMENT,
            "services": {
                "trading_engine": "operational",
                "user_exchange_service": "operational", 
                "real_market_data": "operational",
                "ai_consensus": "operational",
                "copy_trading": "operational",
                "enterprise_features": "operational",
            },
        }
    )

    # Return appropriate status code
    if health_status["status"] == "healthy":
        return health_status
    elif health_status["status"] == "degraded":
        return JSONResponse(status_code=200, content=health_status)
    else:
        return JSONResponse(status_code=503, content=health_status)


# Root endpoint
@app.get("/", tags=["System"])
async def root():
    """
    Welcome endpoint with API information and feature overview.
    """
    return {
        "message": "🚀 Welcome to CryptoUniverse Enterprise",
        "version": "2.0.0",
        "description": "Multi-tenant AI-powered cryptocurrency trading platform",
        "features": {
            "trading_engine": {
                "description": "AI-powered trading with multi-model consensus",
                "exchanges": ["Binance", "Kraken", "KuCoin", "Coinbase"],
                "strategies": ["Momentum", "Mean Reversion", "Arbitrage", "HFT"],
            },
            "enterprise": {
                "description": "Enterprise-grade multi-tenant platform",
                "features": [
                    "Multi-tenant architecture",
                    "Credit-based profit limits",
                    "Role-based access control",
                    "Advanced analytics",
                    "SOC 2 compliance ready",
                ],
            },
            "copy_trading": {
                "description": "Professional copy trading marketplace",
                "features": [
                    "Real-time signal distribution",
                    "Revenue sharing (70/30 split)",
                    "Performance verification",
                    "Risk assessment",
                ],
            },
        },
        "documentation": "/api/docs" if settings.ENVIRONMENT == "development" else "Contact admin",
        "support": {"email": "support@cryptouniverse.com", "discord": "https://discord.gg/cryptouniverse"},
        "status": "operational",
    }


# Metrics endpoint
@app.get("/metrics", tags=["System"])
async def metrics():
    """
    System metrics endpoint for monitoring and alerting.
    """
    try:
        metrics_data = await background_manager.get_system_metrics()
        return JSONResponse(content=metrics_data)
    except Exception as e:
        logger.error("Failed to get metrics", error=str(e))
        return JSONResponse(
            status_code=500, content={"error": "Failed to retrieve metrics", "detail": str(e)}
        )


if __name__ == "__main__":
    logger.info("🚀 Starting CryptoUniverse Enterprise in development mode...")

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
        reload_dirs=["app"] if settings.ENVIRONMENT == "development" else None,
    )
