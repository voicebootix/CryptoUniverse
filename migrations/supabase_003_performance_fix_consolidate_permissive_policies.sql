-- ===============================================================================
-- CRYPTOUNIVERSE PERFORMANCE FIX: CONSOLIDATE MULTIPLE PERMISSIVE RLS POLICIES
-- ===============================================================================
--
-- SEVERITY: HIGH - Query performance degradation
-- ISSUE: Multiple permissive policies for same role+action combinations
-- IMPACT: All policies execute for every query (multiplicative overhead)
--
-- AFFECTED TABLES:
--   - decisions_log (20 policy conflicts)
--   - parameter_updates (20 policy conflicts)
--
-- FIX: Consolidate overlapping policies into single efficient policies
--
-- DEPLOYMENT: Run in Supabase SQL Editor after 002_security_fix_auth_rls_initplan_optimization.sql
-- ===============================================================================

BEGIN;

-- ===============================================================================
-- PHASE 1: CONSOLIDATE DECISIONS_LOG POLICIES
-- ===============================================================================

-- The issue: "Allow anon access" and "Allow service role access" policies
-- overlap for all roles and all actions (INSERT, SELECT, UPDATE, DELETE)
-- This means BOTH policies execute for EVERY query

-- Drop all existing policies to start fresh
DROP POLICY IF EXISTS "Allow service role access" ON public.decisions_log;
DROP POLICY IF EXISTS "Allow anon access" ON public.decisions_log;
DROP POLICY IF EXISTS "Allow authenticated user access" ON public.decisions_log;

-- Create consolidated, efficient policies

-- 1. Service role has full access (highest priority)
CREATE POLICY "Service role full access"
  ON public.decisions_log
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- 2. Authenticated users can view and manage their own logs
CREATE POLICY "Users manage own decisions"
  ON public.decisions_log
  FOR ALL
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- 3. Anon users cannot access (explicit deny, no policy needed)
-- By default, no policy = no access for anon users

-- ===============================================================================
-- PHASE 2: CONSOLIDATE PARAMETER_UPDATES POLICIES
-- ===============================================================================

-- Drop all existing policies
DROP POLICY IF EXISTS "Allow service role access" ON public.parameter_updates;
DROP POLICY IF EXISTS "Allow anon access" ON public.parameter_updates;
DROP POLICY IF EXISTS "Allow authenticated user access" ON public.parameter_updates;

-- Create consolidated, efficient policies

-- 1. Service role has full access
CREATE POLICY "Service role full access"
  ON public.parameter_updates
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- 2. Authenticated users can view and manage their own parameter updates
CREATE POLICY "Users manage own parameter updates"
  ON public.parameter_updates
  FOR ALL
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- ===============================================================================
-- PHASE 3: CONSOLIDATE TRADES_LOG POLICIES (IF NOT ALREADY DONE IN 002)
-- ===============================================================================

-- Drop all existing policies
DROP POLICY IF EXISTS "Allow service role access" ON public.trades_log;
DROP POLICY IF EXISTS "Allow anon access" ON public.trades_log;
DROP POLICY IF EXISTS "Allow authenticated user access" ON public.trades_log;

-- Create consolidated, efficient policies

-- 1. Service role has full access
CREATE POLICY "Service role full access"
  ON public.trades_log
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- 2. Authenticated users can view and manage their own trades
CREATE POLICY "Users manage own trades"
  ON public.trades_log
  FOR ALL
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

COMMIT;

-- ===============================================================================
-- PERFORMANCE IMPACT ANALYSIS
-- ===============================================================================

-- BEFORE:
-- - decisions_log: 20 policies (2 base policies × 5 roles × 4 actions)
-- - parameter_updates: 20 policies (2 base policies × 5 roles × 4 actions)
-- - Every query executed UP TO 8 policies (2 for each action type)

-- AFTER:
-- - decisions_log: 2 policies (service_role + authenticated)
-- - parameter_updates: 2 policies (service_role + authenticated)
-- - Every query executes EXACTLY 1 policy (the one matching the role)

-- EXPECTED IMPROVEMENT: 4-8x faster query execution on these tables

-- ===============================================================================
-- VERIFICATION QUERIES
-- ===============================================================================

-- Verify consolidated policies:
-- SELECT tablename, policyname, roles, cmd
-- FROM pg_policies
-- WHERE tablename IN ('decisions_log', 'parameter_updates', 'trades_log')
-- ORDER BY tablename, policyname;

-- Expected result: 2 policies per table (not 20+)

-- Test query performance:
-- EXPLAIN ANALYZE SELECT * FROM decisions_log WHERE user_id = auth.uid() LIMIT 100;
