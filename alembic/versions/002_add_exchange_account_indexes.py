"""Add performance indexes and constraints to exchange_accounts

Revision ID: 002
Revises: 001
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """Add performance indexes and constraints to exchange_accounts table."""
    # Use autocommit for concurrent index creation
    with op.get_context().autocommit_block():
        
        # Check and resolve any duplicate data before adding unique constraint
        connection = op.get_bind()
        
        # Find potential duplicates
        duplicate_check = text("""
            SELECT user_id, exchange_name, account_name, COUNT(*) as count
            FROM exchange_accounts 
            GROUP BY user_id, exchange_name, account_name 
            HAVING COUNT(*) > 1
        """)
        
        duplicates = connection.execute(duplicate_check).fetchall()
        
        if duplicates:
            # Log duplicates found
            print(f"Found {len(duplicates)} duplicate exchange account combinations")
            
            # Resolve duplicates by keeping the most recent record
            for dup in duplicates:
                user_id, exchange_name, account_name = dup[0], dup[1], dup[2]
                
                resolve_duplicates = text("""
                    DELETE FROM exchange_accounts 
                    WHERE id NOT IN (
                        SELECT id FROM (
                            SELECT id, ROW_NUMBER() OVER (
                                PARTITION BY user_id, exchange_name, account_name 
                                ORDER BY created_at DESC, id DESC
                            ) as rn
                            FROM exchange_accounts 
                            WHERE user_id = :user_id 
                            AND exchange_name = :exchange_name 
                            AND account_name = :account_name
                        ) ranked WHERE rn = 1
                    )
                    AND user_id = :user_id 
                    AND exchange_name = :exchange_name 
                    AND account_name = :account_name
                """)
                
                connection.execute(resolve_duplicates, {
                    'user_id': user_id,
                    'exchange_name': exchange_name, 
                    'account_name': account_name
                })
        
        # Create performance indexes concurrently
        op.create_index(
            'idx_exchange_user_status',
            'exchange_accounts',
            ['user_id', 'status'],
            postgresql_concurrently=True,
            if_not_exists=True
        )
        
        op.create_index(
            'idx_exchange_accounts_user_exchange_status',
            'exchange_accounts', 
            ['user_id', 'exchange_name', 'status'],
            postgresql_concurrently=True,
            if_not_exists=True
        )
        
        op.create_index(
            'idx_exchange_accounts_status_trading',
            'exchange_accounts',
            ['status', 'trading_enabled'],
            postgresql_concurrently=True,
            if_not_exists=True
        )
        
        op.create_index(
            'idx_exchange_accounts_user_trading',
            'exchange_accounts',
            ['user_id', 'trading_enabled'],
            postgresql_concurrently=True,
            if_not_exists=True
        )
        
        op.create_index(
            'idx_exchange_name_status',
            'exchange_accounts',
            ['exchange_name', 'status'],
            postgresql_concurrently=True,
            if_not_exists=True
        )
        
        # Create partial index for default accounts
        op.create_index(
            'idx_exchange_default_true',
            'exchange_accounts',
            ['user_id'],
            postgresql_where=sa.text('is_default = true'),
            postgresql_concurrently=True,
            if_not_exists=True
        )
        
        # Create unique index concurrently first
        op.create_index(
            'uq_user_exchange_account_idx',
            'exchange_accounts',
            ['user_id', 'exchange_name', 'account_name'],
            unique=True,
            postgresql_concurrently=True,
            if_not_exists=True
        )

    # Add the constraint using the unique index (in transaction)
    try:
        op.execute(text("""
            ALTER TABLE exchange_accounts 
            ADD CONSTRAINT unique_user_exchange_account 
            UNIQUE USING INDEX uq_user_exchange_account_idx
        """))
    except Exception:
        # Constraint might already exist, continue
        pass


def downgrade():
    """Remove the indexes and constraints."""
    with op.get_context().autocommit_block():
        
        # Drop constraint first
        try:
            op.drop_constraint('unique_user_exchange_account', 'exchange_accounts')
        except Exception:
            pass
        
        # Drop indexes concurrently
        indexes_to_drop = [
            'uq_user_exchange_account_idx',
            'idx_exchange_default_true',
            'idx_exchange_name_status',
            'idx_exchange_accounts_user_trading',
            'idx_exchange_accounts_status_trading',
            'idx_exchange_accounts_user_exchange_status',
            'idx_exchange_user_status'
        ]
        
        for index_name in indexes_to_drop:
            try:
                op.drop_index(
                    index_name,
                    table_name='exchange_accounts',
                    postgresql_concurrently=True
                )
            except Exception:
                # Index might not exist, continue
                pass