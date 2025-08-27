#!/usr/bin/env python3
"""
Simple Admin User Creation Script for CryptoUniverse
"""

import os
import sys
from datetime import datetime
import uuid

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def create_admin_user():
    """Create the admin user using synchronous SQLAlchemy."""
    try:
        # Import after path setup
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        import bcrypt
        
        print("🔐 Creating admin user...")
        
        # Database URL - use SQLite for simplicity or PostgreSQL if configured
        database_url = os.getenv('DATABASE_URL', 'sqlite:///./cryptouniverse.db')
        
        # Create engine
        engine = create_engine(database_url, echo=False)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Create session
        db = SessionLocal()
        
        # Admin credentials
        admin_email = os.getenv('ADMIN_EMAIL', 'admin@cryptouniverse.com')
        admin_password = os.getenv('ADMIN_PASSWORD', 'AdminPass123!')
        admin_name = os.getenv('ADMIN_NAME', 'System Administrator')
        
        # Check if users table exists, if not create it
        try:
            result = db.execute(text("SELECT COUNT(*) FROM users WHERE email = :email"), {"email": admin_email})
            user_count = result.scalar()
            
            if user_count > 0:
                print(f"✅ Admin user already exists: {admin_email}")
                
                # Update existing user to ensure admin status
                db.execute(text("""
                    UPDATE users 
                    SET role = 'admin', status = 'active', is_active = true, is_verified = true
                    WHERE email = :email
                """), {"email": admin_email})
                db.commit()
                print("✅ Updated existing user to admin status")
                return
                
        except Exception as e:
            print(f"⚠️ Users table might not exist, will create user anyway: {e}")
        
        # Hash password
        password_bytes = admin_password.encode('utf-8')
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        hashed_password = hashed.decode('utf-8')
        
        # Generate UUID
        user_id = str(uuid.uuid4())
        
        # Create admin user with raw SQL
        try:
            db.execute(text("""
                INSERT INTO users (
                    id, email, hashed_password, role, status, 
                    is_active, is_verified, two_factor_enabled, 
                    failed_login_attempts, created_at, updated_at
                ) VALUES (
                    :id, :email, :hashed_password, :role, :status,
                    :is_active, :is_verified, :two_factor_enabled,
                    :failed_login_attempts, :created_at, :updated_at
                )
            """), {
                "id": user_id,
                "email": admin_email,
                "hashed_password": hashed_password,
                "role": "admin",
                "status": "active", 
                "is_active": True,
                "is_verified": True,
                "two_factor_enabled": False,
                "failed_login_attempts": 0,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            
            db.commit()
            
            print(f"✅ Admin user created successfully!")
            print(f"   Email: {admin_email}")
            print(f"   Password: {admin_password}")
            print(f"   Role: admin")
            print(f"   Status: active")
            print(f"   User ID: {user_id}")
            
        except Exception as e:
            print(f"❌ Error inserting user: {e}")
            # Try alternative approach with different column names
            try:
                db.execute(text("""
                    INSERT INTO users (
                        id, email, password_hash, role, status, 
                        is_active, is_verified, mfa_enabled, 
                        failed_login_attempts, created_at, updated_at
                    ) VALUES (
                        :id, :email, :password_hash, :role, :status,
                        :is_active, :is_verified, :mfa_enabled,
                        :failed_login_attempts, :created_at, :updated_at
                    )
                """), {
                    "id": user_id,
                    "email": admin_email,
                    "password_hash": hashed_password,
                    "role": "admin",
                    "status": "active", 
                    "is_active": True,
                    "is_verified": True,
                    "mfa_enabled": False,
                    "failed_login_attempts": 0,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })
                
                db.commit()
                print(f"✅ Admin user created with alternative schema!")
                
            except Exception as e2:
                print(f"❌ Both insert attempts failed: {e2}")
                raise
        
        # Close database session
        db.close()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Installing required packages...")
        os.system("pip install bcrypt sqlalchemy")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        sys.exit(1)

def main():
    """Main function."""
    print("🚀 CryptoUniverse Simple Admin User Creation")
    print("=" * 45)
    
    create_admin_user()
    
    print("=" * 45)
    print("🎉 Admin user setup complete!")
    print("\nYou can now login with:")
    print(f"Email: {os.getenv('ADMIN_EMAIL', 'admin@cryptouniverse.com')}")
    print(f"Password: {os.getenv('ADMIN_PASSWORD', 'AdminPass123!')}")
    print("\n🔗 Login at: https://cryptouniverse-frontend.onrender.com")

if __name__ == "__main__":
    main()
