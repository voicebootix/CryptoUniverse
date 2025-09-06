"""Add performance indexes for slow queries

Revision ID: add_performance_indexes
Revises: 
Create Date: 2024-09-06

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_performance_indexes'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add indexes to improve query performance."""
    
    # Add indexes for users table
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'])
    op.create_index('ix_users_status', 'users', ['status'])
    
    # Add indexes for exchange_accounts table
    op.create_index('ix_exchange_accounts_user_id', 'exchange_accounts', ['user_id'])
    op.create_index('ix_exchange_accounts_exchange_name', 'exchange_accounts', ['exchange_name'])
    op.create_index('ix_exchange_accounts_user_exchange', 'exchange_accounts', ['user_id', 'exchange_name'])
    
    # Add indexes for exchange_balances table
    op.create_index('ix_exchange_balances_account_id', 'exchange_balances', ['account_id'])
    op.create_index('ix_exchange_balances_symbol', 'exchange_balances', ['symbol'])
    op.create_index('ix_exchange_balances_account_symbol', 'exchange_balances', ['account_id', 'symbol'])
    
    # Add indexes for exchange_api_keys table
    op.create_index('ix_exchange_api_keys_account_id', 'exchange_api_keys', ['account_id'])
    op.create_index('ix_exchange_api_keys_key_type', 'exchange_api_keys', ['key_type'])
    
    # Add indexes for portfolios table
    op.create_index('ix_portfolios_user_id', 'portfolios', ['user_id'])
    op.create_index('ix_portfolios_is_default', 'portfolios', ['is_default'])
    

def downgrade():
    """Remove performance indexes."""
    
    # Remove portfolios indexes
    op.drop_index('ix_portfolios_is_default', 'portfolios')
    op.drop_index('ix_portfolios_user_id', 'portfolios')
    
    # Remove exchange_api_keys indexes
    op.drop_index('ix_exchange_api_keys_key_type', 'exchange_api_keys')
    op.drop_index('ix_exchange_api_keys_account_id', 'exchange_api_keys')
    
    # Remove exchange_balances indexes
    op.drop_index('ix_exchange_balances_account_symbol', 'exchange_balances')
    op.drop_index('ix_exchange_balances_symbol', 'exchange_balances')
    op.drop_index('ix_exchange_balances_account_id', 'exchange_balances')
    
    # Remove exchange_accounts indexes
    op.drop_index('ix_exchange_accounts_user_exchange', 'exchange_accounts')
    op.drop_index('ix_exchange_accounts_exchange_name', 'exchange_accounts')
    op.drop_index('ix_exchange_accounts_user_id', 'exchange_accounts')
    
    # Remove users indexes
    op.drop_index('ix_users_status', 'users')
    op.drop_index('ix_users_tenant_id', 'users')
    op.drop_index('ix_users_email', 'users')