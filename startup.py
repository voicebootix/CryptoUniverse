#!/usr/bin/env python3
"""
Startup script for CryptoUniverse backend
Handles database initialization and admin user creation
"""

import asyncio
import os
import sys
from datetime import datetime

# Add app to path
sys.path.insert(0, '/app')

async def initialize_database():
    """Initialize database and create admin user."""
    try:
        from app.core.database import engine, Base
        from app.models.user import User, UserRole, UserStatus
        from app.core.config import get_settings
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy import select
        import bcrypt
        import uuid
        
        settings = get_settings()
        
        print("🔄 Initializing database...")
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created")
        
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
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(initialize_database())
