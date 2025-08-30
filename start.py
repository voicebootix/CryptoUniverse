#!/usr/bin/env python3
"""
CryptoUniverse Enterprise AI Money Manager - Startup Script

Production-ready startup script with proper initialization, health checks,
and graceful shutdown for the enterprise trading platform.
"""

import asyncio
import signal
import sys
import os
from datetime import datetime
from pathlib import Path

import structlog
import uvicorn
from fastapi import FastAPI

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import get_settings
from app.core.database import database, engine
from app.core.redis import redis_client
from app.core.logging import configure_logging
from app.services.background import BackgroundServiceManager
from main import create_application

# Initialize settings and logging
settings = get_settings()
configure_logging(settings.LOG_LEVEL, settings.ENVIRONMENT)
logger = structlog.get_logger(__name__)

# Global references
app: FastAPI = None
background_manager: BackgroundServiceManager = None
shutdown_event = asyncio.Event()


async def startup_checks():
    """Perform startup health checks and initialization."""
    logger.info("🔍 Performing startup checks...")
    
    try:
        # Check database connection
        logger.info("📊 Checking database connection...")
        await database.connect()
        await database.execute("SELECT 1")
        logger.info("✅ Database connection successful")
        
        # Check Redis connection
        logger.info("📦 Checking Redis connection...")
        await redis_client.ping()
        logger.info("✅ Redis connection successful")
        
        # Verify required environment variables
        logger.info("⚙️ Checking environment configuration...")
        required_vars = ["SECRET_KEY", "DATABASE_URL", "REDIS_URL"]
        missing_vars = []
        
        for var in required_vars:
            if not getattr(settings, var, None):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"❌ Missing required environment variables: {missing_vars}")
            return False
        
        logger.info("✅ Environment configuration valid")
        
        # Check API dependencies
        logger.info("🔑 Checking API dependencies...")
        
        # Enhanced market data API check with all sources
        try:
            from app.services.market_data_feeds import market_data_feeds
            from app.services.health_monitor import health_monitor
            
            # Initialize health monitor (which will initialize market_data_feeds)
            await health_monitor.initialize()
            
            # Test primary API
            btc_price = await market_data_feeds.get_real_time_price("BTC")
            if btc_price.get("success"):
                logger.info(f"✅ Market data APIs accessible - BTC price: ${btc_price['data']['price']}")
                logger.info(f"✅ Data source: {btc_price['data']['source']}")
            else:
                logger.warning("⚠️ Market data APIs may have limited access")
            
            # Check API key configuration
            api_keys_status = []
            if hasattr(settings, 'ALPHA_VANTAGE_API_KEY') and settings.ALPHA_VANTAGE_API_KEY:
                api_keys_status.append("Alpha Vantage ✅")
            else:
                api_keys_status.append("Alpha Vantage ❌")
            
            if hasattr(settings, 'COINGECKO_API_KEY') and settings.COINGECKO_API_KEY:
                api_keys_status.append("CoinGecko ✅")
            else:
                api_keys_status.append("CoinGecko ❌")
            
            if hasattr(settings, 'FINNHUB_API_KEY') and settings.FINNHUB_API_KEY:
                api_keys_status.append("Finnhub ✅")
            else:
                api_keys_status.append("Finnhub ❌")
            
            logger.info(f"🔑 API Keys Status: {', '.join(api_keys_status)}")
            
        except Exception as e:
            logger.warning(f"⚠️ Market data API check failed: {e}")
        
        # Supabase check
        try:
            from app.core.supabase import supabase_client
            health = await supabase_client.get_system_health()
            if health.get("connected"):
                logger.info("✅ Supabase integration active")
            else:
                logger.info("ℹ️ Supabase running in mock mode")
        except Exception as e:
            logger.warning(f"⚠️ Supabase check failed: {e}")
        
        logger.info("🎉 All startup checks passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Startup check failed: {e}")
        return False


async def initialize_services():
    """Initialize all background services."""
    global background_manager
    
    logger.info("🚀 Initializing background services...")
    
    try:
        background_manager = BackgroundServiceManager()
        await background_manager.start_all()
        logger.info("✅ Background services initialized")
        
        # Display service status
        status = await background_manager.health_check()
        logger.info(f"📊 Service status: {len(status)} services running")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}")
        return False


async def graceful_shutdown():
    """Perform graceful shutdown of all services."""
    logger.info("🔄 Starting graceful shutdown...")
    
    try:
        # Stop background services
        if background_manager:
            await background_manager.stop_all()
            logger.info("✅ Background services stopped")
        
        # Disconnect from database
        await database.disconnect()
        logger.info("✅ Database disconnected")
        
        # Close Redis connection
        await redis_client.close()
        logger.info("✅ Redis connection closed")
        
        logger.info("👋 Graceful shutdown completed")
        
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"📡 Received signal {signum}, initiating shutdown...")
    shutdown_event.set()


async def health_monitor():
    """Monitor system health during operation."""
    while not shutdown_event.is_set():
        try:
            await asyncio.sleep(300)  # Check every 5 minutes
            
            if background_manager:
                metrics = await background_manager.get_system_metrics()
                
                # Check for high resource usage
                cpu_usage = metrics.get("cpu_usage_percent", 0)
                memory_usage = metrics.get("memory", {}).get("usage_percent", 0)
                
                if cpu_usage > 90:
                    logger.warning(f"⚠️ High CPU usage: {cpu_usage}%")
                
                if memory_usage > 85:
                    logger.warning(f"⚠️ High memory usage: {memory_usage}%")
                
                # Log periodic health status
                logger.info(
                    f"💗 System health: CPU {cpu_usage}%, Memory {memory_usage}%, "
                    f"Uptime {metrics.get('uptime_hours', 0)}h"
                )
                
        except Exception as e:
            logger.error(f"Health monitor error: {e}")


async def main():
    """Main application entry point."""
    global app
    
    logger.info("🚀 Starting CryptoUniverse Enterprise AI Money Manager")
    logger.info(f"🌍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🐍 Python version: {sys.version}")
    logger.info(f"📍 Working directory: {os.getcwd()}")
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Perform startup checks
        if not await startup_checks():
            logger.error("❌ Startup checks failed, exiting...")
            sys.exit(1)
        
        # Initialize services
        if not await initialize_services():
            logger.error("❌ Service initialization failed, exiting...")
            sys.exit(1)
        
        # Create FastAPI application
        logger.info("🏗️ Creating FastAPI application...")
        app = create_application()
        logger.info("✅ FastAPI application created")
        
        # Start health monitor
        health_task = asyncio.create_task(health_monitor())
        
        # Configure uvicorn
        config = uvicorn.Config(
            app,
            host=settings.HOST,
            port=settings.PORT,
            log_level=settings.LOG_LEVEL.lower(),
            reload=settings.ENVIRONMENT == "development",
            access_log=True,
            server_header=False,
            date_header=False,
        )
        
        server = uvicorn.Server(config)
        
        logger.info(f"🌐 Starting server on {settings.HOST}:{settings.PORT}")
        logger.info(f"📖 API Documentation: http://{settings.HOST}:{settings.PORT}/api/docs")
        logger.info("🎯 AI Money Manager is ready for trading!")
        
        # Start server
        server_task = asyncio.create_task(server.serve())
        
        # Wait for shutdown signal
        await shutdown_event.wait()
        
        # Cancel health monitor
        health_task.cancel()
        
        # Stop server
        server.should_exit = True
        await server_task
        
    except KeyboardInterrupt:
        logger.info("📡 Received keyboard interrupt")
    except Exception as e:
        logger.error(f"❌ Application error: {e}")
        sys.exit(1)
    finally:
        await graceful_shutdown()


def run_production():
    """Run in production mode with gunicorn."""
    logger.info("🏭 Starting in production mode...")
    
    # Import here to avoid circular imports
    from gunicorn.app.wsgiapp import WSGIApplication
    
    class StandaloneApplication(WSGIApplication):
        def __init__(self, app, options=None):
            self.options = options or {}
            self.application = app
            super().__init__()
        
        def load_config(self):
            for key, value in self.options.items():
                if key in self.cfg.settings and value is not None:
                    self.cfg.set(key.lower(), value)
        
        def load(self):
            return self.application
    
    options = {
        'bind': f"{settings.HOST}:{settings.PORT}",
        'workers': settings.WORKERS or 4,
        'worker_class': 'uvicorn.workers.UvicornWorker',
        'worker_connections': 1000,
        'max_requests': 1000,
        'max_requests_jitter': 100,
        'timeout': 30,
        'keepalive': 2,
        'preload_app': True,
    }
    
    app = create_application()
    StandaloneApplication(app, options).run()


if __name__ == "__main__":
    if settings.ENVIRONMENT == "production":
        # Use gunicorn for production
        run_production()
    else:
        # Use asyncio for development
        asyncio.run(main())
