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
    
    # Index for exchange accounts with status (for the slow JOIN queries)
    op.create_index(
        'idx_exchange_accounts_user_exchange_status', 
        'exchange_accounts', 
        ['user_id', 'exchange_name', 'status'], 
        unique=False
    )
    
    # Index for exchange API keys by account_id (for JOINs)
    op.create_index(
        'idx_exchange_api_keys_account_status', 
        'exchange_api_keys', 
        ['account_id', 'status'], 
        unique=False
    )
    
    # Index for exchange balances (frequent queries)
    op.create_index(
        'idx_exchange_balances_account_symbol', 
        'exchange_balances', 
        ['account_id', 'symbol'], 
        unique=False
    )
    
    # Index for trades by user and date (for recent trades endpoint)
    op.create_index(
        'idx_trades_user_created_desc', 
        'trades', 
        ['user_id', sa.text('created_at DESC')], 
        unique=False
    )
    
    # Index for portfolios by user
    op.create_index(
        'idx_portfolios_user_default', 
        'portfolios', 
        ['user_id', 'is_default'], 
        unique=False
    )
    
    # Index for active exchange accounts with trading enabled
    op.create_index(
        'idx_exchange_accounts_active_trading', 
        'exchange_accounts', 
        ['status', 'trading_enabled'], 
        unique=False
    )


def downgrade() -> None:
    """Remove performance indexes."""
    
    op.drop_index('idx_exchange_accounts_active_trading', table_name='exchange_accounts')
    op.drop_index('idx_portfolios_user_default', table_name='portfolios')
    op.drop_index('idx_trades_user_created_desc', table_name='trades')
    op.drop_index('idx_exchange_balances_account_symbol', table_name='exchange_balances')
    op.drop_index('idx_exchange_api_keys_account_status', table_name='exchange_api_keys')
    op.drop_index('idx_exchange_accounts_user_exchange_status', table_name='exchange_accounts')
    op.drop_index('idx_exchange_accounts_user_exchange', table_name='exchange_accounts')
    op.drop_index('idx_credit_accounts_user_id', table_name='credit_accounts')
    op.drop_index('idx_users_last_login', table_name='users')
    op.drop_index('idx_user_sessions_refresh_token', table_name='user_sessions')
    op.drop_index('idx_user_sessions_user_expires', table_name='user_sessions')
    op.drop_index('idx_users_email_status', table_name='users')
