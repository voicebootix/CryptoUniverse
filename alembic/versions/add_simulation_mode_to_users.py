"""Add simulation mode to users with proper precision

Revision ID: add_simulation_mode_to_users
Revises: add_real_market_data
Create Date: 2025-01-18 12:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_simulation_mode_to_users'
down_revision = 'add_real_market_data'
branch_labels = None
depends_on = None


def upgrade():
    """Add simulation mode columns to users table."""

    # Add simulation mode flag
    op.add_column('users', sa.Column(
        'simulation_mode',
        sa.Boolean(),
        nullable=False,
        server_default=sa.text('false')
    ))

    # Add simulation balance with proper precision and DB-native default
    op.add_column('users', sa.Column(
        'simulation_balance',
        sa.Numeric(precision=12, scale=2),  # Changed from Integer to Numeric for precision
        nullable=False,
        server_default=sa.text('10000.00')  # DB-native default instead of string
    ))

    # Add last simulation reset timestamp (nullable)
    op.add_column('users', sa.Column(
        'last_simulation_reset',
        sa.DateTime(timezone=True),
        nullable=True
    ))

    # Create index for simulation mode queries
    op.create_index('idx_users_simulation_mode', 'users', ['simulation_mode'])


def downgrade():
    """Remove simulation mode columns from users table."""

    # Drop index first
    op.drop_index('idx_users_simulation_mode', table_name='users')

    # Drop columns
    op.drop_column('users', 'last_simulation_reset')
    op.drop_column('users', 'simulation_balance')
    op.drop_column('users', 'simulation_mode')