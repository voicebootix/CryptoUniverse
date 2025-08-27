#!/usr/bin/env python3
"""
Create Admin User Script for CryptoUniverse Enterprise
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def create_admin_user():
    """Create the admin user if it doesn't exist."""
    try:
        # Import after path setup
        from app.core.database import get_database
        from app.models.user import User, UserRole, UserStatus
        from sqlalchemy.orm import Session
        import bcrypt
        
        print("🔐 Creating admin user...")
        
        # Get database session
        db_gen = get_database()
        db: Session = next(db_gen)
        
        # Admin credentials
        admin_email = os.getenv('ADMIN_EMAIL', 'admin@cryptouniverse.com')
        admin_password = os.getenv('ADMIN_PASSWORD', 'AdminPass123!')
        admin_name = os.getenv('ADMIN_NAME', 'System Administrator')
        
        # Check if admin user exists
        existing_user = db.query(User).filter(User.email == admin_email).first()
        
        if existing_user:
            print(f"✅ Admin user already exists: {admin_email}")
            
            # Update user to ensure it's active and has admin role
            existing_user.role = UserRole.ADMIN
            existing_user.status = UserStatus.ACTIVE
            existing_user.is_active = True
            existing_user.is_verified = True
            db.commit()
            print(f"✅ Updated existing user to admin status")
            return
        
        # Hash password
        password_bytes = admin_password.encode('utf-8')
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        hashed_password = hashed.decode('utf-8')
        
        # Create admin user
        admin_user = User(
            email=admin_email,
            hashed_password=hashed_password,
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            is_active=True,
            is_verified=True,
            two_factor_enabled=False,
            failed_login_attempts=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Add to database
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print(f"✅ Admin user created successfully!")
        print(f"   Email: {admin_email}")
        print(f"   Password: {admin_password}")
        print(f"   Role: {admin_user.role}")
        print(f"   Status: {admin_user.status}")
        print(f"   User ID: {admin_user.id}")
        
        # Close database session
        db.close()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the project root directory")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        sys.exit(1)

def main():
    """Main function."""
    print("🚀 CryptoUniverse Admin User Creation")
    print("=" * 40)
    
    # Run the async function
    asyncio.run(create_admin_user())
    
    print("=" * 40)
    print("🎉 Admin user setup complete!")
    print("\nYou can now login with:")
    print(f"Email: {os.getenv('ADMIN_EMAIL', 'admin@cryptouniverse.com')}")
    print(f"Password: {os.getenv('ADMIN_PASSWORD', 'AdminPass123!')}")

if __name__ == "__main__":
    main()
