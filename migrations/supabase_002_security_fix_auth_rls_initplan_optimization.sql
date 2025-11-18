-- ===============================================================================
-- CRYPTOUNIVERSE PERFORMANCE FIX: AUTH RLS INITPLAN OPTIMIZATION
-- ===============================================================================
--
-- SEVERITY: HIGH - Query performance degradation at scale
-- ISSUE: RLS policies re-evaluating auth functions for each row
-- IMPACT: Queries slow down exponentially with table size
--
-- AFFECTED TABLES:
--   - trades_log (2 policies)
--   - decisions_log (2 policies)
--   - parameter_updates (2 policies)
--
-- FIX: Wrap auth.<function>() calls with (SELECT ...) to force single evaluation
-- REFERENCE: https://supabase.com/docs/guides/database/postgres/row-level-security#call-functions-with-select
--
-- DEPLOYMENT: Run in Supabase SQL Editor after 001_security_fix_enable_rls_on_all_tables.sql
-- ===============================================================================

BEGIN;

-- ===============================================================================
-- PHASE 1: FIX TRADES_LOG RLS POLICIES
-- ===============================================================================

-- Drop existing inefficient policies
DROP POLICY IF EXISTS "Allow service role access" ON public.trades_log;
DROP POLICY IF EXISTS "Allow anon access" ON public.trades_log;

-- Recreate with optimized auth function calls
CREATE POLICY "Allow service role access"
  ON public.trades_log
  FOR ALL
  USING (
    (SELECT auth.jwt()->>'role') = 'service_role'
  );

CREATE POLICY "Allow authenticated user access"
  ON public.trades_log
  FOR SELECT
  TO authenticated
  USING (
    auth.uid() = user_id
  );

-- ===============================================================================
-- PHASE 2: FIX DECISIONS_LOG RLS POLICIES
-- ===============================================================================

-- Drop existing inefficient policies
DROP POLICY IF EXISTS "Allow service role access" ON public.decisions_log;
DROP POLICY IF EXISTS "Allow anon access" ON public.decisions_log;

-- Recreate with optimized auth function calls
CREATE POLICY "Allow service role access"
  ON public.decisions_log
  FOR ALL
  USING (
    (SELECT auth.jwt()->>'role') = 'service_role'
  );

CREATE POLICY "Allow authenticated user access"
  ON public.decisions_log
  FOR SELECT
  TO authenticated
  USING (
    auth.uid() = user_id
  );

-- ===============================================================================
-- PHASE 3: FIX PARAMETER_UPDATES RLS POLICIES
-- ===============================================================================

-- Drop existing inefficient policies
DROP POLICY IF EXISTS "Allow service role access" ON public.parameter_updates;
DROP POLICY IF EXISTS "Allow anon access" ON public.parameter_updates;

-- Recreate with optimized auth function calls
CREATE POLICY "Allow service role access"
  ON public.parameter_updates
  FOR ALL
  USING (
    (SELECT auth.jwt()->>'role') = 'service_role'
  );

CREATE POLICY "Allow authenticated user access"
  ON public.parameter_updates
  FOR SELECT
  TO authenticated
  USING (
    auth.uid() = user_id
  );

COMMIT;

-- ===============================================================================
-- VERIFICATION QUERIES
-- ===============================================================================

-- Verify policies have been recreated:
-- SELECT schemaname, tablename, policyname, qual
-- FROM pg_policies
-- WHERE tablename IN ('trades_log', 'decisions_log', 'parameter_updates')
-- ORDER BY tablename, policyname;

-- Test query performance (should be significantly faster):
-- EXPLAIN ANALYZE SELECT * FROM trades_log WHERE user_id = auth.uid() LIMIT 100;
