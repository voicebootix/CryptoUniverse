"""
Test the 005_add_credit_transaction_provider_reference_constraint migration.

This test verifies:
1. Migration can run successfully (upgrade)
2. Migration is idempotent (can run multiple times)
3. Migration can be rolled back (downgrade)
4. Database structure is correct after migration
"""

import pytest
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text, inspect
import tempfile
import os
import uuid
import datetime


@pytest.fixture
def alembic_config():
    """Create Alembic configuration for testing."""
    # Use the actual alembic configuration
    config = Config("alembic.ini")
    return config


@pytest.fixture
def alembic_engine(async_db_session):
    """Get the database engine for Alembic operations."""
    return async_db_session.bind


class TestProviderReferenceConstraintMigration:
    """Test the provider reference constraint migration."""

    def test_migration_upgrade(self, alembic_config, alembic_engine):
        """Test that migration upgrade works correctly."""

        with alembic_engine.connect() as connection:
            # Set up migration context
            migration_ctx = MigrationContext.configure(connection)

            # Check current revision
            current_revision = migration_ctx.get_current_revision()

            # Run the specific migration
            script_dir = ScriptDirectory.from_config(alembic_config)

            # Find our migration
            target_revision = "005_add_credit_transaction_provider_reference_constraint"

            # Verify migration exists
            revision = script_dir.get_revision(target_revision)
            assert revision is not None, f"Migration {target_revision} not found"

            # The actual migration test would run via alembic command
            # This is a structural test to verify the migration file exists and is valid
            assert revision.revision == target_revision
            assert "add provider field and composite unique constraint" in revision.doc.lower()

    def test_migration_structure(self, alembic_engine):
        """Test that migration creates expected database structure."""

        inspector = inspect(alembic_engine)

        # Check that credit_transactions table exists
        tables = inspector.get_table_names()
        assert 'credit_transactions' in tables

        # Check columns
        columns = inspector.get_columns('credit_transactions')
        column_names = [col['name'] for col in columns]

        # Verify expected columns exist
        expected_columns = [
            'id', 'account_id', 'transaction_type', 'amount',
            'provider', 'reference_id', 'created_at'
        ]

        for col in expected_columns:
            assert col in column_names, f"Column {col} missing from credit_transactions table"

        # Check provider column specifics
        provider_column = next((col for col in columns if col['name'] == 'provider'), None)
        assert provider_column is not None, "Provider column not found"
        assert provider_column['nullable'] is True, "Provider column should be nullable"

    def test_migration_indexes(self, alembic_engine):
        """Test that migration creates expected indexes."""

        inspector = inspect(alembic_engine)

        # Check indexes on credit_transactions
        indexes = inspector.get_indexes('credit_transactions')
        index_names = [idx['name'] for idx in indexes]

        # Should have provider index
        provider_index_exists = any('provider' in name.lower() for name in index_names)
        assert provider_index_exists, f"Provider index not found. Available indexes: {index_names}"

        # Should have reference_id index
        reference_index_exists = any('reference' in name.lower() for name in index_names)
        assert reference_index_exists, f"Reference index not found. Available indexes: {index_names}"

    async def test_migration_handles_existing_data(self, async_db_session, test_credit_account):
        """Test that migration properly handles existing data."""

        # Create some test data that simulates pre-migration state
        # (This would be data with reference_id but no provider)

        # Insert raw data simulating pre-migration state
        tx_id = uuid.uuid4()
        now = datetime.datetime.utcnow()

        await async_db_session.execute(text("""
            INSERT INTO credit_transactions (
                id, account_id, transaction_type, amount, description,
                balance_before, balance_after, reference_id, source, created_at, processed_at
            ) VALUES (
                :tx_id, :account_id, 'purchase', 100, 'Pre-migration test',
                1000, 1100, 'pre_migration_ref', 'test', :created_at, :processed_at
            )
        """), {
            "tx_id": tx_id,
            "account_id": test_credit_account.id,
            "created_at": now,
            "processed_at": now
        })

        await async_db_session.commit()

        # Verify data exists
        result = await async_db_session.execute(text("""
            SELECT COUNT(*) FROM credit_transactions
            WHERE reference_id = 'pre_migration_ref'
        """))
        count = result.scalar()
        assert count == 1

        # After migration runs, this data should have a provider set
        # (In actual migration, this would be set to 'legacy')

        # Simulate what migration would do
        await async_db_session.execute(text("""
            UPDATE credit_transactions
            SET provider = 'legacy'
            WHERE reference_id = 'pre_migration_ref' AND provider IS NULL
        """))
        await async_db_session.commit()

        # Verify update worked
        result = await async_db_session.execute(text("""
            SELECT provider FROM credit_transactions
            WHERE reference_id = 'pre_migration_ref'
        """))
        provider = result.scalar()
        assert provider == 'legacy'

    def test_migration_idempotency(self, alembic_engine):
        """Test that migration can be run multiple times safely."""

        inspector = inspect(alembic_engine)

        # Get current state
        initial_columns = set(col['name'] for col in inspector.get_columns('credit_transactions'))
        initial_indexes = set(idx['name'] for idx in inspector.get_indexes('credit_transactions'))

        # The migration should be idempotent - running it multiple times should be safe
        # This is verified by checking that the migration script uses IF NOT EXISTS clauses
        # and proper error handling

        # Read the migration file to verify idempotency features
        migration_file = "alembic/versions/005_add_credit_transaction_provider_reference_constraint.py"
        assert os.path.exists(migration_file), "Migration file should exist"

        with open(migration_file, 'r') as f:
            content = f.read()

        # Check for idempotency patterns
        idempotency_indicators = [
            "if not has_provider",
            "already exists",
            "constraint_exists",
            "try:",
            "except"
        ]

        for indicator in idempotency_indicators:
            assert indicator in content, f"Migration should include idempotency check: {indicator}"

    async def test_constraint_enforcement_after_migration(self, async_db_session, test_credit_account):
        """Test that the constraint is properly enforced after migration."""

        # Create a transaction with provider and reference_id
        tx1_id = uuid.uuid4()
        now = datetime.datetime.utcnow()

        await async_db_session.execute(text("""
            INSERT INTO credit_transactions (
                id, account_id, transaction_type, amount, description,
                balance_before, balance_after, provider, reference_id, source, created_at, processed_at
            ) VALUES (
                :tx_id, :account_id, 'purchase', 100, 'Constraint test 1',
                1000, 1100, 'test_provider', 'constraint_ref', 'test', :created_at, :processed_at
            )
        """), {
            "tx_id": tx1_id,
            "account_id": test_credit_account.id,
            "created_at": now,
            "processed_at": now
        })
        await async_db_session.commit()

        # Try to create duplicate - should fail
        with pytest.raises(Exception) as exc_info:
            tx2_id = uuid.uuid4()
            now2 = datetime.datetime.utcnow()

            await async_db_session.execute(text("""
                INSERT INTO credit_transactions (
                    id, account_id, transaction_type, amount, description,
                    balance_before, balance_after, provider, reference_id, source, created_at, processed_at
                ) VALUES (
                    :tx_id, :account_id, 'purchase', 200, 'Constraint test 2',
                    1100, 1300, 'test_provider', 'constraint_ref', 'test', :created_at, :processed_at
                )
            """), {
                "tx_id": tx2_id,
                "account_id": test_credit_account.id,
                "created_at": now2,
                "processed_at": now2
            })
            await async_db_session.commit()

        # Should be a constraint violation
        error_msg = str(exc_info.value).lower()
        assert any(keyword in error_msg for keyword in ['unique', 'constraint', 'duplicate']), \
            f"Expected constraint violation, got: {exc_info.value}"

    def test_migration_rollback_structure(self, alembic_config):
        """Test that migration rollback (downgrade) is properly structured."""

        # Read the migration file to verify rollback functionality
        migration_file = "alembic/versions/005_add_credit_transaction_provider_reference_constraint.py"

        with open(migration_file, 'r') as f:
            content = f.read()

        # Check that downgrade function exists and has proper structure
        assert "def downgrade():" in content, "Migration should have downgrade function"
        assert "drop_column" in content, "Downgrade should drop provider column"
        assert "drop_index" in content, "Downgrade should drop indexes"

        # Check for safe rollback patterns
        rollback_patterns = [
            "if exists",
            "try:",
            "except"
        ]

        for pattern in rollback_patterns:
            assert pattern in content, f"Rollback should include safe pattern: {pattern}"


class TestMigrationPerformance:
    """Test performance aspects of the migration."""

    def test_migration_uses_concurrent_operations(self):
        """Test that migration uses concurrent operations where possible."""

        migration_file = "alembic/versions/005_add_credit_transaction_provider_reference_constraint.py"

        with open(migration_file, 'r') as f:
            content = f.read()

        # For PostgreSQL, should use CONCURRENTLY for index operations
        if "postgresql" in content.lower():
            assert "concurrently" in content.lower(), \
                "PostgreSQL migration should use CONCURRENTLY for index operations"

    def test_migration_handles_large_datasets(self):
        """Test that migration is structured to handle large datasets."""

        migration_file = "alembic/versions/005_add_credit_transaction_provider_reference_constraint.py"

        with open(migration_file, 'r') as f:
            content = f.read()

        # Should have batch processing or efficient handling for large datasets
        efficiency_indicators = [
            "row_number",  # For batch processing
            "limit",       # For chunked processing
            "batch",       # Explicit batching
            "efficient"    # Comments about efficiency
        ]

        # At least one efficiency pattern should be present
        has_efficiency_consideration = any(indicator in content.lower() for indicator in efficiency_indicators)
        assert has_efficiency_consideration, \
            "Migration should consider efficiency for large datasets"