#!/usr/bin/env python3
"""
Create Test User for TestSprite
Enterprise-grade script to create required test user in production database
"""

import os
import sys
import asyncio
from pathlib import Path

# Add app to Python path
sys.path.append(str(Path(__file__).parent / "app"))

async def create_testsprite_user():
    """Create the test user required for TestSprite authentication tests."""
    
    print("CREATING TESTSPRITE TEST USER")
    print("=" * 40)
    
    try:
        # Import after adding to path
        import bcrypt
        import uuid
        from datetime import datetime
        
        # For production, you would use your actual database connection
        # This is a template - adapt for your specific database setup
        
        user_data = {
            "email": "test@cryptouniverse.com",
            "password": "TestPassword123!",
            "full_name": "TestSprite Test User",
            "role": "user",
            "status": "active"
        }
        
        # Hash the password
        password_hash = bcrypt.hashpw(
            user_data["password"].encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')
        
        user_id = str(uuid.uuid4())
        
        print(f"User ID: {user_id}")
        print(f"Email: {user_data['email']}")
        print(f"Password: {user_data['password']}")
        print(f"Password Hash: {password_hash[:20]}...")
        
        # SQL for manual database insertion
        sql_insert = f"""
INSERT INTO users (id, email, hashed_password, full_name, role, status, email_verified, created_at)
VALUES (
    '{user_id}',
    '{user_data["email"]}',
    '{password_hash}',
    '{user_data["full_name"]}',
    '{user_data["role"]}',
    '{user_data["status"]}',
    true,
    '{datetime.utcnow().isoformat()}'
);
"""
        
        print("\nSQL INSERT STATEMENT:")
        print("-" * 40)
        print(sql_insert)
        
        print("\nMANUAL DATABASE SETUP INSTRUCTIONS:")
        print("1. Connect to your production database")
        print("2. Execute the SQL INSERT statement above")
        print("3. Verify the user was created successfully")
        print("4. Test login with the credentials provided")
        
        # Save to file for easy access
        with open("testsprite_user_setup.sql", "w") as f:
            f.write("-- TestSprite Test User Setup\n")
            f.write("-- Generated automatically for production deployment\n\n")
            f.write(sql_insert)
        
        print(f"\nSQL saved to: testsprite_user_setup.sql")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Execute test user creation."""
    
    print("TestSprite Test User Generator")
    print("This script generates the SQL to create required test users")
    print()
    
    try:
        success = asyncio.run(create_testsprite_user())
        
        if success:
            print("\nSUCCESS: Test user SQL generated")
            print("Next steps:")
            print("1. Review testsprite_user_setup.sql")
            print("2. Execute the SQL in your production database")
            print("3. Run verify_testsprite_fixes.py to confirm")
        else:
            print("\nFAILED: Could not generate test user")
        
        return success
        
    except Exception as e:
        print(f"FAILED: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
