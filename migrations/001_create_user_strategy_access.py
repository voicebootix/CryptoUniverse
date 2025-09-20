#!/usr/bin/env python3
"""
Migration: Create user_strategy_access table
Enterprise-grade strategy ownership consolidation
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_user_strategy_access'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Create user_strategy_access table for unified strategy ownership"""

    # Create strategy access types enum
    strategy_access_type = postgresql.ENUM(
        'welcome', 'purchased', 'trial', 'admin_grant', 'enterprise_license',
        name='strategyaccesstype',
        create_type=False
    )
    strategy_access_type.create(op.get_bind(), checkfirst=True)

    # Create strategy types enum
    strategy_type = postgresql.ENUM(
        'ai_strategy', 'community_strategy', 'enterprise_strategy',
        name='strategytype',
        create_type=False
    )
    strategy_type.create(op.get_bind(), checkfirst=True)

    # Create user_strategy_access table
    op.create_table(
        'user_strategy_access',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('strategy_id', sa.String(255), nullable=False, comment='Can reference AI catalog or community strategy UUID'),
        sa.Column('strategy_type', strategy_type, nullable=False),
        sa.Column('access_type', strategy_access_type, nullable=False),
        sa.Column('subscription_type', sa.String(50), nullable=False, default='monthly', comment='monthly, permanent, trial'),
        sa.Column('credits_paid', sa.Integer, nullable=False, default=0, comment='Credits paid for access'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, comment='NULL for permanent access'),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True, comment='Strategy-specific configuration and settings'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),

        # Indexes for performance
        sa.Index('idx_user_strategy_access_user_id', 'user_id'),
        sa.Index('idx_user_strategy_access_strategy_id', 'strategy_id'),
        sa.Index('idx_user_strategy_access_active', 'user_id', 'is_active'),
        sa.Index('idx_user_strategy_access_expires', 'expires_at'),

        # Unique constraint to prevent duplicate access records
        sa.UniqueConstraint('user_id', 'strategy_id', name='uq_user_strategy_access'),

        comment='Enterprise unified strategy access control'
    )

    # Create updated_at trigger
    op.execute('''
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';

        CREATE TRIGGER update_user_strategy_access_updated_at
            BEFORE UPDATE ON user_strategy_access
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    ''')

def downgrade():
    """Drop user_strategy_access table and related objects"""
    op.drop_table('user_strategy_access')

    # Drop trigger and function
    op.execute('DROP TRIGGER IF EXISTS update_user_strategy_access_updated_at ON user_strategy_access')
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column()')

    # Drop enums
    sa.Enum(name='strategyaccesstype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='strategytype').drop(op.get_bind(), checkfirst=True)