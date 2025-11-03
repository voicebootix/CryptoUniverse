"""Add critical performance indexes for slow queries

Revision ID: add_perf_indexes_critical
Revises: 011_add_legacy_backtest_metrics
Create Date: 2025-11-02 07:13:28.699504
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_perf_indexes_critical'
down_revision = '011_add_legacy_backtest_metrics'
branch_labels = None
depends_on = None


def upgrade():
    """Create critical performance indexes used by high-traffic queries.

    Note: idx_users_email_active_perf duplicates existing idx_user_email_active
    from User model, and idx_users_id_status_perf is ineffective (id is PK).
    Only creating indexes for exchange_accounts which are actually used.
    """
    # Remove redundant user table indexes - they duplicate model definitions
    # or are ineffective (id+status where id is PK)

    op.create_index(
        "idx_exchange_accounts_user_exchange_status_perf",
        "exchange_accounts",
        ["user_id", "exchange_name", "status"],
        unique=False,
        if_not_exists=True,
    )

    op.create_index(
        "idx_exchange_accounts_user_status_perf",
        "exchange_accounts",
        ["user_id", "status"],
        unique=False,
        if_not_exists=True,
    )


def downgrade():
    """Drop performance indexes if they exist."""
    # Only drop the indexes we created in upgrade()
    op.drop_index(
        "idx_exchange_accounts_user_exchange_status_perf",
        table_name="exchange_accounts",
        if_exists=True,
    )
    op.drop_index(
        "idx_exchange_accounts_user_status_perf",
        table_name="exchange_accounts",
        if_exists=True,
    )
