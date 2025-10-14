"""Ensure winning_trades column exists on backtest_results

Revision ID: 009_add_winning_trades_to_backtest_results
Revises: 008_add_credit_account_lifecycle_columns
Create Date: 2025-09-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "009_add_winning_trades_to_backtest_results"
down_revision = "008_add_credit_account_lifecycle_columns"
branch_labels = None
depends_on = None


BACKTEST_TABLE = "backtest_results"
COLUMN_NAME = "winning_trades"


def upgrade() -> None:
    """Add the missing winning_trades column if it is absent."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns(BACKTEST_TABLE)}

    if COLUMN_NAME not in existing_columns:
        with op.batch_alter_table(BACKTEST_TABLE) as batch_op:
            batch_op.add_column(
                sa.Column(COLUMN_NAME, sa.Integer(), nullable=False, server_default="0")
            )

        with op.batch_alter_table(BACKTEST_TABLE) as batch_op:
            batch_op.alter_column(COLUMN_NAME, server_default=None)


def downgrade() -> None:
    """Drop the winning_trades column if present."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns(BACKTEST_TABLE)}

    if COLUMN_NAME in existing_columns:
        with op.batch_alter_table(BACKTEST_TABLE) as batch_op:
            batch_op.drop_column(COLUMN_NAME)
