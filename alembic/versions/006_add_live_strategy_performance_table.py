"""Add live strategy performance table

Revision ID: 006_add_live_strategy_performance
Revises: 005_add_credit_transaction_provider_reference_constraint
Create Date: 2025-01-18 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_add_live_strategy_performance'
down_revision = '005_add_credit_transaction_provider_reference_constraint'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create live_strategy_performance table
    op.create_table('live_strategy_performance',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_id', sa.String(100), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_updated', sa.DateTime(timezone=True), nullable=False),
        sa.Column('total_return', sa.Numeric(8, 4), nullable=False, server_default=sa.text('0')),
        sa.Column('unrealized_pnl', sa.Numeric(20, 8), nullable=False, server_default=sa.text('0')),
        sa.Column('realized_pnl', sa.Numeric(20, 8), nullable=False, server_default=sa.text('0')),
        sa.Column('total_trades', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('winning_trades', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('losing_trades', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('win_rate', sa.Numeric(5, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('max_drawdown', sa.Numeric(7, 4), nullable=False, server_default=sa.text('0')),
        sa.Column('current_drawdown', sa.Numeric(7, 4), nullable=False, server_default=sa.text('0')),
        sa.Column('allocated_capital', sa.Numeric(20, 8), nullable=False),
        sa.Column('current_value', sa.Numeric(20, 8), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('max_drawdown >= 0.0 AND max_drawdown <= 100.0', name='check_max_drawdown_range'),
        sa.CheckConstraint('current_drawdown >= 0.0 AND current_drawdown <= 100.0', name='check_current_drawdown_range')
    )

    # Create indexes for performance
    op.create_index('idx_live_strategy_performance_user_strategy', 'live_strategy_performance', ['user_id', 'strategy_id'])
    op.create_index('idx_live_strategy_performance_active', 'live_strategy_performance', ['is_active', 'last_updated'])
    op.create_index('idx_live_strategy_performance_strategy_id', 'live_strategy_performance', ['strategy_id'])
    op.create_index('idx_live_strategy_performance_user_id', 'live_strategy_performance', ['user_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_live_strategy_performance_user_id', table_name='live_strategy_performance')
    op.drop_index('idx_live_strategy_performance_strategy_id', table_name='live_strategy_performance')
    op.drop_index('idx_live_strategy_performance_active', table_name='live_strategy_performance')
    op.drop_index('idx_live_strategy_performance_user_strategy', table_name='live_strategy_performance')

    # Drop table
    op.drop_table('live_strategy_performance')