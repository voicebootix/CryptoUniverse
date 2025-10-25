"""Add legacy backtest metrics columns (annual_return, volatility, beta, alpha, avg_trade_return)

Revision ID: 011_add_legacy_backtest_metrics
Revises: 010_add_signal_preferences_to_telegram
Create Date: 2025-10-25 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "011_add_legacy_backtest_metrics"
down_revision = "010_add_signal_preferences_to_telegram"
branch_labels = None
depends_on = None


BACKTEST_TABLE = "backtest_results"
COLUMNS = [
    ("annual_return", sa.Numeric(8, 4)),
    ("volatility", sa.Numeric(8, 4)),
    ("beta", sa.Numeric(6, 4)),
    ("alpha", sa.Numeric(8, 4)),
    ("avg_trade_return", sa.Numeric(8, 4)),
]


def upgrade() -> None:
    """Add missing legacy backtest metrics columns if they are absent."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns(BACKTEST_TABLE)}

    # Add each column if it doesn't exist
    for column_name, column_type in COLUMNS:
        if column_name not in existing_columns:
            with op.batch_alter_table(BACKTEST_TABLE) as batch_op:
                batch_op.add_column(
                    sa.Column(column_name, column_type, nullable=True)
                )
            print(f"✅ Added column: {column_name}")
        else:
            print(f"⏭️  Column already exists: {column_name}")


def downgrade() -> None:
    """Drop the legacy backtest metrics columns if present."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns(BACKTEST_TABLE)}

    # Drop each column if it exists
    for column_name, _ in COLUMNS:
        if column_name in existing_columns:
            with op.batch_alter_table(BACKTEST_TABLE) as batch_op:
                batch_op.drop_column(column_name)
            print(f"✅ Dropped column: {column_name}")
        else:
            print(f"⏭️  Column doesn't exist: {column_name}")
