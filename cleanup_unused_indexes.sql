-- CRITICAL: Remove unused indexes that are slowing down your database
-- Based on your actual usage data, these indexes have 0 scans and are just overhead

-- Remove indexes on empty tables (0 rows)
DROP INDEX IF EXISTS ix_ai_signals_symbol;
DROP INDEX IF EXISTS ix_ai_signals_model_id;
DROP INDEX IF EXISTS ix_ai_signals_consensus_id;
DROP INDEX IF EXISTS idx_signal_symbol_model_created;
DROP INDEX IF EXISTS ix_ai_consensus_symbol;
DROP INDEX IF EXISTS idx_consensus_symbol_created;
DROP INDEX IF EXISTS ix_portfolios_id;  -- Table is empty
DROP INDEX IF EXISTS ix_trading_strategies_strategy_type;  -- Table is empty
DROP INDEX IF EXISTS ix_trading_strategies_user_id;  -- Table is empty
DROP INDEX IF EXISTS idx_trading_strategies_active_execution;  -- Table is empty

-- Remove redundant user indexes (you have 12 indexes on users table with only 8 rows!)
DROP INDEX IF EXISTS idx_user_email_active;  -- Redundant with ix_users_email
DROP INDEX IF EXISTS idx_user_status;  -- Low selectivity
DROP INDEX IF EXISTS idx_user_created;  -- Rarely used
DROP INDEX IF EXISTS idx_user_tenant_role;  -- tenant_id is null for all users
DROP INDEX IF EXISTS idx_users_auth_complete;  -- Complex partial index, rarely used

-- Remove redundant session indexes
DROP INDEX IF EXISTS ix_user_sessions_session_token;  -- You have ix_user_sessions_refresh_token
DROP INDEX IF EXISTS idx_session_user_active;  -- Low selectivity
DROP INDEX IF EXISTS idx_session_token;  -- Redundant
DROP INDEX IF EXISTS ix_user_sessions_device_id;  -- Device_id likely null
DROP INDEX IF EXISTS idx_user_sessions_token_expiry;  -- Complex, rarely used

-- Remove indexes on tables with minimal activity
DROP INDEX IF EXISTS idx_balance_symbol_usd;  -- Low selectivity on symbol
DROP INDEX IF EXISTS idx_balance_updated;  -- Updated_at rarely queried
DROP INDEX IF EXISTS idx_exchange_balances_nonzero_fast;  -- You'll replace with better one

-- Keep only the essential indexes that are actually being used:
-- 1. Primary keys (automatic)
-- 2. Foreign keys (for joins)
-- 3. Unique constraints (for data integrity)  
-- 4. High-usage indexes from your stats
