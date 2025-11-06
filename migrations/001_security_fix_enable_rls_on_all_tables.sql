-- ===============================================================================
-- CRYPTOUNIVERSE CRITICAL SECURITY FIX: ENABLE ROW LEVEL SECURITY (RLS)
-- ===============================================================================
--
-- SEVERITY: CRITICAL - Data exposure vulnerability
-- ISSUE: 80+ tables exposed via PostgREST API without Row Level Security
-- IMPACT: All data publicly accessible without authentication
--
-- DEPLOYMENT: Run in Supabase SQL Editor immediately
-- ROLLBACK: Available via 001_security_fix_enable_rls_on_all_tables_rollback.sql
-- ===============================================================================

BEGIN;

-- ===============================================================================
-- PHASE 1: ENABLE RLS ON USER & AUTHENTICATION TABLES
-- ===============================================================================

-- Users and profiles - restrict to own data
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_activities ENABLE ROW LEVEL SECURITY;

-- User policies: Users can only see and modify their own data
CREATE POLICY "Users can view own record"
  ON public.users FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users can update own record"
  ON public.users FOR UPDATE
  USING (auth.uid() = id);

CREATE POLICY "Service role full access to users"
  ON public.users FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- User profiles policies
CREATE POLICY "Users can view own profile"
  ON public.user_profiles FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can update own profile"
  ON public.user_profiles FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to user_profiles"
  ON public.user_profiles FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- User sessions policies
CREATE POLICY "Users can view own sessions"
  ON public.user_sessions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own sessions"
  ON public.user_sessions FOR DELETE
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to user_sessions"
  ON public.user_sessions FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- User activities policies
CREATE POLICY "Users can view own activities"
  ON public.user_activities FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to user_activities"
  ON public.user_activities FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- ===============================================================================
-- PHASE 2: ENABLE RLS ON FINANCIAL & TRADING TABLES
-- ===============================================================================

-- Exchange accounts and API keys - highly sensitive
ALTER TABLE public.exchange_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exchange_api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exchange_balances ENABLE ROW LEVEL SECURITY;

-- Exchange accounts policies
CREATE POLICY "Users can view own exchange accounts"
  ON public.exchange_accounts FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own exchange accounts"
  ON public.exchange_accounts FOR ALL
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to exchange_accounts"
  ON public.exchange_accounts FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Exchange API keys policies (extra sensitive)
CREATE POLICY "Users can view own API keys"
  ON public.exchange_api_keys FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own API keys"
  ON public.exchange_api_keys FOR ALL
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to exchange_api_keys"
  ON public.exchange_api_keys FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Exchange balances policies
CREATE POLICY "Users can view own exchange balances"
  ON public.exchange_balances FOR SELECT
  USING (
    auth.uid() IN (
      SELECT user_id FROM public.exchange_accounts
      WHERE id = exchange_balances.account_id
    )
  );

CREATE POLICY "Service role full access to exchange_balances"
  ON public.exchange_balances FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Trading tables
ALTER TABLE public.trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trade_signals ENABLE ROW LEVEL SECURITY;

-- Trades policies
CREATE POLICY "Users can view own trades"
  ON public.trades FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to trades"
  ON public.trades FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Orders policies
CREATE POLICY "Users can view own orders"
  ON public.orders FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to orders"
  ON public.orders FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Positions policies
CREATE POLICY "Users can view own positions"
  ON public.positions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to positions"
  ON public.positions FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Trade signals policies
CREATE POLICY "Users can view own trade signals"
  ON public.trade_signals FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to trade_signals"
  ON public.trade_signals FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Portfolio tables
ALTER TABLE public.portfolios ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.portfolio_snapshots ENABLE ROW LEVEL SECURITY;

-- Portfolios policies
CREATE POLICY "Users can view own portfolios"
  ON public.portfolios FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own portfolios"
  ON public.portfolios FOR ALL
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to portfolios"
  ON public.portfolios FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Portfolio snapshots policies
CREATE POLICY "Users can view own portfolio snapshots"
  ON public.portfolio_snapshots FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to portfolio_snapshots"
  ON public.portfolio_snapshots FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- ===============================================================================
-- PHASE 3: ENABLE RLS ON BILLING & SUBSCRIPTION TABLES
-- ===============================================================================

ALTER TABLE public.credit_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.billing_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.credit_packs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscription_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;

-- Credit transactions policies
CREATE POLICY "Users can view own credit transactions"
  ON public.credit_transactions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to credit_transactions"
  ON public.credit_transactions FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Billing history policies
CREATE POLICY "Users can view own billing history"
  ON public.billing_history FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to billing_history"
  ON public.billing_history FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Credit packs - public read, service role manage
CREATE POLICY "Anyone can view credit packs"
  ON public.credit_packs FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Service role full access to credit_packs"
  ON public.credit_packs FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Subscriptions policies
CREATE POLICY "Users can view own subscriptions"
  ON public.subscriptions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to subscriptions"
  ON public.subscriptions FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Subscription plans - public read
CREATE POLICY "Anyone can view subscription plans"
  ON public.subscription_plans FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Service role full access to subscription_plans"
  ON public.subscription_plans FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Payments policies
CREATE POLICY "Users can view own payments"
  ON public.payments FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to payments"
  ON public.payments FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- ===============================================================================
-- PHASE 4: ENABLE RLS ON AI & STRATEGY TABLES
-- ===============================================================================

ALTER TABLE public.ai_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_consensus ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_analysis_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.strategies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.strategy_performance_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.strategy_publishers ENABLE ROW LEVEL SECURITY;

-- AI models - public read for active models
CREATE POLICY "Anyone can view active AI models"
  ON public.ai_models FOR SELECT
  TO authenticated
  USING (is_active = true);

CREATE POLICY "Service role full access to ai_models"
  ON public.ai_models FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- AI signals - user specific
CREATE POLICY "Users can view own AI signals"
  ON public.ai_signals FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to ai_signals"
  ON public.ai_signals FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- AI consensus - public read for authenticated users
CREATE POLICY "Authenticated users can view AI consensus"
  ON public.ai_consensus FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Service role full access to ai_consensus"
  ON public.ai_consensus FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- AI analysis log - user specific
CREATE POLICY "Users can view own AI analysis log"
  ON public.ai_analysis_log FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to ai_analysis_log"
  ON public.ai_analysis_log FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Strategies - public read for published, owner manage
CREATE POLICY "Anyone can view published strategies"
  ON public.strategies FOR SELECT
  TO authenticated
  USING (is_published = true OR auth.uid() = user_id);

CREATE POLICY "Users can manage own strategies"
  ON public.strategies FOR ALL
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to strategies"
  ON public.strategies FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Strategy performance - user specific
CREATE POLICY "Users can view own strategy performance"
  ON public.strategy_performance_history FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to strategy_performance_history"
  ON public.strategy_performance_history FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Strategy publishers - public read
CREATE POLICY "Anyone can view strategy publishers"
  ON public.strategy_publishers FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Service role full access to strategy_publishers"
  ON public.strategy_publishers FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- ===============================================================================
-- PHASE 5: ENABLE RLS ON ANALYTICS & LEARNING TABLES
-- ===============================================================================

ALTER TABLE public.learning_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.risk_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.performance_metrics ENABLE ROW LEVEL SECURITY;

-- Learning data - user specific
CREATE POLICY "Users can view own learning data"
  ON public.learning_data FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to learning_data"
  ON public.learning_data FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Risk assessments - user specific
CREATE POLICY "Users can view own risk assessments"
  ON public.risk_assessments FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to risk_assessments"
  ON public.risk_assessments FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Performance metrics - user specific
CREATE POLICY "Users can view own performance metrics"
  ON public.performance_metrics FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to performance_metrics"
  ON public.performance_metrics FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- ===============================================================================
-- PHASE 6: ENABLE RLS ON MARKET DATA TABLES (PUBLIC READ)
-- ===============================================================================

ALTER TABLE public.market_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.market_data_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orderbook_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.symbols ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.technical_indicators ENABLE ROW LEVEL SECURITY;

-- Market data - public read for authenticated users
CREATE POLICY "Authenticated users can view market data"
  ON public.market_data FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Service role full access to market_data"
  ON public.market_data FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Market data log - service role only
CREATE POLICY "Service role full access to market_data_log"
  ON public.market_data_log FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Orderbook snapshots - public read
CREATE POLICY "Authenticated users can view orderbook snapshots"
  ON public.orderbook_snapshots FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Service role full access to orderbook_snapshots"
  ON public.orderbook_snapshots FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Symbols - public read
CREATE POLICY "Authenticated users can view symbols"
  ON public.symbols FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Service role full access to symbols"
  ON public.symbols FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Technical indicators - public read
CREATE POLICY "Authenticated users can view technical indicators"
  ON public.technical_indicators FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Service role full access to technical_indicators"
  ON public.technical_indicators FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- ===============================================================================
-- PHASE 7: ENABLE RLS ON SYSTEM & LOGGING TABLES
-- ===============================================================================

ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.system_health ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.system_configuration ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.background_tasks ENABLE ROW LEVEL SECURITY;

-- Audit logs - users can view own logs only
CREATE POLICY "Users can view own audit logs"
  ON public.audit_logs FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to audit_logs"
  ON public.audit_logs FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- System health - service role only
CREATE POLICY "Service role full access to system_health"
  ON public.system_health FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- System configuration - service role only
CREATE POLICY "Service role full access to system_configuration"
  ON public.system_configuration FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Background tasks - service role only
CREATE POLICY "Service role full access to background_tasks"
  ON public.background_tasks FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- ===============================================================================
-- PHASE 8: ENABLE RLS ON TENANT & FEATURE TABLES
-- ===============================================================================

ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feature_flags ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feature_usage_analytics ENABLE ROW LEVEL SECURITY;

-- Tenants - users can view own tenant
CREATE POLICY "Users can view own tenant"
  ON public.tenants FOR SELECT
  USING (id IN (SELECT tenant_id FROM public.users WHERE id = auth.uid()));

CREATE POLICY "Service role full access to tenants"
  ON public.tenants FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Tenant settings - users can view own tenant settings
CREATE POLICY "Users can view own tenant settings"
  ON public.tenant_settings FOR SELECT
  USING (tenant_id IN (SELECT tenant_id FROM public.users WHERE id = auth.uid()));

CREATE POLICY "Service role full access to tenant_settings"
  ON public.tenant_settings FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Feature flags - authenticated users can read
CREATE POLICY "Authenticated users can view feature flags"
  ON public.feature_flags FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Service role full access to feature_flags"
  ON public.feature_flags FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Feature usage analytics - user specific
CREATE POLICY "Users can view own feature usage"
  ON public.feature_usage_analytics FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to feature_usage_analytics"
  ON public.feature_usage_analytics FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- ===============================================================================
-- PHASE 9: ENABLE RLS ON A/B TESTING TABLES
-- ===============================================================================

ALTER TABLE public.ab_test_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ab_test_variants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ab_test_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ab_test_metrics ENABLE ROW LEVEL SECURITY;

-- A/B test results - service role only
CREATE POLICY "Service role full access to ab_test_results"
  ON public.ab_test_results FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- A/B test variants - authenticated users can read
CREATE POLICY "Authenticated users can view ab test variants"
  ON public.ab_test_variants FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Service role full access to ab_test_variants"
  ON public.ab_test_variants FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- A/B test participants - users can view own participation
CREATE POLICY "Users can view own ab test participation"
  ON public.ab_test_participants FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to ab_test_participants"
  ON public.ab_test_participants FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- A/B test metrics - service role only
CREATE POLICY "Service role full access to ab_test_metrics"
  ON public.ab_test_metrics FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- ===============================================================================
-- PHASE 10: ENABLE RLS ON OPTIMIZATION & TRADING SESSION TABLES
-- ===============================================================================

ALTER TABLE public.portfolio_optimization_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trading_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

-- Portfolio optimization log - user specific
CREATE POLICY "Users can view own portfolio optimization log"
  ON public.portfolio_optimization_log FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to portfolio_optimization_log"
  ON public.portfolio_optimization_log FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Trading sessions - user specific
CREATE POLICY "Users can view own trading sessions"
  ON public.trading_sessions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to trading_sessions"
  ON public.trading_sessions FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- Documents - user specific or public
CREATE POLICY "Users can view own or public documents"
  ON public.documents FOR SELECT
  USING (auth.uid() = user_id OR is_public = true);

CREATE POLICY "Users can manage own documents"
  ON public.documents FOR ALL
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to documents"
  ON public.documents FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

-- ===============================================================================
-- PHASE 11: ENABLE RLS ON SCHEMA_MIGRATIONS (SYSTEM TABLE)
-- ===============================================================================

ALTER TABLE public.schema_migrations ENABLE ROW LEVEL SECURITY;

-- Schema migrations - service role only
CREATE POLICY "Service role full access to schema_migrations"
  ON public.schema_migrations FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');

COMMIT;

-- ===============================================================================
-- VERIFICATION QUERIES
-- ===============================================================================

-- Run these queries after deployment to verify RLS is enabled:
-- SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
-- SELECT schemaname, tablename, policyname FROM pg_policies WHERE schemaname = 'public' ORDER BY tablename, policyname;
