#!/usr/bin/env python3
"""
Startup script for CryptoUniverse backend
Handles database initialization and admin user creation
"""

import asyncio
import os
import sys
from datetime import datetime

from app.utils.asyncio_compat import async_timeout

# Add app to path
sys.path.insert(0, '/app')

async def initialize_database():
    """Initialize database and create admin user with proper timeout handling."""
    max_retries = 3
    retry_delay = 10  # Increased from 5 seconds
    
    for attempt in range(max_retries):
        try:
            from app.core.database import engine, Base
            from app.models.user import User, UserRole, UserStatus
            from app.models.chat import ChatSession, ChatMessage, ChatSessionSummary  # Import chat models
            from app.core.config import get_settings
            from sqlalchemy.ext.asyncio import AsyncSession
            from sqlalchemy import select, text
            import bcrypt
            import uuid
            
            settings = get_settings()
            
            print(f"🔄 Initializing database... (attempt {attempt + 1}/{max_retries})")
            print(f"📊 Database URL pattern: postgresql://***@{settings.DATABASE_URL.split('@')[1].split('/')[0] if '@' in settings.DATABASE_URL else 'unknown'}/***")
            
            # First test basic connectivity with a longer timeout
            try:
                async with async_timeout(120):  # 2 minute timeout for connection test
                    async with engine.connect() as conn:
                        result = await conn.execute(text("SELECT 1"))
                        print("✅ Database connectivity verified")
            except asyncio.TimeoutError:
                print(f"⏱️ Database connection test timeout after 120s")
                if attempt < max_retries - 1:
                    print(f"⏱️ Waiting {retry_delay}s before retry...")
                    await asyncio.sleep(retry_delay)
                    # Dispose of the engine to reset connection pool
                    await engine.dispose()
                    continue
                else:
                    raise Exception("Database connection timeout after all retries")
            
            # Create all tables with explicit timeout
            try:
                async with async_timeout(90):  # 90 second timeout for table creation
                    async with engine.begin() as conn:
                        await conn.run_sync(Base.metadata.create_all)
                print("✅ Database tables created")
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    print(f"⏱️ Table creation timeout, retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    await engine.dispose()
                    continue
                else:
                    raise Exception("Table creation timeout after all retries")
            
            # Create admin user if it doesn't exist
            async with AsyncSession(engine) as session:
                # Check if admin exists
                result = await session.execute(
                    select(User).where(User.email == "admin@cryptouniverse.com")
                )
                admin_user = result.scalar_one_or_none()
                
                if not admin_user:
                    # Create admin user
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
                    
                    print(f"✅ Admin user created: admin@cryptouniverse.com / {password}")
                else:
                    print("✅ Admin user already exists")
            
            await engine.dispose()
            print("✅ Database initialization complete")
            return  # Success - exit retry loop
            
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"❌ Database initialization failed: {e}")
                print(f"⏱️ Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                print(f"❌ Database initialization failed after all retries: {e}")
                raise

if __name__ == "__main__":
    # Check if we should skip DB init (useful for deployments with connectivity issues)
    if os.getenv("SKIP_DB_INIT") == "true":
        print("⚠️ SKIP_DB_INIT is set - skipping database initialization")
        print("⚠️ Database tables and admin user may need to be created manually")
        sys.exit(0)
    
    try:
        asyncio.run(initialize_database())
    except Exception as e:
        print(f"❌ Fatal error during database initialization: {e}")
        # Check if this is a Render deployment
        if os.getenv("RENDER"):
            print("⚠️ This appears to be a Render deployment")
            print("⚠️ Database connectivity issues are common during build phase")
            print("⚠️ The application will attempt to create tables on first run")
            # Exit with 0 to allow deployment to continue
            sys.exit(0)
        else:
            sys.exit(1)
