<<<<<<< HEAD
"""Add simulation mode to users with proper precision

Revision ID: add_simulation_mode_to_users
Revises: add_real_market_data
Create Date: 2025-01-18 12:10:00.000000
=======
"""Add simulation mode to users table

Revision ID: add_simulation_mode
Revises: add_real_market_data
Create Date: 2024-01-18 12:00:00.000000
>>>>>>> 74798ab3bb0b22f57424b2a99d41a082a3880f44

"""
from alembic import op
import sqlalchemy as sa
<<<<<<< HEAD

# revision identifiers, used by Alembic.
revision = 'add_simulation_mode_to_users'
=======
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = 'add_simulation_mode'
>>>>>>> 74798ab3bb0b22f57424b2a99d41a082a3880f44
down_revision = 'add_real_market_data'
branch_labels = None
depends_on = None


<<<<<<< HEAD
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
=======
def upgrade() -> None:
    """Add simulation mode columns to users table."""

    # Add simulation_mode column (default to True for safety)
    op.add_column('users',
        sa.Column('simulation_mode', sa.Boolean(), nullable=False, server_default='true')
    )

    # Add simulation_balance column (default 10000 USD)
    op.add_column('users',
        sa.Column('simulation_balance', sa.Integer(), nullable=False, server_default='10000')
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
>>>>>>> 74798ab3bb0b22f57424b2a99d41a082a3880f44
    op.drop_column('users', 'last_simulation_reset')
    op.drop_column('users', 'simulation_balance')
    op.drop_column('users', 'simulation_mode')