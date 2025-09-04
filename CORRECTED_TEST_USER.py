#!/usr/bin/env python3
"""
CORRECTED TEST USER CREATION FOR TESTSPRITE
==========================================

Creates test user with correct database schema
Based on actual User model from app/models/user.py
"""

import bcrypt
import uuid
from datetime import datetime

def create_testsprite_user_sql():
    """Generate correct SQL for TestSprite test user."""
    
    print("🔧 CREATING CORRECTED TESTSPRITE USER SQL")
    print("=" * 50)
    
    # Generate user data
    user_id = str(uuid.uuid4())
    profile_id = str(uuid.uuid4())
    
    user_data = {
        "email": "test@cryptouniverse.com",
        "password": "TestPassword123!",
        "first_name": "TestSprite",
        "last_name": "User"
    }
    
    # Hash password
    password_hash = bcrypt.hashpw(
        user_data["password"].encode('utf-8'), 
        bcrypt.gensalt()
    ).decode('utf-8')
    
    current_time = datetime.utcnow().isoformat()
    
    print(f"📋 User Details:")
    print(f"   Email: {user_data['email']}")
    print(f"   Password: {user_data['password']}")
    print(f"   User ID: {user_id}")
    print(f"   Profile ID: {profile_id}")
    print()
    
    # Correct SQL based on actual schema
    users_sql = f"""-- TestSprite Test User Setup (CORRECTED SCHEMA)
-- Generated: {current_time}

-- Step 1: Insert into users table (main authentication data)
INSERT INTO users (
    id, 
    email, 
    hashed_password, 
    is_active, 
    is_verified, 
    role, 
    status, 
    tenant_id,
    two_factor_enabled,
    failed_login_attempts,
    kyc_status,
    created_at, 
    updated_at
) VALUES (
    '{user_id}',
    '{user_data["email"]}',
    '{password_hash}',
    true,
    true,
    'trader',
    'active',
    NULL,
    false,
    0,
    'not_started',
    '{current_time}',
    '{current_time}'
);

-- Step 2: Insert into user_profiles table (name and profile data)
INSERT INTO user_profiles (
    id,
    user_id,
    first_name,
    last_name,
    country,
    timezone,
    language,
    default_risk_level,
    preferred_exchanges,
    favorite_symbols,
    email_notifications,
    sms_notifications,
    telegram_notifications,
    push_notifications,
    public_profile,
    show_performance,
    allow_copy_trading,
    onboarding_completed,
    onboarding_step,
    ui_preferences,
    dashboard_layout,
    created_at,
    updated_at
) VALUES (
    '{profile_id}',
    '{user_id}',
    '{user_data["first_name"]}',
    '{user_data["last_name"]}',
    'US',
    'UTC',
    'en',
    'medium',
    '[]',
    '[]',
    true,
    false,
    false,
    true,
    false,
    false,
    false,
    true,
    10,
    '{{}}',
    '{{}}',
    '{current_time}',
    '{current_time}'
);

-- Verify the user was created
SELECT 
    u.id,
    u.email,
    u.is_active,
    u.is_verified,
    u.role,
    u.status,
    p.first_name,
    p.last_name
FROM users u
LEFT JOIN user_profiles p ON u.id = p.user_id
WHERE u.email = '{user_data["email"]}';
"""
    
    # Save to file
    filename = "testsprite_user_corrected.sql"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(users_sql)
    
    print(f"✅ Corrected SQL saved to: {filename}")
    print()
    print("📋 CORRECTED SQL:")
    print("-" * 50)
    print(users_sql)
    
    return filename

def main():
    """Generate corrected TestSprite user SQL."""
    
    print("🏢 ENTERPRISE TESTSPRITE USER CREATION (CORRECTED)")
    print("=" * 60)
    print("Using correct database schema from app/models/user.py")
    print()
    
    try:
        filename = create_testsprite_user_sql()
        
        print()
        print("🎯 DEPLOYMENT INSTRUCTIONS:")
        print("=" * 30)
        print("1. Connect to your production database")
        print(f"2. Execute the SQL from: {filename}")
        print("3. Verify both tables have the new records")
        print("4. Test login with credentials:")
        print("   Email: test@cryptouniverse.com")
        print("   Password: TestPassword123!")
        print("5. Run: python verify_testsprite_fixes.py")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
