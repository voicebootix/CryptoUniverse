-- ===============================================================================
-- CRYPTOUNIVERSE SECURITY FIX: SECURITY DEFINER VIEWS
-- ===============================================================================
--
-- SEVERITY: HIGH - Security privilege escalation risk
-- ISSUE: 4 views with SECURITY DEFINER property bypass RLS
-- IMPACT: Users can access data through views that they shouldn't see directly
--
-- AFFECTED VIEWS:
--   - portfolio_evolution
--   - daily_performance
--   - v_user_strategy_summary
--   - ai_performance
--
-- FIX: Convert to SECURITY INVOKER or add proper RLS filters
-- REFERENCE: https://supabase.com/docs/guides/database/database-linter?lint=0010_security_definer_view
--
-- DEPLOYMENT: Run in Supabase SQL Editor
-- ===============================================================================

BEGIN;

-- ===============================================================================
-- PHASE 1: FIX portfolio_evolution VIEW
-- ===============================================================================

-- Drop existing SECURITY DEFINER view
DROP VIEW IF EXISTS public.portfolio_evolution CASCADE;

-- Recreate as SECURITY INVOKER with user-scoped filtering
CREATE OR REPLACE VIEW public.portfolio_evolution
WITH (security_invoker = true)
AS
SELECT
    ps.user_id,
    ps.portfolio_id,
    ps.timestamp,
    ps.total_value,
    ps.total_invested,
    ps.total_pnl,
    ps.total_pnl_percentage,
    ps.asset_allocation,
    ps.performance_metrics,
    ps.created_at
FROM public.portfolio_snapshots ps
WHERE
    -- Only show data for authenticated user
    ps.user_id = auth.uid()
ORDER BY ps.timestamp DESC;

-- Grant appropriate permissions
GRANT SELECT ON public.portfolio_evolution TO authenticated;
REVOKE ALL ON public.portfolio_evolution FROM anon;

-- Add helpful comment
COMMENT ON VIEW public.portfolio_evolution IS
'Portfolio value evolution over time. SECURITY INVOKER ensures users only see their own data via RLS policies.';

-- ===============================================================================
-- PHASE 2: FIX daily_performance VIEW
-- ===============================================================================

-- Drop existing SECURITY DEFINER view
DROP VIEW IF EXISTS public.daily_performance CASCADE;

-- Recreate as SECURITY INVOKER with user-scoped filtering
CREATE OR REPLACE VIEW public.daily_performance
WITH (security_invoker = true)
AS
SELECT
    pm.user_id,
    DATE(pm.timestamp) AS performance_date,
    pm.strategy_id,
    AVG(pm.win_rate) AS avg_win_rate,
    SUM(pm.total_trades) AS total_trades,
    SUM(pm.winning_trades) AS winning_trades,
    SUM(pm.losing_trades) AS losing_trades,
    AVG(pm.profit_factor) AS avg_profit_factor,
    SUM(pm.total_pnl) AS total_pnl,
    AVG(pm.sharpe_ratio) AS avg_sharpe_ratio,
    AVG(pm.max_drawdown) AS avg_max_drawdown,
    MAX(pm.timestamp) AS last_update
FROM public.performance_metrics pm
WHERE
    -- Only show data for authenticated user
    pm.user_id = auth.uid()
    AND pm.timestamp >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY
    pm.user_id,
    DATE(pm.timestamp),
    pm.strategy_id
ORDER BY performance_date DESC, pm.strategy_id;

-- Grant appropriate permissions
GRANT SELECT ON public.daily_performance TO authenticated;
REVOKE ALL ON public.daily_performance FROM anon;

-- Add helpful comment
COMMENT ON VIEW public.daily_performance IS
'Daily aggregated performance metrics per strategy. SECURITY INVOKER ensures users only see their own data.';

-- ===============================================================================
-- PHASE 3: FIX v_user_strategy_summary VIEW
-- ===============================================================================

-- Drop existing SECURITY DEFINER view
DROP VIEW IF EXISTS public.v_user_strategy_summary CASCADE;

-- Recreate as SECURITY INVOKER with user-scoped filtering
CREATE OR REPLACE VIEW public.v_user_strategy_summary
WITH (security_invoker = true)
AS
SELECT
    s.id AS strategy_id,
    s.name AS strategy_name,
    s.user_id,
    s.strategy_type,
    s.is_active,
    s.is_published,
    COUNT(DISTINCT t.id) AS total_trades,
    COALESCE(SUM(CASE WHEN t.pnl > 0 THEN 1 ELSE 0 END), 0) AS winning_trades,
    COALESCE(SUM(CASE WHEN t.pnl < 0 THEN 1 ELSE 0 END), 0) AS losing_trades,
    COALESCE(
        SUM(CASE WHEN t.pnl > 0 THEN 1 ELSE 0 END)::float /
        NULLIF(COUNT(t.id), 0) * 100,
        0
    ) AS win_rate_percentage,
    COALESCE(SUM(t.pnl), 0) AS total_pnl,
    COALESCE(AVG(t.pnl), 0) AS avg_pnl_per_trade,
    MAX(t.created_at) AS last_trade_at,
    s.created_at AS strategy_created_at,
    s.updated_at AS strategy_updated_at
FROM public.strategies s
LEFT JOIN public.trades t ON t.strategy_id = s.id AND t.status = 'CLOSED'
WHERE
    -- Only show strategies owned by user OR published strategies
    (s.user_id = auth.uid() OR s.is_published = true)
GROUP BY
    s.id,
    s.name,
    s.user_id,
    s.strategy_type,
    s.is_active,
    s.is_published,
    s.created_at,
    s.updated_at
ORDER BY s.updated_at DESC;

-- Grant appropriate permissions
GRANT SELECT ON public.v_user_strategy_summary TO authenticated;
REVOKE ALL ON public.v_user_strategy_summary FROM anon;

-- Add helpful comment
COMMENT ON VIEW public.v_user_strategy_summary IS
'Comprehensive strategy performance summary. SECURITY INVOKER with explicit user_id check ensures proper access control.';

-- ===============================================================================
-- PHASE 4: FIX ai_performance VIEW
-- ===============================================================================

-- Drop existing SECURITY DEFINER view
DROP VIEW IF EXISTS public.ai_performance CASCADE;

-- Recreate as SECURITY INVOKER with proper filtering
CREATE OR REPLACE VIEW public.ai_performance
WITH (security_invoker = true)
AS
SELECT
    am.id AS model_id,
    am.name AS model_name,
    am.model_type,
    am.version,
    am.is_active,
    COUNT(DISTINCT ais.id) AS total_signals,
    COUNT(DISTINCT CASE WHEN ais.signal_strength > 0.7 THEN ais.id END) AS strong_signals,
    COUNT(DISTINCT aal.id) AS total_analyses,
    COALESCE(AVG(aal.confidence_score), 0) AS avg_confidence,
    COALESCE(AVG(aal.execution_time_ms), 0) AS avg_execution_time_ms,
    MAX(aal.created_at) AS last_analysis_at,
    am.created_at AS model_created_at,
    am.updated_at AS model_updated_at,
    -- Performance metrics from actual trades (if available)
    COUNT(DISTINCT t.id) FILTER (WHERE t.signal_source = am.name) AS trades_from_model,
    COALESCE(
        SUM(t.pnl) FILTER (WHERE t.signal_source = am.name),
        0
    ) AS total_pnl_from_model
FROM public.ai_models am
LEFT JOIN public.ai_signals ais ON ais.model_id = am.id
LEFT JOIN public.ai_analysis_log aal ON aal.model_id = am.id
LEFT JOIN public.trades t ON t.signal_source = am.name AND t.status = 'CLOSED'
WHERE
    -- Only show active models OR models used by current user
    (
        am.is_active = true
        OR EXISTS (
            SELECT 1 FROM public.ai_signals ais2
            WHERE ais2.model_id = am.id
            AND ais2.user_id = auth.uid()
        )
    )
    -- Filter trades to only show current user's trades
    AND (t.user_id = auth.uid() OR t.user_id IS NULL)
GROUP BY
    am.id,
    am.name,
    am.model_type,
    am.version,
    am.is_active,
    am.created_at,
    am.updated_at
ORDER BY am.is_active DESC, total_signals DESC;

-- Grant appropriate permissions
GRANT SELECT ON public.ai_performance TO authenticated;
REVOKE ALL ON public.ai_performance FROM anon;

-- Add helpful comment
COMMENT ON VIEW public.ai_performance IS
'AI model performance metrics and statistics. SECURITY INVOKER with user-scoped trade filtering ensures proper data isolation.';

COMMIT;

-- ===============================================================================
-- SECURITY IMPACT ANALYSIS
-- ===============================================================================

-- BEFORE:
-- - Views ran with SECURITY DEFINER (creator's privileges)
-- - Users could access ALL data through views, bypassing RLS
-- - Potential data leak for sensitive portfolio and trading data

-- AFTER:
-- - Views run with SECURITY INVOKER (caller's privileges)
-- - Views enforce user_id checks with auth.uid()
-- - Views respect RLS policies on underlying tables
-- - Users can only see their own data + explicitly public data

-- ===============================================================================
-- VERIFICATION QUERIES
-- ===============================================================================

-- Verify views are SECURITY INVOKER:
-- SELECT
--     schemaname,
--     viewname,
--     definition
-- FROM pg_views
-- WHERE viewname IN (
--     'portfolio_evolution',
--     'daily_performance',
--     'v_user_strategy_summary',
--     'ai_performance'
-- );

-- Test view access (should only show current user's data):
-- SELECT * FROM portfolio_evolution LIMIT 10;
-- SELECT * FROM daily_performance LIMIT 10;
-- SELECT * FROM v_user_strategy_summary LIMIT 10;
-- SELECT * FROM ai_performance LIMIT 10;
