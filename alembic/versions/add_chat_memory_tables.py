"""Add chat memory tables for persistent conversation storage

Revision ID: add_chat_memory_001
Revises: previous_revision
Create Date: 2024-01-XX XX:XX:XX.XXXXXX

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'add_chat_memory_001'
down_revision = '004_targeted_performance_fix'
branch_labels = None
depends_on = None


def upgrade():
    """Create chat memory tables."""
    
    # Chat Sessions table
    op.create_table('chat_sessions',
        sa.Column('session_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_activity', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, onupdate=sa.func.now()),
        sa.Column('context', postgresql.JSONB, nullable=True),
        sa.Column('portfolio_state', postgresql.JSONB, nullable=True),
        sa.Column('active_strategies', postgresql.JSONB, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('session_type', sa.String, nullable=False, server_default=sa.text("'general'")),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('session_id')
    )
    
    # Create indexes for chat_sessions
    op.create_index('ix_chat_sessions_user_active', 'chat_sessions', ['user_id', 'is_active'])
    op.create_index('ix_chat_sessions_last_activity', 'chat_sessions', ['last_activity'])
    op.create_index('ix_chat_sessions_user_id', 'chat_sessions', ['user_id'])
    
    # Chat Messages table
    op.create_table('chat_messages',
        sa.Column('message_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('message_type', sa.String, nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('intent', sa.String, nullable=True),
        sa.Column('confidence', sa.Float, nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('processed', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('model_used', sa.String, nullable=True),
        sa.Column('processing_time_ms', sa.Float, nullable=True),
        sa.Column('tokens_used', sa.Float, nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.session_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('message_id')
    )
    
    # Create indexes for chat_messages
    op.create_index('ix_chat_messages_session_timestamp', 'chat_messages', ['session_id', 'timestamp'])
    op.create_index('ix_chat_messages_user_timestamp', 'chat_messages', ['user_id', 'timestamp'])
    op.create_index('ix_chat_messages_intent', 'chat_messages', ['intent'])
    op.create_index('ix_chat_messages_type', 'chat_messages', ['message_type'])
    op.create_index('ix_chat_messages_session_id', 'chat_messages', ['session_id'])
    op.create_index('ix_chat_messages_user_id', 'chat_messages', ['user_id'])
    
    # Chat Session Summaries table
    op.create_table('chat_session_summaries',
        sa.Column('summary_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('summary_text', sa.Text, nullable=False),
        sa.Column('messages_summarized', sa.Integer, nullable=False),
        sa.Column('summary_type', sa.String, nullable=False, server_default=sa.text("'conversation'")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('start_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('key_decisions', postgresql.JSONB, nullable=True),
        sa.Column('trade_actions', postgresql.JSONB, nullable=True),
        sa.Column('portfolio_changes', postgresql.JSONB, nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.session_id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('summary_id')
    )
    
    # Create indexes for chat_session_summaries
    op.create_index('ix_chat_summaries_session_created', 'chat_session_summaries', ['session_id', 'created_at'])
    op.create_index('ix_chat_summaries_user_created', 'chat_session_summaries', ['user_id', 'created_at'])
    op.create_index('ix_chat_session_summaries_session_id', 'chat_session_summaries', ['session_id'])
    op.create_index('ix_chat_session_summaries_user_id', 'chat_session_summaries', ['user_id'])


def downgrade():
    """Drop chat memory tables."""
    
    # Drop indexes first
    op.drop_index('ix_chat_session_summaries_user_id', table_name='chat_session_summaries')
    op.drop_index('ix_chat_session_summaries_session_id', table_name='chat_session_summaries')
    op.drop_index('ix_chat_summaries_user_created', table_name='chat_session_summaries')
    op.drop_index('ix_chat_summaries_session_created', table_name='chat_session_summaries')
    
    op.drop_index('ix_chat_messages_user_id', table_name='chat_messages')
    op.drop_index('ix_chat_messages_session_id', table_name='chat_messages')
    op.drop_index('ix_chat_messages_type', table_name='chat_messages')
    op.drop_index('ix_chat_messages_intent', table_name='chat_messages')
    op.drop_index('ix_chat_messages_user_timestamp', table_name='chat_messages')
    op.drop_index('ix_chat_messages_session_timestamp', table_name='chat_messages')
    
    op.drop_index('ix_chat_sessions_user_id', table_name='chat_sessions')
    op.drop_index('ix_chat_sessions_last_activity', table_name='chat_sessions')
    op.drop_index('ix_chat_sessions_user_active', table_name='chat_sessions')
    
    # Drop tables
    op.drop_table('chat_session_summaries')
    op.drop_table('chat_messages')
    op.drop_table('chat_sessions')