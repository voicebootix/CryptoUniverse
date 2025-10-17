"""Rename metadata to meta in signal tables to avoid SQLAlchemy reserved word conflict

Revision ID: 010_rename_metadata_to_meta_in_signal_tables
Revises: 009_add_winning_trades_to_backtest_results
Create Date: 2025-10-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "010_rename_metadata_to_meta_in_signal_tables"
down_revision = "009_add_winning_trades_to_backtest_results"
branch_labels = None
depends_on = None


TABLES = [
    "signal_channels",
    "signal_subscriptions",
    "signal_events",
    "signal_delivery_logs",
]


def upgrade() -> None:
    """Rename metadata column to meta in all signal tables."""
    for table in TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column("metadata", new_column_name="meta")


def downgrade() -> None:
    """Rename meta column back to metadata in all signal tables."""
    for table in TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column("meta", new_column_name="metadata")
