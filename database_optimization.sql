-- =====================================================
-- ENTERPRISE DATABASE OPTIMIZATION SCRIPT
-- Phase 4: Performance Optimization
-- =====================================================
--
-- ⚠️  CRITICAL: TRANSACTION REQUIREMENTS
-- =====================================================
-- This script contains CREATE INDEX CONCURRENTLY and VACUUM statements
-- that MUST be executed outside a transaction to avoid failures.
--
-- For manual execution:
--   psql -d your_database -f database_optimization.sql
--
-- For migrations (Alembic):
--   Use autocommit_block with postgresql_concurrently=True
--   or equivalent DB client settings
--
-- =====================================================

-- 1. CRITICAL INDEXES FOR FREQUENTLY QUERIED COLUMNS
-- =====================================================

-- User-related indexes
-- Note: idx_users_id removed - primary key already indexed
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_created_at ON users(created_at);
-- Additional covering index for user lookups with all frequently accessed columns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_id_covering ON users(id, email, username, is_active, is_admin, created_at, updated_at);

-- User sessions indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_sessions_created_at ON user_sessions(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_sessions_user_id_created_at ON user_sessions(user_id, created_at);

-- Chat-related indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_sessions_created_at ON chat_sessions(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_sessions_user_id_created_at ON chat_sessions(user_id, created_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_session_id_created_at ON chat_messages(session_id, created_at);
-- Additional index for timestamp-based queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_timestamp ON chat_messages(timestamp);

-- Trading strategies indexes
-- Note: idx_trading_strategies_id removed - primary key already indexed
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trading_strategies_strategy_type ON trading_strategies(strategy_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trading_strategies_created_at ON trading_strategies(created_at);

-- User strategy access indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_strategy_access_user_id ON user_strategy_access(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_strategy_access_strategy_id ON user_strategy_access(strategy_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_strategy_access_is_active ON user_strategy_access(is_active);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_strategy_access_user_id_active ON user_strategy_access(user_id, is_active);

-- Exchange accounts indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exchange_accounts_user_id ON exchange_accounts(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exchange_accounts_exchange_name ON exchange_accounts(exchange_name);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exchange_accounts_user_id_exchange ON exchange_accounts(user_id, exchange_name);

-- Exchange balances indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exchange_balances_account_id ON exchange_balances(account_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exchange_balances_symbol ON exchange_balances(symbol);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exchange_balances_updated_at ON exchange_balances(updated_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exchange_balances_account_id_updated_at ON exchange_balances(account_id, updated_at);

-- Portfolio snapshots indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_portfolio_snapshots_user_id ON portfolio_snapshots(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_portfolio_snapshots_created_at ON portfolio_snapshots(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_portfolio_snapshots_user_id_created_at ON portfolio_snapshots(user_id, created_at);

-- Trades indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_user_id ON trades(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_strategy_id ON trades(strategy_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_created_at ON trades(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_user_id_created_at ON trades(user_id, created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_strategy_id_created_at ON trades(strategy_id, created_at);

-- Performance metrics indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_performance_metrics_strategy_id ON performance_metrics(strategy_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_performance_metrics_user_id ON performance_metrics(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_performance_metrics_created_at ON performance_metrics(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_performance_metrics_strategy_id_created_at ON performance_metrics(strategy_id, created_at);

-- Backtest results indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_backtest_results_strategy_id ON backtest_results(strategy_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_backtest_results_user_id ON backtest_results(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_backtest_results_created_at ON backtest_results(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_backtest_results_strategy_id_created_at ON backtest_results(strategy_id, created_at);

-- Credit transactions indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_credit_transactions_user_id ON credit_transactions(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_credit_transactions_created_at ON credit_transactions(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_credit_transactions_user_id_created_at ON credit_transactions(user_id, created_at);

-- System configuration indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_system_configuration_key ON system_configuration(key);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_system_configuration_updated_at ON system_configuration(updated_at);

-- 2. COMPOSITE INDEXES FOR COMPLEX QUERIES
-- =====================================================

-- Multi-column indexes for common query patterns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_sessions_user_id_active_created ON user_sessions(user_id, is_active, created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_session_id_type_created ON chat_messages(session_id, message_type, created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_user_id_strategy_created ON trades(user_id, strategy_id, created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exchange_balances_account_symbol_updated ON exchange_balances(account_id, symbol, updated_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_performance_metrics_user_strategy_created ON performance_metrics(user_id, strategy_id, created_at);

-- 3. PARTIAL INDEXES FOR ACTIVE RECORDS
-- =====================================================

-- Only index active records to reduce index size
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_strategy_access_active ON user_strategy_access(user_id, strategy_id) WHERE is_active = true;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exchange_accounts_active ON exchange_accounts(user_id, exchange_name) WHERE is_active = true;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trading_strategies_active ON trading_strategies(id, strategy_type) WHERE is_active = true;

-- 4. COVERING INDEXES FOR FREQUENT SELECTS
-- =====================================================

-- Covering indexes to avoid table lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_id_email_role ON users(id, email, role);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_sessions_user_id_session_created ON user_sessions(user_id, session_id, created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_sessions_user_id_id_created ON chat_sessions(user_id, id, created_at);

-- 5. STATISTICS UPDATE
-- =====================================================

-- Update table statistics for better query planning
ANALYZE users;
ANALYZE user_sessions;
ANALYZE chat_sessions;
ANALYZE chat_messages;
ANALYZE trading_strategies;
ANALYZE user_strategy_access;
ANALYZE exchange_accounts;
ANALYZE exchange_balances;
ANALYZE portfolio_snapshots;
ANALYZE trades;
ANALYZE performance_metrics;
ANALYZE backtest_results;
ANALYZE credit_transactions;
ANALYZE system_configuration;

-- 6. QUERY OPTIMIZATION SETTINGS
-- =====================================================

-- PostgreSQL cluster-level optimization (requires superuser privileges)
-- =====================================================
-- The following ALTER SYSTEM statements require superuser privileges
-- and cluster-wide changes. They should be executed by DBAs or in
-- infrastructure-as-code playbooks, not in application-managed scripts.
--
-- Required cluster-level changes:
-- ALTER SYSTEM SET shared_buffers = '256MB';
-- ALTER SYSTEM SET effective_cache_size = '1GB';
-- ALTER SYSTEM SET maintenance_work_mem = '64MB';
-- ALTER SYSTEM SET checkpoint_completion_target = 0.9;
-- ALTER SYSTEM SET wal_buffers = '16MB';
-- ALTER SYSTEM SET default_statistics_target = 100;
--
-- After executing these commands, restart PostgreSQL or reload configuration:
-- SELECT pg_reload_conf();
--
-- For application-level tuning, use session-level SET commands in
-- database connection initialization instead.

-- 7. VACUUM AND REINDEX
-- =====================================================

-- Clean up and optimize tables
VACUUM ANALYZE users;
VACUUM ANALYZE user_sessions;
VACUUM ANALYZE chat_sessions;
VACUUM ANALYZE chat_messages;
VACUUM ANALYZE trading_strategies;
VACUUM ANALYZE user_strategy_access;
VACUUM ANALYZE exchange_accounts;
VACUUM ANALYZE exchange_balances;
VACUUM ANALYZE portfolio_snapshots;
VACUUM ANALYZE trades;
VACUUM ANALYZE performance_metrics;
VACUUM ANALYZE backtest_results;
VACUUM ANALYZE credit_transactions;
VACUUM ANALYZE system_configuration;

-- 8. MONITORING QUERIES
-- =====================================================

-- Query to monitor slow queries (run this to check performance)
-- SELECT query, mean_time, calls, total_time 
-- FROM pg_stat_statements 
-- WHERE mean_time > 1000 
-- ORDER BY mean_time DESC 
-- LIMIT 10;

-- Query to check index usage
-- SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
-- FROM pg_stat_user_indexes 
-- WHERE idx_scan = 0 
-- ORDER BY schemaname, tablename, indexname;

COMMIT;