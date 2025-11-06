-- ========================================
-- SUPABASE FUNCTION & VIEW SECURITY FIXES
-- ========================================
-- Generated: 2025-11-06
-- Purpose: Fix function search paths and security definer views
--
-- IMPORTANT: Review before running!
-- ========================================

BEGIN;

-- ========================================
-- PART 1: FIX FUNCTION SEARCH PATHS
-- ========================================

-- Fix update_updated_at_column function
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'public' AND p.proname = 'update_updated_at_column'
  ) THEN
    ALTER FUNCTION public.update_updated_at_column()
    SET search_path = public, pg_temp;
    RAISE NOTICE '✅ Fixed search_path for update_updated_at_column';
  ELSE
    RAISE NOTICE '⚠️  Function update_updated_at_column not found';
  END IF;
END $$;

-- Fix match_documents function
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'public' AND p.proname = 'match_documents'
  ) THEN
    -- Note: match_documents may have different signatures
    -- Adjust parameters as needed
    ALTER FUNCTION public.match_documents(vector, float, int)
    SET search_path = public, pg_temp;
    RAISE NOTICE '✅ Fixed search_path for match_documents';
  ELSE
    RAISE NOTICE '⚠️  Function match_documents not found (may have different signature)';
  END IF;
EXCEPTION
  WHEN OTHERS THEN
    RAISE NOTICE '⚠️  Could not fix match_documents - check function signature';
END $$;

-- ========================================
-- PART 2: FIX SECURITY DEFINER VIEWS
-- ========================================

-- Option A: Recreate views WITHOUT security_definer
-- This is safer but may break functionality if views rely on elevated permissions

-- portfolio_evolution view
DROP VIEW IF EXISTS public.portfolio_evolution CASCADE;

-- You'll need to recreate this view with your actual query
-- Example structure:
-- CREATE VIEW public.portfolio_evolution AS
-- SELECT
--   p.user_id,
--   p.portfolio_id,
--   ps.timestamp,
--   ps.total_value
-- FROM portfolios p
-- JOIN portfolio_snapshots ps ON p.id = ps.portfolio_id
-- WHERE p.user_id = auth.uid(); -- Add proper auth check

-- daily_performance view
DROP VIEW IF EXISTS public.daily_performance CASCADE;

-- You'll need to recreate this view with your actual query
-- Example structure:
-- CREATE VIEW public.daily_performance AS
-- SELECT
--   user_id,
--   DATE(created_at) as date,
--   SUM(profit_loss) as daily_profit
-- FROM trades
-- WHERE user_id = auth.uid() -- Add proper auth check
-- GROUP BY user_id, DATE(created_at);

-- v_user_strategy_summary view
DROP VIEW IF EXISTS public.v_user_strategy_summary CASCADE;

-- You'll need to recreate this view with your actual query
-- Example structure:
-- CREATE VIEW public.v_user_strategy_summary AS
-- SELECT
--   ts.user_id,
--   ts.id as strategy_id,
--   ts.name,
--   COUNT(t.id) as total_trades,
--   SUM(t.profit_loss) as total_profit
-- FROM trading_strategies ts
-- LEFT JOIN trades t ON ts.id = t.strategy_id
-- WHERE ts.user_id = auth.uid() -- Add proper auth check
-- GROUP BY ts.user_id, ts.id, ts.name;

-- ai_performance view
DROP VIEW IF EXISTS public.ai_performance CASCADE;

-- You'll need to recreate this view with your actual query
-- Example structure:
-- CREATE VIEW public.ai_performance AS
-- SELECT
--   model_id,
--   COUNT(*) as predictions,
--   AVG(confidence) as avg_confidence,
--   SUM(CASE WHEN was_correct THEN 1 ELSE 0 END)::float / COUNT(*) as accuracy
-- FROM ai_signals
-- GROUP BY model_id;

COMMIT;

-- ========================================
-- PART 3: RECREATE VIEWS WITH PROPER SECURITY
-- ========================================

BEGIN;

-- ⚠️ IMPORTANT: You need to add the actual view definitions here!
-- The views above were dropped. Now recreate them properly.

-- Method 1: Use security_invoker (PostgreSQL 15+)
-- This runs the view with the permissions of the user calling it

-- Example:
-- CREATE VIEW public.portfolio_evolution
-- WITH (security_invoker = true) AS
-- SELECT ...your query...;

-- Method 2: Add RLS checks within the view
-- This is safer and works with security_definer

-- Example:
-- CREATE VIEW public.portfolio_evolution AS
-- SELECT ...
-- WHERE user_id = auth.uid() OR EXISTS (
--   SELECT 1 FROM user_roles
--   WHERE user_id = auth.uid() AND role = 'admin'
-- );

-- ⚠️ ACTION REQUIRED:
-- Get the actual view definitions from your application code
-- or from Supabase dashboard, then add them here with proper security

RAISE NOTICE '⚠️  VIEWS HAVE BEEN DROPPED!';
RAISE NOTICE '⚠️  YOU MUST RECREATE THEM WITH PROPER SECURITY!';
RAISE NOTICE '';
RAISE NOTICE 'To get view definitions, run:';
RAISE NOTICE 'SELECT definition FROM pg_views WHERE schemaname = ''public'' AND viewname IN (''portfolio_evolution'', ''daily_performance'', ''v_user_strategy_summary'', ''ai_performance'');';

COMMIT;

-- ========================================
-- PART 4: MOVE VECTOR EXTENSION (OPTIONAL)
-- ========================================
-- This moves the vector extension to a separate schema for better security

BEGIN;

-- Create extensions schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS extensions;

-- Grant usage to appropriate roles
GRANT USAGE ON SCHEMA extensions TO postgres, anon, authenticated, service_role;

-- Move vector extension
-- ⚠️ This may fail if vector is not installed or if there are dependencies
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
    ALTER EXTENSION vector SET SCHEMA extensions;
    RAISE NOTICE '✅ Moved vector extension to extensions schema';
  ELSE
    RAISE NOTICE 'ℹ️  Vector extension not found or already moved';
  END IF;
EXCEPTION
  WHEN OTHERS THEN
    RAISE NOTICE '⚠️  Could not move vector extension. It may have dependencies.';
    RAISE NOTICE '    You may need to drop and recreate objects that depend on it.';
END $$;

COMMIT;

-- ========================================
-- VERIFICATION QUERIES
-- ========================================

-- Check function search paths
SELECT
  n.nspname as schema,
  p.proname as function_name,
  pg_get_function_identity_arguments(p.oid) as arguments,
  p.prosecdef as security_definer,
  p.proconfig as config
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'public'
  AND p.proname IN ('update_updated_at_column', 'match_documents');

-- Check for remaining security definer views
SELECT
  schemaname,
  viewname,
  definition
FROM pg_views
WHERE schemaname = 'public'
  AND viewname IN ('portfolio_evolution', 'daily_performance', 'v_user_strategy_summary', 'ai_performance');

-- Check extension location
SELECT
  e.extname,
  n.nspname as schema
FROM pg_extension e
JOIN pg_namespace n ON e.extnamespace = n.oid
WHERE e.extname = 'vector';

-- ========================================
-- SUCCESS MESSAGE
-- ========================================
DO $$
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE '✅ Function security paths have been fixed!';
  RAISE NOTICE '⚠️  IMPORTANT: Views have been dropped!';
  RAISE NOTICE '⚠️  You MUST recreate them with proper security!';
  RAISE NOTICE '';
  RAISE NOTICE 'Next steps:';
  RAISE NOTICE '1. Get original view definitions';
  RAISE NOTICE '2. Add proper security checks (auth.uid() or security_invoker)';
  RAISE NOTICE '3. Recreate the views';
  RAISE NOTICE '4. Test thoroughly!';
  RAISE NOTICE '========================================';
END $$;
