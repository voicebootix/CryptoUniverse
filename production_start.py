#!/usr/bin/env python3
"""
CryptoUniverse Enterprise - Production Startup Script

Enterprise-grade startup script for production deployment with Supabase database,
proper health checks, database migrations, and service initialization.

No mock data, no placeholders - production-ready deployment.
"""

import asyncio
import os
import sys
import signal
from datetime import datetime
from pathlib import Path

import structlog
import uvicorn
from sqlalchemy import text

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import get_settings
from app.core.database import engine, db_manager
from app.core.redis import get_redis_client
from app.core.logging import configure_logging
from app.services.background import BackgroundServiceManager
from app.services.user_exchange_service import user_exchange_service
from app.services.real_market_data_service import real_market_data_service
from main import create_application

# Initialize settings and logging
settings = get_settings()
configure_logging(settings.LOG_LEVEL, settings.ENVIRONMENT)
logger = structlog.get_logger(__name__)

# Global references
app = None
background_manager = None
shutdown_event = asyncio.Event()


async def check_database_connection():
    """Check and validate Supabase database connection."""
    logger.info("🔍 Checking Supabase database connection...")
    
    try:
        # Test basic connection
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info("✅ Database connected", version=version[:50] + "..." if len(version) > 50 else version)
        
        # Check if tables exist
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            
            required_tables = [
                'users', 'tenants', 'exchange_accounts', 'exchange_api_keys', 
                'exchange_balances', 'trades', 'positions', 'orders',
                'trading_strategies', 'portfolios', 'credit_accounts'
            ]
            
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                logger.warning(
                    "⚠️ Missing database tables - migrations needed",
                    missing_tables=missing_tables,
                    existing_tables=tables
                )
                return False
            else:
                logger.info("✅ All required database tables exist", table_count=len(tables))
                return True
                
    except Exception as e:
        logger.error("❌ Database connection failed", error=str(e))
        return False


async def check_redis_connection():
    """Check Redis connection."""
    logger.info("🔍 Checking Redis connection...")
    
    try:
        redis = await get_redis_client()
        await redis.ping()
        
        # Test set/get operation
        test_key = "health_check_test"
        await redis.set(test_key, "ok", ex=10)
        result = await redis.get(test_key)
        
        if result == "ok":
            logger.info("✅ Redis connection and operations working")
            await redis.delete(test_key)
            return True
        else:
            logger.error("❌ Redis operations failed")
            return False
            
    except Exception as e:
        logger.error("❌ Redis connection failed", error=str(e))
        return False


async def check_exchange_apis():
    """Check if exchange APIs are accessible."""
    logger.info("🔍 Checking exchange API accessibility...")
    
    try:
        # Test public endpoints (no API keys needed)
        import aiohttp
        
        exchange_tests = [
            {"name": "binance", "url": "https://api.binance.com/api/v3/ping"},
            {"name": "kraken", "url": "https://api.kraken.com/0/public/SystemStatus"},
            {"name": "kucoin", "url": "https://api.kucoin.com/api/v1/status"},
            {"name": "coinbase", "url": "https://api.exchange.coinbase.com/time"}
        ]
        
        results = {}
        async with aiohttp.ClientSession() as session:
            for exchange in exchange_tests:
                try:
                    async with session.get(
                        exchange["url"], 
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        results[exchange["name"]] = {
                            "status": "online" if response.status == 200 else "offline",
                            "status_code": response.status
                        }
                except Exception as e:
                    results[exchange["name"]] = {"status": "offline", "error": str(e)}
        
        online_exchanges = [name for name, result in results.items() if result["status"] == "online"]
        
        logger.info(
            "📊 Exchange API status",
            online_exchanges=online_exchanges,
            total_tested=len(exchange_tests),
            results=results
        )
        
        return len(online_exchanges) > 0
        
    except Exception as e:
        logger.error("❌ Exchange API check failed", error=str(e))
        return False


async def run_database_migrations():
    """Run database migrations if needed."""
    logger.info("🔄 Checking database migrations...")
    
    try:
        # Import alembic programmatically
        from alembic.config import Config
        from alembic import command
        
        # Get alembic config
        alembic_cfg = Config("alembic.ini")
        
        # Override sqlalchemy.url with current DATABASE_URL
        if os.getenv("DATABASE_URL"):
            database_url = os.getenv("DATABASE_URL")
            # Convert to sync URL for alembic
            if database_url.startswith("postgresql+asyncpg://"):
                sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
            else:
                sync_url = database_url
            alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
        
        # Run migrations
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Database migrations completed")
        return True
        
    except Exception as e:
        logger.error("❌ Database migrations failed", error=str(e))
        return False


async def initialize_services():
    """Initialize all services."""
    logger.info("🚀 Initializing enterprise services...")
    
    try:
        # Initialize user exchange service
        logger.info("📊 Initializing user exchange service...")
        # Service is already initialized as global instance
        
        # Initialize real market data service
        logger.info("📈 Initializing real market data service...")
        # Service is already initialized as global instance
        
        # Test market data service
        market_test = await real_market_data_service.get_real_time_price("BTC")
        if market_test.get("success"):
            logger.info("✅ Real market data service operational", btc_price=market_test.get("price"))
        else:
            logger.warning("⚠️ Market data service issues", error=market_test.get("error"))
        
        logger.info("✅ All enterprise services initialized")
        return True
        
    except Exception as e:
        logger.error("❌ Service initialization failed", error=str(e))
        return False


async def startup_checks():
    """Comprehensive startup checks for production deployment."""
    logger.info("🔍 Starting enterprise-grade startup checks...")
    
    checks = [
        ("Database Connection", check_database_connection),
        ("Redis Connection", check_redis_connection),
        ("Exchange APIs", check_exchange_apis),
        ("Database Migrations", run_database_migrations),
        ("Service Initialization", initialize_services)
    ]
    
    failed_checks = []
    
    for check_name, check_func in checks:
        logger.info(f"🔄 Running check: {check_name}")
        try:
            success = await check_func()
            if success:
                logger.info(f"✅ {check_name} - PASSED")
            else:
                logger.error(f"❌ {check_name} - FAILED")
                failed_checks.append(check_name)
        except Exception as e:
            logger.error(f"❌ {check_name} - ERROR", error=str(e))
            failed_checks.append(check_name)
    
    if failed_checks:
        logger.error(
            "❌ Startup checks failed",
            failed_checks=failed_checks,
            total_checks=len(checks)
        )
        return False
    
    logger.info("🎉 All startup checks passed - system ready for production!")
    return True


async def graceful_shutdown():
    """Handle graceful shutdown."""
    logger.info("🔄 Initiating graceful shutdown...")
    
    try:
        # Stop background services
        if background_manager:
            await background_manager.stop_all()
            logger.info("✅ Background services stopped")
        
        # Close database connections
        await engine.dispose()
        logger.info("✅ Database connections closed")
        
        # Close Redis connections
        try:
            redis = await get_redis_client()
            await redis.close()
            logger.info("✅ Redis connections closed")
        except:
            pass
        
        logger.info("👋 Graceful shutdown completed")
        
    except Exception as e:
        logger.error("❌ Shutdown error", error=str(e))


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"📡 Received signal {signum} - initiating shutdown...")
    shutdown_event.set()


async def main():
    """Main application startup."""
    global app, background_manager
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info(
        "🚀 CryptoUniverse Enterprise starting...",
        environment=settings.ENVIRONMENT,
        version="2.0.0",
        database_url=settings.DATABASE_URL[:50] + "..." if settings.DATABASE_URL else "Not configured"
    )
    
    # Run startup checks
    startup_success = await startup_checks()
    
    if not startup_success:
        logger.error("❌ Startup checks failed - cannot start application")
        sys.exit(1)
    
    # Create application
    app = create_application()
    
    # Initialize background services
    background_manager = BackgroundServiceManager()
    
    # Start background services
    try:
        await background_manager.start_all()
        logger.info("✅ Background services started")
    except Exception as e:
        logger.error("❌ Failed to start background services", error=str(e))
        sys.exit(1)
    
    # Start the server
    logger.info(
        "🎉 CryptoUniverse Enterprise ready!",
        host=settings.HOST,
        port=settings.PORT,
        docs_url=f"{settings.BASE_URL}/api/docs" if settings.ENVIRONMENT == "development" else "Contact admin"
    )
    
    # Create uvicorn config
    config = uvicorn.Config(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
        reload=False,  # No reload in production
        workers=1  # Single worker for async app
    )
    
    server = uvicorn.Server(config)
    
    # Run server with graceful shutdown
    try:
        # Start server in background
        server_task = asyncio.create_task(server.serve())
        
        # Wait for shutdown signal
        await shutdown_event.wait()
        
        # Initiate graceful shutdown
        logger.info("🔄 Shutdown signal received - stopping server...")
        server.should_exit = True
        
        # Wait for server to stop
        await server_task
        
    except Exception as e:
        logger.error("❌ Server error", error=str(e))
    finally:
        # Cleanup
        await graceful_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Application stopped by user")
    except Exception as e:
        logger.error("❌ Application crashed", error=str(e))
        sys.exit(1)