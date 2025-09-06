#!/usr/bin/env python3
"""
Create TestSprite test users in production database
Ensures test@cryptouniverse.com and admin@cryptouniverse.com exist for TestSprite testing
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent / "app"))

import bcrypt
from app.core.database import get_database, engine
from app.models.user import User, UserRole, UserStatus
from app.models.tenant import Tenant
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

async def create_testsprite_users():
    """Create test users required for TestSprite testing."""
    
    print("🧪 CREATING TESTSPRITE TEST USERS")
    print("=" * 50)
    
    try:
        # Get database session
        async for db in get_database():
            # Test user for TestSprite
            test_email = "test@cryptouniverse.com"
            test_password = "TestPassword123!"
            
            # Admin user for TestSprite
            admin_email = "admin@cryptouniverse.com"  
            admin_password = "AdminPass123!"
            
            # Check if test user exists
            result = await db.execute(select(User).filter(User.email == test_email))
            test_user = result.scalar_one_or_none()
            
            if not test_user:
                print(f"👤 Creating test user: {test_email}")
                
                # Hash password
                password_hash = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                # Create test user
                test_user = User(
                    id=uuid.uuid4(),
                    email=test_email,
                    hashed_password=password_hash,
                    role=UserRole.USER,
                    status=UserStatus.ACTIVE,
                    created_at=datetime.utcnow(),
                    email_verified=True  # Auto-verify for testing
                )
                
                db.add(test_user)
                print(f"✅ Test user created: {test_email}")
            else:
                print(f"✅ Test user already exists: {test_email}")
            
            # Check if admin user exists  
            result = await db.execute(select(User).filter(User.email == admin_email))
            admin_user = result.scalar_one_or_none()
            
            if not admin_user:
                print(f"👨‍💼 Creating admin user: {admin_email}")
                
                # Hash password
                password_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                # Create admin user
                admin_user = User(
                    id=uuid.uuid4(),
                    email=admin_email,
                    hashed_password=password_hash,
                    role=UserRole.ADMIN,
                    status=UserStatus.ACTIVE,
                    created_at=datetime.utcnow(),
                    email_verified=True  # Auto-verify for testing
                )
                
                db.add(admin_user)
                print(f"✅ Admin user created: {admin_email}")
            else:
                print(f"✅ Admin user already exists: {admin_email}")
            
            # Commit changes
            await db.commit()
            print("\n💾 Database changes committed successfully")
            
            print(f"\n🧪 TESTSPRITE TEST CREDENTIALS:")
            print(f"Test User: {test_email} / {test_password}")
            print(f"Admin User: {admin_email} / {admin_password}")
            
            print(f"\n🔗 Test Login Endpoints:")
            print(f"Production: https://cryptouniverse.onrender.com/api/v1/auth/login")
            print(f"Local: http://localhost:8000/api/v1/auth/login")
            
            break  # Exit the async generator loop
            
    except Exception as e:
        print(f"❌ Error creating test users: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False
        
    return True

async def test_auth_service():
    """Test that authentication service is working."""
    print("\n🔧 TESTING AUTH SERVICE")
    print("=" * 30)
    
    try:
        from app.api.v1.endpoints.auth import auth_service
        
        # Test password hashing
        test_password = "TestPassword123!"
        hashed = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Test password verification
        is_valid = auth_service.verify_password(test_password, hashed)
        
        if is_valid:
            print("✅ Auth service password verification working")
        else:
            print("❌ Auth service password verification failed")
            
        return is_valid
        
    except Exception as e:
        print(f"❌ Auth service test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main execution function."""
    print("🚀 TESTSPRITE USER SETUP")
    print("Setting up required test users for TestSprite testing...")
    print()
    
    try:
        # Test auth service first
        auth_ok = await test_auth_service()
        if not auth_ok:
            print("❌ Auth service test failed - aborting")
            return False
            
        # Create test users
        users_ok = await create_testsprite_users()
        if not users_ok:
            print("❌ User creation failed - aborting")
            return False
            
        print("\n🎯 SUCCESS: TestSprite users are ready!")
        print("You can now run TestSprite tests with the credentials above.")
        
        return True
        
    except Exception as e:
        print(f"❌ Setup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
