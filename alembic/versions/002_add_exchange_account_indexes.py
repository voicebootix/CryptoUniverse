"""Add performance indexes and constraints to exchange_accounts

Revision ID: 002
Revises: 001
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError, ProgrammingError

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
            
            # Resolve ALL duplicates in a single set-based DELETE using CTE
            resolve_all_duplicates = text("""
                WITH ranked_accounts AS (
                    SELECT id, ROW_NUMBER() OVER (
                        PARTITION BY user_id, exchange_name, account_name 
                        ORDER BY created_at DESC, id DESC
                    ) as rn
                    FROM exchange_accounts
                )
                DELETE FROM exchange_accounts 
                WHERE id IN (
                    SELECT id FROM ranked_accounts WHERE rn > 1
                )
            """)
            
            result = connection.execute(resolve_all_duplicates)
            print(f"Removed {result.rowcount} duplicate records in single operation")
        
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
        alter_statement = """
            ALTER TABLE exchange_accounts 
            ADD CONSTRAINT unique_user_exchange_account 
            UNIQUE USING INDEX uq_user_exchange_account_idx
        """
        op.execute(text(alter_statement))
    except (DBAPIError, OperationalError, ProgrammingError) as e:
        # Expected: constraint already exists or index doesn't exist
        import logging
        logger = logging.getLogger('alembic.runtime.migration')
        logger.warning(
            f"Constraint creation failed (likely already exists): {e}. "
            f"Statement: {alter_statement.strip()}"
        )
        # Continue - this is expected for idempotent migrations
    except Exception as e:
        # Unexpected error - re-raise to surface real issues
        import logging
        logger = logging.getLogger('alembic.runtime.migration')
        logger.error(f"Unexpected error creating constraint: {e}")
        raise


def downgrade():
    """Remove the indexes and constraints."""
    with op.get_context().autocommit_block():
        
        # Drop constraint first
        try:
            op.drop_constraint('unique_user_exchange_account', 'exchange_accounts')
        except (DBAPIError, OperationalError, ProgrammingError) as e:
            # Expected: constraint doesn't exist
            import logging
            logger = logging.getLogger('alembic.runtime.migration')
            logger.warning(f"Constraint drop failed (likely doesn't exist): {e}")
        except Exception as e:
            # Unexpected error - log but continue with index cleanup
            import logging
            logger = logging.getLogger('alembic.runtime.migration')
            logger.error(f"Unexpected error dropping constraint: {e}")
            # Don't raise - continue with index cleanup
        
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
            except (DBAPIError, OperationalError, ProgrammingError) as e:
                # Expected: index doesn't exist
                import logging
                logger = logging.getLogger('alembic.runtime.migration')
                logger.warning(f"Index drop failed for {index_name} (likely doesn't exist): {e}")
            except Exception as e:
                # Unexpected error - log but continue with other indexes
                import logging
                logger = logging.getLogger('alembic.runtime.migration')
                logger.error(f"Unexpected error dropping index {index_name}: {e}")
                # Don't raise - continue with other indexes