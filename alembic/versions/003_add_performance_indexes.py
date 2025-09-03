"""Add performance indexes for user operations

Revision ID: 003_add_performance_indexes
Revises: 002_add_exchange_account_indexes
Create Date: 2025-01-09 04:56:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '003_add_performance_indexes'
down_revision = '002_add_exchange_account_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance indexes for common queries."""
    
    # Index for user login queries (email lookup)
    op.create_index(
        'idx_users_email_status', 
        'users', 
        ['email', 'status'], 
        unique=False
    )
    
    # Index for user sessions cleanup and lookup
    op.create_index(
        'idx_user_sessions_user_expires', 
        'user_sessions', 
        ['user_id', 'expires_at', 'is_active'], 
        unique=False
    )
    
    # Index for user sessions by refresh token
    op.create_index(
        'idx_user_sessions_refresh_token', 
        'user_sessions', 
        ['refresh_token'], 
        unique=True
    )
    
    # Index for user last_login updates
    op.create_index(
        'idx_users_last_login', 
        'users', 
        ['last_login'], 
        unique=False
    )
    
    # Index for credit account lookups
    op.create_index(
        'idx_credit_accounts_user_id', 
        'credit_accounts', 
        ['user_id'], 
        unique=True
    )
    
    # Index for exchange accounts by user and exchange
    op.create_index(
        'idx_exchange_accounts_user_exchange', 
        'exchange_accounts', 
        ['user_id', 'exchange_name'], 
        unique=False
    )


def downgrade() -> None:
    """Remove performance indexes."""
    
    op.drop_index('idx_exchange_accounts_user_exchange', table_name='exchange_accounts')
    op.drop_index('idx_credit_accounts_user_id', table_name='credit_accounts')
    op.drop_index('idx_users_last_login', table_name='users')
    op.drop_index('idx_user_sessions_refresh_token', table_name='user_sessions')
    op.drop_index('idx_user_sessions_user_expires', table_name='user_sessions')
    op.drop_index('idx_users_email_status', table_name='users')
