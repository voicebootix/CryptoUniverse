"""Add lifetime credit tracking columns

Revision ID: 008_add_credit_account_lifecycle_columns
Revises: 007_rename_market_data_to_legacy
Create Date: 2025-02-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


revision = "008_add_credit_account_lifecycle_columns"
down_revision = "007_rename_market_data_to_legacy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add lifetime tracking columns and backfill existing data."""

    with op.batch_alter_table("credit_accounts") as batch_op:
        batch_op.add_column(sa.Column("total_purchased_credits", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("total_used_credits", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("last_usage_at", sa.DateTime(), nullable=True))

    bind = op.get_bind()

    # Align new counters with existing balances
    bind.execute(
        text(
            """
            UPDATE credit_accounts
            SET total_purchased_credits = COALESCE(total_credits, 0),
                total_used_credits = COALESCE(used_credits, 0)
            """
        )
    )

    # Ensure profit potential limits remain consistent with new totals
    bind.execute(
        text(
            """
            UPDATE credit_accounts
            SET total_profit_potential_usd = COALESCE(total_credits, 0) * 4,
                current_profit_limit_usd = GREATEST(COALESCE(total_credits, 0), COALESCE(available_credits, 0)) * 4
            """
        )
    )

    with op.batch_alter_table("credit_accounts") as batch_op:
        batch_op.alter_column("total_purchased_credits", server_default=None)
        batch_op.alter_column("total_used_credits", server_default=None)


def downgrade() -> None:
    """Remove lifetime tracking columns."""

    with op.batch_alter_table("credit_accounts") as batch_op:
        batch_op.drop_column("last_usage_at")
        batch_op.drop_column("total_used_credits")
        batch_op.drop_column("total_purchased_credits")
