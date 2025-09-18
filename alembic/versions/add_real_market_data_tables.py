<<<<<<< HEAD
"""Add real market data tables with corrected precision

Revision ID: add_real_market_data
Revises:
Create Date: 2025-01-18 12:00:00.000000
=======
"""Add real market data tables

Revision ID: add_real_market_data
Revises: add_chat_memory_tables
Create Date: 2024-01-18 10:00:00.000000
>>>>>>> 74798ab3bb0b22f57424b2a99d41a082a3880f44

"""
from alembic import op
import sqlalchemy as sa
<<<<<<< HEAD
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = 'add_real_market_data'
down_revision = None  # Update this to point to the latest migration
=======
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_real_market_data'
down_revision = 'add_chat_memory_tables'
>>>>>>> 74798ab3bb0b22f57424b2a99d41a082a3880f44
branch_labels = None
depends_on = None


<<<<<<< HEAD
def upgrade():
    """Create market data tables."""

    # Market data table
    op.create_table('market_data',
        sa.Column('id', UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('exchange', sa.String(length=50), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('open_price', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('high_price', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('low_price', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('close_price', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('volume', sa.Numeric(precision=30, scale=8), nullable=False),
        sa.Column('quote_volume', sa.Numeric(precision=30, scale=8), nullable=True),
        sa.Column('vwap', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('trade_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes for market_data
    op.create_index('idx_market_data_symbol', 'market_data', ['symbol'])
    op.create_index('idx_market_data_timestamp', 'market_data', ['timestamp'])
    op.create_index('idx_market_data_symbol_timestamp', 'market_data', ['symbol', 'timestamp'])
    op.create_index('idx_market_data_exchange_timestamp', 'market_data', ['exchange', 'timestamp'])

    # Trading signals table
    op.create_table('trading_signals',
        sa.Column('id', UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('strategy_id', sa.String(length=100), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('signal_type', sa.String(length=10), nullable=False),
        sa.Column('strength', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('confidence', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('entry_price', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('stop_loss', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('take_profit', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('risk_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('timeframe', sa.String(length=10), nullable=True),
        sa.Column('indicators_used', JSONB, nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='active'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes for trading_signals
    op.create_index('idx_trading_signals_strategy_id', 'trading_signals', ['strategy_id'])
    op.create_index('idx_trading_signals_symbol', 'trading_signals', ['symbol'])

    # Backtest results table
    op.create_table('backtest_results',
        sa.Column('id', UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('strategy_id', sa.String(length=100), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('total_return', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('annual_return', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('max_drawdown', sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column('sharpe_ratio', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('sortino_ratio', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('total_trades', sa.Integer(), nullable=False),
        sa.Column('winning_trades', sa.Integer(), nullable=False),
        sa.Column('losing_trades', sa.Integer(), nullable=False),
        # Fixed: win_rate precision changed from (5,4) to (5,2) for 0-100% range
        sa.Column('win_rate', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('volatility', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('beta', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('alpha', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('initial_capital', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('final_capital', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('avg_trade_return', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('profit_factor', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('parameters', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes for backtest_results
    op.create_index('idx_backtest_results_strategy_id', 'backtest_results', ['strategy_id'])

    # Strategy performance table
    op.create_table('strategy_performance',
        sa.Column('id', UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('strategy_id', sa.String(length=100), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_updated', sa.DateTime(timezone=True), nullable=False),
        sa.Column('total_return', sa.Numeric(precision=8, scale=4), nullable=False, default=0),
        sa.Column('unrealized_pnl', sa.Numeric(precision=20, scale=8), nullable=False, default=0),
        sa.Column('realized_pnl', sa.Numeric(precision=20, scale=8), nullable=False, default=0),
        sa.Column('total_trades', sa.Integer(), nullable=False, default=0),
        sa.Column('winning_trades', sa.Integer(), nullable=False, default=0),
        sa.Column('losing_trades', sa.Integer(), nullable=False, default=0),
        # Fixed: win_rate precision changed from (5,4) to (5,2) for 0-100% range
        sa.Column('win_rate', sa.Numeric(precision=5, scale=2), nullable=False, default=0),
        sa.Column('max_drawdown', sa.Numeric(precision=6, scale=4), nullable=False, default=0),
        sa.Column('current_drawdown', sa.Numeric(precision=6, scale=4), nullable=False, default=0),
        sa.Column('allocated_capital', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('current_value', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes for strategy_performance
    op.create_index('idx_strategy_performance_strategy_id', 'strategy_performance', ['strategy_id'])
    op.create_index('idx_strategy_performance_user_id', 'strategy_performance', ['user_id'])
    op.create_index('idx_strategy_performance_user_strategy', 'strategy_performance', ['user_id', 'strategy_id'])
    op.create_index('idx_strategy_performance_active', 'strategy_performance', ['is_active', 'last_updated'])

    # Market indicators table
    op.create_table('market_indicators',
        sa.Column('id', UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('indicator_name', sa.String(length=50), nullable=False),
        sa.Column('timeframe', sa.String(length=10), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('value', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('values', JSONB, nullable=True),
        sa.Column('parameters', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes for market_indicators
    op.create_index('idx_market_indicators_symbol', 'market_indicators', ['symbol'])
    op.create_index('idx_market_indicators_timestamp', 'market_indicators', ['timestamp'])
    op.create_index('idx_market_indicators_symbol_name_time', 'market_indicators', ['symbol', 'indicator_name', 'timestamp'])


def downgrade():
    """Drop market data tables."""

    # Drop indexes first
    op.drop_index('idx_market_indicators_symbol_name_time', table_name='market_indicators')
    op.drop_index('idx_market_indicators_timestamp', table_name='market_indicators')
    op.drop_index('idx_market_indicators_symbol', table_name='market_indicators')

    op.drop_index('idx_strategy_performance_active', table_name='strategy_performance')
    op.drop_index('idx_strategy_performance_user_strategy', table_name='strategy_performance')
    op.drop_index('idx_strategy_performance_user_id', table_name='strategy_performance')
    op.drop_index('idx_strategy_performance_strategy_id', table_name='strategy_performance')

    op.drop_index('idx_backtest_results_strategy_id', table_name='backtest_results')

    op.drop_index('idx_trading_signals_symbol', table_name='trading_signals')
    op.drop_index('idx_trading_signals_strategy_id', table_name='trading_signals')

    op.drop_index('idx_market_data_exchange_timestamp', table_name='market_data')
    op.drop_index('idx_market_data_symbol_timestamp', table_name='market_data')
    op.drop_index('idx_market_data_timestamp', table_name='market_data')
    op.drop_index('idx_market_data_symbol', table_name='market_data')

    # Drop tables
    op.drop_table('market_indicators')
    op.drop_table('strategy_performance')
    op.drop_table('backtest_results')
    op.drop_table('trading_signals')
    op.drop_table('market_data')
=======
def upgrade() -> None:
    # Create market_data_ohlcv table
    op.create_table('market_data_ohlcv',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('exchange', sa.String(50), nullable=False),
        sa.Column('timeframe', sa.String(10), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('open', sa.Numeric(20, 8), nullable=False),
        sa.Column('high', sa.Numeric(20, 8), nullable=False),
        sa.Column('low', sa.Numeric(20, 8), nullable=False),
        sa.Column('close', sa.Numeric(20, 8), nullable=False),
        sa.Column('volume', sa.Numeric(20, 8), nullable=False),
        sa.Column('trade_count', sa.Integer(), nullable=True),
        sa.Column('vwap', sa.Numeric(20, 8), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source', sa.String(50), nullable=True),
        sa.Column('is_validated', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol', 'exchange', 'timeframe', 'timestamp', name='unique_candle')
    )
    op.create_index('idx_ohlcv_lookup', 'market_data_ohlcv', ['symbol', 'exchange', 'timeframe', 'timestamp'])
    op.create_index('idx_ohlcv_timestamp', 'market_data_ohlcv', ['timestamp'])

    # Create market_tickers table
    op.create_table('market_tickers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('exchange', sa.String(50), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_price', sa.Numeric(20, 8), nullable=False),
        sa.Column('bid', sa.Numeric(20, 8), nullable=True),
        sa.Column('ask', sa.Numeric(20, 8), nullable=True),
        sa.Column('bid_size', sa.Numeric(20, 8), nullable=True),
        sa.Column('ask_size', sa.Numeric(20, 8), nullable=True),
        sa.Column('open_24h', sa.Numeric(20, 8), nullable=True),
        sa.Column('high_24h', sa.Numeric(20, 8), nullable=True),
        sa.Column('low_24h', sa.Numeric(20, 8), nullable=True),
        sa.Column('volume_24h', sa.Numeric(20, 8), nullable=True),
        sa.Column('quote_volume_24h', sa.Numeric(20, 8), nullable=True),
        sa.Column('change_24h', sa.Numeric(10, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_ticker_lookup', 'market_tickers', ['symbol', 'exchange', 'timestamp'])

    # Create orderbook_snapshots table
    op.create_table('orderbook_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('exchange', sa.String(50), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('bids', sa.JSON(), nullable=False),
        sa.Column('asks', sa.JSON(), nullable=False),
        sa.Column('best_bid', sa.Numeric(20, 8), nullable=True),
        sa.Column('best_ask', sa.Numeric(20, 8), nullable=True),
        sa.Column('spread', sa.Numeric(20, 8), nullable=True),
        sa.Column('spread_pct', sa.Numeric(10, 4), nullable=True),
        sa.Column('bid_depth_10', sa.Numeric(20, 8), nullable=True),
        sa.Column('ask_depth_10', sa.Numeric(20, 8), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('levels_count', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_orderbook_lookup', 'orderbook_snapshots', ['symbol', 'exchange', 'timestamp'])

    # Create strategy_performance_history table
    op.create_table('strategy_performance_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_id', sa.String(100), nullable=False),
        sa.Column('strategy_name', sa.String(200), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('timeframe', sa.String(20), nullable=False),
        sa.Column('total_trades', sa.Integer(), nullable=True),
        sa.Column('winning_trades', sa.Integer(), nullable=True),
        sa.Column('losing_trades', sa.Integer(), nullable=True),
        sa.Column('win_rate', sa.Numeric(5, 4), nullable=True),
        sa.Column('starting_balance', sa.Numeric(20, 8), nullable=False),
        sa.Column('ending_balance', sa.Numeric(20, 8), nullable=False),
        sa.Column('total_pnl', sa.Numeric(20, 8), nullable=False),
        sa.Column('total_pnl_pct', sa.Numeric(10, 4), nullable=True),
        sa.Column('max_drawdown', sa.Numeric(10, 4), nullable=True),
        sa.Column('sharpe_ratio', sa.Numeric(10, 4), nullable=True),
        sa.Column('sortino_ratio', sa.Numeric(10, 4), nullable=True),
        sa.Column('calmar_ratio', sa.Numeric(10, 4), nullable=True),
        sa.Column('best_trade_pnl', sa.Numeric(20, 8), nullable=True),
        sa.Column('worst_trade_pnl', sa.Numeric(20, 8), nullable=True),
        sa.Column('avg_trade_pnl', sa.Numeric(20, 8), nullable=True),
        sa.Column('avg_win_pnl', sa.Numeric(20, 8), nullable=True),
        sa.Column('avg_loss_pnl', sa.Numeric(20, 8), nullable=True),
        sa.Column('total_fees', sa.Numeric(20, 8), nullable=True),
        sa.Column('total_slippage', sa.Numeric(20, 8), nullable=True),
        sa.Column('avg_execution_time', sa.Float(), nullable=True),
        sa.Column('traded_symbols', sa.JSON(), nullable=True),
        sa.Column('trade_distribution', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_live', sa.Boolean(), nullable=True),
        sa.Column('data_source', sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_perf_history_lookup', 'strategy_performance_history', ['strategy_id', 'user_id', 'period_start'])
    op.create_index('idx_perf_history_user', 'strategy_performance_history', ['user_id', 'period_start'])

    # Create backtest_results table
    op.create_table('backtest_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_id', sa.String(100), nullable=False),
        sa.Column('strategy_name', sa.String(200), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('initial_capital', sa.Numeric(20, 8), nullable=False),
        sa.Column('symbols', sa.JSON(), nullable=False),
        sa.Column('strategy_params', sa.JSON(), nullable=True),
        sa.Column('risk_params', sa.JSON(), nullable=True),
        sa.Column('execution_params', sa.JSON(), nullable=True),
        sa.Column('final_capital', sa.Numeric(20, 8), nullable=False),
        sa.Column('total_return', sa.Numeric(10, 4), nullable=True),
        sa.Column('total_return_pct', sa.Numeric(10, 4), nullable=True),
        sa.Column('total_trades', sa.Integer(), nullable=True),
        sa.Column('win_rate', sa.Numeric(5, 4), nullable=True),
        sa.Column('profit_factor', sa.Numeric(10, 4), nullable=True),
        sa.Column('expectancy', sa.Numeric(20, 8), nullable=True),
        sa.Column('max_drawdown', sa.Numeric(10, 4), nullable=True),
        sa.Column('max_drawdown_duration', sa.Integer(), nullable=True),
        sa.Column('sharpe_ratio', sa.Numeric(10, 4), nullable=True),
        sa.Column('sortino_ratio', sa.Numeric(10, 4), nullable=True),
        sa.Column('calmar_ratio', sa.Numeric(10, 4), nullable=True),
        sa.Column('equity_curve', sa.JSON(), nullable=True),
        sa.Column('trade_log', sa.JSON(), nullable=True),
        sa.Column('monthly_returns', sa.JSON(), nullable=True),
        sa.Column('data_quality_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('data_gaps_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('execution_time', sa.Float(), nullable=True),
        sa.Column('data_source', sa.String(50), nullable=True),
        sa.Column('engine_version', sa.String(20), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_backtest_lookup', 'backtest_results', ['strategy_id', 'created_at'])
    op.create_index('idx_backtest_user', 'backtest_results', ['user_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('idx_backtest_user', table_name='backtest_results')
    op.drop_index('idx_backtest_lookup', table_name='backtest_results')
    op.drop_table('backtest_results')

    op.drop_index('idx_perf_history_user', table_name='strategy_performance_history')
    op.drop_index('idx_perf_history_lookup', table_name='strategy_performance_history')
    op.drop_table('strategy_performance_history')

    op.drop_index('idx_orderbook_lookup', table_name='orderbook_snapshots')
    op.drop_table('orderbook_snapshots')

    op.drop_index('idx_ticker_lookup', table_name='market_tickers')
    op.drop_table('market_tickers')

    op.drop_index('idx_ohlcv_timestamp', table_name='market_data_ohlcv')
    op.drop_index('idx_ohlcv_lookup', table_name='market_data_ohlcv')
    op.drop_table('market_data_ohlcv')
>>>>>>> 74798ab3bb0b22f57424b2a99d41a082a3880f44
