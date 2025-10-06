"""Create signal intelligence tables."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "009_signal_intelligence_tables"
down_revision = "008_add_credit_account_lifecycle_columns"
branch_labels = None
depends_on = None


CHANNELS_TABLE = "signal_channels"
SUBSCRIPTIONS_TABLE = "signal_subscriptions"
EVENTS_TABLE = "signal_events"
DELIVERIES_TABLE = "signal_delivery_logs"


def upgrade() -> None:
    """Create core signal intelligence tables."""
    # Ensure legacy tables are empty before proceeding so we don't destroy data accidentally.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    legacy_tables = (
        "signal_dispatch_logs",
        "signal_group_subscriptions",
        "signal_groups",
    )

    for legacy in legacy_tables:
        if legacy in inspector.get_table_names():
            count = bind.execute(sa.text(f"SELECT COUNT(*) FROM {legacy}")).scalar()  # type: ignore[arg-type]
            if count:
                raise RuntimeError(
                    "Legacy signal table contains rows. Aborting migration to avoid data loss: "
                    f"{legacy} has {count} rows."
                )

    op.create_table(
        CHANNELS_TABLE,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("risk_profile", sa.String(length=40), nullable=False, server_default="balanced"),
        sa.Column("cadence_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("max_daily_events", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("autopilot_supported", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("min_credit_balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "required_strategy_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "delivery_channels",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "pricing",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "configuration",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_signal_channels_active", CHANNELS_TABLE, ["is_active"])
    op.create_index("idx_signal_channels_cadence", CHANNELS_TABLE, ["cadence_minutes"])
    op.create_index("ix_signal_channels_slug", CHANNELS_TABLE, ["slug"], unique=True)

    op.create_table(
        SUBSCRIPTIONS_TABLE,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("autopilot_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "preferred_channels",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("billing_plan", sa.String(length=50), nullable=False, server_default="standard"),
        sa.Column("reserved_credits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("webhook_url", sa.String(length=512), nullable=True),
        sa.Column("max_daily_events", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("cadence_override_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("last_event_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["channel_id"], [f"{CHANNELS_TABLE}.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("channel_id", "user_id", name="uq_signal_subscription"),
    )
    op.create_index(
        "idx_signal_subscription_user",
        SUBSCRIPTIONS_TABLE,
        ["user_id", "is_active"],
    )
    op.create_index(
        "idx_signal_subscription_channel",
        SUBSCRIPTIONS_TABLE,
        ["channel_id", "is_active"],
    )

    op.create_table(
        EVENTS_TABLE,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generated_for_subscription_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("triggered_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("risk_band", sa.String(length=32), nullable=False, server_default="balanced"),
        sa.Column(
            "opportunity_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "analysis_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["channel_id"], [f"{CHANNELS_TABLE}.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["generated_for_subscription_id"],
            [f"{SUBSCRIPTIONS_TABLE}.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "idx_signal_events_channel_time",
        EVENTS_TABLE,
        ["channel_id", "triggered_at"],
    )
    op.create_index(
        "idx_signal_events_subscription",
        EVENTS_TABLE,
        ["generated_for_subscription_id"],
    )

    op.create_table(
        DELIVERIES_TABLE,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("delivery_channel", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("credit_cost", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("credit_transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
        sa.Column("execution_reference", sa.String(length=255), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.ForeignKeyConstraint(["event_id"], [f"{EVENTS_TABLE}.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscription_id"], [f"{SUBSCRIPTIONS_TABLE}.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["credit_transaction_id"], ["credit_transactions.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "idx_signal_delivery_channel",
        DELIVERIES_TABLE,
        ["delivery_channel", "status"],
    )
    op.create_index("idx_signal_delivery_time", DELIVERIES_TABLE, ["delivered_at"])
    op.create_index("idx_signal_delivery_credit", DELIVERIES_TABLE, ["credit_transaction_id"])

    op.add_column(
        "user_telegram_connections",
        sa.Column(
            "signal_preferences",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    """Drop signal intelligence tables."""
    op.drop_column("user_telegram_connections", "signal_preferences")
    op.drop_index("idx_signal_delivery_credit", table_name=DELIVERIES_TABLE)
    op.drop_index("idx_signal_delivery_time", table_name=DELIVERIES_TABLE)
    op.drop_index("idx_signal_delivery_channel", table_name=DELIVERIES_TABLE)
    op.drop_table(DELIVERIES_TABLE)

    op.drop_index("idx_signal_events_subscription", table_name=EVENTS_TABLE)
    op.drop_index("idx_signal_events_channel_time", table_name=EVENTS_TABLE)
    op.drop_table(EVENTS_TABLE)

    op.drop_index("idx_signal_subscription_channel", table_name=SUBSCRIPTIONS_TABLE)
    op.drop_index("idx_signal_subscription_user", table_name=SUBSCRIPTIONS_TABLE)
    op.drop_table(SUBSCRIPTIONS_TABLE)

    op.drop_index("ix_signal_channels_slug", table_name=CHANNELS_TABLE)
    op.drop_index("idx_signal_channels_cadence", table_name=CHANNELS_TABLE)
    op.drop_index("idx_signal_channels_active", table_name=CHANNELS_TABLE)
    op.drop_table(CHANNELS_TABLE)
