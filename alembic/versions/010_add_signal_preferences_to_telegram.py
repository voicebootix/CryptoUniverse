"""Add signal_preferences column to user_telegram_connections

Revision ID: 010_add_signal_preferences_to_telegram
Revises: 009_signal_intelligence_tables
Create Date: 2025-03-14 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "010_add_signal_preferences_to_telegram"
down_revision = "009_signal_intelligence_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add signal_preferences JSON column to user_telegram_connections table."""

    with op.batch_alter_table("user_telegram_connections") as batch_op:
        batch_op.add_column(
            sa.Column(
                "signal_preferences",
                sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
                nullable=False,
                server_default="{}"
            )
        )

    # Remove server_default after column creation (standard pattern)
    with op.batch_alter_table("user_telegram_connections") as batch_op:
        batch_op.alter_column("signal_preferences", server_default=None)


def downgrade() -> None:
    """Remove signal_preferences column from user_telegram_connections table."""

    with op.batch_alter_table("user_telegram_connections") as batch_op:
        batch_op.drop_column("signal_preferences")
