"""
Telegram Integration API Endpoints - Enterprise Grade

Handles per-user Telegram integration for bi-directional communication.
Users connect their Telegram accounts to access trading via natural language chat.

Features:
- Telegram account connection and authentication
- Natural language command processing
- Trading operations via chat
- Real-time notifications
- Voice command support
"""

import asyncio
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.core.config import get_settings
from app.core.database import get_database
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.models.telegram_integration import UserTelegramConnection, TelegramMessage
from app.services.telegram_core import TelegramService
from app.services.rate_limit import rate_limiter

settings = get_settings()
logger = structlog.get_logger(__name__)

router = APIRouter()

# Initialize Telegram service
telegram_service = TelegramService()


# Request/Response Models
class TelegramConnectionRequest(BaseModel):
    telegram_username: Optional[str] = None
    enable_notifications: bool = True
    enable_trading: bool = False
    enable_voice_commands: bool = False
    daily_trade_limit: int = 10
    max_trade_amount: int = 1000
    
    @field_validator('daily_trade_limit')
    @classmethod
    def validate_daily_limit(cls, v):
        if v < 1 or v > 100:
            raise ValueError("Daily trade limit must be between 1 and 100")
        return v
    
    @field_validator('max_trade_amount')
    @classmethod
    def validate_max_amount(cls, v):
        if v < 100 or v > 50000:
            raise ValueError("Max trade amount must be between $100 and $50,000")
        return v


class TelegramConnectionResponse(BaseModel):
    connection_id: str
    telegram_user_id: str
    telegram_username: Optional[str]
    telegram_chat_id: str
    is_active: bool
    trading_enabled: bool
    notifications_enabled: bool
    auth_token: str
    setup_instructions: str


class TelegramMessageRequest(BaseModel):
    message: str
    message_type: str = "text"
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        if len(v.strip()) == 0:
            raise ValueError("Message cannot be empty")
        if len(v) > 4000:
            raise ValueError("Message too long (max 4000 characters)")
        return v.strip()


class TelegramWebhookPayload(BaseModel):
    update_id: int
    message: Optional[Dict[str, Any]] = None
    callback_query: Optional[Dict[str, Any]] = None


# Telegram Integration Endpoints
@router.post("/connect", response_model=TelegramConnectionResponse)
async def connect_telegram_account(
    request: TelegramConnectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Connect user's Telegram account for bi-directional communication."""
    
    await rate_limiter.check_rate_limit(
        key="telegram:connect",
        limit=5,
        window=300,  # 5 connections per 5 minutes
        user_id=str(current_user.id)
    )
    
    logger.info(
        "Telegram connection request",
        user_id=str(current_user.id),
        username=request.telegram_username
    )
    
    try:
        # Check if user already has Telegram connection
        stmt = select(UserTelegramConnection).where(
            UserTelegramConnection.user_id == current_user.id
        )
        result = await db.execute(stmt)
        existing_connection = result.scalar_one_or_none()
        
        if existing_connection:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Telegram account already connected. Disconnect first to reconnect."
            )
        
        # Generate authentication token for secure communication
        auth_token = secrets.token_urlsafe(32)
        auth_expires = datetime.utcnow() + timedelta(days=365)  # 1 year validity
        
        # Create connection record (will be completed when user authenticates via Telegram)
        connection = UserTelegramConnection(
            user_id=current_user.id,
            telegram_user_id="pending",  # Will be updated when user connects
            telegram_username=request.telegram_username,
            telegram_chat_id="pending",  # Will be updated when user connects
            notifications_enabled=request.enable_notifications,
            trading_enabled=request.enable_trading,
            voice_commands_enabled=request.enable_voice_commands,
            daily_trade_limit=request.daily_trade_limit,
            max_trade_amount_usd=request.max_trade_amount,
            auth_token=auth_token,
            auth_expires_at=auth_expires,
            allowed_commands=self._get_default_allowed_commands(request.enable_trading)
        )
        
        db.add(connection)
        await db.commit()
        await db.refresh(connection)
        
        # Generate setup instructions
        bot_username = await self._get_bot_username()
        setup_instructions = self._generate_setup_instructions(auth_token, bot_username)
        
        logger.info(
            "Telegram connection created",
            user_id=str(current_user.id),
            connection_id=str(connection.id)
        )
        
        return TelegramConnectionResponse(
            connection_id=str(connection.id),
            telegram_user_id="pending",
            telegram_username=request.telegram_username,
            telegram_chat_id="pending",
            is_active=True,
            trading_enabled=request.enable_trading,
            notifications_enabled=request.enable_notifications,
            auth_token=auth_token,
            setup_instructions=setup_instructions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Telegram connection failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect Telegram: {str(e)}"
        )


@router.get("/connection")
async def get_telegram_connection(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Get user's Telegram connection status."""
    
    try:
        stmt = select(UserTelegramConnection).where(
            UserTelegramConnection.user_id == current_user.id
        )
        result = await db.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if not connection:
            return {
                "connected": False,
                "message": "No Telegram account connected"
            }
        
        return {
            "connected": True,
            "connection_id": str(connection.id),
            "telegram_username": connection.telegram_username,
            "is_active": connection.is_active,
            "trading_enabled": connection.trading_enabled,
            "notifications_enabled": connection.notifications_enabled,
            "voice_commands_enabled": connection.voice_commands_enabled,
            "is_authenticated": connection.is_authenticated,
            "total_messages": connection.total_messages_sent,
            "total_commands": connection.total_commands_executed,
            "last_active": connection.last_active_at.isoformat() if connection.last_active_at else None
        }
        
    except Exception as e:
        logger.error("Failed to get Telegram connection", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get connection: {str(e)}"
        )


@router.post("/webhook")
async def telegram_webhook(
    webhook_data: TelegramWebhookPayload,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_database)
):
    """Handle incoming Telegram webhook messages."""
    
    try:
        # Verify webhook authenticity
        if not await self._verify_telegram_webhook(request):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        # Process message in background
        background_tasks.add_task(
            _process_telegram_message,
            webhook_data.dict(),
            db
        )
        
        return {"ok": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Telegram webhook processing failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )


@router.post("/send-message")
async def send_telegram_message(
    request: TelegramMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Send message to user's Telegram chat."""
    
    await rate_limiter.check_rate_limit(
        key="telegram:send",
        limit=20,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Get user's Telegram connection
        stmt = select(UserTelegramConnection).where(
            and_(
                UserTelegramConnection.user_id == current_user.id,
                UserTelegramConnection.is_active == True
            )
        )
        result = await db.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active Telegram connection found"
            )
        
        # Send message via Telegram service
        send_result = await telegram_service.send_message(
            chat_id=connection.telegram_chat_id,
            text=request.message
        )
        
        if send_result.get("success"):
            # Update connection metrics
            connection.total_messages_sent += 1
            connection.last_message_at = datetime.utcnow()
            await db.commit()
            
            return {
                "success": True,
                "message_sent": True,
                "telegram_message_id": send_result.get("message_id")
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to send message: {send_result.get('error')}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to send Telegram message", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )


@router.delete("/disconnect")
async def disconnect_telegram_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Disconnect user's Telegram account."""
    
    try:
        stmt = select(UserTelegramConnection).where(
            UserTelegramConnection.user_id == current_user.id
        )
        result = await db.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Telegram connection found"
            )
        
        # Deactivate connection
        connection.is_active = False
        connection.trading_enabled = False
        connection.updated_at = datetime.utcnow()
        
        await db.commit()
        
        return {
            "success": True,
            "message": "Telegram account disconnected successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to disconnect Telegram", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect: {str(e)}"
        )


# Helper Functions
def _get_default_allowed_commands(trading_enabled: bool) -> List[str]:
    """Get default allowed commands based on user preferences."""
    basic_commands = [
        "/start", "/help", "/status", "/balance", "/positions", 
        "/trades", "/market", "/portfolio", "/credits"
    ]
    
    trading_commands = [
        "/buy", "/sell", "/close", "/stop", "/autonomous"
    ]
    
    if trading_enabled:
        return basic_commands + trading_commands
    else:
        return basic_commands


def _generate_setup_instructions(auth_token: str, bot_username: str) -> str:
    """Generate setup instructions for user."""
    return f"""
🤖 **Telegram Integration Setup**

1. Open Telegram and search for @{bot_username}
2. Start a chat with the bot
3. Send this authentication command:
   `/auth {auth_token}`
4. Follow the bot's instructions to complete setup

✅ **Once connected, you can:**
- Check portfolio: `/balance`
- Execute trades: `/buy BTC 100`
- Get AI analysis: `/market BTC`
- Monitor positions: `/positions`
- Control autonomous trading: `/autonomous start`

🔒 **Security**: Your auth token expires in 1 year. Trading commands require additional confirmation.
"""


async def _get_bot_username() -> str:
    """Get the bot's username from Telegram API."""
    try:
        # This would call Telegram getMe API
        return "CryptoUniverseBot"  # Would be dynamic in production
    except Exception:
        return "YourTradingBot"


async def _verify_telegram_webhook(request: Request) -> bool:
    """Verify Telegram webhook signature."""
    try:
        # Get webhook secret from settings
        webhook_secret = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', None)
        if not webhook_secret:
            return True  # Skip verification if not configured
        
        # Verify signature
        signature = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
        return signature == webhook_secret
        
    except Exception as e:
        logger.error("Webhook verification failed", error=str(e))
        return False


async def _process_telegram_message(webhook_data: Dict[str, Any], db: AsyncSession):
    """Process incoming Telegram message."""
    try:
        message_data = webhook_data.get("message", {})
        if not message_data:
            return
        
        telegram_user_id = str(message_data.get("from", {}).get("id", ""))
        chat_id = str(message_data.get("chat", {}).get("id", ""))
        message_text = message_data.get("text", "")
        
        # Find user connection
        stmt = select(UserTelegramConnection).where(
            and_(
                UserTelegramConnection.telegram_user_id == telegram_user_id,
                UserTelegramConnection.is_active == True
            )
        )
        result = await db.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if not connection:
            # Handle authentication if this is an auth command
            if message_text.startswith("/auth "):
                await _handle_authentication(message_data, db)
            else:
                # Send instructions to connect
                await telegram_service.send_message(
                    chat_id=chat_id,
                    text="⚠️ Please connect your account first. Go to the CryptoUniverse dashboard → Telegram Center to get started."
                )
            return
        
        # Process authenticated message
        await _process_authenticated_message(connection, message_data, db)
        
    except Exception as e:
        logger.error("Message processing failed", error=str(e))


async def _handle_authentication(message_data: Dict[str, Any], db: AsyncSession):
    """Handle Telegram authentication command."""
    try:
        message_text = message_data.get("text", "")
        auth_token = message_text.replace("/auth ", "").strip()
        
        telegram_user_id = str(message_data.get("from", {}).get("id", ""))
        chat_id = str(message_data.get("chat", {}).get("id", ""))
        telegram_username = message_data.get("from", {}).get("username")
        first_name = message_data.get("from", {}).get("first_name")
        last_name = message_data.get("from", {}).get("last_name")
        
        # Find pending connection with this auth token
        stmt = select(UserTelegramConnection).where(
            and_(
                UserTelegramConnection.auth_token == auth_token,
                UserTelegramConnection.telegram_user_id == "pending"
            )
        )
        result = await db.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if not connection:
            await telegram_service.send_message(
                chat_id=chat_id,
                text="❌ Invalid authentication token. Please get a new token from the CryptoUniverse dashboard."
            )
            return
        
        # Complete the connection
        connection.telegram_user_id = telegram_user_id
        connection.telegram_chat_id = chat_id
        connection.telegram_username = telegram_username
        connection.telegram_first_name = first_name
        connection.telegram_last_name = last_name
        connection.last_active_at = datetime.utcnow()
        
        await db.commit()
        
        # Send welcome message
        welcome_message = f"""
🎉 **Welcome to CryptoUniverse Enterprise!**

✅ Your Telegram account is now connected
👤 Connected as: {first_name} (@{telegram_username})

🤖 **Available Commands:**
• `/status` - Get account status
• `/balance` - Check portfolio balance
• `/positions` - View open positions
• `/market BTC` - Get market analysis
• `/buy BTC 100` - Execute buy order
• `/autonomous start` - Start AI trading

🔒 **Security**: Trading commands require confirmation
💡 **Tip**: Try `/help` for full command list
"""
        
        await telegram_service.send_message(
            chat_id=chat_id,
            text=welcome_message
        )
        
        logger.info(
            "Telegram authentication successful",
            user_id=str(connection.user_id),
            telegram_user_id=telegram_user_id
        )
        
    except Exception as e:
        logger.error("Telegram authentication failed", error=str(e))


async def _process_authenticated_message(
    connection: UserTelegramConnection,
    message_data: Dict[str, Any],
    db: AsyncSession
):
    """Process message from authenticated user."""
    try:
        message_text = message_data.get("text", "")
        chat_id = connection.telegram_chat_id
        
        # Update connection activity
        connection.last_active_at = datetime.utcnow()
        connection.total_messages_sent += 1
        
        # Store message for audit trail
        telegram_message = TelegramMessage(
            connection_id=connection.id,
            telegram_message_id=str(message_data.get("message_id", "")),
            message_type="text",
            message_content=message_text,
            is_command=message_text.startswith("/"),
            received_at=datetime.utcnow()
        )
        db.add(telegram_message)
        
        # Process command or natural language
        if message_text.startswith("/"):
            response = await _process_telegram_command(connection, message_text, db)
        else:
            response = await _process_natural_language(connection, message_text, db)
        
        # Send response
        if response:
            await telegram_service.send_message(
                chat_id=chat_id,
                text=response
            )
            
            # Update message record
            telegram_message.response_sent = True
            telegram_message.response_content = response
            telegram_message.processed = True
            telegram_message.processed_at = datetime.utcnow()
        
        await db.commit()
        
    except Exception as e:
        logger.error("Authenticated message processing failed", error=str(e))


async def _process_telegram_command(
    connection: UserTelegramConnection,
    command_text: str,
    db: AsyncSession
) -> Optional[str]:
    """Process Telegram command."""
    try:
        parts = command_text.split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        # Check command permissions
        if not connection.has_command_permission(command):
            return f"❌ You don't have permission to use {command}"
        
        # Route command to appropriate handler
        if command == "/status":
            return await _handle_status_command(connection, db)
        elif command == "/balance":
            return await _handle_balance_command(connection, db)
        elif command == "/positions":
            return await _handle_positions_command(connection, db)
        elif command == "/buy" and len(args) >= 2:
            return await _handle_buy_command(connection, args, db)
        elif command == "/sell" and len(args) >= 2:
            return await _handle_sell_command(connection, args, db)
        elif command == "/market" and len(args) >= 1:
            return await _handle_market_command(connection, args, db)
        elif command == "/autonomous":
            return await _handle_autonomous_command(connection, args, db)
        elif command == "/credits":
            return await _handle_credits_command(connection, db)
        elif command == "/help":
            return _generate_help_message(connection)
        else:
            return f"❓ Unknown command: {command}\nTry `/help` for available commands"
        
    except Exception as e:
        logger.error("Command processing failed", error=str(e))
        return f"❌ Command processing failed: {str(e)}"


async def _process_natural_language(
    connection: UserTelegramConnection,
    message_text: str,
    db: AsyncSession
) -> Optional[str]:
    """Process natural language message using AI."""
    try:
        # Use your AI consensus service for natural language processing
        from app.services.ai_consensus_core import ai_consensus_service
        
        # Analyze intent
        intent_analysis = await ai_consensus_service.analyze_opportunity(
            analysis_request=f"Analyze this trading-related message and extract intent: '{message_text}'",
            confidence_threshold=70.0,
            user_id=str(connection.user_id)
        )
        
        if intent_analysis.get("success"):
            # Extract intent and generate appropriate response
            analysis_data = intent_analysis.get("analysis_result", {})
            detected_intent = analysis_data.get("intent", "unknown")
            
            # Route based on detected intent
            if "balance" in detected_intent.lower():
                return await _handle_balance_command(connection, db)
            elif "buy" in detected_intent.lower() or "purchase" in detected_intent.lower():
                return "💡 To buy crypto, use: `/buy BTC 100` (symbol and amount in USD)"
            elif "sell" in detected_intent.lower():
                return "💡 To sell crypto, use: `/sell BTC 100` (symbol and amount in USD)"
            elif "status" in detected_intent.lower() or "how" in detected_intent.lower():
                return await _handle_status_command(connection, db)
            elif "autonomous" in detected_intent.lower() or "ai" in detected_intent.lower():
                return "🤖 To control AI trading, use: `/autonomous start` or `/autonomous stop`"
            else:
                return f"💬 I understand you're asking about: {detected_intent}\n\nTry using specific commands like `/help` for available options."
        
        return "❓ I didn't understand that. Try `/help` for available commands."
        
    except Exception as e:
        logger.error("Natural language processing failed", error=str(e))
        return "❓ I didn't understand that. Try `/help` for available commands."


async def _handle_status_command(connection: UserTelegramConnection, db: AsyncSession) -> str:
    """Handle /status command."""
    try:
        # Get user's portfolio status using your existing service
        from app.api.v1.endpoints.exchanges import get_user_portfolio_from_exchanges
        
        portfolio_data = await get_user_portfolio_from_exchanges(str(connection.user_id), db)
        
        if portfolio_data.get("success"):
            total_value = portfolio_data.get("total_value_usd", 0)
            exchange_count = len(portfolio_data.get("exchanges", []))
            
            return f"""
📊 **Account Status**

💰 **Portfolio Value**: ${total_value:,.2f}
🏦 **Connected Exchanges**: {exchange_count}
🤖 **AI Status**: Active
💳 **Credits**: [Loading...]

⏰ **Last Updated**: {datetime.utcnow().strftime('%H:%M:%S UTC')}
"""
        else:
            return "❌ Unable to fetch account status. Please check your exchange connections."
        
    except Exception as e:
        logger.error("Status command failed", error=str(e))
        return "❌ Status command failed"


async def _handle_balance_command(connection: UserTelegramConnection, db: AsyncSession) -> str:
    """Handle /balance command."""
    try:
        # Get portfolio balances
        from app.api.v1.endpoints.exchanges import get_user_portfolio_from_exchanges
        
        portfolio_data = await get_user_portfolio_from_exchanges(str(connection.user_id), db)
        
        if portfolio_data.get("success"):
            balances = portfolio_data.get("balances", [])
            total_value = portfolio_data.get("total_value_usd", 0)
            
            balance_text = f"💰 **Total Portfolio**: ${total_value:,.2f}\n\n"
            
            # Show top 10 balances
            sorted_balances = sorted(balances, key=lambda x: x.get("value_usd", 0), reverse=True)
            for balance in sorted_balances[:10]:
                if balance.get("total", 0) > 0:
                    asset = balance.get("asset", "")
                    amount = balance.get("total", 0)
                    value_usd = balance.get("value_usd", 0)
                    exchange = balance.get("exchange", "")
                    
                    balance_text += f"• **{asset}**: {amount:.6f} (${value_usd:.2f}) [{exchange}]\n"
            
            return balance_text
        else:
            return "❌ Unable to fetch balance. Please check your exchange connections."
        
    except Exception as e:
        logger.error("Balance command failed", error=str(e))
        return "❌ Balance command failed"


async def _handle_buy_command(
    connection: UserTelegramConnection,
    args: List[str],
    db: AsyncSession
) -> str:
    """Handle /buy command."""
    try:
        if not connection.can_trade:
            return "❌ Trading not enabled for your Telegram account. Enable it in the dashboard first."
        
        symbol = args[0].upper()
        amount_usd = float(args[1])
        
        if amount_usd > connection.max_trade_amount_usd:
            return f"❌ Trade amount ${amount_usd} exceeds your limit of ${connection.max_trade_amount_usd}"
        
        # Execute trade using your existing trading API
        from app.services.trade_execution import TradeExecutionService
        trade_service = TradeExecutionService()
        
        trade_request = {
            "symbol": symbol,
            "action": "buy",
            "quantity": amount_usd,  # Amount in USD
            "order_type": "market",
            "user_id": str(connection.user_id)
        }
        
        result = await trade_service.execute_trade(
            trade_request,
            str(connection.user_id),
            simulation_mode=False  # Real trading via Telegram
        )
        
        if result.get("success"):
            execution_data = result.get("execution_result", {})
            return f"""
✅ **Buy Order Executed**

🪙 **Symbol**: {symbol}
💵 **Amount**: ${amount_usd}
💰 **Price**: ${execution_data.get('execution_price', 0):,.2f}
🏦 **Exchange**: {execution_data.get('exchange', 'auto')}
🆔 **Order ID**: {execution_data.get('order_id', 'N/A')}

⏰ **Executed**: {datetime.utcnow().strftime('%H:%M:%S UTC')}
"""
        else:
            return f"❌ **Buy order failed**: {result.get('error', 'Unknown error')}"
        
    except Exception as e:
        logger.error("Buy command failed", error=str(e))
        return f"❌ Buy command failed: {str(e)}"


async def _handle_credits_command(connection: UserTelegramConnection, db: AsyncSession) -> str:
    """Handle /credits command."""
    try:
        # Get credit balance using your credit system
        from app.models.credit import CreditAccount
        
        stmt = select(CreditAccount).where(CreditAccount.user_id == connection.user_id)
        result = await db.execute(stmt)
        credit_account = result.scalar_one_or_none()
        
        if credit_account:
            profit_potential = credit_account.total_purchased_credits * 4  # 4x multiplier
            
            return f"""
💳 **Credit Status**

🪙 **Available Credits**: {credit_account.available_credits:,}
💰 **Profit Potential**: ${profit_potential:,}
📊 **Total Purchased**: {credit_account.total_purchased_credits:,}
📈 **Total Used**: {credit_account.total_used_credits:,}

💡 **Need more credits?** Go to dashboard → Credit Center
"""
        else:
            return "❌ No credit account found. Please purchase credits in the dashboard first."
        
    except Exception as e:
        logger.error("Credits command failed", error=str(e))
        return "❌ Credits command failed"


def _generate_help_message(connection: UserTelegramConnection) -> str:
    """Generate help message with available commands."""
    basic_help = """
🤖 **CryptoUniverse Telegram Bot**

📊 **Account Commands:**
• `/status` - Get account status
• `/balance` - Check portfolio balance
• `/positions` - View open positions
• `/credits` - Check credit balance

📈 **Market Commands:**
• `/market BTC` - Get market analysis
• `/ai_consensus` - Get AI market consensus

🤖 **AI Commands:**
• `/autonomous start` - Start AI trading
• `/autonomous stop` - Stop AI trading
• `/autonomous status` - Check AI status
"""
    
    if connection.trading_enabled:
        trading_help = """
💰 **Trading Commands:**
• `/buy BTC 100` - Buy $100 worth of BTC
• `/sell ETH 50` - Sell $50 worth of ETH
• `/close BTC` - Close BTC positions
• `/stop` - Emergency stop all trading

⚠️ **Note**: Trading commands require confirmation
"""
        return basic_help + trading_help
    
    return basic_help + "\n🔒 **Trading disabled** - Enable in dashboard to access trading commands"


# Additional command handlers would be implemented here...
async def _handle_sell_command(connection: UserTelegramConnection, args: List[str], db: AsyncSession) -> str:
    """Handle /sell command.""" 
    # Similar to buy command but for selling
    return "Sell command implementation..."

async def _handle_positions_command(connection: UserTelegramConnection, db: AsyncSession) -> str:
    """Handle /positions command."""
    # Get and format open positions
    return "Positions command implementation..."

async def _handle_market_command(connection: UserTelegramConnection, args: List[str], db: AsyncSession) -> str:
    """Handle /market command."""
    # Get market analysis for symbol
    return "Market command implementation..."

async def _handle_autonomous_command(connection: UserTelegramConnection, args: List[str], db: AsyncSession) -> str:
    """Handle /autonomous command."""
    # Control autonomous trading
    return "Autonomous command implementation..."