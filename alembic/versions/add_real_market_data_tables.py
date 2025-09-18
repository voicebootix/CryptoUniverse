"""Add real market data tables

Revision ID: add_real_market_data
Revises: add_chat_memory_001
Create Date: 2025-01-18 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_real_market_data'
down_revision = 'add_chat_memory_001'
branch_labels = None
depends_on = None


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
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('source', sa.String(50), nullable=True),
        sa.Column('is_validated', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol', 'exchange', 'timeframe', 'timestamp', name='unique_candle')
    )
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
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_ticker_lookup', 'market_tickers', ['symbol', 'exchange', 'timestamp'])

    # Create orderbook_snapshots table
    op.create_table('orderbook_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('exchange', sa.String(50), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('bids', postgresql.JSONB(), nullable=False),
        sa.Column('asks', postgresql.JSONB(), nullable=False),
        sa.Column('best_bid', sa.Numeric(20, 8), nullable=True),
        sa.Column('best_ask', sa.Numeric(20, 8), nullable=True),
        sa.Column('spread', sa.Numeric(20, 8), nullable=True),
        sa.Column('spread_pct', sa.Numeric(10, 4), nullable=True),
        sa.Column('bid_depth_10', sa.Numeric(20, 8), nullable=True),
        sa.Column('ask_depth_10', sa.Numeric(20, 8), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
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
        sa.Column('win_rate', sa.Numeric(5, 2), nullable=True),
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
        sa.Column('traded_symbols', postgresql.JSONB(), nullable=True),
        sa.Column('trade_distribution', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
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
        sa.Column('symbols', postgresql.JSONB(), nullable=False),
        sa.Column('strategy_params', postgresql.JSONB(), nullable=True),
        sa.Column('risk_params', postgresql.JSONB(), nullable=True),
        sa.Column('execution_params', postgresql.JSONB(), nullable=True),
        sa.Column('final_capital', sa.Numeric(20, 8), nullable=False),
        sa.Column('total_return', sa.Numeric(10, 4), nullable=True),
        sa.Column('total_return_pct', sa.Numeric(10, 4), nullable=True),
        sa.Column('total_trades', sa.Integer(), nullable=True),
        sa.Column('win_rate', sa.Numeric(5, 2), nullable=True),
        sa.Column('profit_factor', sa.Numeric(10, 4), nullable=True),
        sa.Column('expectancy', sa.Numeric(20, 8), nullable=True),
        sa.Column('max_drawdown', sa.Numeric(10, 4), nullable=True),
        sa.Column('max_drawdown_duration', sa.Integer(), nullable=True),
        sa.Column('sharpe_ratio', sa.Numeric(10, 4), nullable=True),
        sa.Column('sortino_ratio', sa.Numeric(10, 4), nullable=True),
        sa.Column('calmar_ratio', sa.Numeric(10, 4), nullable=True),
        sa.Column('equity_curve', postgresql.JSONB(), nullable=True),
        sa.Column('trade_log', postgresql.JSONB(), nullable=True),
        sa.Column('monthly_returns', postgresql.JSONB(), nullable=True),
        sa.Column('data_quality_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('data_gaps_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
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
    op.drop_table('market_data_ohlcv')
