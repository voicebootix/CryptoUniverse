"""Add critical performance indexes for slow queries

Revision ID: add_perf_indexes_critical
Revises: 011_add_legacy_backtest_metrics
Create Date: 2025-11-02 07:13:28.699504
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    """Create critical performance indexes used by high-traffic queries."""
    op.create_index(
        "idx_users_email_active_perf",
        "users",
        ["email", "is_active"],
        unique=False,
        if_not_exists=True,
    )

    op.create_index(
        "idx_users_id_status_perf",
        "users",
        ["id", "status"],
        unique=False,
        if_not_exists=True,
    )

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
    op.drop_index(
        "idx_users_email_active_perf",
        table_name="users",
        if_exists=True,
    )
    op.drop_index(
        "idx_users_id_status_perf",
        table_name="users",
        if_exists=True,
    )
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
