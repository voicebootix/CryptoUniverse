-- ========================================
-- SUPABASE PERFORMANCE FIXES
-- ========================================
-- Generated: 2025-11-06
-- Purpose: Drop unused indexes to improve write performance and reduce storage
--
-- IMPORTANT: Review carefully before running!
-- These indexes have not been used, but verify they're truly not needed
-- ========================================

BEGIN;

-- ========================================
-- PART 1: DROP UNUSED INDEXES
-- ========================================

-- Exchange Accounts Indexes
DROP INDEX IF EXISTS idx_exchange_accounts_status_trading_user;
DROP INDEX IF EXISTS idx_exchange_accounts_user_status_active;
DROP INDEX IF EXISTS idx_exchange_user_status;
DROP INDEX IF EXISTS idx_exchange_name_status;
DROP INDEX IF EXISTS idx_exchange_default;

-- Exchange Balances Indexes
DROP INDEX IF EXISTS idx_exchange_balances_account_nonzero;
DROP INDEX IF EXISTS idx_exchange_balances_sync_status;

-- Market Data Indexes
DROP INDEX IF EXISTS ix_market_data_symbol;
DROP INDEX IF EXISTS ix_market_data_timestamp;
DROP INDEX IF EXISTS ix_market_data_exchange;
DROP INDEX IF EXISTS idx_market_symbol_exchange_time;
DROP INDEX IF EXISTS idx_market_data_symbol_time;

-- Signal Channels
DROP INDEX IF EXISTS idx_signal_channels_slug;

-- Orderbook Snapshots
DROP INDEX IF EXISTS idx_orderbook_lookup;
DROP INDEX IF EXISTS ix_orderbook_snapshots_symbol;
DROP INDEX IF EXISTS ix_orderbook_snapshots_timestamp;
DROP INDEX IF EXISTS ix_orderbook_snapshots_exchange;

-- Technical Indicators
DROP INDEX IF EXISTS ix_technical_indicators_timestamp;
DROP INDEX IF EXISTS ix_technical_indicators_indicator_name;
DROP INDEX IF EXISTS idx_indicator_symbol_name_time;
DROP INDEX IF EXISTS ix_technical_indicators_symbol;

-- Strategy Performance History
DROP INDEX IF EXISTS idx_perf_history_user;
DROP INDEX IF EXISTS ix_strategy_performance_history_strategy_id;
DROP INDEX IF EXISTS ix_strategy_performance_history_user_id;
DROP INDEX IF EXISTS ix_strategy_performance_history_period_start;
DROP INDEX IF EXISTS idx_perf_history_lookup;

-- Trades Log
DROP INDEX IF EXISTS idx_trades_log_symbol;
DROP INDEX IF EXISTS idx_trades_log_status;
DROP INDEX IF EXISTS idx_trades_log_profitable;

-- Decisions Log
DROP INDEX IF EXISTS idx_decisions_log_type;
DROP INDEX IF EXISTS idx_decisions_log_confidence;
DROP INDEX IF EXISTS idx_decisions_log_executed;

-- AI Models
DROP INDEX IF EXISTS ix_ai_models_provider;

-- Trades
DROP INDEX IF EXISTS idx_trades_symbol_time;
DROP INDEX IF EXISTS idx_trades_session_id;

-- System Health
DROP INDEX IF EXISTS ix_system_health_status;
DROP INDEX IF EXISTS ix_system_health_service_name;

-- Portfolio Snapshots
DROP INDEX IF EXISTS idx_portfolio_snapshots_session_id;

-- AI Analysis Log
DROP INDEX IF EXISTS idx_ai_analysis_log_session_id;

-- Audit Logs
DROP INDEX IF EXISTS ix_audit_logs_user_id;
DROP INDEX IF EXISTS idx_audit_event_created;
DROP INDEX IF EXISTS ix_audit_logs_event_type;

-- Parameter Updates
DROP INDEX IF EXISTS idx_parameter_updates_timestamp;

-- Tenants
DROP INDEX IF EXISTS idx_tenant_slug;
DROP INDEX IF EXISTS ix_tenants_id;
DROP INDEX IF EXISTS idx_tenant_type_status;
DROP INDEX IF EXISTS idx_tenant_created;
DROP INDEX IF EXISTS idx_tenant_domain;

-- Subscription Plans
DROP INDEX IF EXISTS ix_subscription_plans_stripe_price_id_yearly;
DROP INDEX IF EXISTS ix_subscription_plans_id;
DROP INDEX IF EXISTS ix_subscription_plans_tier;
DROP INDEX IF EXISTS idx_plan_tier_active;
DROP INDEX IF EXISTS idx_plan_sort;
DROP INDEX IF EXISTS ix_subscription_plans_stripe_price_id_monthly;
DROP INDEX IF EXISTS ix_subscription_plans_stripe_price_id_quarterly;

-- Credit Packs
DROP INDEX IF EXISTS ix_credit_packs_stripe_product_id;
DROP INDEX IF EXISTS ix_credit_packs_pack_type;
DROP INDEX IF EXISTS idx_pack_type_active;
DROP INDEX IF EXISTS ix_credit_packs_stripe_price_id;
DROP INDEX IF EXISTS idx_pack_popular;
DROP INDEX IF EXISTS idx_pack_stripe;

-- Backtest Results
DROP INDEX IF EXISTS ix_backtest_results_strategy_id;
DROP INDEX IF EXISTS idx_backtest_lookup;
DROP INDEX IF EXISTS idx_backtest_user;

-- Background Tasks
DROP INDEX IF EXISTS ix_background_tasks_status;
DROP INDEX IF EXISTS ix_background_tasks_task_name;
DROP INDEX IF EXISTS idx_task_status_created;

-- Users
DROP INDEX IF EXISTS ix_users_tenant_id;

-- AB Test Variants
DROP INDEX IF EXISTS ix_ab_test_variants_status;

-- User Sessions
DROP INDEX IF EXISTS ix_user_sessions_user_id;

-- AB Test Results
DROP INDEX IF EXISTS ix_ab_test_results_date;

-- User Activities
DROP INDEX IF EXISTS ix_user_activities_activity_type;
DROP INDEX IF EXISTS idx_activity_flagged;
DROP INDEX IF EXISTS idx_activity_risk;
DROP INDEX IF EXISTS idx_activity_user_type;
DROP INDEX IF EXISTS ix_user_activities_user_id;
DROP INDEX IF EXISTS ix_user_activities_session_id;
DROP INDEX IF EXISTS ix_user_activities_activity_category;
DROP INDEX IF EXISTS idx_activity_category;
DROP INDEX IF EXISTS idx_activity_created;

-- Subscriptions
DROP INDEX IF EXISTS idx_subscription_status;
DROP INDEX IF EXISTS idx_subscription_billing_date;
DROP INDEX IF EXISTS ix_subscriptions_status;
DROP INDEX IF EXISTS ix_subscriptions_plan_id;
DROP INDEX IF EXISTS ix_subscriptions_stripe_customer_id;
DROP INDEX IF EXISTS idx_subscription_stripe;
DROP INDEX IF EXISTS ix_subscriptions_id;

-- AB Test Participants
DROP INDEX IF EXISTS ix_ab_test_participants_status;

-- AB Test Metrics
DROP INDEX IF EXISTS ix_ab_test_metrics_metric_date;

-- Trading Strategies
DROP INDEX IF EXISTS idx_trading_strategies_category;

-- Billing History
DROP INDEX IF EXISTS ix_billing_history_stripe_invoice_id;
DROP INDEX IF EXISTS ix_billing_history_stripe_charge_id;
DROP INDEX IF EXISTS ix_billing_history_stripe_payment_intent_id;
DROP INDEX IF EXISTS idx_billing_stripe_payment;
DROP INDEX IF EXISTS ix_billing_history_transaction_type;
DROP INDEX IF EXISTS ix_billing_history_id;
DROP INDEX IF EXISTS idx_billing_type_status;

-- Chat Sessions
DROP INDEX IF EXISTS idx_chat_sessions_user_activity;

COMMIT;

-- ========================================
-- PART 2: KEEP ESSENTIAL INDEXES
-- ========================================
-- These are the indexes you SHOULD keep (already exist, just documenting):

-- Critical indexes to KEEP:
-- - Primary keys (automatic)
-- - Foreign keys (for joins)
-- - idx_exchange_accounts_user_status_trading (if used for active trading queries)
-- - User lookup indexes that are actually being used

-- ========================================
-- PART 3: CREATE OPTIMIZED INDEXES
-- ========================================
-- Create better, more targeted indexes based on actual query patterns

BEGIN;

-- Example: Composite index for common query patterns
-- Only uncomment if you actually use these query patterns!

-- For finding active exchange accounts by user
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exchange_accounts_active_user
-- ON exchange_accounts(user_id, status)
-- WHERE status = 'ACTIVE';

-- For recent trades by user
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_user_recent
-- ON trades(user_id, created_at DESC)
-- WHERE created_at > NOW() - INTERVAL '30 days';

-- For active subscriptions by user
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_subscriptions_active_user
-- ON subscriptions(user_id, status)
-- WHERE status = 'active';

-- For market data queries
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_market_data_recent
-- ON market_data(symbol, timestamp DESC)
-- WHERE timestamp > NOW() - INTERVAL '7 days';

COMMIT;

-- ========================================
-- PART 4: ANALYZE ALL TABLES AFTER INDEX CHANGES
-- ========================================
BEGIN;

-- Update statistics for query planner across ALL public tables
-- This is important after dropping 100+ indexes
ANALYZE VERBOSE;

-- Note: ANALYZE VERBOSE will show progress for each table
-- This may take a few minutes depending on database size

COMMIT;

-- ========================================
-- SUCCESS MESSAGE
-- ========================================
DO $$
BEGIN
  RAISE NOTICE '✅ Unused indexes have been dropped!';
  RAISE NOTICE '📊 Storage space saved and write performance improved!';
  RAISE NOTICE '⚠️  Monitor query performance and recreate indexes if needed';
END $$;
