"""Create strategy_scanning_policies table"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.constants.opportunity import DEFAULT_STRATEGY_POLICY_PRESETS

# revision identifiers, used by Alembic.
revision = "add_strategy_scanning_policies_table"
<<<<<<< HEAD
down_revision = "011_add_legacy_backtest_metrics"
=======
down_revision = None
>>>>>>> origin/main
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "strategy_scanning_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("strategy_key", sa.String(length=128), nullable=False, unique=True),
        sa.Column("max_symbols", sa.Integer(), nullable=True),
        sa.Column("chunk_size", sa.Integer(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.sql.expression.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "idx_strategy_scanning_policies_enabled_priority",
        "strategy_scanning_policies",
        ["enabled", "priority"],
    )

    policies_table = sa.table(
        "strategy_scanning_policies",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("strategy_key", sa.String()),
        sa.column("max_symbols", sa.Integer()),
        sa.column("chunk_size", sa.Integer()),
        sa.column("priority", sa.Integer()),
        sa.column("enabled", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    now = datetime.now(timezone.utc)
    seed_rows = []
    for key, payload in DEFAULT_STRATEGY_POLICY_PRESETS.items():
        seed_rows.append(
            {
                "id": uuid.uuid4(),
                "strategy_key": key,
                "max_symbols": payload.get("max_symbols"),
                "chunk_size": payload.get("chunk_size"),
                "priority": payload.get("priority", 100),
                "enabled": bool(payload.get("enabled", True)),
                "created_at": now,
                "updated_at": now,
            }
        )

    if seed_rows:
        op.bulk_insert(policies_table, seed_rows)


def downgrade() -> None:
    op.drop_index("idx_strategy_scanning_policies_enabled_priority", table_name="strategy_scanning_policies")
    op.drop_table("strategy_scanning_policies")
