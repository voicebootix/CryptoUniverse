"""Add Kraken nonce coordination table and performance indexes

Revision ID: 012_add_nonce_coordination_and_indexes
Revises: 011_add_legacy_backtest_metrics
Create Date: 2025-11-28 00:00:00.000000
"""

from __future__ import annotations

import datetime

from alembic import op
import sqlalchemy as sa


revision = "012_add_nonce_coordination_and_indexes"
down_revision = "011_add_legacy_backtest_metrics"
branch_labels = None
depends_on = None


KRAKEN_TABLE = "kraken_nonce_counters"


def _create_nonce_table() -> None:
    op.create_table(
        KRAKEN_TABLE,
        sa.Column("key_hash", sa.String(length=64), primary_key=True),
        sa.Column("last_nonce", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    initial_nonce = int(datetime.datetime.utcnow().timestamp() * 1000)
    op.execute(
        sa.text(
            f"INSERT INTO {KRAKEN_TABLE} (key_hash, last_nonce) VALUES (:key_hash, :last_nonce)"
        ),
        {"key_hash": "global", "last_nonce": initial_nonce},
    )


def _drop_nonce_table() -> None:
    op.drop_table(KRAKEN_TABLE)


def upgrade() -> None:
    """Add nonce coordination table and supporting indexes."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if KRAKEN_TABLE not in inspector.get_table_names():
        _create_nonce_table()

    op.create_index(
        "ix_users_tenant_email",
        "users",
        ["tenant_id", "email"],
        unique=False,
    )
    op.create_index(
        "ix_exchange_accounts_user_default",
        "exchange_accounts",
        ["user_id", "is_default", "status"],
        unique=False,
    )
    op.create_index(
        "ix_exchange_balances_account_active",
        "exchange_balances",
        ["account_id", "is_active", "symbol"],
        unique=False,
    )
    op.create_index(
        "ix_positions_portfolio_symbol_status",
        "positions",
        ["portfolio_id", "status", "symbol"],
        unique=False,
    )
    op.create_index(
        "ix_signal_delivery_subscription_status",
        "signal_delivery_logs",
        ["subscription_id", "status", "delivered_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove nonce coordination table and supporting indexes."""
    op.drop_index("ix_signal_delivery_subscription_status", table_name="signal_delivery_logs")
    op.drop_index("ix_positions_portfolio_symbol_status", table_name="positions")
    op.drop_index("ix_exchange_balances_account_active", table_name="exchange_balances")
    op.drop_index("ix_exchange_accounts_user_default", table_name="exchange_accounts")
    op.drop_index("ix_users_tenant_email", table_name="users")
    _drop_nonce_table()
