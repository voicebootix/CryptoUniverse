"""Add user_id column to trades table

Revision ID: 001_add_user_id_to_trades
Revises: 
Create Date: 2025-08-31 08:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '001_add_user_id_to_trades'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add user_id column to trades table if it doesn't exist."""
    
    # Check if trades table exists and if user_id column is missing
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Check if trades table exists
    if 'trades' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('trades')]
        
        # Add user_id column if it doesn't exist
        if 'user_id' not in columns:
            op.add_column('trades', sa.Column('user_id', UUID(as_uuid=True), nullable=True))
            
            # Create index on user_id
            op.create_index('ix_trades_user_id', 'trades', ['user_id'])
            
            # If users table exists, add foreign key constraint
            if 'users' in inspector.get_table_names():
                op.create_foreign_key(
                    'fk_trades_user_id', 'trades', 'users', 
                    ['user_id'], ['id'], ondelete='CASCADE'
                )
        
        # Add any other missing essential columns for trades
        if 'symbol' not in columns:
            op.add_column('trades', sa.Column('symbol', sa.String(20), nullable=True))
            op.create_index('ix_trades_symbol', 'trades', ['symbol'])
            
        if 'status' not in columns:
            op.add_column('trades', sa.Column('status', sa.String(20), nullable=True, default='pending'))
            op.create_index('ix_trades_status', 'trades', ['status'])
        
        if 'created_at' not in columns:
            op.add_column('trades', sa.Column('created_at', sa.DateTime, nullable=True, default=sa.func.now()))
            
        # Set user_id to nullable=False after adding the column
        if 'user_id' in [col['name'] for col in inspector.get_columns('trades')]:
            # First, update any NULL user_id values with a default UUID or admin user
            bind.execute(sa.text("""
                UPDATE trades 
                SET user_id = (SELECT id FROM users LIMIT 1) 
                WHERE user_id IS NULL AND EXISTS (SELECT 1 FROM users LIMIT 1)
            """))
            
            # Then make the column NOT NULL
            op.alter_column('trades', 'user_id', nullable=False)


def downgrade() -> None:
    """Remove user_id column from trades table."""
    
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    if 'trades' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('trades')]
        
        if 'user_id' in columns:
            # Drop foreign key constraint
            op.drop_constraint('fk_trades_user_id', 'trades', type_='foreignkey')
            
            # Drop index
            op.drop_index('ix_trades_user_id', 'trades')
            
            # Drop column
            op.drop_column('trades', 'user_id')
