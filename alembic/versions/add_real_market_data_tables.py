"""Add real market data tables with corrected precision

Revision ID: add_real_market_data
Revises:
Create Date: 2025-01-18 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = 'add_real_market_data'
down_revision = None  # Update this to point to the latest migration
branch_labels = None
depends_on = None


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