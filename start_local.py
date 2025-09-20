#!/usr/bin/env python3
"""
Local development startup script for CryptoUniverse.
Uses SQLite database and graceful Redis degradation.
"""
import os
import sys
import asyncio
import uvicorn
from pathlib import Path

# Set local environment
os.environ["ENV_FILE"] = ".env.local"

# Ensure we're in the right directory
project_root = Path(__file__).parent
os.chdir(project_root)

print("🚀 Starting CryptoUniverse in LOCAL DEVELOPMENT mode...")
print(f"📁 Working directory: {project_root}")
print("🔧 Using SQLite database and Redis graceful degradation")

async def main():
    """Main startup function with local configuration."""
    try:
        # Import after setting environment
        from app.core.config import get_settings
        settings = get_settings()

        print(f"🌟 Environment: {settings.ENVIRONMENT}")
        print(f"🔌 Database: SQLite (local)")
        print(f"📡 Redis: Graceful degradation")
        print(f"🌐 Server: http://localhost:{settings.PORT}")

        # Test basic imports
        from app.core.database import engine
        from app.core.redis import get_redis_client

        # Test database connection with SQLite
        print("\n🔍 Testing database connection...")
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            print("✅ SQLite database connected!")

        # Test Redis (should gracefully degrade)
        print("\n🔍 Testing Redis connection...")
        redis = await get_redis_client()
        if redis:
            print("✅ Redis connected!")
        else:
            print("⚠️  Redis unavailable - using graceful degradation")

        print("\n🎯 Starting FastAPI server...")

        # Start the server
        config = uvicorn.Config(
            "main:app",
            host="0.0.0.0",
            port=settings.PORT,
            reload=True,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()

    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Startup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())