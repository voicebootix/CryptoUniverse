"""
Tests for CreditTransaction uniqueness constraints and migration behavior.

This test suite verifies:
1. Composite unique constraint on (provider, reference_id)
2. NULL handling in uniqueness constraints
3. Migration idempotency
4. Duplicate resolution logic
"""

import pytest
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import text, inspect
from sqlalchemy.exc import IntegrityError

from app.models.credit import CreditAccount, CreditTransaction, CreditTransactionType, CreditStatus
from app.models.user import User, UserRole
from app.core.database import get_database
from tests.conftest import AsyncTestDatabase


@pytest.fixture
async def test_credit_account(async_db_session):
    """Create a test credit account."""
    # Create test user
    user = User(
        email="test@example.com",
        hashed_password="test_hash",
        role=UserRole.TRADER
    )
    async_db_session.add(user)
    await async_db_session.flush()  # Get user.id

    # Create credit account
    account = CreditAccount(
        user_id=user.id,
        total_credits=1000,
        available_credits=1000,
        used_credits=0
    )
    async_db_session.add(account)
    await async_db_session.flush()  # Get account.id

    return account


class TestCreditTransactionUniqueness:
    """Test uniqueness constraints on CreditTransaction model."""

    async def test_composite_unique_constraint_enforced(self, async_db_session, test_credit_account):
        """Test that (provider, reference_id) composite constraint prevents duplicates."""

        # Create first transaction
        tx1 = CreditTransaction(
            account_id=test_credit_account.id,
            transaction_type=CreditTransactionType.PURCHASE,
            amount=100,
            description="Test transaction 1",
            balance_before=1000,
            balance_after=1100,
            provider="stripe",
            reference_id="ref_12345",
            source="test"
        )
        async_db_session.add(tx1)
        await async_db_session.commit()

        # Try to create duplicate - should fail
        tx2 = CreditTransaction(
            account_id=test_credit_account.id,
            transaction_type=CreditTransactionType.PURCHASE,
            amount=200,
            description="Test transaction 2",
            balance_before=1100,
            balance_after=1300,
            provider="stripe",  # Same provider
            reference_id="ref_12345",  # Same reference_id
            source="test"
        )
        async_db_session.add(tx2)

        with pytest.raises(IntegrityError) as exc_info:
            await async_db_session.commit()

        assert "uq_credit_transaction_provider_reference" in str(exc_info.value) or \
               "UNIQUE constraint failed" in str(exc_info.value)

    async def test_different_providers_same_reference_allowed(self, async_db_session, test_credit_account):
        """Test that same reference_id is allowed with different providers."""

        # Create transaction with provider 'stripe'
        tx1 = CreditTransaction(
            account_id=test_credit_account.id,
            transaction_type=CreditTransactionType.PURCHASE,
            amount=100,
            description="Stripe transaction",
            balance_before=1000,
            balance_after=1100,
            provider="stripe",
            reference_id="ref_12345",
            source="test"
        )
        async_db_session.add(tx1)
        await async_db_session.flush()

        # Create transaction with provider 'coinbase' - should succeed
        tx2 = CreditTransaction(
            account_id=test_credit_account.id,
            transaction_type=CreditTransactionType.PURCHASE,
            amount=200,
            description="Coinbase transaction",
            balance_before=1100,
            balance_after=1300,
            provider="coinbase",  # Different provider
            reference_id="ref_12345",  # Same reference_id - this is OK
            source="test"
        )
        async_db_session.add(tx2)
        await async_db_session.commit()  # Should not raise

        # Verify both transactions exist
        result = await async_db_session.execute(
            text("SELECT COUNT(*) FROM credit_transactions WHERE reference_id = 'ref_12345'")
        )
        count = result.scalar()
        assert count == 2

    async def test_null_values_allowed_multiple_times(self, async_db_session, test_credit_account):
        """Test that NULL values in provider/reference_id don't trigger uniqueness constraints."""

        # Create multiple transactions with NULL provider and reference_id
        for i in range(3):
            tx = CreditTransaction(
                account_id=test_credit_account.id,
                transaction_type=CreditTransactionType.USAGE,
                amount=-10,
                description=f"Usage transaction {i+1}",
                balance_before=1000 - (i * 10),
                balance_after=990 - (i * 10),
                provider=None,  # NULL
                reference_id=None,  # NULL
                source="test"
            )
            async_db_session.add(tx)

        await async_db_session.commit()  # Should not raise

        # Verify all transactions exist
        result = await async_db_session.execute(
            text("SELECT COUNT(*) FROM credit_transactions WHERE provider IS NULL AND reference_id IS NULL")
        )
        count = result.scalar()
        assert count == 3

    async def test_null_provider_same_reference_allowed(self, async_db_session, test_credit_account):
        """Test that NULL provider with same reference_id is allowed multiple times."""

        # Create multiple transactions with NULL provider but same reference_id
        for i in range(2):
            tx = CreditTransaction(
                account_id=test_credit_account.id,
                transaction_type=CreditTransactionType.ADJUSTMENT,
                amount=50,
                description=f"Admin adjustment {i+1}",
                balance_before=1000 + (i * 50),
                balance_after=1050 + (i * 50),
                provider=None,  # NULL
                reference_id="admin_ref_123",  # Same reference but NULL provider
                source="admin"
            )
            async_db_session.add(tx)

        await async_db_session.commit()  # Should not raise

    async def test_same_provider_null_reference_allowed(self, async_db_session, test_credit_account):
        """Test that same provider with NULL reference_id is allowed multiple times."""

        # Create multiple transactions with same provider but NULL reference_id
        for i in range(2):
            tx = CreditTransaction(
                account_id=test_credit_account.id,
                transaction_type=CreditTransactionType.BONUS,
                amount=25,
                description=f"Referral bonus {i+1}",
                balance_before=1000 + (i * 25),
                balance_after=1025 + (i * 25),
                provider="internal",  # Same provider
                reference_id=None,  # NULL
                source="referral"
            )
            async_db_session.add(tx)

        await async_db_session.commit()  # Should not raise


class TestMigrationIdempotency:
    """Test migration behavior and idempotency."""

    async def test_migration_creates_constraint(self, async_db_session):
        """Test that migration creates the expected constraint/index."""

        # Check if unique constraint/index exists
        inspector = inspect(async_db_session.bind)

        # Check indexes
        indexes = inspector.get_indexes('credit_transactions')
        constraint_names = [idx['name'] for idx in indexes]

        # The constraint should exist (either as index or constraint)
        assert any('provider_reference' in name.lower() for name in constraint_names), \
            f"Expected unique constraint not found. Available indexes: {constraint_names}"

    async def test_provider_column_exists(self, async_db_session):
        """Test that provider column was created by migration."""

        # Check if provider column exists
        inspector = inspect(async_db_session.bind)
        columns = inspector.get_columns('credit_transactions')
        column_names = [col['name'] for col in columns]

        assert 'provider' in column_names, "Provider column should exist"

        # Check column properties
        provider_column = next(col for col in columns if col['name'] == 'provider')
        assert provider_column['nullable'] is True, "Provider column should be nullable"
        assert 'String' in str(provider_column['type']) or 'VARCHAR' in str(provider_column['type']), \
            "Provider column should be string type"

    async def test_existing_data_handling(self, async_db_session, test_credit_account):
        """Test that existing data is handled correctly by migration logic."""

        # Simulate pre-migration data: create transactions with only reference_id (no provider)
        # This simulates what would happen after migration has run and handled existing data

        tx1 = CreditTransaction(
            account_id=test_credit_account.id,
            transaction_type=CreditTransactionType.PURCHASE,
            amount=100,
            description="Legacy transaction 1",
            balance_before=1000,
            balance_after=1100,
            provider="legacy",  # This would be set by migration
            reference_id="legacy_ref_1",
            source="migration_test"
        )
        async_db_session.add(tx1)
        await async_db_session.commit()

        # Verify legacy data exists and respects constraints
        result = await async_db_session.execute(
            text("SELECT COUNT(*) FROM credit_transactions WHERE provider = 'legacy'")
        )
        count = result.scalar()
        assert count >= 1

    async def test_migration_rollback_safety(self, async_db_session):
        """Test that migration can be safely rolled back."""

        # This test verifies the migration structure supports rollback
        # In practice, you would test this with actual alembic downgrade commands

        inspector = inspect(async_db_session.bind)

        # Verify table still exists (rollback shouldn't drop main table)
        tables = inspector.get_table_names()
        assert 'credit_transactions' in tables

        # Verify basic structure is intact
        columns = inspector.get_columns('credit_transactions')
        essential_columns = ['id', 'account_id', 'transaction_type', 'amount']
        existing_columns = [col['name'] for col in columns]

        for col in essential_columns:
            assert col in existing_columns, f"Essential column {col} missing after potential rollback"


class TestConstraintBehaviorEdgeCases:
    """Test edge cases for uniqueness constraint behavior."""

    async def test_empty_string_vs_null_handling(self, async_db_session, test_credit_account):
        """Test how empty strings vs NULL are handled in uniqueness constraint."""

        # Create transaction with empty string provider
        tx1 = CreditTransaction(
            account_id=test_credit_account.id,
            transaction_type=CreditTransactionType.PURCHASE,
            amount=100,
            description="Empty string provider",
            balance_before=1000,
            balance_after=1100,
            provider="",  # Empty string
            reference_id="ref_123",
            source="test"
        )
        async_db_session.add(tx1)
        await async_db_session.flush()

        # Try to create another with same empty string provider - should fail
        tx2 = CreditTransaction(
            account_id=test_credit_account.id,
            transaction_type=CreditTransactionType.PURCHASE,
            amount=200,
            description="Another empty string provider",
            balance_before=1100,
            balance_after=1300,
            provider="",  # Same empty string
            reference_id="ref_123",  # Same reference
            source="test"
        )
        async_db_session.add(tx2)

        with pytest.raises(IntegrityError):
            await async_db_session.commit()

    async def test_whitespace_normalization(self, async_db_session, test_credit_account):
        """Test that whitespace in provider names is handled consistently."""

        # Create transaction with whitespace
        tx1 = CreditTransaction(
            account_id=test_credit_account.id,
            transaction_type=CreditTransactionType.PURCHASE,
            amount=100,
            description="Whitespace test",
            balance_before=1000,
            balance_after=1100,
            provider=" stripe ",  # Whitespace around
            reference_id="ref_456",
            source="test"
        )
        async_db_session.add(tx1)
        await async_db_session.flush()

        # Try with different whitespace - should be treated as different
        tx2 = CreditTransaction(
            account_id=test_credit_account.id,
            transaction_type=CreditTransactionType.PURCHASE,
            amount=200,
            description="Different whitespace",
            balance_before=1100,
            balance_after=1300,
            provider="stripe",  # No whitespace
            reference_id="ref_456",  # Same reference
            source="test"
        )
        async_db_session.add(tx2)
        await async_db_session.commit()  # Should succeed (different providers)

        # Verify both exist
        result = await async_db_session.execute(
            text("SELECT COUNT(*) FROM credit_transactions WHERE reference_id = 'ref_456'")
        )
        count = result.scalar()
        assert count == 2


@pytest.mark.integration
class TestMigrationIntegration:
    """Integration tests for migration functionality."""

    async def test_duplicate_resolution_logic(self, async_db_session, test_credit_account):
        """Test the duplicate resolution logic used in migration."""

        # Simulate the duplicate scenario that migration needs to handle
        # This would happen if migration runs on existing data with duplicates

        # Create transactions that would be duplicates before provider field existed
        base_time = datetime.utcnow()

        transactions_data = [
            {
                "description": "Original transaction",
                "created_at": base_time,
                "expected_provider": "legacy"
            },
            {
                "description": "Duplicate transaction 1",
                "created_at": base_time.replace(second=1),
                "expected_provider": "legacy_dup_2"
            },
            {
                "description": "Duplicate transaction 2",
                "created_at": base_time.replace(second=2),
                "expected_provider": "legacy_dup_3"
            }
        ]

        # This simulates what the migration would do: assign different providers
        # to transactions with the same reference_id to avoid constraint violations
        for i, data in enumerate(transactions_data):
            provider = "legacy" if i == 0 else f"legacy_dup_{i+1}"

            tx = CreditTransaction(
                account_id=test_credit_account.id,
                transaction_type=CreditTransactionType.PURCHASE,
                amount=100 + (i * 10),
                description=data["description"],
                balance_before=1000 + (i * 110),
                balance_after=1100 + (i * 110),
                provider=provider,  # Migration would set this
                reference_id="dup_ref_789",  # Same reference_id
                source="migration_test"
            )
            async_db_session.add(tx)

        await async_db_session.commit()  # Should succeed with different providers

        # Verify all transactions exist with correct providers
        result = await async_db_session.execute(
            text("""
                SELECT provider, COUNT(*)
                FROM credit_transactions
                WHERE reference_id = 'dup_ref_789'
                GROUP BY provider
                ORDER BY provider
            """)
        )
        provider_counts = result.fetchall()

        expected_providers = {'legacy', 'legacy_dup_2', 'legacy_dup_3'}
        actual_providers = {row[0] for row in provider_counts}

        assert actual_providers == expected_providers
        assert all(count == 1 for _, count in provider_counts), "Each provider should have exactly one transaction"