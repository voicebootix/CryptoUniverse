-- ENTERPRISE DATABASE PERFORMANCE OPTIMIZATION
-- Proper indexes to fix 60+ second queries while preserving ALL sophisticated features

-- 1. CRITICAL: Portfolio Historical Analysis Index
-- Fixes the expensive daily P&L historical queries (portfolio_risk_core.py:1550-1556)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_portfolio_user_created_desc 
ON portfolios(user_id, created_at DESC) 
WHERE total_value_usd > 0;

-- 2. CRITICAL: Exchange Balance User Lookup Index  
-- Optimizes portfolio retrieval queries (chat_service_adapters_fixed.py:64-65)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exchange_account_user_active 
ON exchange_accounts(user_id, is_active) 
WHERE is_active = true;

-- 3. CRITICAL: Exchange Balance Performance Index
-- Optimizes balance queries with cost basis (portfolio_risk_core.py:1631-1637)  
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exchange_balance_nonzero_cost 
ON exchange_balances(exchange_account_id, total_balance, avg_cost_basis) 
WHERE total_balance > 0;

-- 4. CRITICAL: Exchange Balance Value Index
-- Optimizes portfolio value calculations and P&L analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exchange_balance_usd_value 
ON exchange_balances(exchange_account_id, usd_value DESC, symbol) 
WHERE usd_value > 0;

-- 5. Chat Session Performance Index
-- Optimizes chat memory retrieval (chat_memory.py:169-178)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_message_session_timestamp 
ON chat_messages(session_id, timestamp DESC) 
WHERE processed = true;

-- 6. Chat Session User Index  
-- Optimizes user session retrieval (chat_memory.py:226-239)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_session_user_activity 
ON chat_sessions(user_id, last_activity DESC, is_active) 
WHERE is_active = true;

-- 7. Historical Portfolio Analysis Index
-- For sophisticated time-series risk analysis 
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_portfolio_time_series 
ON portfolios(user_id, created_at, total_value_usd) 
WHERE total_value_usd > 0;

-- 8. Multi-Exchange Portfolio Aggregation Index
-- Optimizes cross-exchange portfolio analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exchange_balance_multi_exchange 
ON exchange_balances(symbol, total_balance, usd_value, exchange_account_id) 
WHERE total_balance > 0;

-- IMPORTANT: These indexes preserve ALL enterprise features while fixing performance
-- - Historical P&L analysis: KEPT + OPTIMIZED
-- - Sophisticated risk calculations: KEPT + OPTIMIZED  
-- - Cross-exchange portfolio analysis: KEPT + OPTIMIZED
-- - Chat memory and context: KEPT + OPTIMIZED