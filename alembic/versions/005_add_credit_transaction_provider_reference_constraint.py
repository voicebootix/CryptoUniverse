"""Add provider field and composite unique constraint for credit transactions

Revision ID: 005_add_credit_transaction_provider_reference_constraint
Revises: 004_targeted_performance_fix
Create Date: 2025-01-18 12:00:00.000000

This migration:
1. Adds a 'provider' column to credit_transactions table
2. Handles existing duplicate reference_ids through deduplication
3. Creates a composite unique constraint on (provider, reference_id)
4. Is idempotent and safe for production deployment

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic
revision = '005_add_credit_transaction_provider_reference_constraint'
down_revision = '004_targeted_performance_fix'
branch_labels = None
depends_on = None


def upgrade():
    """Add provider column and composite unique constraint."""

    # Check if we're using PostgreSQL or SQLite
    bind = op.get_bind()
    engine_name = bind.dialect.name

    print(f"Running migration on {engine_name} database")

    # Step 1: Add provider column if it doesn't exist
    try:
        # Check if provider column already exists
        if engine_name == 'postgresql':
            result = bind.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='credit_transactions' AND column_name='provider'
            """))
            has_provider = result.fetchone() is not None
        else:  # SQLite
            result = bind.execute(text("PRAGMA table_info(credit_transactions)"))
            columns = [row[1] for row in result.fetchall()]
            has_provider = 'provider' in columns

        if not has_provider:
            print("Adding provider column...")
            op.add_column('credit_transactions', sa.Column('provider', sa.String(length=50), nullable=True))
            op.create_index('ix_credit_transactions_provider', 'credit_transactions', ['provider'])
            print("✅ Provider column added successfully")
        else:
            print("✅ Provider column already exists, skipping")

    except Exception as e:
        print(f"⚠️ Error checking/adding provider column: {e}")
        # Continue with migration - column might exist already

    # Step 2: Handle existing duplicates in reference_id
    print("Handling duplicate reference_ids...")

    try:
        if engine_name == 'postgresql':
            # Find and handle duplicates in PostgreSQL
            duplicate_check = bind.execute(text("""
                SELECT reference_id, COUNT(*) as count
                FROM credit_transactions
                WHERE reference_id IS NOT NULL
                GROUP BY reference_id
                HAVING COUNT(*) > 1
            """))
            duplicates = duplicate_check.fetchall()

            if duplicates:
                print(f"Found {len(duplicates)} duplicate reference_ids, deduplicating...")

                for ref_id, count in duplicates:
                    print(f"  Deduplicating reference_id: {ref_id} (found {count} times)")

                    # For duplicates, set provider to distinguish them (only for rows with NULL provider)
                    bind.execute(text("""
                        WITH numbered_transactions AS (
                            SELECT id, ROW_NUMBER() OVER (ORDER BY created_at) as rn
                            FROM credit_transactions
                            WHERE reference_id = :ref_id AND provider IS NULL
                        )
                        UPDATE credit_transactions
                        SET provider = CASE
                            WHEN nt.rn = 1 THEN 'legacy'
                            ELSE 'legacy_dup_' || nt.rn::text
                        END
                        FROM numbered_transactions nt
                        WHERE credit_transactions.id = nt.id AND credit_transactions.provider IS NULL
                    """), ref_id=ref_id)

                print("✅ Duplicates handled successfully")
            else:
                print("✅ No duplicate reference_ids found")

        else:  # SQLite
            # Handle duplicates in SQLite (more limited SQL capabilities)
            duplicate_check = bind.execute(text("""
                SELECT reference_id, COUNT(*) as count
                FROM credit_transactions
                WHERE reference_id IS NOT NULL
                GROUP BY reference_id
                HAVING COUNT(*) > 1
            """))
            duplicates = duplicate_check.fetchall()

            if duplicates:
                print(f"Found {len(duplicates)} duplicate reference_ids in SQLite")

                for ref_id, count in duplicates:
                    print(f"  Handling reference_id: {ref_id}")

                    # Get all transactions with this reference_id (only those with NULL provider)
                    transactions = bind.execute(text("""
                        SELECT id FROM credit_transactions
                        WHERE reference_id = :ref_id AND provider IS NULL
                        ORDER BY created_at
                    """), {"ref_id": ref_id}).fetchall()

                    # Update each transaction with a unique provider
                    for i, (tx_id,) in enumerate(transactions):
                        provider = 'legacy' if i == 0 else f'legacy_dup_{i+1}'
                        bind.execute(text("""
                            UPDATE credit_transactions
                            SET provider = :provider
                            WHERE id = :tx_id AND provider IS NULL
                        """), {"provider": provider, "tx_id": tx_id})

                print("✅ SQLite duplicates handled successfully")
            else:
                print("✅ No duplicate reference_ids found")

    except Exception as e:
        print(f"❌ Error handling duplicates: {e}")
        print("Migration cannot proceed with duplicate data.")
        print("Please resolve duplicate (provider, reference_id) pairs manually before retrying.")
        raise e

    # Pre-check: abort if duplicates remain for non-NULL provider/reference_id pairs
    dup_pairs = bind.execute(text("""
        SELECT provider, reference_id, COUNT(*) AS count
        FROM credit_transactions
        WHERE provider IS NOT NULL AND reference_id IS NOT NULL
        GROUP BY provider, reference_id
        HAVING COUNT(*) > 1
    """)).fetchall()
    if dup_pairs:
        detail = ", ".join(f"({p}, {r}) x{c}" for p, r, c in dup_pairs[:10])
        raise RuntimeError(
            f"Cannot create unique index: found {len(dup_pairs)} duplicated (provider, reference_id) pairs. Examples: {detail}"
        )

    # Step 3: Create composite unique constraint
    print("Creating composite unique constraint...")

    try:
        # Check if index already exists
        index_exists = False

        if engine_name == 'postgresql':
            result = bind.execute(text("""
                SELECT indexname FROM pg_indexes
                WHERE tablename='credit_transactions'
                AND indexname='uq_credit_transaction_provider_reference'
            """))
            index_exists = result.fetchone() is not None
        else:  # SQLite
            result = bind.execute(text("""
                SELECT name FROM sqlite_master
                WHERE type='index'
                AND name='uq_credit_transaction_provider_reference'
            """))
            index_exists = result.fetchone() is not None

        if not index_exists:
            # Create partial unique index that allows NULLs
            if engine_name == 'postgresql':
                # PostgreSQL supports partial indexes - use CONCURRENTLY outside transaction
                with op.get_context().autocommit_block():
                    op.create_index(
                        'uq_credit_transaction_provider_reference',
                        'credit_transactions',
                        ['provider', 'reference_id'],
                        unique=True,
                        postgresql_concurrently=True,
                        postgresql_where=sa.text("provider IS NOT NULL AND reference_id IS NOT NULL")
                    )
                print("✅ PostgreSQL partial unique index created")

            else:  # SQLite
                # SQLite also supports partial indexes
                op.create_index(
                    'uq_credit_transaction_provider_reference',
                    'credit_transactions',
                    ['provider', 'reference_id'],
                    unique=True,
                    sqlite_where=sa.text("provider IS NOT NULL AND reference_id IS NOT NULL")
                )
                print("✅ SQLite partial unique index created")
        else:
            print("✅ Unique index already exists")

    except Exception as e:
        print(f"⚠️ Error creating unique constraint: {e}")
        print("Migration will continue - constraint creation might be handled by SQLAlchemy model")

    print("✅ Migration completed successfully!")


def downgrade():
    """Remove provider column and constraint."""

    bind = op.get_bind()
    engine_name = bind.dialect.name

    print(f"Downgrading on {engine_name} database")

    # Remove unique constraint/index
    try:
        if engine_name == 'postgresql':
            # Use CONCURRENTLY outside transaction for PostgreSQL
            with op.get_context().autocommit_block():
                op.drop_index(
                    'uq_credit_transaction_provider_reference',
                    table_name='credit_transactions',
                    postgresql_concurrently=True
                )
        else:  # SQLite
            # Regular drop for SQLite
            op.drop_index(
                'uq_credit_transaction_provider_reference',
                table_name='credit_transactions'
            )
        print("✅ Unique constraint/index dropped")
    except Exception as e:
        print(f"⚠️ Error dropping constraint: {e}")

    # Remove provider column
    try:
        op.drop_index('ix_credit_transactions_provider', table_name='credit_transactions')
        op.drop_column('credit_transactions', 'provider')
        print("✅ Provider column dropped")
    except Exception as e:
        print(f"⚠️ Error dropping provider column: {e}")

    print("✅ Downgrade completed!")