-- High Impact Performance Indexes
-- These indexes will dramatically improve query speed for strategy loading

-- 1. User strategies lookup (most critical)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trading_strategies_user_active
ON trading_strategies (user_id, is_active)
WHERE is_active = true;

-- 2. Portfolio queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_portfolios_user_default
ON portfolios (user_id, is_default);

-- 3. Strategy access lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_strategy_access_user_strategy
ON strategy_access (user_id, strategy_id, is_active);

-- 4. User trades performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_user_status
ON trades (user_id, status, created_at DESC);

-- 5. Position lookup optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_positions_user_symbol_status
ON positions (user_id, symbol, status);

-- 6. Credit transactions (for admin operations)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_credit_transactions_user_type
ON credit_transactions (user_id, transaction_type, created_at DESC);

-- Performance query hints
ANALYZE trading_strategies;
ANALYZE portfolios;
ANALYZE strategy_access;
ANALYZE trades;
ANALYZE positions;
ANALYZE credit_transactions;