"""
CryptoUniverse Enterprise - Main Application

Multi-tenant AI-powered cryptocurrency trading platform with enterprise features.
This application migrates and enhances the existing Flowise-based trading system
with native Python implementation and enterprise-grade features.
"""

import asyncio
import json
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
import uvicorn
from fastapi import FastAPI, Request, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from jose import JWTError

# Core imports
from app.core.config import get_settings
from app.core.database import engine, db_manager
# from app.core.enterprise_startup import get_application  # DISABLED temporarily
from app.core.logging import configure_logging
from app.core.redis import get_redis_client, close_redis_client

# API routes
from app.api.v1.router import api_router

# Middleware
from app.middleware.auth import AuthMiddleware
from app.middleware.tenant import TenantMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.logging import RequestLoggingMiddleware

# Background services
from app.services.background import BackgroundServiceManager

# Global exception handler
from fastapi import status
from fastapi.responses import JSONResponse

# Initialize settings and logging
settings = get_settings()
configure_logging(settings.LOG_LEVEL, settings.ENVIRONMENT)
logger = structlog.get_logger()

# Background service manager
background_manager = BackgroundServiceManager()


async def start_monitoring_delayed(delay: int):
    """Start system monitoring after a delay to reduce initial memory load."""
    await asyncio.sleep(delay)
    try:
        from app.services.system_monitoring import system_monitoring_service
        await system_monitoring_service.start_monitoring()
        logger.info("✅ System monitoring started (delayed)")
    except Exception as e:
        logger.warning("System monitoring failed to start", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Detect if we're running in Gunicorn with multiple workers
    import os
    worker_id = os.environ.get("APP_WORKER_ID", os.getpid())
    is_primary_worker = worker_id == os.getpid() or str(worker_id) == "1"
    
    # Startup
    logger.info(
        "🚀 CryptoUniverse Enterprise starting up...",
        version="2.0.0",
        environment=settings.ENVIRONMENT,
        worker_id=worker_id,
        is_primary=is_primary_worker
    )

    try:
        # Connect to database
        await db_manager.connect()
        logger.info("✅ Database connected")
        
        # Ensure tables exist (in case startup.py failed during build)
        try:
            from app.core.database import engine, Base
            from sqlalchemy import inspect
            
            async with engine.connect() as conn:
                # Check if tables exist
                def check_tables(connection):
                    inspector = inspect(connection)
                    return len(inspector.get_table_names()) > 0
                
                tables_exist = await conn.run_sync(check_tables)
                
                if not tables_exist:
                    logger.warning("⚠️ No database tables found - creating now...")
                    await conn.run_sync(Base.metadata.create_all)
                    logger.info("✅ Database tables created")
                    
                    # Also create admin user
                    from app.models.user import User, UserRole, UserStatus
                    from sqlalchemy.ext.asyncio import AsyncSession
                    from sqlalchemy import select
                    import bcrypt
                    import uuid
                    from datetime import datetime
                    
                    async with AsyncSession(engine) as session:
                        result = await session.execute(
                            select(User).where(User.email == "admin@cryptouniverse.com")
                        )
                        if not result.scalar_one_or_none():
                            password = "AdminPass123!"
                            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                            admin_user = User(
                                id=uuid.uuid4(),
                                email="admin@cryptouniverse.com",
                                hashed_password=password_hash,
                                role=UserRole.ADMIN,
                                status=UserStatus.ACTIVE,
                                is_active=True,
                                is_verified=True,
                                created_at=datetime.utcnow(),
                                updated_at=datetime.utcnow()
                            )
                            session.add(admin_user)
                            await session.commit()
                            logger.info("✅ Admin user created")
        except Exception as e:
            logger.warning(f"⚠️ Table check/creation failed: {e}")
            # Continue anyway - tables might already exist

        # Connect to Redis
        try:
            redis = await get_redis_client()
            await redis.ping()
            logger.info("✅ Redis connected")
        except Exception as e:
            logger.warning("⚠️ Redis connection failed - running in degraded mode", error=str(e))

        # Only start background services on the primary worker to avoid conflicts
        if is_primary_worker:
            # Start background services with staged initialization
            try:
                # Start only essential services initially
                await background_manager.start_essential_services()
                logger.info("✅ Essential background services started")
                
                # Schedule heavy services to start after 30 seconds
                asyncio.create_task(background_manager.start_deferred_services(delay=30))
                logger.info("📅 Heavy services scheduled for deferred startup")
            except Exception as e:
                logger.warning("⚠️ Background services failed to start - running without them", error=str(e)) 

            # Start lightweight system monitoring with delayed initialization
            try:
                from app.services.system_monitoring import system_monitoring_service
                # Start with reduced interval for memory efficiency
                system_monitoring_service.monitoring_interval = 60  # 1 minute instead of 30s
                system_monitoring_service.max_metric_points = 100  # Reduced from 1000
                
                # Schedule monitoring to start after services are stable
                asyncio.create_task(start_monitoring_delayed(45))  # Start after 45 seconds
                logger.info("📊 System monitoring scheduled for delayed startup")
            except Exception as e:
                logger.warning("System monitoring scheduling failed", error=str(e))
        else:
            logger.info("📋 Secondary worker - skipping background services initialization")


        logger.info(
            "🎉 CryptoUniverse Enterprise is ready!",
            api_docs=f"{settings.BASE_URL}/api/docs" if settings.ENVIRONMENT == "development" else "Contact admin",
        )

    except Exception as e:
        logger.error("❌ Failed to start application", error=str(e))
        raise

    yield

    # Shutdown - PHASE 5: Enhanced graceful shutdown
    logger.info("🔄 CryptoUniverse Enterprise shutting down...", worker_id=worker_id)
    shutdown_start = time.time()

    try:
        # Only stop background services on primary worker
        if is_primary_worker:
            # Stop system monitoring first
            try:
                from app.services.system_monitoring import system_monitoring_service
                if system_monitoring_service.monitoring_active:
                    await asyncio.wait_for(
                        system_monitoring_service.stop_monitoring(),
                        timeout=5.0
                    )
                    logger.info("📊 System monitoring stopped")
            except asyncio.TimeoutError:
                logger.warning("⚠️ System monitoring shutdown timed out")
            except Exception as e:
                logger.warning("⚠️ System monitoring shutdown failed", error=str(e))

            # Stop background services gracefully with timeout
            try:
                await asyncio.wait_for(
                    background_manager.stop_all(),
                    timeout=10.0  # 10 second timeout for all services
                )
                logger.info("✅ Background services stopped")
            except asyncio.TimeoutError:
                logger.warning("⚠️ Background services shutdown timed out after 10s")
            except Exception as e:
                logger.warning("⚠️ Background services cleanup failed", error=str(e))

        # AI Manager was not started during temporary fixes
        logger.info("🧠 AI Manager was not started - no shutdown needed")

        # Disconnect from database with timeout
        try:
            await asyncio.wait_for(
                db_manager.disconnect(),
                timeout=5.0
            )
            logger.info("✅ Database disconnected")
        except asyncio.TimeoutError:
            logger.warning("⚠️ Database disconnect timed out")
        except Exception as e:
            logger.warning("⚠️ Database disconnect failed", error=str(e))

        # Close Redis connection with timeout
        try:
            await asyncio.wait_for(
                close_redis_client(),
                timeout=3.0
            )
            logger.info("✅ Redis disconnected")
        except asyncio.TimeoutError:
            logger.warning("⚠️ Redis disconnect timed out")
        except Exception as e:
            logger.warning("⚠️ Redis disconnect failed", error=str(e))

    except Exception as e:
        logger.error("❌ Critical error during shutdown", error=str(e))

    shutdown_time = time.time() - shutdown_start
    logger.info(f"👋 Shutdown complete in {shutdown_time:.2f}s")


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
    
    # Always include production frontend URL
    production_origins = [
        settings.FRONTEND_URL, # Ensure frontend URL is always included
        settings.BASE_URL # Ensure base URL is also included
    ]
    
    # Add localhost for development
    if settings.ENVIRONMENT == "development":
        dev_origins = [
            "http://localhost:3000",
            "http://localhost:8000", 
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000"
        ]
        cors_origins.extend(dev_origins)
    
    # Ensure production origins are always included
    for origin in production_origins:
        if origin not in cors_origins:
            cors_origins.append(origin)
    
    # Debug CORS configuration in production
    logger.info(f"CORS origins configured: {cors_origins}")
    logger.info(f"Frontend URL: {settings.FRONTEND_URL}")
    logger.info(f"Base URL: {settings.BASE_URL}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    # FORCE CORS origins to ensure frontend works
    cors_origins = [
        "https://cryptouniverse-frontend.onrender.com",
        "https://cryptouniverse.onrender.com",
        "http://localhost:3000",
        "http://localhost:8000"
    ]
    
    logger.info(f"Final CORS origins being used: {cors_origins}")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,  # Remove fallback to wildcard
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=86400  # Cache preflight for 24 hours
    )
    
    # Add explicit OPTIONS handler for troubleshooting
    @app.options("/{path:path}")
    async def handle_options(path: str):
        """Handle preflight OPTIONS requests explicitly."""
        from fastapi.responses import Response
        response = Response()
        response.headers["Access-Control-Allow-Origin"] = settings.FRONTEND_URL
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response
    
    # Note: Health and root endpoints are defined at module scope to avoid duplication

    # Add SessionMiddleware for OAuth
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

    # Security middleware
    if settings.allowed_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

    # Custom middleware - Order matters! Applied in reverse order
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)  # Re-enabled with Redis failover
    app.add_middleware(TenantMiddleware)  # Re-enabled for multi-tenant isolation
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

    # ENTERPRISE: Add Global Exception Handler for CORS
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        # Log the full traceback for enterprise debugging
        logger.error("Unhandled exception", exc_info=True, method=request.method, path=request.url.path)
        
        # Let CORSMiddleware handle CORS headers
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected server error occurred. Please contact support."}
        )

    # Add CORS debugging endpoint (protected)
    @app.get("/debug/cors")
    async def debug_cors(request: Request):
        """Debug CORS configuration (development/admin only)."""
        # Always allow in development mode
        if settings.ENVIRONMENT == "development":
            return {
                "cors_origins": settings.cors_origins,
                "frontend_url": settings.FRONTEND_URL,
                "base_url": settings.BASE_URL,
                "environment": settings.ENVIRONMENT,
                "headers_info": "Check browser network tab for Access-Control-Allow-Origin header"
            }
        
        # In production, check for debug token first (most secure)
        debug_token = request.headers.get("X-Debug-Token")
        if debug_token and settings.DEBUG_TOKEN and debug_token == settings.DEBUG_TOKEN:
            logger.info("Debug CORS endpoint accessed with valid token", 
                       client_ip=request.client.host if request.client else "unknown")
            return {
                "cors_origins": settings.cors_origins,
                "frontend_url": settings.FRONTEND_URL,
                "base_url": settings.BASE_URL,
                "environment": settings.ENVIRONMENT,
                "headers_info": "Check browser network tab for Access-Control-Allow-Origin header"
            }
        
        # Access denied - log the attempt
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        logger.warning("Unauthorized debug endpoint access", 
                      client_ip=client_ip,
                      user_agent=user_agent,
                      path="/debug/cors")
        
        # Return 403 without exposing system details
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return app


# Create application instance
app = create_application()

# Health check endpoint
@app.get("/health", tags=["System"])
@app.head("/health", tags=["System"])
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

    # Check Redis health
    try:
        redis = await get_redis_client()
        if redis:
            await redis.ping()
            health_status["checks"]["redis"] = "connected"
        else:
            health_status["checks"]["redis"] = "unavailable"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["redis"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check background services
    try:
        services_health = await background_manager.health_check()
        running_services = sum(1 for status in services_health.values() if status == "running")
        total_services = len(services_health)
        health_status["checks"]["background_services"] = f"{running_services}/{total_services} running"
        if running_services < total_services / 2:
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["background_services"] = f"error: {str(e)}"

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
@app.head("/", tags=["System"])
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


# Global WebSocket endpoint for real-time updates
@app.websocket("/ws/{path:path}")
async def global_websocket_endpoint(websocket: WebSocket, path: str):
    """
    Global WebSocket endpoint that routes to appropriate service handlers.
    Handles authentication and routing for all WebSocket connections.
    """
    try:
        # Import WebSocket manager
        from app.services.websocket import manager
        
        # Extract user authentication from bearer subprotocol header
        user_id = "anonymous"
        token = None
        selected_subprotocol = None  # Initialize to None, only set if safe subprotocol offered
        
        # Read subprotocols from Sec-WebSocket-Protocol header
        subprotocols = getattr(websocket, 'scope', {}).get('subprotocols', [])
        
        # Scan client-offered subprotocols for bearer token format
        safe_subprotocols = {"json", "jwt"}  # Safe subprotocols we can echo back
        
        if subprotocols:
            # Look for bearer authentication pattern: ["bearer", <token>, "json"]
            bearer_index = None
            for i, subprotocol in enumerate(subprotocols):
                # Check if this is a safe subprotocol we can echo back
                if subprotocol.lower() in safe_subprotocols:
                    selected_subprotocol = subprotocol.lower()
                
                # Check for bearer indicator
                if subprotocol.lower() == "bearer":
                    bearer_index = i
                    break
            
            # If bearer found, look for JWT token in next subprotocol entry
            if bearer_index is not None and bearer_index + 1 < len(subprotocols):
                token = subprotocols[bearer_index + 1]
        
        # Validate token if provided
        if token:
            try:
                from app.core.security import verify_access_token
                payload = verify_access_token(token)
                if payload and payload.get("sub"):
                    user_id = payload["sub"]
                    logger.info("WebSocket authenticated via bearer subprotocol", user_id=user_id, path=path)
                else:
                    # Invalid token - reject connection
                    await websocket.close(code=1008, reason="Invalid authentication token")
                    return
            except JWTError as e:
                logger.warning("WebSocket JWT authentication failed, rejecting connection", 
                             path=path, error=str(e), exc_info=True)
                await websocket.close(code=1008, reason="Authentication failed")
                return
        
        # Accept connection - only pass subprotocol if safe one was offered by client
        if selected_subprotocol:
            await websocket.accept(subprotocol=selected_subprotocol)
        else:
            await websocket.accept()
        
        # Connect to WebSocket manager
        await manager.connect(websocket, user_id)
        
        # Handle different WebSocket paths
        if path.startswith("api/v1/trading/ws"):
            # Market data and trading updates - allow anonymous
            await manager.subscribe_to_market_data(websocket, ["BTC", "ETH", "SOL"])
        elif path.startswith("api/v1/ai-consensus"):
            # AI consensus updates - require authentication
            if user_id == "anonymous":
                await websocket.close(code=1008, reason="Authentication required for AI consensus")
                return
            await manager.subscribe_to_ai_consensus(websocket, user_id)
        
        # Keep connection alive and handle messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "subscribe_market":
                    symbols = message.get("symbols", [])
                    await manager.subscribe_to_market_data(websocket, symbols)
                    await websocket.send_json({
                        "type": "subscription_confirmed",
                        "symbols": symbols,
                        "path": path
                    })
                elif message_type == "subscribe_ai_consensus":
                    # Verify (1) connection path is ai-consensus endpoint and (2) user is authenticated
                    if not path.startswith("api/v1/ai-consensus"):
                        await websocket.send_json({
                            "type": "error",
                            "message": "unauthorized - wrong endpoint for AI consensus subscription"
                        })
                        continue
                    
                    if user_id == "anonymous":
                        await websocket.send_json({
                            "type": "error", 
                            "message": "unauthorized - authentication required for AI consensus"
                        })
                        continue
                    
                    await manager.subscribe_to_ai_consensus(websocket, user_id)
                    await websocket.send_json({
                        "type": "ai_consensus_subscription_confirmed",
                        "user_id": user_id
                    })
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                # Log the original exception server-side including traceback
                logger.exception("WebSocket message handling error", user_id=user_id, path=path, error=str(e))
                try:
                    # Send generic error message to client instead of exception string
                    await websocket.send_json({
                        "type": "error",
                        "message": "internal server error"
                    })
                except (ConnectionError, WebSocketDisconnect) as send_error:
                    # Log send failures rather than silently ignoring
                    logger.warning("Failed to send error message to WebSocket client", 
                                 user_id=user_id, path=path, send_error=str(send_error))
    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected normally", user_id=user_id, path=path)
    except Exception as e:
        logger.exception("WebSocket connection error", user_id=user_id, path=path)
    finally:
        try:
            await manager.disconnect(websocket, user_id)
        except Exception as e:
            logger.exception("WebSocket disconnect cleanup failed", user_id=user_id, error=str(e))


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