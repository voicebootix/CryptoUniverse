#!/usr/bin/env python3
"""
Render-optimized startup script for CryptoUniverse Enterprise Backend
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set default environment variables for Render
os.environ.setdefault('ENVIRONMENT', 'production')
os.environ.setdefault('HOST', '0.0.0.0')
os.environ.setdefault('PORT', '10000')
os.environ.setdefault('LOG_LEVEL', 'INFO')

# Required environment variables with defaults for development
if not os.environ.get('SECRET_KEY'):
    os.environ['SECRET_KEY'] = 'render-development-key-change-in-production-make-it-very-long-and-secure-for-real-deployment'

if not os.environ.get('DATABASE_URL'):
    # This will be set by Render automatically when you add a database
    print("⚠️  DATABASE_URL not set - will be provided by Render database service")

if not os.environ.get('REDIS_URL'):
    # This will be set by Render automatically when you add Redis
    print("⚠️  REDIS_URL not set - will be provided by Render Redis service")

try:
    import uvicorn
    from app.core.config import get_settings
    
    print("🚀 Starting CryptoUniverse Enterprise Backend...")
    
    # Get settings
    settings = get_settings()
    
    print(f"🌍 Environment: {settings.ENVIRONMENT}")
    print(f"🌐 Host: {settings.HOST}:{settings.PORT}")
    
    # Configure uvicorn for Render
    config = {
        "app": "main:app",
        "host": settings.HOST,
        "port": int(settings.PORT),
        "log_level": settings.LOG_LEVEL.lower(),
        "access_log": True,
        "server_header": False,
        "date_header": False,
        "workers": 1,  # Single worker for Render starter plan
    }
    
    if settings.ENVIRONMENT == "production":
        config.update({
            "reload": False,
            "debug": False,
        })
    else:
        config.update({
            "reload": True,
            "debug": True,
        })
    
    print("🎯 CryptoUniverse Backend is starting...")
    print(f"📚 API Documentation will be available at: http://{settings.HOST}:{settings.PORT}/api/docs")
    
    # Start the server
    uvicorn.run(**config)
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("📦 Installing missing dependencies...")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Startup error: {e}")
    sys.exit(1)
