-- ========================================
-- SUPABASE SECURITY FIXES - COMPREHENSIVE MIGRATION
-- ========================================
-- Generated: 2025-11-06
-- Purpose: Fix all critical security issues identified by Supabase Advisor
--
-- IMPORTANT: Review and test in development environment first!
-- Backup your database before running!
-- ========================================

BEGIN;

-- ========================================
-- PART 1: ENABLE ROW LEVEL SECURITY (RLS)
-- ========================================
-- This is CRITICAL for data security!

-- User & Authentication Tables
ALTER TABLE IF EXISTS users ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS user_activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS user_oauth_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS user_telegram_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS user_strategy_access ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS user_analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS login_history ENABLE ROW LEVEL SECURITY;

-- Exchange & Trading Accounts
ALTER TABLE IF EXISTS exchange_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS exchange_api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS exchange_balances ENABLE ROW LEVEL SECURITY;

-- Financial & Billing Tables
ALTER TABLE IF EXISTS credit_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS credit_packs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS credit_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS billing_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS subscription_plans ENABLE ROW LEVEL SECURITY;

-- Trading & Strategy Tables
ALTER TABLE IF EXISTS trading_strategies ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS trading_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS trading_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS strategy_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS strategy_performance_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS strategy_followers ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS strategy_publishers ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS strategy_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS strategy_scanning_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS live_strategy_performance ENABLE ROW LEVEL SECURITY;

-- Portfolio & Position Tables
ALTER TABLE IF EXISTS portfolios ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS portfolio_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS trades ENABLE ROW LEVEL SECURITY;

-- Chat & Communication
ALTER TABLE IF EXISTS chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS chat_session_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS telegram_messages ENABLE ROW LEVEL SECURITY;

-- Backtest & Analysis
ALTER TABLE IF EXISTS backtest_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS risk_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS risk_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS performance_metrics ENABLE ROW LEVEL SECURITY;

-- AI & ML Tables
ALTER TABLE IF EXISTS ai_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS ai_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS ai_consensus ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS ai_analysis_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS learning_data ENABLE ROW LEVEL SECURITY;

-- Market Data Tables (May need different policies)
ALTER TABLE IF EXISTS market_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS market_data_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS market_data_ohlcv ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS market_tickers ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS market_indicators ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS symbols ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS technical_indicators ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS orderbook_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS legacy_market_data ENABLE ROW LEVEL SECURITY;

-- Signal & Copy Trading
ALTER TABLE IF EXISTS signal_channels ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS signal_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS signal_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS signal_delivery_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS copy_trade_signals ENABLE ROW LEVEL SECURITY;

-- System & Admin Tables
ALTER TABLE IF EXISTS audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS system_health ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS system_configuration ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS background_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS portfolio_optimization_log ENABLE ROW LEVEL SECURITY;

-- Multi-tenant Tables
ALTER TABLE IF EXISTS tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS tenant_settings ENABLE ROW LEVEL SECURITY;

-- A/B Testing
ALTER TABLE IF EXISTS ab_tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS ab_test_variants ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS ab_test_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS ab_test_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS ab_test_metrics ENABLE ROW LEVEL SECURITY;

-- OAuth
ALTER TABLE IF EXISTS oauth_states ENABLE ROW LEVEL SECURITY;

-- NOTE: alembic_version is NOT RLS-enabled because it's a system table
-- that Alembic migrations need to access without user context.
-- If you need to enable RLS on it, ensure you create a permissive policy
-- for the role used by Alembic (typically postgres or service_role).

COMMIT;

-- ========================================
-- PART 2: CREATE RLS POLICIES
-- ========================================
-- Run this AFTER enabling RLS

BEGIN;

-- ----------------------------------------
-- USERS TABLE POLICIES
-- ----------------------------------------
DROP POLICY IF EXISTS "Users can view their own data" ON users;
CREATE POLICY "Users can view their own data"
ON users FOR SELECT
USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update their own data" ON users;
CREATE POLICY "Users can update their own data"
ON users FOR UPDATE
USING (auth.uid() = id);

-- ----------------------------------------
-- USER PROFILES POLICIES
-- ----------------------------------------
DROP POLICY IF EXISTS "Users can view their own profile" ON user_profiles;
CREATE POLICY "Users can view their own profile"
ON user_profiles FOR SELECT
USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update their own profile" ON user_profiles;
CREATE POLICY "Users can update their own profile"
ON user_profiles FOR UPDATE
USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert their own profile" ON user_profiles;
CREATE POLICY "Users can insert their own profile"
ON user_profiles FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- ----------------------------------------
-- EXCHANGE ACCOUNTS POLICIES
-- ----------------------------------------
DROP POLICY IF EXISTS "Users can view their own exchange accounts" ON exchange_accounts;
CREATE POLICY "Users can view their own exchange accounts"
ON exchange_accounts FOR SELECT
USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can manage their own exchange accounts" ON exchange_accounts;
CREATE POLICY "Users can manage their own exchange accounts"
ON exchange_accounts FOR ALL
USING (auth.uid() = user_id);

-- ----------------------------------------
-- EXCHANGE API KEYS POLICIES (EXTRA SECURE!)
-- ----------------------------------------
DROP POLICY IF EXISTS "Users can view their own API keys" ON exchange_api_keys;
CREATE POLICY "Users can view their own API keys"
ON exchange_api_keys FOR SELECT
USING (
  auth.uid() IN (
    SELECT user_id FROM exchange_accounts WHERE id = exchange_api_keys.account_id
  )
);

DROP POLICY IF EXISTS "Users can manage their own API keys" ON exchange_api_keys;
CREATE POLICY "Users can manage their own API keys"
ON exchange_api_keys FOR ALL
USING (
  auth.uid() IN (
    SELECT user_id FROM exchange_accounts WHERE id = exchange_api_keys.account_id
  )
);

-- ----------------------------------------
-- EXCHANGE BALANCES POLICIES
-- ----------------------------------------
DROP POLICY IF EXISTS "Users can view their own balances" ON exchange_balances;
CREATE POLICY "Users can view their own balances"
ON exchange_balances FOR SELECT
USING (
  auth.uid() IN (
    SELECT user_id FROM exchange_accounts WHERE id = exchange_balances.account_id
  )
);

-- ----------------------------------------
-- CREDIT TRANSACTIONS POLICIES
-- ----------------------------------------
DROP POLICY IF EXISTS "Users can view their own credit transactions" ON credit_transactions;
CREATE POLICY "Users can view their own credit transactions"
ON credit_transactions FOR SELECT
USING (auth.uid() = user_id);

-- ----------------------------------------
-- BILLING HISTORY POLICIES
-- ----------------------------------------
DROP POLICY IF EXISTS "Users can view their own billing history" ON billing_history;
CREATE POLICY "Users can view their own billing history"
ON billing_history FOR SELECT
USING (auth.uid() = user_id);

-- ----------------------------------------
-- SUBSCRIPTIONS POLICIES
-- ----------------------------------------
DROP POLICY IF EXISTS "Users can view their own subscriptions" ON subscriptions;
CREATE POLICY "Users can view their own subscriptions"
ON subscriptions FOR SELECT
USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can manage their own subscriptions" ON subscriptions;
CREATE POLICY "Users can manage their own subscriptions"
ON subscriptions FOR ALL
USING (auth.uid() = user_id);

-- ----------------------------------------
-- SUBSCRIPTION PLANS POLICIES (PUBLIC READ)
-- ----------------------------------------
DROP POLICY IF EXISTS "Anyone can view subscription plans" ON subscription_plans;
CREATE POLICY "Anyone can view subscription plans"
ON subscription_plans FOR SELECT
USING (is_active = true);

-- ----------------------------------------
-- CREDIT PACKS POLICIES (PUBLIC READ)
-- ----------------------------------------
DROP POLICY IF EXISTS "Anyone can view credit packs" ON credit_packs;
CREATE POLICY "Anyone can view credit packs"
ON credit_packs FOR SELECT
USING (is_active = true);

-- ----------------------------------------
-- TRADING STRATEGIES POLICIES
-- ----------------------------------------
DROP POLICY IF EXISTS "Users can view their own strategies" ON trading_strategies;
CREATE POLICY "Users can view their own strategies"
ON trading_strategies FOR SELECT
USING (auth.uid() = user_id OR visibility = 'public');

DROP POLICY IF EXISTS "Users can manage their own strategies" ON trading_strategies;
CREATE POLICY "Users can manage their own strategies"
ON trading_strategies FOR ALL
USING (auth.uid() = user_id);

-- ----------------------------------------
-- ORDERS POLICIES
-- ----------------------------------------
DROP POLICY IF EXISTS "Users can view their own orders" ON orders;
CREATE POLICY "Users can view their own orders"
ON orders FOR SELECT
USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can create their own orders" ON orders;
CREATE POLICY "Users can create their own orders"
ON orders FOR INSERT
WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update their own orders" ON orders;
CREATE POLICY "Users can update their own orders"
ON orders FOR UPDATE
USING (auth.uid() = user_id);

-- ----------------------------------------
-- TRADES POLICIES
-- ----------------------------------------
DROP POLICY IF EXISTS "Users can view their own trades" ON trades;
CREATE POLICY "Users can view their own trades"
ON trades FOR SELECT
USING (auth.uid() = user_id);

-- ----------------------------------------
-- POSITIONS POLICIES
-- ----------------------------------------
DROP POLICY IF EXISTS "Users can view their own positions" ON positions;
CREATE POLICY "Users can view their own positions"
ON positions FOR SELECT
USING (auth.uid() = user_id);

-- ----------------------------------------
-- PORTFOLIOS POLICIES
-- ----------------------------------------
DROP POLICY IF EXISTS "Users can view their own portfolios" ON portfolios;
CREATE POLICY "Users can view their own portfolios"
ON portfolios FOR SELECT
USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can manage their own portfolios" ON portfolios;
CREATE POLICY "Users can manage their own portfolios"
ON portfolios FOR ALL
USING (auth.uid() = user_id);

-- ----------------------------------------
-- CHAT SESSIONS POLICIES
-- ----------------------------------------
DROP POLICY IF EXISTS "Users can view their own chat sessions" ON chat_sessions;
CREATE POLICY "Users can view their own chat sessions"
ON chat_sessions FOR SELECT
USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can create their own chat sessions" ON chat_sessions;
CREATE POLICY "Users can create their own chat sessions"
ON chat_sessions FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- ----------------------------------------
-- CHAT MESSAGES POLICIES
-- ----------------------------------------
DROP POLICY IF EXISTS "Users can view their own chat messages" ON chat_messages;
CREATE POLICY "Users can view their own chat messages"
ON chat_messages FOR SELECT
USING (
  auth.uid() IN (
    SELECT user_id FROM chat_sessions WHERE id = chat_messages.session_id
  )
);

DROP POLICY IF EXISTS "Users can create their own chat messages" ON chat_messages;
CREATE POLICY "Users can create their own chat messages"
ON chat_messages FOR INSERT
WITH CHECK (
  auth.uid() IN (
    SELECT user_id FROM chat_sessions WHERE id = chat_messages.session_id
  )
);

-- ----------------------------------------
-- BACKTEST RESULTS POLICIES
-- ----------------------------------------
DROP POLICY IF EXISTS "Users can view their own backtest results" ON backtest_results;
CREATE POLICY "Users can view their own backtest results"
ON backtest_results FOR SELECT
USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can create their own backtest results" ON backtest_results;
CREATE POLICY "Users can create their own backtest results"
ON backtest_results FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- ----------------------------------------
-- MARKET DATA POLICIES (PUBLIC READ FOR MOST)
-- ----------------------------------------
DROP POLICY IF EXISTS "Anyone can view market data" ON market_data;
CREATE POLICY "Anyone can view market data"
ON market_data FOR SELECT
USING (true); -- Public read access

DROP POLICY IF EXISTS "Anyone can view symbols" ON symbols;
CREATE POLICY "Anyone can view symbols"
ON symbols FOR SELECT
USING (true); -- Public read access

DROP POLICY IF EXISTS "Anyone can view market tickers" ON market_tickers;
CREATE POLICY "Anyone can view market tickers"
ON market_tickers FOR SELECT
USING (true); -- Public read access

-- ----------------------------------------
-- AUDIT LOGS POLICIES (ADMIN ONLY)
-- ----------------------------------------
DROP POLICY IF EXISTS "Users can view their own audit logs" ON audit_logs;
CREATE POLICY "Users can view their own audit logs"
ON audit_logs FOR SELECT
USING (auth.uid() = user_id);

-- ----------------------------------------
-- SYSTEM HEALTH (PUBLIC READ)
-- ----------------------------------------
DROP POLICY IF EXISTS "Anyone can view system health" ON system_health;
CREATE POLICY "Anyone can view system health"
ON system_health FOR SELECT
USING (true);

-- ----------------------------------------
-- DOCUMENTS POLICIES
-- ----------------------------------------
DROP POLICY IF EXISTS "Users can view their own documents" ON documents;
CREATE POLICY "Users can view their own documents"
ON documents FOR SELECT
USING (auth.uid()::text = user_id::text);

-- ----------------------------------------
-- REMAINING TABLES - ADD POLICIES FOR ALL RLS-ENABLED TABLES
-- ----------------------------------------

-- Portfolio Snapshots
DROP POLICY IF EXISTS "Users view own portfolio snapshots" ON portfolio_snapshots;
CREATE POLICY "Users view own portfolio snapshots"
ON portfolio_snapshots FOR SELECT
USING (
  portfolio_id IN (
    SELECT id FROM portfolios WHERE user_id = auth.uid()
  )
);

-- Trading Sessions
DROP POLICY IF EXISTS "Users view own trading sessions" ON trading_sessions;
CREATE POLICY "Users view own trading sessions"
ON trading_sessions FOR ALL
USING (auth.uid() = user_id);

-- Strategy Performance History
DROP POLICY IF EXISTS "Users view own strategy performance" ON strategy_performance_history;
CREATE POLICY "Users view own strategy performance"
ON strategy_performance_history FOR SELECT
USING (auth.uid() = user_id);

-- Strategy Performance
DROP POLICY IF EXISTS "Users view own performance" ON strategy_performance;
CREATE POLICY "Users view own performance"
ON strategy_performance FOR SELECT
USING (
  strategy_id IN (
    SELECT id FROM trading_strategies WHERE user_id = auth.uid()
  )
);

-- Strategy Followers
DROP POLICY IF EXISTS "Users manage own follows" ON strategy_followers;
CREATE POLICY "Users manage own follows"
ON strategy_followers FOR ALL
USING (auth.uid() = user_id);

-- Strategy Publishers
DROP POLICY IF EXISTS "Users manage own publications" ON strategy_publishers;
CREATE POLICY "Users manage own publications"
ON strategy_publishers FOR ALL
USING (auth.uid() = user_id);

-- User Sessions
DROP POLICY IF EXISTS "Users view own sessions" ON user_sessions;
CREATE POLICY "Users view own sessions"
ON user_sessions FOR ALL
USING (auth.uid() = user_id);

-- User Activities
DROP POLICY IF EXISTS "Users view own activities" ON user_activities;
CREATE POLICY "Users view own activities"
ON user_activities FOR SELECT
USING (auth.uid() = user_id);

-- User OAuth Connections
DROP POLICY IF EXISTS "Users manage own oauth" ON user_oauth_connections;
CREATE POLICY "Users manage own oauth"
ON user_oauth_connections FOR ALL
USING (auth.uid() = user_id);

-- User Telegram Connections
DROP POLICY IF EXISTS "Users manage own telegram" ON user_telegram_connections;
CREATE POLICY "Users manage own telegram"
ON user_telegram_connections FOR ALL
USING (auth.uid() = user_id);

-- User Strategy Access
DROP POLICY IF EXISTS "Users view own strategy access" ON user_strategy_access;
CREATE POLICY "Users view own strategy access"
ON user_strategy_access FOR SELECT
USING (auth.uid() = user_id);

-- User Analytics
DROP POLICY IF EXISTS "Users view own analytics" ON user_analytics;
CREATE POLICY "Users view own analytics"
ON user_analytics FOR SELECT
USING (auth.uid() = user_id);

-- Login History
DROP POLICY IF EXISTS "Users view own login history" ON login_history;
CREATE POLICY "Users view own login history"
ON login_history FOR SELECT
USING (auth.uid() = user_id);

-- Chat Session Summaries
DROP POLICY IF EXISTS "Users view own chat summaries" ON chat_session_summaries;
CREATE POLICY "Users view own chat summaries"
ON chat_session_summaries FOR SELECT
USING (
  auth.uid() IN (
    SELECT user_id FROM chat_sessions WHERE id = chat_session_summaries.session_id
  )
);

-- Risk Assessments
DROP POLICY IF EXISTS "Users view own risk assessments" ON risk_assessments;
CREATE POLICY "Users view own risk assessments"
ON risk_assessments FOR SELECT
USING (auth.uid() = user_id);

-- Risk Metrics
DROP POLICY IF EXISTS "Users view own risk metrics" ON risk_metrics;
CREATE POLICY "Users view own risk metrics"
ON risk_metrics FOR SELECT
USING (auth.uid() = user_id);

-- Performance Metrics
DROP POLICY IF EXISTS "Users view own performance metrics" ON performance_metrics;
CREATE POLICY "Users view own performance metrics"
ON performance_metrics FOR SELECT
USING (auth.uid() = user_id);

-- AI Models (Public read for reference)
DROP POLICY IF EXISTS "Anyone can view AI models" ON ai_models;
CREATE POLICY "Anyone can view AI models"
ON ai_models FOR SELECT
USING (is_active = true);

-- AI Signals
DROP POLICY IF EXISTS "Users view own AI signals" ON ai_signals;
CREATE POLICY "Users view own AI signals"
ON ai_signals FOR SELECT
USING (auth.uid() = user_id OR visibility = 'public');

-- AI Consensus
DROP POLICY IF EXISTS "Anyone can view AI consensus" ON ai_consensus;
CREATE POLICY "Anyone can view AI consensus"
ON ai_consensus FOR SELECT
USING (true);

-- AI Analysis Log
DROP POLICY IF EXISTS "Users view own AI analysis" ON ai_analysis_log;
CREATE POLICY "Users view own AI analysis"
ON ai_analysis_log FOR SELECT
USING (auth.uid() = user_id);

-- Learning Data (service role only)
DROP POLICY IF EXISTS "Service role manages learning data" ON learning_data;
CREATE POLICY "Service role manages learning data"
ON learning_data FOR ALL
USING (auth.role() = 'service_role');

-- Market Data Log (service role write, public read)
DROP POLICY IF EXISTS "Anyone can view market data log" ON market_data_log;
CREATE POLICY "Anyone can view market data log"
ON market_data_log FOR SELECT
USING (true);

-- Market Data OHLCV (public read)
DROP POLICY IF EXISTS "Anyone can view OHLCV data" ON market_data_ohlcv;
CREATE POLICY "Anyone can view OHLCV data"
ON market_data_ohlcv FOR SELECT
USING (true);

-- Technical Indicators (public read)
DROP POLICY IF EXISTS "Anyone can view technical indicators" ON technical_indicators;
CREATE POLICY "Anyone can view technical indicators"
ON technical_indicators FOR SELECT
USING (true);

-- Orderbook Snapshots (public read)
DROP POLICY IF EXISTS "Anyone can view orderbook" ON orderbook_snapshots;
CREATE POLICY "Anyone can view orderbook"
ON orderbook_snapshots FOR SELECT
USING (true);

-- Legacy Market Data (public read)
DROP POLICY IF EXISTS "Anyone can view legacy market data" ON legacy_market_data;
CREATE POLICY "Anyone can view legacy market data"
ON legacy_market_data FOR SELECT
USING (true);

-- Market Indicators (public read)
DROP POLICY IF EXISTS "Anyone can view market indicators" ON market_indicators;
CREATE POLICY "Anyone can view market indicators"
ON market_indicators FOR SELECT
USING (true);

-- Signal Channels (public read)
DROP POLICY IF EXISTS "Anyone can view signal channels" ON signal_channels;
CREATE POLICY "Anyone can view signal channels"
ON signal_channels FOR SELECT
USING (true);

-- Signal Subscriptions
DROP POLICY IF EXISTS "Users manage own subscriptions" ON signal_subscriptions;
CREATE POLICY "Users manage own subscriptions"
ON signal_subscriptions FOR ALL
USING (auth.uid() = user_id);

-- Signal Events (public read based on channel)
DROP POLICY IF EXISTS "Users view subscribed signal events" ON signal_events;
CREATE POLICY "Users view subscribed signal events"
ON signal_events FOR SELECT
USING (
  channel_id IN (
    SELECT channel_id FROM signal_subscriptions WHERE user_id = auth.uid()
  )
);

-- Signal Delivery Logs
DROP POLICY IF EXISTS "Users view own delivery logs" ON signal_delivery_logs;
CREATE POLICY "Users view own delivery logs"
ON signal_delivery_logs FOR SELECT
USING (auth.uid() = user_id);

-- Copy Trade Signals
DROP POLICY IF EXISTS "Users view own copy signals" ON copy_trade_signals;
CREATE POLICY "Users view own copy signals"
ON copy_trade_signals FOR SELECT
USING (auth.uid() = user_id OR visibility = 'public');

-- System Configuration (service role only)
DROP POLICY IF EXISTS "Service role manages config" ON system_configuration;
CREATE POLICY "Service role manages config"
ON system_configuration FOR ALL
USING (auth.role() = 'service_role');

-- Portfolio Optimization Log
DROP POLICY IF EXISTS "Users view own optimization" ON portfolio_optimization_log;
CREATE POLICY "Users view own optimization"
ON portfolio_optimization_log FOR SELECT
USING (auth.uid() = user_id);

-- Tenants (multi-tenant isolation)
DROP POLICY IF EXISTS "Users view own tenant" ON tenants;
CREATE POLICY "Users view own tenant"
ON tenants FOR SELECT
USING (
  id IN (
    SELECT tenant_id FROM users WHERE id = auth.uid()
  )
);

-- Tenant Settings
DROP POLICY IF EXISTS "Users view own tenant settings" ON tenant_settings;
CREATE POLICY "Users view own tenant settings"
ON tenant_settings FOR SELECT
USING (
  tenant_id IN (
    SELECT tenant_id FROM users WHERE id = auth.uid()
  )
);

-- AB Tests (public read active tests)
DROP POLICY IF EXISTS "Anyone can view active AB tests" ON ab_tests;
CREATE POLICY "Anyone can view active AB tests"
ON ab_tests FOR SELECT
USING (status = 'active');

-- AB Test Variants
DROP POLICY IF EXISTS "Anyone can view active variants" ON ab_test_variants;
CREATE POLICY "Anyone can view active variants"
ON ab_test_variants FOR SELECT
USING (status = 'active');

-- AB Test Results
DROP POLICY IF EXISTS "Admins view test results" ON ab_test_results;
CREATE POLICY "Admins view test results"
ON ab_test_results FOR SELECT
USING (auth.jwt() ->> 'role' = 'admin');

-- AB Test Participants
DROP POLICY IF EXISTS "Users view own participation" ON ab_test_participants;
CREATE POLICY "Users view own participation"
ON ab_test_participants FOR SELECT
USING (auth.uid() = user_id);

-- AB Test Metrics
DROP POLICY IF EXISTS "Admins view test metrics" ON ab_test_metrics;
CREATE POLICY "Admins view test metrics"
ON ab_test_metrics FOR SELECT
USING (auth.jwt() ->> 'role' = 'admin');

-- OAuth States (temporary, user-specific)
DROP POLICY IF EXISTS "Users manage own oauth states" ON oauth_states;
CREATE POLICY "Users manage own oauth states"
ON oauth_states FOR ALL
USING (auth.uid() = user_id);

-- Background Tasks (service role only)
DROP POLICY IF EXISTS "Service role manages tasks" ON background_tasks;
CREATE POLICY "Service role manages tasks"
ON background_tasks FOR ALL
USING (auth.role() = 'service_role');

-- Credit Accounts
DROP POLICY IF EXISTS "Users view own credit account" ON credit_accounts;
CREATE POLICY "Users view own credit account"
ON credit_accounts FOR SELECT
USING (auth.uid() = user_id);

-- Strategy Scanning Policies
DROP POLICY IF EXISTS "Users view own scanning policies" ON strategy_scanning_policies;
CREATE POLICY "Users view own scanning policies"
ON strategy_scanning_policies FOR SELECT
USING (auth.uid() = user_id);

-- Strategy Submissions
DROP POLICY IF EXISTS "Users manage own submissions" ON strategy_submissions;
CREATE POLICY "Users manage own submissions"
ON strategy_submissions FOR ALL
USING (auth.uid() = user_id);

-- Live Strategy Performance (public for published strategies)
DROP POLICY IF EXISTS "Users view accessible live performance" ON live_strategy_performance;
CREATE POLICY "Users view accessible live performance"
ON live_strategy_performance FOR SELECT
USING (
  strategy_id IN (
    SELECT id FROM trading_strategies
    WHERE user_id = auth.uid() OR visibility = 'public'
  )
);

-- Telegram Messages
DROP POLICY IF EXISTS "Users view own telegram messages" ON telegram_messages;
CREATE POLICY "Users view own telegram messages"
ON telegram_messages FOR SELECT
USING (
  auth.uid() IN (
    SELECT user_id FROM user_telegram_connections
    WHERE telegram_user_id = telegram_messages.telegram_user_id
  )
);

COMMIT;

-- ========================================
-- SUCCESS MESSAGE
-- ========================================
DO $$
BEGIN
  RAISE NOTICE '✅ RLS has been enabled and basic policies created!';
  RAISE NOTICE '⚠️  IMPORTANT: Review and customize policies based on your business logic!';
  RAISE NOTICE '⚠️  IMPORTANT: Test thoroughly before deploying to production!';
END $$;
