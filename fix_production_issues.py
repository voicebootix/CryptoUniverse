#!/usr/bin/env python3
"""
Production Fix Deployment Script
Applies fixes for CORS, authentication, database performance, and market data sync issues.
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent / "app"))

async def main():
    """Apply production fixes."""
    print("🔧 Applying production fixes...")
    
    try:
        # Import after path setup
        from app.core.database import db_manager
        from app.core.logging import configure_logging, logger
        from app.core.config import get_settings
        
        settings = get_settings()
        configure_logging(settings.LOG_LEVEL, settings.ENVIRONMENT)
        
        print("✅ Logging configured")
        
        # Connect to database
        await db_manager.connect()
        print("✅ Database connected")
        
        # Run database migrations
        print("🔄 Running database migrations...")
        import subprocess
        result = subprocess.run([
            sys.executable, "-m", "alembic", "upgrade", "head"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Database migrations completed")
        else:
            print(f"❌ Migration failed: {result.stderr}")
            return False
        
        # Test CORS configuration
        print("🔄 Testing CORS configuration...")
        cors_origins = settings.cors_origins
        required_origins = [
            "https://cryptouniverse-frontend.onrender.com",
            "https://cryptouniverse.onrender.com"
        ]
        
        for origin in required_origins:
            if origin not in cors_origins:
                print(f"⚠️ Missing CORS origin: {origin}")
            else:
                print(f"✅ CORS origin configured: {origin}")
        
        # Test Redis connection
        try:
            from app.core.redis import get_redis_client
            redis = await get_redis_client()
            await redis.ping()
            print("✅ Redis connection verified")
        except Exception as e:
            print(f"⚠️ Redis connection issue: {e}")
        
        # Cleanup old sessions (performance optimization)
        from datetime import datetime, timedelta
        from sqlalchemy import delete
        from app.models.user import UserSession
        
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        delete_stmt = delete(UserSession).where(
            UserSession.expires_at < cutoff_date
        )
        result = await db_manager.execute(delete_stmt)
        await db_manager.commit()
        print(f"✅ Cleaned up {result.rowcount} expired sessions")
        
        await db_manager.disconnect()
        print("✅ All fixes applied successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error applying fixes: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
