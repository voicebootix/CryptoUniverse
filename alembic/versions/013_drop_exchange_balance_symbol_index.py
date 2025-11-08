"""Drop redundant exchange balance symbol index."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "013_drop_exchange_balance_symbol_index"
down_revision = "012_add_nonce_coordination_and_indexes"
branch_labels = None
depends_on = None


INDEX_NAME = "idx_balance_account_symbol"
TABLE_NAME = "exchange_balances"


def upgrade() -> None:
    """Drop the redundant composite index if it exists."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = {index["name"] for index in inspector.get_indexes(TABLE_NAME)}

    if INDEX_NAME in existing_indexes:
        op.drop_index(INDEX_NAME, table_name=TABLE_NAME)


def downgrade() -> None:
    """Recreate the dropped index."""
    op.create_index(INDEX_NAME, TABLE_NAME, ["account_id", "symbol"])
