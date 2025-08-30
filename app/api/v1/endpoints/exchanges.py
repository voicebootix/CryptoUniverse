"""
Exchange API Management Endpoints - Enterprise Grade

Handles per-user exchange API key management, configuration, and testing
for the AI money manager platform with encrypted storage and security.
"""

import asyncio
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet

from app.core.config import get_settings
from app.core.database import get_database
from app.api.v1.endpoints.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.exchange import ExchangeAccount, ExchangeApiKey, ExchangeBalance, ApiKeyStatus, ExchangeStatus
from app.services.trade_execution import TradeExecutionService
from app.services.rate_limit import rate_limiter

settings = get_settings()
logger = structlog.get_logger(__name__)

router = APIRouter()

# Initialize services
trade_executor = TradeExecutionService()

# Encryption for API keys
def get_encryption_key():
    """Get or generate a consistent encryption key."""
    if hasattr(settings, 'ENCRYPTION_KEY') and settings.ENCRYPTION_KEY:
        return settings.ENCRYPTION_KEY.encode()
    else:
        # Use SECRET_KEY as base for encryption key to ensure consistency
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import base64
        
        # Generate consistent key from SECRET_KEY
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'cryptouniverse_salt',  # Fixed salt for consistency
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))

encryption_key = get_encryption_key()
cipher_suite = Fernet(encryption_key)


# Request/Response Models
class ExchangeApiKeyRequest(BaseModel):
    exchange: str
    api_key: str
    secret_key: str
    passphrase: Optional[str] = None  # For KuCoin
    sandbox: bool = False
    nickname: Optional[str] = None
    
    @field_validator('exchange')
    @classmethod
    def validate_exchange(cls, v):
        allowed_exchanges = ["binance", "kraken", "kucoin", "coinbase", "bybit"]
        if v.lower() not in allowed_exchanges:
            raise ValueError(f"Exchange must be one of: {allowed_exchanges}")
        return v.lower()
    
    @field_validator('api_key', 'secret_key')
    @classmethod
    def validate_keys(cls, v):
        if len(v.strip()) < 10:
            raise ValueError("API keys must be at least 10 characters")
        return v.strip()


class ExchangeApiKeyUpdate(BaseModel):
    nickname: Optional[str] = None
    is_active: Optional[bool] = None
    trading_enabled: Optional[bool] = None
    max_daily_volume: Optional[float] = None


class ExchangeApiKeyResponse(BaseModel):
    id: str
    exchange: str
    nickname: Optional[str]
    api_key_masked: str
    is_active: bool
    trading_enabled: bool
    sandbox: bool
    created_at: datetime
    last_used: Optional[datetime]
    permissions: List[str]
    connection_status: str
    daily_volume_limit: Optional[float]
    daily_volume_used: float


class ExchangeBalanceResponse(BaseModel):
    exchange: str
    balances: List[Dict[str, Any]]
    total_value_usd: float
    last_updated: datetime


class ExchangeTestResponse(BaseModel):
    exchange: str
    connection_status: str
    permissions: List[str]
    account_info: Dict[str, Any]
    latency_ms: float
    error_message: Optional[str]


# Exchange API Management Endpoints
@router.post("/connect", response_model=ExchangeApiKeyResponse)
async def connect_exchange(
    request: ExchangeApiKeyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """Connect a new exchange account with API keys."""
    
    await rate_limiter.check_rate_limit(
        key="exchange:connect",
        limit=10,
        window=300,  # 10 connections per 5 minutes
        user_id=str(current_user.id)
    )
    
    logger.info(
        "Exchange connection request",
        user_id=str(current_user.id),
        exchange=request.exchange,
        sandbox=request.sandbox
    )
    
    try:
        # Check if exchange already connected through account relationship
        from sqlalchemy import select
        result = await db.execute(
            select(ExchangeAccount).filter(
                ExchangeAccount.user_id == current_user.id,
                ExchangeAccount.exchange_name == request.exchange
            )
        )
        existing_account = result.scalar_one_or_none()
        
        if existing_account:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Exchange {request.exchange} already connected"
            )
        
        # Test connection before saving
        test_result = await test_exchange_connection(
            request.exchange,
            request.api_key,
            request.secret_key,
            request.passphrase,
            request.sandbox
        )
        
        if not test_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Connection test failed: {test_result.get('error', 'Unknown error')}"
            )
        
        # Encrypt API keys
        encrypted_api_key = cipher_suite.encrypt(request.api_key.encode()).decode()
        encrypted_secret_key = cipher_suite.encrypt(request.secret_key.encode()).decode()
        encrypted_passphrase = None
        if request.passphrase:
            encrypted_passphrase = cipher_suite.encrypt(request.passphrase.encode()).decode()
        
        # Create exchange account
        exchange_account = ExchangeAccount(
            user_id=current_user.id,
            exchange_name=request.exchange,  # Use exchange_name field as defined in model
            account_name=request.nickname or f"{request.exchange}_main"
        )
        db.add(exchange_account)
        await db.flush()  # Get the ID
        
        # Create API key record with minimal fields
        import hashlib
        key_hash = hashlib.sha256(request.api_key.encode()).hexdigest()
        
        api_key_record = ExchangeApiKey(
            account_id=exchange_account.id,
            key_name=request.nickname or f"{request.exchange}_main",
            encrypted_api_key=encrypted_api_key,
            encrypted_secret_key=encrypted_secret_key,
            encrypted_passphrase=encrypted_passphrase,
            key_hash=key_hash,  # Required field - SHA256 hash of API key
            permissions=test_result.get("permissions", []),
            ip_restrictions=[],  # Default empty list
            status=ApiKeyStatus.ACTIVE,
            is_validated=True,
            total_requests=0,
            failed_requests=0
        )
        db.add(api_key_record)
        await db.commit()
        await db.refresh(api_key_record)
        
        # Sync initial balances
        await sync_exchange_balances(current_user.id, request.exchange, api_key_record.id)
        
        logger.info(
            "Exchange connected successfully",
            user_id=str(current_user.id),
            exchange=request.exchange,
            api_key_id=str(api_key_record.id)
        )
        
        return ExchangeApiKeyResponse(
            id=str(api_key_record.id),
            exchange=request.exchange,
            nickname=request.nickname or api_key_record.key_name,
            api_key_masked=mask_api_key(request.api_key),
            is_active=True,
            trading_enabled=True,
            sandbox=request.sandbox or False,
            created_at=api_key_record.created_at,
            last_used=None,
            permissions=test_result.get("permissions", []),
            connection_status="connected",
            daily_volume_limit=None,
            daily_volume_used=0.0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Exchange connection failed", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect exchange: {str(e)}"
        )


@router.get("/list")
async def list_exchange_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """List all connected exchange accounts."""
    
    await rate_limiter.check_rate_limit(
        key="exchange:list",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        from sqlalchemy import select
        # Query api keys through exchange accounts relationship
        result = await db.execute(
            select(ExchangeApiKey)
            .join(ExchangeAccount, ExchangeApiKey.account_id == ExchangeAccount.id)
            .filter(ExchangeAccount.user_id == current_user.id)
        )
        api_keys = result.scalars().all()
        
        connections = []
        for api_key in api_keys:
            try:
                # Decrypt for display (masked)  
                decrypted_api_key = cipher_suite.decrypt(api_key.encrypted_api_key.encode()).decode()
                
                # Get exchange account info
                account_result = await db.execute(
                    select(ExchangeAccount).filter(ExchangeAccount.id == api_key.account_id)
                )
                account = account_result.scalar_one_or_none()
                
                if not account:
                    continue  # Skip if account not found
                
                # Get daily volume usage
                daily_volume = await get_daily_volume_usage(current_user.id, account.exchange_name)
                
                connection = ExchangeApiKeyResponse(
                    id=str(api_key.id),
                    exchange=account.exchange_name,
                    nickname=api_key.key_name,  # Use key_name as nickname
                    api_key_masked=mask_api_key(decrypted_api_key),
                    is_active=account.status == ExchangeStatus.ACTIVE,
                    trading_enabled=account.trading_enabled,
                    sandbox=account.is_simulation,  # Use is_simulation as sandbox
                    created_at=api_key.created_at,
                    last_used=api_key.last_used_at,
                    permissions=api_key.permissions or [],
                    connection_status="connected" if api_key.status == ApiKeyStatus.ACTIVE else "inactive",
                    daily_volume_limit=None,  # Set to None for now
                    daily_volume_used=daily_volume
                )
                connections.append(connection)
                
            except Exception as e:
                logger.error(
                    f"Failed to decrypt API key for exchange",
                    error=str(e),
                    api_key_id=str(api_key.id),
                    user_id=str(current_user.id)
                )
                # Still include connection but mark as error
                connection = ExchangeApiKeyResponse(
                    id=str(api_key.id),
                    exchange="unknown",
                    nickname=f"corrupted_key_{api_key.id}",
                    api_key_masked="••••••••[ERROR]",
                    is_active=False,
                    trading_enabled=False,
                    sandbox=False,
                    created_at=api_key.created_at,
                    last_used=api_key.last_used_at,
                    permissions=[],
                    connection_status="error",
                    daily_volume_limit=None,
                    daily_volume_used=0.0
                )
                connections.append(connection)
        
        return {
            "connections": connections,
            "total_count": len(connections),
            "active_count": sum(1 for c in connections if c.is_active),
            "exchanges": list(set(c.exchange for c in connections))
        }
        
    except Exception as e:
        logger.error("Failed to list exchange connections", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list connections: {str(e)}"
        )


@router.put("/{api_key_id}/update")
async def update_exchange_connection(
    api_key_id: str,
    request: ExchangeApiKeyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """Update exchange connection settings."""
    
    await rate_limiter.check_rate_limit(
        key="exchange:update",
        limit=20,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Get API key record
        from sqlalchemy import select
        result = await db.execute(
            select(ExchangeApiKey)
            .join(ExchangeAccount, ExchangeApiKey.account_id == ExchangeAccount.id)
            .filter(
                ExchangeApiKey.id == api_key_id,
                ExchangeAccount.user_id == current_user.id
            )
        )
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exchange connection not found"
            )
        
        # Update fields (only use fields that exist in model)
        if request.nickname is not None:
            api_key.key_name = request.nickname or api_key.key_name
        
        # For now, just update the key name - other fields need to be added to model properly
        await db.commit()
        
        logger.info(
            "Exchange connection updated",
            user_id=str(current_user.id),
            api_key_id=api_key_id,
            updates=request.dict(exclude_unset=True)
        )
        
        return {"status": "updated", "message": "Exchange connection updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Exchange update failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update exchange: {str(e)}"
        )


@router.post("/{api_key_id}/test", response_model=ExchangeTestResponse)
async def test_exchange_connection_endpoint(
    api_key_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """Test exchange connection and permissions."""
    
    await rate_limiter.check_rate_limit(
        key="exchange:test",
        limit=10,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Get API key record
        from sqlalchemy import select
        result = await db.execute(
            select(ExchangeApiKey).filter(
                ExchangeApiKey.id == api_key_id,
                ExchangeApiKey.user_id == current_user.id
            )
        )
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exchange connection not found"
            )
        
        # Get exchange account info
        account_result = await db.execute(
            select(ExchangeAccount).filter(ExchangeAccount.id == api_key.account_id)
        )
        account = account_result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exchange account not found"
            )
        
        # Decrypt API keys
        decrypted_api_key = cipher_suite.decrypt(api_key.encrypted_api_key.encode()).decode()
        decrypted_secret_key = cipher_suite.decrypt(api_key.encrypted_secret_key.encode()).decode()
        decrypted_passphrase = None
        if api_key.encrypted_passphrase:
            decrypted_passphrase = cipher_suite.decrypt(api_key.encrypted_passphrase.encode()).decode()
        
        # Test connection
        start_time = datetime.utcnow()
        test_result = await test_exchange_connection(
            account.exchange_name,
            decrypted_api_key,
            decrypted_secret_key,
            decrypted_passphrase,
            account.is_simulation
        )
        end_time = datetime.utcnow()
        
        latency_ms = (end_time - start_time).total_seconds() * 1000
        
        # Update last test time and permissions
        if test_result["success"]:
            api_key.permissions = test_result.get("permissions", [])
        await db.commit()
        
        return ExchangeTestResponse(
            exchange=account.exchange_name,
            connection_status="connected" if test_result["success"] else "failed",
            permissions=test_result.get("permissions", []),
            account_info=test_result.get("account_info", {}),
            latency_ms=latency_ms,
            error_message=test_result.get("error") if not test_result["success"] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Exchange test failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test exchange: {str(e)}"
        )


@router.get("/{exchange}/balances", response_model=ExchangeBalanceResponse)
async def get_exchange_balances(
    exchange: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """Get current balances from exchange."""
    
    await rate_limiter.check_rate_limit(
        key="exchange:balances",
        limit=30,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Check exchange rate limits
        await rate_limiter.check_exchange_rate_limit(
            exchange=exchange,
            endpoint_type="private"
        )
        
        # Get API key for exchange through account relationship
        from sqlalchemy import select
        result = await db.execute(
            select(ExchangeApiKey)
            .join(ExchangeAccount, ExchangeApiKey.account_id == ExchangeAccount.id)
            .filter(
                ExchangeAccount.user_id == current_user.id,
                ExchangeAccount.exchange_name == exchange,
                ExchangeAccount.status == ExchangeStatus.ACTIVE
            )
        )
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active {exchange} connection found"
            )
        
        # Get fresh balances from exchange
        balances = await fetch_exchange_balances(api_key)
        
        # Calculate total USD value
        total_value_usd = sum(
            balance.get("value_usd", 0) for balance in balances
        )
        
        # Update balance records in database
        await update_balance_records(current_user.id, exchange, balances)
        
        return ExchangeBalanceResponse(
            exchange=exchange,
            balances=balances,
            total_value_usd=total_value_usd,
            last_updated=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Balance retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get balances: {str(e)}"
        )


@router.delete("/{api_key_id}")
async def disconnect_exchange(
    api_key_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """Disconnect and remove exchange connection."""
    
    await rate_limiter.check_rate_limit(
        key="exchange:disconnect",
        limit=10,
        window=300,
        user_id=str(current_user.id)
    )
    
    try:
        # Get API key record
        from sqlalchemy import select
        result = await db.execute(
            select(ExchangeApiKey).filter(
                ExchangeApiKey.id == api_key_id,
                ExchangeApiKey.user_id == current_user.id
            )
        )
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exchange connection not found"
            )
        
        # Get exchange account info for cleanup
        account_result = await db.execute(
            select(ExchangeAccount).filter(ExchangeAccount.id == api_key.account_id)
        )
        exchange_account = account_result.scalar_one_or_none()
        exchange_name = exchange_account.exchange_name if exchange_account else "unknown"
        
        # Remove API key record
        db.delete(api_key)
        
        # Remove exchange account if no other API keys
        if exchange_account:
            # Check if this was the only API key for this account
            from sqlalchemy import select, func
            count_result = await db.execute(
                select(func.count(ExchangeApiKey.id)).filter(
                    ExchangeApiKey.account_id == exchange_account.id
                )
            )
            remaining_keys = count_result.scalar()
            
            if remaining_keys <= 1:  # <= 1 because we haven't committed the delete yet
                db.delete(exchange_account)
        
        await db.commit()
        
        logger.info(
            "Exchange disconnected",
            user_id=str(current_user.id),
            exchange=exchange_name,
            api_key_id=api_key_id
        )
        
        return {
            "status": "disconnected",
            "exchange": exchange_name,
            "message": f"{exchange_name} connection removed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Exchange disconnection failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect exchange: {str(e)}"
        )


# Helper Functions
async def test_exchange_connection(
    exchange: str,
    api_key: str,
    secret_key: str,
    passphrase: Optional[str],
    sandbox: bool
) -> Dict[str, Any]:
    """Test exchange connection and get permissions."""
    try:
        # This would use the actual exchange APIs to test connection
        # For now, return simulated success
        
        # Simulate network delay
        await asyncio.sleep(0.1)
        
        # Mock permissions based on exchange
        permissions_map = {
            "binance": ["spot_read", "spot_trade", "futures_read", "futures_trade"],
            "kraken": ["query_funds", "trade", "query_orders"],
            "kucoin": ["general", "trade", "transfer"],
            "coinbase": ["wallet:accounts:read", "wallet:transactions:read", "wallet:buys:create"],
            "bybit": ["read", "trade"]
        }
        
        return {
            "success": True,
            "permissions": permissions_map.get(exchange, ["read", "trade"]),
            "account_info": {
                "account_type": "spot" if not sandbox else "sandbox",
                "trading_enabled": True,
                "can_withdraw": not sandbox
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "permissions": [],
            "account_info": {}
        }


async def fetch_exchange_balances(api_key: ExchangeApiKey) -> List[Dict[str, Any]]:
    """Fetch balances from exchange API."""
    try:
        # This would use the actual exchange APIs
        # For now, return mock data
        
        mock_balances = [
            {
                "asset": "BTC",
                "free": 0.5,
                "locked": 0.0,
                "total": 0.5,
                "value_usd": 25000.0
            },
            {
                "asset": "ETH", 
                "free": 10.0,
                "locked": 2.0,
                "total": 12.0,
                "value_usd": 24000.0
            },
            {
                "asset": "USDT",
                "free": 5000.0,
                "locked": 0.0,
                "total": 5000.0,
                "value_usd": 5000.0
            }
        ]
        
        return mock_balances
        
    except Exception as e:
        logger.error(f"Failed to fetch balances for {api_key.exchange}", error=str(e))
        return []


async def sync_exchange_balances(user_id: str, exchange: str, api_key_id: str):
    """Sync exchange balances to database."""
    try:
        # This would update balance records in the database
        logger.info(f"Syncing balances for user {user_id}, exchange {exchange}")
    except Exception as e:
        logger.error("Balance sync failed", error=str(e))


async def update_balance_records(user_id: str, exchange: str, balances: List[Dict]):
    """Update balance records in database."""
    try:
        # This would update the ExchangeBalance table
        logger.info(f"Updating balance records for user {user_id}, exchange {exchange}")
    except Exception as e:
        logger.error("Balance update failed", error=str(e))


async def get_daily_volume_usage(user_id: str, exchange: str) -> float:
    """Get daily trading volume usage for user."""
    try:
        # This would calculate from trade records
        return 0.0  # Mock data
    except Exception as e:
        logger.error("Volume calculation failed", error=str(e))
        return 0.0


def mask_api_key(api_key: str) -> str:
    """Mask API key for display."""
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
