#!/usr/bin/env python3
"""
Minimal startup script for CryptoUniverse Enterprise Backend
Bypasses complex dependencies that cause setuptools.build_meta issues
"""

import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set minimal environment variables
os.environ.setdefault('ENVIRONMENT', 'production')
os.environ.setdefault('HOST', '0.0.0.0')
os.environ.setdefault('PORT', '10000')
os.environ.setdefault('LOG_LEVEL', 'INFO')

# Required environment variables with defaults
if not os.environ.get('SECRET_KEY'):
    os.environ['SECRET_KEY'] = 'minimal-render-key-change-in-production-very-long-and-secure'

print("🚀 Starting CryptoUniverse Enterprise Backend (Minimal Mode)...")

try:
    # Import only the minimal FastAPI app
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    import uvicorn
    
    # Create minimal app
    app = FastAPI(
        title="CryptoUniverse Enterprise API",
        description="Cryptocurrency trading platform API",
        version="1.0.0"
    )
    
    @app.get("/")
    async def root():
        return {"message": "CryptoUniverse Enterprise API", "status": "running"}
    
    @app.get("/api/v1/status")
    async def status():
        return {
            "status": "healthy",
            "service": "cryptouniverse-backend",
            "version": "1.0.0",
            "environment": os.environ.get('ENVIRONMENT', 'production')
        }
    
    @app.get("/health")
    async def health():
        return {"status": "ok"}
    
    if __name__ == "__main__":
        # Get settings
        host = os.environ.get('HOST', '0.0.0.0')
        port = int(os.environ.get('PORT', 10000))
        log_level = os.environ.get('LOG_LEVEL', 'info').lower()
        
        print(f"🌍 Environment: {os.environ.get('ENVIRONMENT')}")
        print(f"🌐 Host: {host}:{port}")
        print(f"📚 API Documentation: http://{host}:{port}/docs")
        
        # Start the server
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level=log_level,
            access_log=True,
            server_header=False,
            date_header=False,
        )
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("📦 Some dependencies may not be installed correctly")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Startup error: {e}")
    sys.exit(1)
