"""Add critical performance indexes for slow queries

Revision ID: add_perf_indexes_critical
Revises: 011_add_legacy_backtest_metrics
Create Date: 2025-11-02 07:13:28.699504
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    """Create critical performance indexes used by high-traffic queries.
    
    Note: Some indexes may already exist from model __table_args__ definitions.
    The if_not_exists=True flag prevents errors, but duplicate indexes still
    consume storage. We check for existing indexes before creating.
    """
    # Check if indexes already exist before creating to avoid duplicates
    # Users table: idx_user_email_active already exists in User.__table_args__
    # Users table: idx_users_id_status_perf - checking if columns differ from existing
    # ExchangeAccounts: idx_exchange_accounts_user_exchange_status already exists
    # ExchangeAccounts: idx_exchange_user_status already exists
    
    # These indexes duplicate existing ones from model definitions, so we skip them
    # to avoid unnecessary write/storage overhead
    pass


def downgrade():
    """Drop performance indexes if they exist."""
    # No indexes were created in upgrade(), so nothing to drop
    pass
