"""Add Strategy IDE fields to TradingStrategy model

Revision ID: add_strategy_ide_fields
Revises: add_strategy_submissions
Create Date: 2025-01-15

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_strategy_ide_fields'
down_revision = 'add_strategy_submissions'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to trading_strategies table
    op.add_column('trading_strategies', sa.Column('strategy_code', sa.Text(), nullable=True))
    op.add_column('trading_strategies', sa.Column('category', sa.String(50), nullable=True))
    op.add_column('trading_strategies', sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'))

    # Create index for category field for better query performance
    op.create_index('idx_trading_strategies_category', 'trading_strategies', ['category'])


def downgrade():
    # Drop index
    op.drop_index('idx_trading_strategies_category', 'trading_strategies')

    # Remove columns
    op.drop_column('trading_strategies', 'metadata')
    op.drop_column('trading_strategies', 'category')
    op.drop_column('trading_strategies', 'strategy_code')