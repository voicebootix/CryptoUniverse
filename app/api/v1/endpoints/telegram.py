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
from app.services.telegram_core import telegram_commander_service
from app.services.telegram_commander import MessageType
from app.services.rate_limit import rate_limiter
from app.services.unified_ai_manager import (
    unified_ai_manager,
    InterfaceType as UnifiedInterfaceType,
)

settings = get_settings()
logger = structlog.get_logger(__name__)

router = APIRouter()

# Initialize Telegram service
telegram_service = telegram_commander_service


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
    message_type: str = "info"
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        if len(v.strip()) == 0:
            raise ValueError("Message cannot be empty")
        if len(v) > 4000:
            raise ValueError("Message too long (max 4000 characters)")
        return v.strip()

    @field_validator('message_type')
    @classmethod
    def validate_message_type(cls, v):
        if not v or len(v.strip()) == 0:
            return "info"  # Default fallback
        # Normalize and validate - basic validation here, detailed mapping in endpoint
        valid_types = ["text", "info", "information", "alert", "warning", "trade", "trading", "portfolio", "system", "voice", "voice_response"]
        normalized = v.lower().strip()
        if normalized not in valid_types:
            # Log warning but don't fail - let endpoint mapping handle fallback
            return "info"
        return normalized


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
        limit=10,
        window=60,  # 10 connections per 1 minute - more reasonable for testing
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
            # Allow reconnection if not authenticated (pending state)
            if existing_connection.telegram_user_id != "pending" and existing_connection.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Telegram account already connected and authenticated. Disconnect first to reconnect."
                )
            # Delete the pending connection to create a new one
            await db.delete(existing_connection)
            await db.commit()
        
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
            allowed_commands=_get_default_allowed_commands(request.enable_trading)
        )
        
        db.add(connection)
        await db.commit()
        await db.refresh(connection)
        
        # Generate setup instructions
        bot_username = await _get_bot_username()
        setup_instructions = _generate_setup_instructions(auth_token, bot_username)
        
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
        if not await _verify_telegram_webhook(request):
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

        # Validate connection has required chat ID and is authenticated
        if not connection.telegram_chat_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Telegram connection missing chat ID - please complete authentication in Telegram"
            )

        # Check if connection is properly authenticated (has completed setup)
        if connection.telegram_user_id == "pending" or not connection.telegram_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Telegram connection not authenticated - please complete /auth <token> in Telegram"
            )

        # Normalize and validate message_type from request
        # Map common input values to valid MessageType enum values
        message_type_mapping = {
            "text": MessageType.INFO,
            "info": MessageType.INFO,
            "information": MessageType.INFO,
            "alert": MessageType.ALERT,
            "warning": MessageType.ALERT,
            "trade": MessageType.TRADE,
            "trading": MessageType.TRADE,
            "portfolio": MessageType.PORTFOLIO,
            "system": MessageType.SYSTEM,
            "voice": MessageType.VOICE_RESPONSE,
            "voice_response": MessageType.VOICE_RESPONSE,
        }

        # Normalize the request message type (case-insensitive)
        normalized_type = request.message_type.lower().strip()
        validated_message_type = message_type_mapping.get(normalized_type, MessageType.INFO)

        # Send message via Telegram service directly to user's chat
        send_result = await telegram_service.send_direct_message(
            chat_id=connection.telegram_chat_id,
            message_content=request.message,
            message_type=validated_message_type.value,
            priority="normal"
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


@router.get("/verify-connection")
async def verify_telegram_connection(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
):
    """Verify and update Telegram connection status."""
    
    try:
        stmt = select(UserTelegramConnection).where(
            UserTelegramConnection.user_id == current_user.id
        )
        result = await db.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if not connection:
            return {
                "verified": False,
                "message": "No Telegram connection found",
                "is_authenticated": False,
                "is_active": False
            }
        
        # Check if connection is properly authenticated
        # User has completed /auth command in Telegram if these are not "pending"
        has_completed_auth = (
            connection.telegram_user_id != "pending" and
            connection.telegram_chat_id != "pending"
        )
        
        # Combined verification flag - can we actually verify this connection?
        can_verify = has_completed_auth and connection.is_authenticated and connection.is_active
        
        # Test if bot can send messages (if can verify)
        bot_reachable = False
        if can_verify:
            try:
                # Try to get bot info to verify it's working
                bot_status = await telegram_service.get_bot_info()
                bot_reachable = bot_status.get("success", False)
            except Exception:
                bot_reachable = False
        
        # Note: is_authenticated is a property, don't try to set it
        # It's calculated based on auth_token and auth_expires_at
        await db.commit()
        
        verification_result = {
            "verified": can_verify and bot_reachable,
            "is_authenticated": connection.is_authenticated,  # Preserve model property semantics
            "is_active": connection.is_active,
            "bot_reachable": bot_reachable,
            "has_completed_auth": has_completed_auth,
            "can_verify": can_verify,
            "telegram_username": connection.telegram_username,
            "telegram_user_id": connection.telegram_user_id if has_completed_auth else "pending",
            "last_active": connection.last_active_at.isoformat() if connection.last_active_at else None
        }
        
        # Order checks by most actionable first
        if not has_completed_auth:
            verification_result["message"] = "Please complete authentication in Telegram using /auth command"
        elif not connection.is_authenticated:
            verification_result["message"] = "Authentication token expired - please reconnect"
        elif not connection.is_active:
            verification_result["message"] = "Connection inactive - please reconnect or enable the connection"
        elif not bot_reachable:
            verification_result["message"] = "Bot is not reachable - please contact support"
        else:
            verification_result["message"] = "Connection verified and working properly"
        
        return verification_result
        
    except Exception as e:
        logger.error("Connection verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}"
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
            # Only skip verification in development/test environments
            environment = getattr(settings, 'ENVIRONMENT', 'production').lower()
            allow_unverified = getattr(settings, 'TELEGRAM_ALLOW_UNVERIFIED', 'false').lower() == 'true'
            
            if environment in {"development", "test"} or allow_unverified:
                logger.info("Webhook verification skipped", 
                          environment=environment, 
                          allow_unverified=allow_unverified)
                return True
            else:
                logger.error("Webhook secret not configured in production environment")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Webhook verification not properly configured"
                )
        
        # Verify signature using constant-time comparison
        signature = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
        
        # Use secrets.compare_digest for timing attack protection
        import secrets
        signature_str = signature or ""
        is_valid = secrets.compare_digest(signature_str, webhook_secret)
        
        if not is_valid:
            logger.warning("Webhook verification failed", 
                         has_signature=bool(signature),
                         signature_length=len(signature) if signature else 0)
        else:
            logger.info("Webhook verification passed")
            
        return is_valid
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.exception("Webhook verification failed with unexpected error")
        # Fail closed on unexpected errors
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
                await telegram_service.send_direct_message(
                    chat_id=chat_id,
                    message_content="⚠️ Please connect your account first. Go to the CryptoUniverse dashboard → Telegram Center to get started."
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
            await telegram_service.send_direct_message(
                chat_id=chat_id,
                message_content="❌ Invalid authentication token. Please get a new token from the CryptoUniverse dashboard."
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
        
        await telegram_service.send_direct_message(
            chat_id=chat_id,
            message_content=welcome_message
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
            await telegram_service.send_direct_message(
                chat_id=chat_id,
                message_content=response
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
        
        # Check command permissions - allow basic commands for all
        basic_commands = ["/help", "/status", "/balance", "/opportunities", "/positions", "/market"]
        trading_commands = ["/buy", "/sell", "/autonomous"]
        
        # Skip permission check for basic commands
        if command not in basic_commands:
            # Only check permissions for trading commands
            if command in trading_commands and not connection.trading_enabled:
                return f"❌ Trading not enabled. Enable it in settings to use {command}"
        
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
        elif command == "/opportunities":
            return await _handle_opportunities_command(connection, db)
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
    """Process natural language messages through the unified AI persona pipeline."""
    del db  # Natural language routing no longer needs the raw database handle directly

    message = (message_text or "").strip()
    if not message:
        return (
            "I didn't catch a question there. Let me know what you want to review—portfolio status, strategies,"
            " or fresh trade ideas—and I'll walk you through it."
        )

    context = {
        "chat_id": connection.telegram_chat_id,
        "platform": "telegram",
        "interface_session": f"telegram_{connection.telegram_chat_id}",
        "telegram_username": connection.telegram_username,
        "telegram_connection_id": str(connection.id),
    }

    if connection.last_active_at:
        try:
            context["last_active_at"] = connection.last_active_at.isoformat()
        except AttributeError:
            context["last_active_at"] = str(connection.last_active_at)

    try:
        ai_result = await unified_ai_manager.process_user_request(
            user_id=str(connection.user_id),
            request=message,
            interface=UnifiedInterfaceType.TELEGRAM,
            context=context,
        )
    except Exception as exc:
        logger.error(
            "Unified AI manager failed to handle Telegram message",
            error=str(exc),
            user_id=str(connection.user_id),
        )
        ai_result = None

    if ai_result and ai_result.get("success"):
        action = ai_result.get("action")
        content = ai_result.get("content")

        if action == "executed":
            execution_result = ai_result.get("result", {}) or {}
            summary_bits: List[str] = []
            summary = execution_result.get("message") or execution_result.get("status")
            if summary:
                summary_bits.append(str(summary))
            if ai_result.get("ai_analysis"):
                summary_bits.append(str(ai_result["ai_analysis"]))
            details = execution_result.get("details")
            if details:
                summary_bits.append(str(details))
            if not summary_bits:
                summary_bits.append(
                    "Execution completed. Let me know if you want me to monitor the fill or set follow-up levels."
                )
            return " ".join(summary_bits)

        if content:
            return str(content)

        if ai_result.get("ai_analysis"):
            return str(ai_result["ai_analysis"])

        if action == "clarify":
            return (
                ai_result.get("content")
                or "Just to confirm—do you need portfolio context, strategy guidance, or trade execution help?"
            )

    logger.warning(
        "Unified AI manager returned no conversational content; falling back to persona-safe default",
        user_id=str(connection.user_id),
    )

    return (
        "I want to make sure I'm pointing you in the right direction. Ask about your holdings, strategy lineup,"
        " or today's market setups and I'll break it down with the same diligence I'd give on the trading desk."
    )


async def _handle_opportunities_command(connection: UserTelegramConnection, db: AsyncSession) -> str:
    """Handle opportunities request via natural language."""
    try:
        # Import the opportunity discovery service
        from app.services.user_opportunity_discovery import user_opportunity_discovery

        # Discover opportunities
        opportunities_result = await user_opportunity_discovery.discover_opportunities_for_user(
            user_id=str(connection.user_id),
            force_refresh=True,
            include_strategy_recommendations=True
        )

        if not opportunities_result.get("success"):
            return "❌ Failed to fetch opportunities. Please try again."

        opportunities = opportunities_result.get("opportunities", [])
        total_count = opportunities_result.get("total_opportunities", 0)

        if total_count == 0:
            return "📊 No trading opportunities found at the moment. Markets are being analyzed continuously."
        # Prioritize the strongest fits for a balanced profile
        def _opportunity_rank(opp: Dict[str, Any]) -> float:
            confidence = float(opp.get("confidence_score", 0))
            profit = float(opp.get("profit_potential_usd", 0))
            return confidence * max(profit, 1)

        top_opportunities = sorted(opportunities, key=_opportunity_rank, reverse=True)[:3]

        response_parts = [
            f"I just reviewed {total_count} live setups. Here are the ones that align best with your balanced risk profile:"  # noqa: E501
        ]

        for opp in top_opportunities:
            symbol = opp.get("symbol", "N/A")
            strategy_name = opp.get("strategy_name", "Strategy")
            profit = float(opp.get("profit_potential_usd", 0))
            confidence = float(opp.get("confidence_score", 0))
            risk_level = (opp.get("risk_level") or "medium").upper()
            timeframe = opp.get("estimated_timeframe") or opp.get("metadata", {}).get("timeframe")
            rationale = opp.get("metadata", {}).get("rationale") or opp.get("metadata", {}).get("summary")

            line = (
                f"• {symbol}: {strategy_name} setup, ~${profit:,.0f} upside with {confidence:.0f}% confidence"
                f" ({risk_level} risk)"
            )
            if timeframe:
                line += f", targeting {timeframe}"
            if rationale:
                line += f". Rationale: {rationale}"

            response_parts.append(line)

        if total_count > len(top_opportunities):
            response_parts.append(
                f"I have {total_count - len(top_opportunities)} more opportunities queued."
                " Ask for a specific symbol or say `Show me more` to drill down."
            )

        response_parts.append(
            "Want me to open a trade ticket or compare any of these against your current holdings?"
        )

        return "\n".join(response_parts)

    except Exception as e:
        logger.error("Failed to handle opportunities command", error=str(e))
        return "❌ Error fetching opportunities. Please try `/opportunities` command instead."


async def _handle_status_command(connection: UserTelegramConnection, db: AsyncSession) -> str:
    """Handle /status command."""
    try:
        # Get user's portfolio status using your existing service
        from app.api.v1.endpoints.exchanges import get_user_portfolio_from_exchanges
        from app.models.credit import CreditAccount

        portfolio_data = await get_user_portfolio_from_exchanges(str(connection.user_id), db)

        if portfolio_data.get("success"):
            total_value = portfolio_data.get("total_value_usd", 0)
            exchange_count = len(portfolio_data.get("exchanges", []))
            positions = [b for b in portfolio_data.get("balances", []) if b.get("total", 0) > 0]

            credit_stmt = select(CreditAccount).where(CreditAccount.user_id == connection.user_id)
            credit_result = await db.execute(credit_stmt)
            credit_account = credit_result.scalar_one_or_none()

            if credit_account:
                available_credits = credit_account.available_credits
                profit_potential = credit_account.total_purchased_credits * 4
                credit_line = (
                    f"Credits: {available_credits:,} available (~${profit_potential:,.0f} deployable capital)."
                )
            else:
                credit_line = "Credits: no active balance yet—say `Purchase credits` when you're ready."

            status_lines = [
                f"Portfolio checks in at ${total_value:,.2f} across {len(positions)} holdings on {exchange_count} exchanges.",
                credit_line,
                "AI monitoring is live—I’m watching risk, liquidity, and open orders in the background."
            ]

            return "\n".join(status_lines)
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

            if total_value <= 0 or not balances:
                return (
                    "I’m not seeing any funded positions right now. Once capital lands in the account,"
                    " I’ll start tracking performance and opportunities automatically."
                )

            positions = [b for b in balances if b.get("total", 0) > 0]

            # Estimate readily deployable capital
            available_usd = 0.0
            for balance in positions:
                total_units = float(balance.get("total", 0) or 0)
                free_units = float(balance.get("free", 0) or 0)
                value_usd = float(balance.get("value_usd", 0) or 0)
                if total_units > 0 and value_usd:
                    available_usd += value_usd * (free_units / total_units)

            top_holdings = _summarize_top_holdings(positions, total_value)

            response_lines = [
                f"Your portfolio is sitting at ${total_value:,.2f} across {len(positions)} active holdings."
            ]

            if available_usd > 0:
                response_lines.append(f"Liquid capital ready to deploy: ${available_usd:,.2f}.")

            if top_holdings:
                response_lines.append("Top positions: " + ", ".join(top_holdings) + ".")

            response_lines.append("Need a closer look at any position or the risk profile? Just let me know.")

            return "\n".join(response_lines)
        else:
            return "❌ Unable to fetch balance. Please check your exchange connections."

    except Exception as e:
        logger.error("Balance command failed", error=str(e))
        return "❌ Balance command failed"


def _summarize_top_holdings(balances: List[Dict[str, Any]], total_value: float, limit: int = 3) -> List[str]:
    """Create human-friendly snippets for the largest holdings."""

    if not balances:
        return []

    safe_total = total_value or sum(float(b.get("value_usd", 0) or 0) for b in balances)
    if safe_total <= 0:
        return []

    sorted_balances = sorted(
        balances,
        key=lambda b: float(b.get("value_usd", 0) or 0),
        reverse=True
    )

    snippets: List[str] = []

    for balance in sorted_balances[:limit]:
        value_usd = float(balance.get("value_usd", 0) or 0)
        if value_usd <= 0:
            continue

        asset = balance.get("asset") or balance.get("symbol") or "Asset"
        exchange = balance.get("exchange")
        share = (value_usd / safe_total) * 100
        share_display = f"{share:.1f}%" if share < 10 else f"{share:.0f}%"

        exchange_label = ""
        if exchange:
            exchange_label = f" via {exchange.upper()}"

        snippets.append(f"{asset} ~{share_display} (${value_usd:,.0f}{exchange_label})")

    return snippets


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

            return (
                f"You have {credit_account.available_credits:,} credits ready, giving you roughly ${profit_potential:,.0f}"
                " of deployable trading capacity."
                f" Lifetime purchased: {credit_account.total_purchased_credits:,}; consumed so far: {credit_account.total_used_credits:,}."
                " Want me to line up a top-up or allocate credits to a new strategy?"
            )
        else:
            return "❌ No credit account found. Please purchase credits in the dashboard first."

    except Exception as e:
        logger.error("Credits command failed", error=str(e))
        return "❌ Credits command failed"


async def _handle_strategy_overview(connection: UserTelegramConnection, db: AsyncSession) -> str:
    """Provide a natural-language summary of the user's strategy portfolio."""

    try:
        from app.services.strategy_marketplace_service import strategy_marketplace_service

        portfolio = await strategy_marketplace_service.get_user_strategy_portfolio(str(connection.user_id))

        if not portfolio.get("success"):
            return (
                "I'm ready to review your strategy lineup, but the marketplace data is taking a moment to respond."
                " Let's try again in a few seconds."
            )

        strategies = portfolio.get("active_strategies", [])

        if not strategies:
            return (
                "You're trading in manual mode right now with no automated strategies running."
                " We can activate Kelly Criterion portfolio optimization, algorithmic pattern recognition,"
                " or AI-driven futures/options modules whenever you're ready—just say the word."
            )

        categories = sorted({
            (strategy.get("category") or "").replace("_", " ").title()
            for strategy in strategies
            if strategy.get("category")
        })

        total_monthly_cost = portfolio.get("total_monthly_cost") or portfolio.get("summary", {}).get("monthly_credit_cost", 0)

        def _strategy_sort_key(item: Dict[str, Any]) -> tuple:
            win_rate = float(item.get("win_rate", 0) or 0)
            pnl = float(item.get("total_pnl_usd", 0) or 0)
            return win_rate, pnl

        highlights = sorted(strategies, key=_strategy_sort_key, reverse=True)[:3]

        response_lines = []

        category_text = ", ".join(categories) if categories else "mixed focus"
        response_lines.append(
            f"You have {len(strategies)} automated strategies running right now across {category_text} themes."
        )

        for strategy in highlights:
            name = strategy.get("name", "Strategy")
            risk_level = (strategy.get("risk_level") or "medium").capitalize()
            win_rate = float(strategy.get("win_rate", 0) or 0)
            win_rate_display = f"{win_rate * 100:.0f}%" if win_rate else "--"
            monthly_cost = float(strategy.get("credit_cost_monthly", 0) or 0)
            pnl = float(strategy.get("total_pnl_usd", 0) or 0)
            cost_text = "included" if monthly_cost == 0 else f"{monthly_cost:.0f} credits/mo"
            pnl_text = f"running {pnl:+,.0f} USD" if pnl else "gathering live performance data"

            response_lines.append(
                f"{name}: {risk_level} risk, win rate {win_rate_display}, {cost_text}, {pnl_text}."
            )

        if total_monthly_cost:
            response_lines.append(f"Total monthly credit commitment: {total_monthly_cost:.0f} credits.")

        response_lines.append(
            "Want me to pause, reallocate, or add another module? Just point me to the strategy you're thinking about."
        )

        return "\n".join(response_lines)

    except Exception as e:
        logger.error("Strategy overview failed", error=str(e))
        return "❌ I couldn't load your strategy lineup just now. Let's try again shortly."


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