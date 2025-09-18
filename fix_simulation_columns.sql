-- Fix missing simulation columns in users table
-- This script adds the missing columns that are defined in the User model
-- but don't exist in the database

-- Add simulation_mode column (default to true for safety)
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS simulation_mode BOOLEAN NOT NULL DEFAULT true;

-- Add simulation_balance column (default 10000 USD virtual balance)
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS simulation_balance INTEGER NOT NULL DEFAULT 10000;

-- Add last_simulation_reset column
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS last_simulation_reset TIMESTAMP WITH TIME ZONE;

-- Create index for quick filtering on simulation mode
CREATE INDEX IF NOT EXISTS idx_users_simulation_mode ON users (simulation_mode);

-- Update users with active exchange accounts to live mode
UPDATE users
SET simulation_mode = false
WHERE id IN (
    SELECT DISTINCT user_id
    FROM exchange_accounts
    WHERE status = 'active'
    AND trading_enabled = true
)
AND simulation_mode = true;

-- Mark migration as applied in alembic version table
INSERT INTO alembic_version (version_num)
VALUES ('add_simulation_mode_to_users')
ON CONFLICT (version_num) DO NOTHING;

-- Verify the columns were added
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'users'
AND column_name IN ('simulation_mode', 'simulation_balance', 'last_simulation_reset')
ORDER BY column_name;