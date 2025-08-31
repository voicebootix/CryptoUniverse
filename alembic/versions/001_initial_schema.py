"""Initial schema for CryptoUniverse Enterprise

Revision ID: 001_initial_schema
Revises: 
Create Date: 2024-01-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE userrole AS ENUM ('admin', 'trader', 'viewer', 'api_only')")
    op.execute("CREATE TYPE subscriptionstatus AS ENUM ('active', 'inactive', 'canceled', 'past_due', 'trialing')")
    op.execute("CREATE TYPE subscriptiontier AS ENUM ('free', 'basic', 'pro', 'enterprise')")
    op.execute("CREATE TYPE exchangestatus AS ENUM ('active', 'inactive', 'maintenance', 'error', 'suspended')")
    op.execute("CREATE TYPE exchangetype AS ENUM ('spot', 'futures', 'margin', 'options')")
    op.execute("CREATE TYPE apikeystatus AS ENUM ('active', 'inactive', 'expired', 'invalid', 'suspended')")
    op.execute("CREATE TYPE tradeaction AS ENUM ('buy', 'sell')")
    op.execute("CREATE TYPE tradestatus AS ENUM ('pending', 'executing', 'completed', 'failed', 'canceled', 'partially_filled')")
    op.execute("CREATE TYPE ordertype AS ENUM ('market', 'limit', 'stop_loss', 'take_profit', 'stop_limit', 'trailing_stop')")
    op.execute("CREATE TYPE orderstatus AS ENUM ('pending', 'open', 'filled', 'partially_filled', 'canceled', 'expired', 'rejected')")
    op.execute("CREATE TYPE positiontype AS ENUM ('long', 'short')")
    op.execute("CREATE TYPE positionstatus AS ENUM ('open', 'closed', 'closing')")
    op.execute("CREATE TYPE strategytype AS ENUM ('manual', 'algorithmic', 'ai_consensus', 'copy_trading', 'arbitrage', 'momentum', 'mean_reversion', 'scalping', 'dca')")
    
    # Create tenants table
    op.create_table('tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('domain', sa.String(length=100), nullable=True),
        sa.Column('settings', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('max_users', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('domain')
    )
    op.create_index(op.f('ix_tenants_id'), 'tenants', ['id'], unique=False)
    op.create_index(op.f('ix_tenants_name'), 'tenants', ['name'], unique=False)
    
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=254), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=True),
        sa.Column('full_name', sa.String(length=100), nullable=True),
        sa.Column('hashed_password', sa.String(length=128), nullable=True),
        sa.Column('role', sa.Enum('admin', 'trader', 'viewer', 'api_only', name='userrole'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('simulation_mode', sa.Boolean(), nullable=False),
        sa.Column('timezone', sa.String(length=50), nullable=False),
        sa.Column('preferences', sa.JSON(), nullable=False),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'email')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)
    op.create_index(op.f('ix_users_tenant_id'), 'users', ['tenant_id'], unique=False)
    
    # Create credit_transactions table
    op.create_table('credit_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('transaction_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('reference_id', sa.String(length=100), nullable=True),
        sa.Column('stripe_payment_intent_id', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_credit_transactions_id'), 'credit_transactions', ['id'], unique=False)
    op.create_index(op.f('ix_credit_transactions_user_id'), 'credit_transactions', ['user_id'], unique=False)
    
    # Create credit_accounts table
    op.create_table('credit_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('available_credits', sa.Integer(), nullable=False),
        sa.Column('total_purchased_credits', sa.Integer(), nullable=False),
        sa.Column('total_used_credits', sa.Integer(), nullable=False),
        sa.Column('credit_limit', sa.Integer(), nullable=False),
        sa.Column('auto_recharge_enabled', sa.Boolean(), nullable=False),
        sa.Column('auto_recharge_threshold', sa.Integer(), nullable=False),
        sa.Column('auto_recharge_amount', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_credit_accounts_id'), 'credit_accounts', ['id'], unique=False)
    op.create_index(op.f('ix_credit_accounts_user_id'), 'credit_accounts', ['user_id'], unique=False)
    
    # Create exchange_accounts table
    op.create_table('exchange_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('exchange_name', sa.String(length=50), nullable=False),
        sa.Column('exchange_type', sa.Enum('spot', 'futures', 'margin', 'options', name='exchangetype'), nullable=False),
        sa.Column('account_type', sa.String(length=20), nullable=False),
        sa.Column('account_name', sa.String(length=100), nullable=False),
        sa.Column('exchange_account_id', sa.String(length=100), nullable=True),
        sa.Column('status', sa.Enum('active', 'inactive', 'maintenance', 'error', 'suspended', name='exchangestatus'), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('is_simulation', sa.Boolean(), nullable=False),
        sa.Column('trading_enabled', sa.Boolean(), nullable=False),
        sa.Column('max_daily_trades', sa.Integer(), nullable=False),
        sa.Column('max_position_size_usd', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('allowed_symbols', sa.JSON(), nullable=False),
        sa.Column('daily_loss_limit_usd', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('max_open_positions', sa.Integer(), nullable=False),
        sa.Column('stop_loss_required', sa.Boolean(), nullable=False),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False),
        sa.Column('retry_attempts', sa.Integer(), nullable=False),
        sa.Column('last_connection_test', sa.DateTime(), nullable=True),
        sa.Column('last_successful_request', sa.DateTime(), nullable=True),
        sa.Column('consecutive_failures', sa.Integer(), nullable=False),
        sa.Column('total_requests', sa.Integer(), nullable=False),
        sa.Column('successful_requests', sa.Integer(), nullable=False),
        sa.Column('trades_today', sa.Integer(), nullable=False),
        sa.Column('daily_loss_usd', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('last_trade_at', sa.DateTime(), nullable=True),
        sa.Column('last_reset_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_exchange_default', 'exchange_accounts', ['is_default'], unique=False)
    op.create_index('idx_exchange_name_status', 'exchange_accounts', ['exchange_name', 'status'], unique=False)
    op.create_index('idx_exchange_user_status', 'exchange_accounts', ['user_id', 'status'], unique=False)
    op.create_index(op.f('ix_exchange_accounts_id'), 'exchange_accounts', ['id'], unique=False)
    op.create_index(op.f('ix_exchange_accounts_user_id'), 'exchange_accounts', ['user_id'], unique=False)
    op.create_index('unique_user_exchange_account', 'exchange_accounts', ['user_id', 'exchange_name', 'account_name'], unique=True)
    
    # Create exchange_api_keys table
    op.create_table('exchange_api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key_name', sa.String(length=100), nullable=False),
        sa.Column('key_type', sa.String(length=20), nullable=False),
        sa.Column('encrypted_api_key', sa.Text(), nullable=False),
        sa.Column('encrypted_secret_key', sa.Text(), nullable=False),
        sa.Column('encrypted_passphrase', sa.Text(), nullable=True),
        sa.Column('key_hash', sa.String(length=64), nullable=False),
        sa.Column('permissions', sa.JSON(), nullable=False),
        sa.Column('ip_restrictions', sa.JSON(), nullable=False),
        sa.Column('status', sa.Enum('active', 'inactive', 'expired', 'invalid', 'suspended', name='apikeystatus'), nullable=False),
        sa.Column('is_validated', sa.Boolean(), nullable=False),
        sa.Column('validation_error', sa.Text(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('total_requests', sa.Integer(), nullable=False),
        sa.Column('failed_requests', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('rotation_required', sa.Boolean(), nullable=False),
        sa.Column('last_rotation_at', sa.DateTime(), nullable=True),
        sa.Column('created_by_ip', sa.String(length=45), nullable=True),
        sa.Column('last_modified_ip', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('validated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['exchange_accounts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_api_key_account_status', 'exchange_api_keys', ['account_id', 'status'], unique=False)
    op.create_index('idx_api_key_expires', 'exchange_api_keys', ['expires_at'], unique=False)
    op.create_index('idx_api_key_hash', 'exchange_api_keys', ['key_hash'], unique=False)
    op.create_index(op.f('ix_exchange_api_keys_id'), 'exchange_api_keys', ['id'], unique=False)
    op.create_index(op.f('ix_exchange_api_keys_status'), 'exchange_api_keys', ['status'], unique=False)
    
    # Create exchange_balances table
    op.create_table('exchange_balances',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('asset_type', sa.String(length=20), nullable=False),
        sa.Column('total_balance', sa.Numeric(precision=25, scale=8), nullable=False),
        sa.Column('available_balance', sa.Numeric(precision=25, scale=8), nullable=False),
        sa.Column('locked_balance', sa.Numeric(precision=25, scale=8), nullable=False),
        sa.Column('usd_value', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('avg_cost_basis', sa.Numeric(precision=15, scale=8), nullable=True),
        sa.Column('last_sync_balance', sa.Numeric(precision=25, scale=8), nullable=True),
        sa.Column('balance_change_24h', sa.Numeric(precision=25, scale=8), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('sync_enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['exchange_accounts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_balance_account_symbol', 'exchange_balances', ['account_id', 'symbol'], unique=False)
    op.create_index('idx_balance_symbol_usd', 'exchange_balances', ['symbol', 'usd_value'], unique=False)
    op.create_index('idx_balance_updated', 'exchange_balances', ['updated_at'], unique=False)
    op.create_index(op.f('ix_exchange_balances_id'), 'exchange_balances', ['id'], unique=False)
    op.create_index(op.f('ix_exchange_balances_symbol'), 'exchange_balances', ['symbol'], unique=False)
    op.create_index('unique_account_symbol_balance', 'exchange_balances', ['account_id', 'symbol'], unique=True)
    
    # Create portfolios table
    op.create_table('portfolios',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('total_value_usd', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('cash_balance_usd', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('invested_value_usd', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('total_pnl_usd', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('unrealized_pnl_usd', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('realized_pnl_usd', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('max_drawdown_percent', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('sharpe_ratio', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('volatility_percent', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('risk_level', sa.String(length=20), nullable=False),
        sa.Column('max_position_size_percent', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('max_sector_allocation_percent', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_portfolios_id'), 'portfolios', ['id'], unique=False)
    op.create_index(op.f('ix_portfolios_user_id'), 'portfolios', ['user_id'], unique=False)
    
    # Create trading_strategies table
    op.create_table('trading_strategies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('strategy_type', sa.Enum('manual', 'algorithmic', 'ai_consensus', 'copy_trading', 'arbitrage', 'momentum', 'mean_reversion', 'scalping', 'dca', name='strategytype'), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=False),
        sa.Column('risk_parameters', sa.JSON(), nullable=False),
        sa.Column('entry_conditions', sa.JSON(), nullable=False),
        sa.Column('exit_conditions', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_simulation', sa.Boolean(), nullable=False),
        sa.Column('max_positions', sa.Integer(), nullable=False),
        sa.Column('max_risk_per_trade', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('target_symbols', sa.JSON(), nullable=False),
        sa.Column('target_exchanges', sa.JSON(), nullable=False),
        sa.Column('timeframe', sa.String(length=10), nullable=False),
        sa.Column('total_trades', sa.Integer(), nullable=False),
        sa.Column('winning_trades', sa.Integer(), nullable=False),
        sa.Column('total_pnl', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('max_drawdown', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('sharpe_ratio', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column('ai_models', sa.JSON(), nullable=False),
        sa.Column('confidence_threshold', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('consensus_required', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_executed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trading_strategies_id'), 'trading_strategies', ['id'], unique=False)
    op.create_index(op.f('ix_trading_strategies_strategy_type'), 'trading_strategies', ['strategy_type'], unique=False)
    op.create_index(op.f('ix_trading_strategies_user_id'), 'trading_strategies', ['user_id'], unique=False)
    
    # Create trades table
    op.create_table('trades',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('exchange_account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('action', sa.Enum('buy', 'sell', name='tradeaction'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'executing', 'completed', 'failed', 'canceled', 'partially_filled', name='tradestatus'), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=25, scale=8), nullable=False),
        sa.Column('price', sa.Numeric(precision=25, scale=8), nullable=True),
        sa.Column('executed_quantity', sa.Numeric(precision=25, scale=8), nullable=False),
        sa.Column('executed_price', sa.Numeric(precision=25, scale=8), nullable=True),
        sa.Column('order_type', sa.Enum('market', 'limit', 'stop_loss', 'take_profit', 'stop_limit', 'trailing_stop', name='ordertype'), nullable=False),
        sa.Column('external_order_id', sa.String(length=100), nullable=True),
        sa.Column('total_value', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('fees_paid', sa.Numeric(precision=15, scale=8), nullable=False),
        sa.Column('fee_currency', sa.String(length=10), nullable=False),
        sa.Column('stop_loss_price', sa.Numeric(precision=25, scale=8), nullable=True),
        sa.Column('take_profit_price', sa.Numeric(precision=25, scale=8), nullable=True),
        sa.Column('trailing_stop_distance', sa.Numeric(precision=25, scale=8), nullable=True),
        sa.Column('is_simulation', sa.Boolean(), nullable=False),
        sa.Column('execution_mode', sa.String(length=20), nullable=False),
        sa.Column('urgency', sa.String(length=10), nullable=False),
        sa.Column('ai_confidence', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('ai_reasoning', sa.Text(), nullable=True),
        sa.Column('signal_source', sa.String(length=50), nullable=True),
        sa.Column('market_price_at_execution', sa.Numeric(precision=25, scale=8), nullable=True),
        sa.Column('slippage_bps', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('spread_bps', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('risk_score', sa.Integer(), nullable=False),
        sa.Column('position_size_percent', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('portfolio_impact_percent', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('credits_used', sa.Integer(), nullable=False),
        sa.Column('profit_realized_usd', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('meta_data', sa.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['exchange_account_id'], ['exchange_accounts.id'], ),
        sa.ForeignKeyConstraint(['strategy_id'], ['trading_strategies.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_trade_executed', 'trades', ['executed_at'], unique=False)
    op.create_index('idx_trade_external_order', 'trades', ['external_order_id'], unique=False)
    op.create_index('idx_trade_simulation', 'trades', ['is_simulation'], unique=False)
    op.create_index('idx_trade_status_created', 'trades', ['status', 'created_at'], unique=False)
    op.create_index('idx_trade_user_symbol', 'trades', ['user_id', 'symbol'], unique=False)
    op.create_index(op.f('ix_trades_id'), 'trades', ['id'], unique=False)
    op.create_index(op.f('ix_trades_status'), 'trades', ['status'], unique=False)
    op.create_index(op.f('ix_trades_symbol'), 'trades', ['symbol'], unique=False)
    op.create_index(op.f('ix_trades_user_id'), 'trades', ['user_id'], unique=False)
    
    # Create positions table
    op.create_table('positions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('exchange_account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('portfolio_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('position_type', sa.Enum('long', 'short', name='positiontype'), nullable=False),
        sa.Column('status', sa.Enum('open', 'closed', 'closing', name='positionstatus'), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=25, scale=8), nullable=False),
        sa.Column('average_entry_price', sa.Numeric(precision=25, scale=8), nullable=False),
        sa.Column('current_price', sa.Numeric(precision=25, scale=8), nullable=True),
        sa.Column('entry_value', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('current_value', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('unrealized_pnl', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('realized_pnl', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('stop_loss_price', sa.Numeric(precision=25, scale=8), nullable=True),
        sa.Column('take_profit_price', sa.Numeric(precision=25, scale=8), nullable=True),
        sa.Column('trailing_stop_distance', sa.Numeric(precision=25, scale=8), nullable=True),
        sa.Column('max_loss_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('high_water_mark', sa.Numeric(precision=25, scale=8), nullable=True),
        sa.Column('low_water_mark', sa.Numeric(precision=25, scale=8), nullable=True),
        sa.Column('max_unrealized_profit', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('max_unrealized_loss', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('auto_close_enabled', sa.Boolean(), nullable=False),
        sa.Column('max_hold_duration_hours', sa.Integer(), nullable=True),
        sa.Column('partial_close_enabled', sa.Boolean(), nullable=False),
        sa.Column('opened_at', sa.DateTime(), nullable=False),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('last_updated_at', sa.DateTime(), nullable=False),
        sa.Column('meta_data', sa.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['exchange_account_id'], ['exchange_accounts.id'], ),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ),
        sa.ForeignKeyConstraint(['strategy_id'], ['trading_strategies.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_position_opened', 'positions', ['opened_at'], unique=False)
    op.create_index('idx_position_portfolio', 'positions', ['portfolio_id', 'status'], unique=False)
    op.create_index('idx_position_status', 'positions', ['status'], unique=False)
    op.create_index('idx_position_user_symbol', 'positions', ['user_id', 'symbol'], unique=False)
    op.create_index(op.f('ix_positions_id'), 'positions', ['id'], unique=False)
    op.create_index(op.f('ix_positions_symbol'), 'positions', ['symbol'], unique=False)
    op.create_index(op.f('ix_positions_user_id'), 'positions', ['user_id'], unique=False)
    
    # Create orders table
    op.create_table('orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('exchange_account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('trade_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('position_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('side', sa.Enum('buy', 'sell', name='tradeaction'), nullable=False),
        sa.Column('order_type', sa.Enum('market', 'limit', 'stop_loss', 'take_profit', 'stop_limit', 'trailing_stop', name='ordertype'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'open', 'filled', 'partially_filled', 'canceled', 'expired', 'rejected', name='orderstatus'), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=25, scale=8), nullable=False),
        sa.Column('price', sa.Numeric(precision=25, scale=8), nullable=True),
        sa.Column('stop_price', sa.Numeric(precision=25, scale=8), nullable=True),
        sa.Column('filled_quantity', sa.Numeric(precision=25, scale=8), nullable=False),
        sa.Column('remaining_quantity', sa.Numeric(precision=25, scale=8), nullable=False),
        sa.Column('average_fill_price', sa.Numeric(precision=25, scale=8), nullable=True),
        sa.Column('external_order_id', sa.String(length=100), nullable=True),
        sa.Column('client_order_id', sa.String(length=100), nullable=True),
        sa.Column('time_in_force', sa.String(length=10), nullable=False),
        sa.Column('reduce_only', sa.Boolean(), nullable=False),
        sa.Column('post_only', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('filled_at', sa.DateTime(), nullable=True),
        sa.Column('canceled_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['exchange_account_id'], ['exchange_accounts.id'], ),
        sa.ForeignKeyConstraint(['position_id'], ['positions.id'], ),
        sa.ForeignKeyConstraint(['trade_id'], ['trades.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_order_client', 'orders', ['client_order_id'], unique=False)
    op.create_index('idx_order_external', 'orders', ['external_order_id'], unique=False)
    op.create_index('idx_order_status_created', 'orders', ['status', 'created_at'], unique=False)
    op.create_index('idx_order_symbol_status', 'orders', ['symbol', 'status'], unique=False)
    op.create_index(op.f('ix_orders_id'), 'orders', ['id'], unique=False)
    op.create_index(op.f('ix_orders_status'), 'orders', ['status'], unique=False)
    op.create_index(op.f('ix_orders_symbol'), 'orders', ['symbol'], unique=False)
    op.create_index(op.f('ix_orders_user_id'), 'orders', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop all tables in reverse order
    op.drop_table('orders')
    op.drop_table('positions')
    op.drop_table('trades')
    op.drop_table('trading_strategies')
    op.drop_table('portfolios')
    op.drop_table('exchange_balances')
    op.drop_table('exchange_api_keys')
    op.drop_table('exchange_accounts')
    op.drop_table('credit_accounts')
    op.drop_table('users')
    op.drop_table('tenants')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS strategytype")
    op.execute("DROP TYPE IF EXISTS positionstatus")
    op.execute("DROP TYPE IF EXISTS positiontype")
    op.execute("DROP TYPE IF EXISTS orderstatus")
    op.execute("DROP TYPE IF EXISTS ordertype")
    op.execute("DROP TYPE IF EXISTS tradestatus")
    op.execute("DROP TYPE IF EXISTS tradeaction")
    op.execute("DROP TYPE IF EXISTS apikeystatus")
    op.execute("DROP TYPE IF EXISTS exchangetype")
    op.execute("DROP TYPE IF EXISTS exchangestatus")
    op.execute("DROP TYPE IF EXISTS subscriptiontier")
    op.execute("DROP TYPE IF EXISTS subscriptionstatus")
    op.execute("DROP TYPE IF EXISTS userrole")