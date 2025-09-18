"""Add simulation mode to users table

Revision ID: add_simulation_mode_to_users
Revises: add_real_market_data
Create Date: 2025-01-18 12:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = 'add_simulation_mode_to_users'
down_revision = 'add_real_market_data'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add simulation mode columns to users table."""

    # Add simulation_mode column (default to True for safety)
    op.add_column('users',
        sa.Column('simulation_mode', sa.Boolean(), nullable=False, server_default='true')
    )

    # Add simulation_balance column with proper precision
    op.add_column('users',
        sa.Column('simulation_balance', sa.Numeric(precision=12, scale=2), nullable=False, server_default=sa.text('10000.00'))
    )

    # Add last_simulation_reset column
    op.add_column('users',
        sa.Column('last_simulation_reset', sa.DateTime(timezone=True), nullable=True)
    )

    # Create index for quick filtering
    op.create_index('idx_users_simulation_mode', 'users', ['simulation_mode'])

    # Set existing admin users to live mode if they have exchange accounts
    connection = op.get_bind()

    # Update users with active exchange accounts to live mode
    connection.execute(text("""
        UPDATE users
        SET simulation_mode = false
        WHERE id IN (
            SELECT DISTINCT user_id
            FROM exchange_accounts
            WHERE status = 'active'
            AND trading_enabled = true
        )
    """))

    print("✅ Added simulation_mode to users table")
    print("   - New users default to simulation mode for safety")
    print("   - Users with active exchanges set to live mode")


def downgrade() -> None:
    """Remove simulation mode columns from users table."""

    op.drop_index('idx_users_simulation_mode', 'users')
    op.drop_column('users', 'last_simulation_reset')
    op.drop_column('users', 'simulation_balance')
    op.drop_column('users', 'simulation_mode')