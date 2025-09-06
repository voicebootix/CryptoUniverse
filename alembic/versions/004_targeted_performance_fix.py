"""Targeted performance optimization based on actual usage data

Revision ID: 004_targeted_performance_fix
Revises: 003_add_performance_indexes
Create Date: 2025-01-09 06:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '004_targeted_performance_fix'
down_revision = '003_add_performance_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add only the indexes that will actually improve performance based on real usage."""
    
    # CRITICAL: These are the only indexes you actually need based on your data
    
    # 1. Optimize the hot exchange_accounts queries (2,108 scans!)
    # Your current ix_exchange_accounts_id is being hammered
    try:
        op.create_index(
            'idx_exchange_accounts_user_status_optimized',
            'exchange_accounts',
            ['user_id', 'status', 'trading_enabled'],
            unique=False
        )
    except:
        pass  # May already exist
    
    # 2. Optimize exchange_api_keys status lookups (1,137 scans!)
    try:
        op.create_index(
            'idx_api_keys_account_status_optimized',
            'exchange_api_keys', 
            ['account_id', 'status', 'expires_at'],
            unique=False
        )
    except:
        pass
    
    # 3. Optimize the hot exchange_balances queries (919 scans!)
    try:
        op.create_index(
            'idx_balances_account_nonzero',
            'exchange_balances',
            ['account_id', 'total_balance'],
            postgresql_where=sa.text('total_balance > 0'),
            unique=False
        )
    except:
        pass
    
    # 4. Optimize user session lookups (most active table with 73 rows)
    try:
        op.create_index(
            'idx_sessions_user_active_expires',
            'user_sessions',
            ['user_id', 'is_active', 'expires_at'],
            postgresql_where=sa.text('is_active = true'),
            unique=False
        )
    except:
        pass


def downgrade() -> None:
    """Remove targeted performance indexes."""
    
    try:
        op.drop_index('idx_sessions_user_active_expires', table_name='user_sessions')
    except:
        pass
    
    try:
        op.drop_index('idx_balances_account_nonzero', table_name='exchange_balances')
    except:
        pass
        
    try:
        op.drop_index('idx_api_keys_account_status_optimized', table_name='exchange_api_keys')
    except:
        pass
        
    try:
        op.drop_index('idx_exchange_accounts_user_status_optimized', table_name='exchange_accounts')
    except:
        pass
