"""Rename market_data table to legacy_market_data

Revision ID: 007_rename_market_data_to_legacy
Revises: 006_add_live_strategy_performance
Create Date: 2025-01-18 18:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007_rename_market_data_to_legacy'
down_revision = '006_add_live_strategy_performance'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if market_data table exists before renaming
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'market_data' in inspector.get_table_names():
        # Rename table from market_data to legacy_market_data
        op.rename_table('market_data', 'legacy_market_data')

        # Rename indexes to match new table name - check existence first
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        existing_indexes = {idx['name'] for idx in inspector.get_indexes('legacy_market_data')}

        if 'idx_market_data_symbol_timestamp' in existing_indexes:
            op.drop_index('idx_market_data_symbol_timestamp', table_name='legacy_market_data')
        if 'idx_market_data_exchange_timestamp' in existing_indexes:
            op.drop_index('idx_market_data_exchange_timestamp', table_name='legacy_market_data')

        # Create new indexes with proper names
        op.create_index('idx_legacy_market_data_symbol_timestamp', 'legacy_market_data', ['symbol', 'timestamp'])
        op.create_index('idx_legacy_market_data_exchange_timestamp', 'legacy_market_data', ['exchange', 'timestamp'])
    else:
        # If market_data doesn't exist, create legacy_market_data directly
        op.create_table('legacy_market_data',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('symbol', sa.String(20), nullable=False),
            sa.Column('exchange', sa.String(50), nullable=False),
            sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
            sa.Column('open_price', sa.Numeric(20, 8), nullable=False),
            sa.Column('high_price', sa.Numeric(20, 8), nullable=False),
            sa.Column('low_price', sa.Numeric(20, 8), nullable=False),
            sa.Column('close_price', sa.Numeric(20, 8), nullable=False),
            sa.Column('volume', sa.Numeric(30, 8), nullable=False),
            sa.Column('quote_volume', sa.Numeric(30, 8), nullable=True),
            sa.Column('vwap', sa.Numeric(20, 8), nullable=True),
            sa.Column('trade_count', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )

        # Create indexes
        op.create_index('idx_legacy_market_data_symbol_timestamp', 'legacy_market_data', ['symbol', 'timestamp'])
        op.create_index('idx_legacy_market_data_exchange_timestamp', 'legacy_market_data', ['exchange', 'timestamp'])
        op.create_index('idx_legacy_market_data_symbol', 'legacy_market_data', ['symbol'])
        op.create_index('idx_legacy_market_data_timestamp', 'legacy_market_data', ['timestamp'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_legacy_market_data_symbol_timestamp', table_name='legacy_market_data')
    op.drop_index('idx_legacy_market_data_exchange_timestamp', table_name='legacy_market_data')

    # Check for additional indexes before dropping
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'legacy_market_data' in inspector.get_table_names():
        existing_indexes = {idx['name'] for idx in inspector.get_indexes('legacy_market_data')}
        if 'idx_legacy_market_data_symbol' in existing_indexes:
            op.drop_index('idx_legacy_market_data_symbol', table_name='legacy_market_data')
        if 'idx_legacy_market_data_timestamp' in existing_indexes:
            op.drop_index('idx_legacy_market_data_timestamp', table_name='legacy_market_data')

    # Rename table back
    op.rename_table('legacy_market_data', 'market_data')

    # Recreate original indexes
    op.create_index('idx_market_data_symbol_timestamp', 'market_data', ['symbol', 'timestamp'])
    op.create_index('idx_market_data_exchange_timestamp', 'market_data', ['exchange', 'timestamp'])