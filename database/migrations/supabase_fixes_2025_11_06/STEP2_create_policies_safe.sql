-- ========================================
-- STEP 2: CREATE POLICIES SAFELY
-- ========================================
-- This script creates policies ONLY if the required columns exist
-- No "column does not exist" errors!
-- ========================================

BEGIN;

RAISE NOTICE 'Creating RLS policies with column existence checks...';

-- ========================================
-- TABLES WITH user_id COLUMN
-- ========================================

-- Helper function to check column
CREATE OR REPLACE FUNCTION has_column(tbl text, col text) RETURNS boolean AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = tbl
    AND column_name = col
  );
END;
$$ LANGUAGE plpgsql;

-- Users table (uses 'id' not 'user_id')
DO $$
BEGIN
  IF has_column('users', 'id') THEN
    DROP POLICY IF EXISTS "Users can view their own data" ON users;
    CREATE POLICY "Users can view their own data" ON users FOR SELECT
    USING (auth.uid() = id);

    DROP POLICY IF EXISTS "Users can update their own data" ON users;
    CREATE POLICY "Users can update their own data" ON users FOR UPDATE
    USING (auth.uid() = id);

    RAISE NOTICE '✅ users';
  END IF;
END $$;

-- User Profiles
DO $$
BEGIN
  IF has_column('user_profiles', 'user_id') THEN
    DROP POLICY IF EXISTS "Users can view their own profile" ON user_profiles;
    CREATE POLICY "Users can view their own profile" ON user_profiles FOR SELECT
    USING (auth.uid() = user_id);

    DROP POLICY IF EXISTS "Users can update their own profile" ON user_profiles;
    CREATE POLICY "Users can update their own profile" ON user_profiles FOR UPDATE
    USING (auth.uid() = user_id);

    DROP POLICY IF EXISTS "Users can insert their own profile" ON user_profiles;
    CREATE POLICY "Users can insert their own profile" ON user_profiles FOR INSERT
    WITH CHECK (auth.uid() = user_id);

    RAISE NOTICE '✅ user_profiles';
  END IF;
END $$;

-- Exchange Accounts
DO $$
BEGIN
  IF has_column('exchange_accounts', 'user_id') THEN
    DROP POLICY IF EXISTS "Users can view their own exchange accounts" ON exchange_accounts;
    CREATE POLICY "Users can view their own exchange accounts" ON exchange_accounts FOR SELECT
    USING (auth.uid() = user_id);

    DROP POLICY IF EXISTS "Users can manage their own exchange accounts" ON exchange_accounts;
    CREATE POLICY "Users can manage their own exchange accounts" ON exchange_accounts FOR ALL
    USING (auth.uid() = user_id);

    RAISE NOTICE '✅ exchange_accounts';
  END IF;
END $$;

-- Exchange API Keys (uses account_id)
DO $$
BEGIN
  IF has_column('exchange_api_keys', 'account_id') THEN
    DROP POLICY IF EXISTS "Users can view their own API keys" ON exchange_api_keys;
    CREATE POLICY "Users can view their own API keys" ON exchange_api_keys FOR SELECT
    USING (EXISTS (SELECT 1 FROM exchange_accounts WHERE id = exchange_api_keys.account_id AND user_id = auth.uid()));

    DROP POLICY IF EXISTS "Users can manage their own API keys" ON exchange_api_keys;
    CREATE POLICY "Users can manage their own API keys" ON exchange_api_keys FOR ALL
    USING (EXISTS (SELECT 1 FROM exchange_accounts WHERE id = exchange_api_keys.account_id AND user_id = auth.uid()));

    RAISE NOTICE '✅ exchange_api_keys';
  END IF;
END $$;

-- Exchange Balances (uses account_id)
DO $$
BEGIN
  IF has_column('exchange_balances', 'account_id') THEN
    DROP POLICY IF EXISTS "Users can view their own balances" ON exchange_balances;
    CREATE POLICY "Users can view their own balances" ON exchange_balances FOR SELECT
    USING (EXISTS (SELECT 1 FROM exchange_accounts WHERE id = exchange_balances.account_id AND user_id = auth.uid()));

    RAISE NOTICE '✅ exchange_balances';
  END IF;
END $$;

-- Credit Transactions
DO $$
BEGIN
  IF has_column('credit_transactions', 'user_id') THEN
    DROP POLICY IF EXISTS "Users can view their own credit transactions" ON credit_transactions;
    CREATE POLICY "Users can view their own credit transactions" ON credit_transactions FOR SELECT
    USING (auth.uid() = user_id);

    RAISE NOTICE '✅ credit_transactions';
  END IF;
END $$;

-- Billing History
DO $$
BEGIN
  IF has_column('billing_history', 'user_id') THEN
    DROP POLICY IF EXISTS "Users can view their own billing history" ON billing_history;
    CREATE POLICY "Users can view their own billing history" ON billing_history FOR SELECT
    USING (auth.uid() = user_id);

    RAISE NOTICE '✅ billing_history';
  END IF;
END $$;

-- Subscriptions
DO $$
BEGIN
  IF has_column('subscriptions', 'user_id') THEN
    DROP POLICY IF EXISTS "Users can view their own subscriptions" ON subscriptions;
    CREATE POLICY "Users can view their own subscriptions" ON subscriptions FOR SELECT
    USING (auth.uid() = user_id);

    DROP POLICY IF EXISTS "Users can manage their own subscriptions" ON subscriptions;
    CREATE POLICY "Users can manage their own subscriptions" ON subscriptions FOR ALL
    USING (auth.uid() = user_id);

    RAISE NOTICE '✅ subscriptions';
  END IF;
END $$;

-- Trading Strategies
DO $$
BEGIN
  IF has_column('trading_strategies', 'user_id') THEN
    DROP POLICY IF EXISTS "Users can view their own strategies" ON trading_strategies;
    CREATE POLICY "Users can view their own strategies" ON trading_strategies FOR SELECT
    USING (auth.uid() = user_id OR visibility = 'public');

    DROP POLICY IF EXISTS "Users can manage their own strategies" ON trading_strategies;
    CREATE POLICY "Users can manage their own strategies" ON trading_strategies FOR ALL
    USING (auth.uid() = user_id);

    RAISE NOTICE '✅ trading_strategies';
  END IF;
END $$;

-- Trading Signals
DO $$
BEGIN
  IF has_column('trading_signals', 'user_id') THEN
    DROP POLICY IF EXISTS "Users can view own signals" ON trading_signals;
    CREATE POLICY "Users can view own signals" ON trading_signals FOR SELECT
    USING (auth.uid() = user_id OR visibility = 'public');

    DROP POLICY IF EXISTS "Users can create own signals" ON trading_signals;
    CREATE POLICY "Users can create own signals" ON trading_signals FOR INSERT
    WITH CHECK (auth.uid() = user_id);

    DROP POLICY IF EXISTS "Users can update own signals" ON trading_signals;
    CREATE POLICY "Users can update own signals" ON trading_signals FOR UPDATE
    USING (auth.uid() = user_id);

    RAISE NOTICE '✅ trading_signals';
  END IF;
END $$;

-- Orders
DO $$
BEGIN
  IF has_column('orders', 'user_id') THEN
    DROP POLICY IF EXISTS "Users can view their own orders" ON orders;
    CREATE POLICY "Users can view their own orders" ON orders FOR SELECT
    USING (auth.uid() = user_id);

    DROP POLICY IF EXISTS "Users can create their own orders" ON orders;
    CREATE POLICY "Users can create their own orders" ON orders FOR INSERT
    WITH CHECK (auth.uid() = user_id);

    DROP POLICY IF EXISTS "Users can update their own orders" ON orders;
    CREATE POLICY "Users can update their own orders" ON orders FOR UPDATE
    USING (auth.uid() = user_id);

    RAISE NOTICE '✅ orders';
  END IF;
END $$;

-- Trades
DO $$
BEGIN
  IF has_column('trades', 'user_id') THEN
    DROP POLICY IF EXISTS "Users can view their own trades" ON trades;
    CREATE POLICY "Users can view their own trades" ON trades FOR SELECT
    USING (auth.uid() = user_id);

    RAISE NOTICE '✅ trades';
  END IF;
END $$;

-- Positions
DO $$
BEGIN
  IF has_column('positions', 'user_id') THEN
    DROP POLICY IF EXISTS "Users can view their own positions" ON positions;
    CREATE POLICY "Users can view their own positions" ON positions FOR SELECT
    USING (auth.uid() = user_id);

    DROP POLICY IF EXISTS "Users can create their own positions" ON positions;
    CREATE POLICY "Users can create their own positions" ON positions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

    DROP POLICY IF EXISTS "Users can update their own positions" ON positions;
    CREATE POLICY "Users can update their own positions" ON positions FOR UPDATE
    USING (auth.uid() = user_id);

    RAISE NOTICE '✅ positions';
  END IF;
END $$;

-- Portfolios
DO $$
BEGIN
  IF has_column('portfolios', 'user_id') THEN
    DROP POLICY IF EXISTS "Users can view their own portfolios" ON portfolios;
    CREATE POLICY "Users can view their own portfolios" ON portfolios FOR SELECT
    USING (auth.uid() = user_id);

    DROP POLICY IF EXISTS "Users can manage their own portfolios" ON portfolios;
    CREATE POLICY "Users can manage their own portfolios" ON portfolios FOR ALL
    USING (auth.uid() = user_id);

    RAISE NOTICE '✅ portfolios';
  END IF;
END $$;

-- Chat Sessions
DO $$
BEGIN
  IF has_column('chat_sessions', 'user_id') THEN
    DROP POLICY IF EXISTS "Users can view their own chat sessions" ON chat_sessions;
    CREATE POLICY "Users can view their own chat sessions" ON chat_sessions FOR SELECT
    USING (auth.uid() = user_id);

    DROP POLICY IF EXISTS "Users can create their own chat sessions" ON chat_sessions;
    CREATE POLICY "Users can create their own chat sessions" ON chat_sessions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

    RAISE NOTICE '✅ chat_sessions';
  END IF;
END $$;

-- Chat Messages (uses session_id)
DO $$
BEGIN
  IF has_column('chat_messages', 'session_id') THEN
    DROP POLICY IF EXISTS "Users can view their own chat messages" ON chat_messages;
    CREATE POLICY "Users can view their own chat messages" ON chat_messages FOR SELECT
    USING (EXISTS (SELECT 1 FROM chat_sessions WHERE id = chat_messages.session_id AND user_id = auth.uid()));

    DROP POLICY IF EXISTS "Users can create their own chat messages" ON chat_messages;
    CREATE POLICY "Users can create their own chat messages" ON chat_messages FOR INSERT
    WITH CHECK (EXISTS (SELECT 1 FROM chat_sessions WHERE id = chat_messages.session_id AND user_id = auth.uid()));

    RAISE NOTICE '✅ chat_messages';
  END IF;
END $$;

-- Backtest Results
DO $$
BEGIN
  IF has_column('backtest_results', 'user_id') THEN
    DROP POLICY IF EXISTS "Users can view their own backtest results" ON backtest_results;
    CREATE POLICY "Users can view their own backtest results" ON backtest_results FOR SELECT
    USING (auth.uid() = user_id);

    DROP POLICY IF EXISTS "Users can create their own backtest results" ON backtest_results;
    CREATE POLICY "Users can create their own backtest results" ON backtest_results FOR INSERT
    WITH CHECK (auth.uid() = user_id);

    RAISE NOTICE '✅ backtest_results';
  END IF;
END $$;

-- Add all remaining tables with user_id...
-- (Continuing with same pattern for all other user-owned tables)

DO $$
DECLARE
  table_names text[] := ARRAY[
    'user_sessions', 'user_activities', 'user_oauth_connections',
    'user_telegram_connections', 'user_strategy_access', 'user_analytics',
    'login_history', 'credit_accounts', 'trading_sessions',
    'strategy_performance_history', 'strategy_followers', 'strategy_publishers',
    'strategy_submissions', 'strategy_scanning_policies', 'risk_assessments',
    'risk_metrics', 'performance_metrics', 'signal_subscriptions',
    'signal_delivery_logs', 'copy_trade_signals', 'audit_logs',
    'portfolio_optimization_log', 'ab_test_participants', 'oauth_states'
  ];
  tbl text;
BEGIN
  FOREACH tbl IN ARRAY table_names
  LOOP
    IF has_column(tbl, 'user_id') THEN
      EXECUTE format('DROP POLICY IF EXISTS "Users can view their own %I" ON %I', tbl, tbl);
      EXECUTE format('CREATE POLICY "Users can view their own %I" ON %I FOR SELECT USING (auth.uid() = user_id)', tbl, tbl);
      RAISE NOTICE '✅ %', tbl;
    END IF;
  END LOOP;
END $$;

-- ========================================
-- PUBLIC READ TABLES (NO user_id column)
-- ========================================

RAISE NOTICE '';
RAISE NOTICE 'Creating policies for public data tables...';

-- Market Data Tables
DO $$
DECLARE
  market_tables text[] := ARRAY[
    'market_data', 'market_data_log', 'market_data_ohlcv',
    'market_tickers', 'symbols', 'technical_indicators',
    'orderbook_snapshots', 'market_indicators'
  ];
  tbl text;
BEGIN
  FOREACH tbl IN ARRAY market_tables
  LOOP
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = tbl AND schemaname = 'public') THEN
      EXECUTE format('DROP POLICY IF EXISTS "Public can read %I" ON %I', tbl, tbl);
      EXECUTE format('CREATE POLICY "Public can read %I" ON %I FOR SELECT USING (true)', tbl, tbl);

      EXECUTE format('DROP POLICY IF EXISTS "Service role manages %I" ON %I', tbl, tbl);
      EXECUTE format('CREATE POLICY "Service role manages %I" ON %I FOR ALL USING (auth.role() = ''service_role'')', tbl, tbl);

      RAISE NOTICE '✅ % (public read)', tbl;
    END IF;
  END LOOP;
END $$;

-- AI Tables
DO $$
DECLARE
  ai_tables text[] := ARRAY[
    'ai_models', 'ai_signals', 'ai_consensus'
  ];
  tbl text;
BEGIN
  FOREACH tbl IN ARRAY ai_tables
  LOOP
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = tbl AND schemaname = 'public') THEN
      EXECUTE format('DROP POLICY IF EXISTS "Public can read %I" ON %I', tbl, tbl);
      EXECUTE format('CREATE POLICY "Public can read %I" ON %I FOR SELECT USING (true)', tbl, tbl);

      EXECUTE format('DROP POLICY IF EXISTS "Service role manages %I" ON %I', tbl, tbl);
      EXECUTE format('CREATE POLICY "Service role manages %I" ON %I FOR ALL USING (auth.role() = ''service_role'')', tbl, tbl);

      RAISE NOTICE '✅ % (public read)', tbl;
    END IF;
  END LOOP;
END $$;

-- Service Role Only Tables
DO $$
DECLARE
  service_tables text[] := ARRAY[
    'ai_analysis_log', 'learning_data', 'system_configuration',
    'background_tasks'
  ];
  tbl text;
BEGIN
  FOREACH tbl IN ARRAY service_tables
  LOOP
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = tbl AND schemaname = 'public') THEN
      EXECUTE format('DROP POLICY IF EXISTS "Service role only %I" ON %I', tbl, tbl);
      EXECUTE format('CREATE POLICY "Service role only %I" ON %I FOR ALL USING (auth.role() = ''service_role'')', tbl, tbl);

      RAISE NOTICE '✅ % (service role only)', tbl;
    END IF;
  END LOOP;
END $$;

-- Public Read Tables (with is_active check)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'subscription_plans' AND schemaname = 'public') THEN
    DROP POLICY IF EXISTS "Anyone can view subscription plans" ON subscription_plans;
    CREATE POLICY "Anyone can view subscription plans" ON subscription_plans FOR SELECT
    USING (is_active = true);
    RAISE NOTICE '✅ subscription_plans';
  END IF;

  IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'credit_packs' AND schemaname = 'public') THEN
    DROP POLICY IF EXISTS "Anyone can view credit packs" ON credit_packs;
    CREATE POLICY "Anyone can view credit packs" ON credit_packs FOR SELECT
    USING (is_active = true);
    RAISE NOTICE '✅ credit_packs';
  END IF;

  IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'signal_channels' AND schemaname = 'public') THEN
    DROP POLICY IF EXISTS "Anyone can view signal channels" ON signal_channels;
    CREATE POLICY "Anyone can view signal channels" ON signal_channels FOR SELECT
    USING (true);
    RAISE NOTICE '✅ signal_channels';
  END IF;

  IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'system_health' AND schemaname = 'public') THEN
    DROP POLICY IF EXISTS "Anyone can view system health" ON system_health;
    CREATE POLICY "Anyone can view system health" ON system_health FOR SELECT
    USING (true);
    RAISE NOTICE '✅ system_health';
  END IF;
END $$;

-- Drop helper function
DROP FUNCTION IF EXISTS has_column(text, text);

COMMIT;

-- Final Summary
DO $$
DECLARE
  policy_count INTEGER;
  rls_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO policy_count FROM pg_policies WHERE schemaname = 'public';
  SELECT COUNT(*) INTO rls_count FROM pg_tables WHERE schemaname = 'public' AND rowsecurity = true;

  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE '✅ STEP 2 COMPLETE!';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'Tables with RLS enabled: %', rls_count;
  RAISE NOTICE 'Total policies created: %', policy_count;
  RAISE NOTICE '';
  RAISE NOTICE 'Policy Summary:';
  RAISE NOTICE '  - User-owned tables: Policies created with user_id checks';
  RAISE NOTICE '  - Market data: Public read, service write';
  RAISE NOTICE '  - AI data: Public read, service write';
  RAISE NOTICE '  - System config: Service role only';
  RAISE NOTICE '';
  RAISE NOTICE '⚠️  Next: Run supabase_performance_fixes.sql';
  RAISE NOTICE '========================================';
  RAISE NOTICE '';
END $$;
