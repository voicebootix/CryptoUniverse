"""Add strategy submissions table

Revision ID: add_strategy_submissions
Revises:
Create Date: 2025-01-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'add_strategy_submissions'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create strategy_submissions table (using String for enums for SQLite compatibility)
    op.create_table('strategy_submissions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('risk_level', sa.String(20), nullable=True, default='medium'),
        sa.Column('expected_return_min', sa.Float(), nullable=True, default=0.0),
        sa.Column('expected_return_max', sa.Float(), nullable=True, default=0.0),
        sa.Column('required_capital', sa.DECIMAL(15, 2), nullable=True, default=1000.0),
        sa.Column('pricing_model', sa.String(20), nullable=True, default='free'),
        sa.Column('price_amount', sa.DECIMAL(10, 2), nullable=True),
        sa.Column('profit_share_percentage', sa.Float(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True, default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewer_id', sa.String(36), nullable=True),
        sa.Column('reviewer_feedback', sa.Text(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('backtest_results', sa.JSON(), nullable=True),
        sa.Column('validation_results', sa.JSON(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('target_audience', sa.JSON(), nullable=True),
        sa.Column('complexity_level', sa.String(20), nullable=True, default='intermediate'),
        sa.Column('documentation_quality', sa.Integer(), nullable=True, default=0),
        sa.Column('support_level', sa.String(20), nullable=True, default='standard'),
        sa.Column('strategy_code', sa.Text(), nullable=True),
        sa.Column('strategy_config', sa.JSON(), nullable=True),
        sa.Column('total_subscribers', sa.Integer(), nullable=True, default=0),
        sa.Column('total_revenue', sa.DECIMAL(15, 2), nullable=True, default=0.0),
        sa.Column('average_rating', sa.Float(), nullable=True, default=0.0),
        sa.Column('total_reviews', sa.Integer(), nullable=True, default=0),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for better query performance
    op.create_index('idx_strategy_submissions_user_id', 'strategy_submissions', ['user_id'])
    op.create_index('idx_strategy_submissions_status', 'strategy_submissions', ['status'])
    op.create_index('idx_strategy_submissions_category', 'strategy_submissions', ['category'])
    op.create_index('idx_strategy_submissions_created_at', 'strategy_submissions', ['created_at'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_strategy_submissions_created_at', 'strategy_submissions')
    op.drop_index('idx_strategy_submissions_category', 'strategy_submissions')
    op.drop_index('idx_strategy_submissions_status', 'strategy_submissions')
    op.drop_index('idx_strategy_submissions_user_id', 'strategy_submissions')

    # Drop table
    op.drop_table('strategy_submissions')