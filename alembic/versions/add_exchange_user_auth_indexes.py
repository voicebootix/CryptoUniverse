"""Add optimized indexes for exchange accounts and users.

Revision ID: add_exchange_user_auth_indexes
Revises: add_real_market_data
Create Date: 2025-01-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_exchange_user_auth_indexes"
down_revision = "add_real_market_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply performance-focused indexes."""
    op.create_index(
        "idx_exchange_accounts_status_trading_user",
        "exchange_accounts",
        ["status", "trading_enabled", "user_id"],
    )
    op.create_index(
        "idx_users_auth_lookup",
        "users",
        ["email", "status", "is_active", "is_verified"],
    )


def downgrade() -> None:
    """Revert index additions."""
    op.drop_index(
        "idx_users_auth_lookup",
        table_name="users",
    )
    op.drop_index(
        "idx_exchange_accounts_status_trading_user",
        table_name="exchange_accounts",
    )
