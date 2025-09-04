-- TestSprite Test User Setup (CORRECTED SCHEMA)
-- Generated: 2025-09-04T08:28:45.698573

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
    '7bcaaac3-1fae-4a8b-8c0c-e83278edca2e',
    'test@cryptouniverse.com',
    '$2b$12$gEsrxsYN7O/Iktfv.g7V6eo9T0y7DvYgbAiwgJ0qqnawdroi.cdm.',
    true,
    true,
    'trader',
    'active',
    NULL,
    false,
    0,
    'not_started',
    '2025-09-04T08:28:45.698573',
    '2025-09-04T08:28:45.698573'
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
    '8d40cb5a-aacd-4722-a4e6-82f15fca1bfc',
    '7bcaaac3-1fae-4a8b-8c0c-e83278edca2e',
    'TestSprite',
    'User',
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
    '{}',
    '{}',
    '2025-09-04T08:28:45.698573',
    '2025-09-04T08:28:45.698573'
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
WHERE u.email = 'test@cryptouniverse.com';
