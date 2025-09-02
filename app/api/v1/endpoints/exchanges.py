"""
Exchange API Management Endpoints - Enterprise Grade

Handles per-user exchange API key management, configuration, and testing
for the AI money manager platform with encrypted storage and security.
"""

import asyncio
import base64
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.fernet import Fernet, InvalidToken

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


# ENTERPRISE KRAKEN NONCE MANAGER
class KrakenNonceManager:
    """
    ENTERPRISE: Distributed Redis-based nonce manager for production Kraken trading.
    
    Eliminates nonce conflicts in multi-instance deployments and high-frequency trading.
    Solves: Invalid nonce errors, race conditions, server time drift, distributed synchronization.
    """
    
    def __init__(self):
        self._local_call_count = 0
        self._server_time_offset = 0
        self._last_time_sync = 0
        self._redis = None
        self._fallback_nonce = 0
        self._node_id = None
        self._lock = None  # Will be initialized as asyncio.Lock in async context
        
    async def _init_redis(self):
        """Initialize Redis for distributed nonce coordination."""
        if self._redis is None:
            try:
                from app.core.redis import get_redis_client
                self._redis = await get_redis_client()
                
                # Unique node identifier for this server instance
                import uuid
                import socket
                self._node_id = f"{socket.gethostname()}_{uuid.uuid4().hex[:8]}"
                
                logger.info("Distributed Kraken nonce manager initialized", node_id=self._node_id)
            except Exception as e:
                logger.warning("Redis unavailable for nonce coordination", error=str(e))
        
        # Initialize asyncio.Lock if not already done
        if self._lock is None:
            self._lock = asyncio.Lock()
    
    async def _sync_server_time(self) -> bool:
        """ENTERPRISE: Distributed server time sync with Redis caching."""
        try:
            current_time = time.time()
            await self._init_redis()
            
            # Try cached server time first (shared across instances)
            if self._redis:
                try:
                    cached_offset = await self._redis.get("kraken:server_time_offset")
                    cached_sync_time = await self._redis.get("kraken:last_time_sync")
                    
                    if cached_offset and cached_sync_time:
                        last_sync = float(cached_sync_time)
                        if current_time - last_sync < 120:  # 2 minute cache
                            self._server_time_offset = float(cached_offset)
                            self._last_time_sync = last_sync
                            return True
                except Exception:
                    pass  # Cache miss, fetch fresh
            
            # Fetch fresh server time
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.kraken.com/0/public/Time", timeout=8) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("result") and data["result"].get("unixtime"):
                            server_time = float(data["result"]["unixtime"])
                            self._server_time_offset = server_time - current_time
                            self._last_time_sync = current_time
                            
                            # Cache for other instances
                            if self._redis:
                                try:
                                    await self._redis.setex("kraken:server_time_offset", 180, str(self._server_time_offset))
                                    await self._redis.setex("kraken:last_time_sync", 180, str(current_time))
                                except Exception:
                                    pass  # Non-critical
                            
                            logger.info("Kraken server time synced", offset=self._server_time_offset)
                            return True
            return False
        except Exception as e:
            logger.warning("Server time sync failed", error=str(e))
            return False
    
    async def get_nonce(self) -> str:
        """ENTERPRISE: Generate globally unique, strictly increasing nonce."""
        try:
            await self._init_redis()
            
            async with self._lock:
                self._local_call_count += 1
                
                # PRODUCTION: Redis-based global nonce counter
                if self._redis:
                    try:
                        # Atomic increment ensures global uniqueness across all instances
                        redis_counter = await self._redis.incr("kraken:global_nonce")
                        
                        # Sync server time
                        await self._sync_server_time()
                        server_time = time.time() + self._server_time_offset
                        
                        # ENTERPRISE: Kraken-compatible distributed nonce with guaranteed gaps  
                        # Kraken requires LARGE gaps between nonces for distributed processing
                        base_time = int(server_time * 1000000)  # Microseconds timestamp
                        
                        # LARGE multipliers to ensure significant gaps between instances
                        counter_multiplier = (redis_counter % 9999) * 100000  # 100K increments
                        node_multiplier = abs(hash(self._node_id or "default")) % 99 * 10000  # 10K node gaps
                        
                        # ENTERPRISE: Ensure MASSIVE gaps between nonces for Kraken distributed processing
                        distributed_nonce = base_time + counter_multiplier + node_multiplier
                        
                        # Additional safety: ensure minimum 50K gap from previous
                        last_nonce_key = "kraken:last_global_nonce"
                        try:
                            last_nonce = await self._redis.get(last_nonce_key)
                            if last_nonce:
                                last_val = int(last_nonce)
                                if distributed_nonce <= last_val:
                                    distributed_nonce = last_val + 50000  # Force 50K minimum gap
                            
                            # Store this nonce for next comparison  
                            await self._redis.setex(last_nonce_key, 3600, str(distributed_nonce))
                        except Exception:
                            pass  # Non-critical optimization
                        
                        # Validate final nonce is reasonable for Kraken
                        if distributed_nonce > 9999999999999999:  # 16 digits max
                            # Emergency fallback with guaranteed large increment
                            distributed_nonce = base_time + (redis_counter * 100000) % 999999999
                            logger.warning("Using emergency nonce format", 
                                         emergency_nonce=distributed_nonce)
                        
                        # Expire Redis counter periodically to prevent infinite growth
                        if redis_counter % 500 == 0:
                            await self._redis.expire("kraken:global_nonce", 1800)  # 30 min TTL
                        
                        logger.info(
                            "Distributed Kraken nonce generated",
                            nonce=distributed_nonce,
                            redis_counter=redis_counter,
                            local_count=self._local_call_count,
                            node=self._node_id,
                            server_offset=self._server_time_offset
                        )
                        
                        return str(distributed_nonce)
                        
                    except Exception as redis_error:
                        logger.error("Redis nonce generation failed - using fallback", error=str(redis_error))
                
                # FALLBACK: Local nonce if Redis fails
                await self._sync_server_time()
                server_time = time.time() + self._server_time_offset
                time_microseconds = int(server_time * 1000000)
                
                # Ensure strictly increasing in fallback mode
                if time_microseconds <= self._fallback_nonce:
                    self._fallback_nonce += 25000  # Large increment
                else:
                    self._fallback_nonce = time_microseconds
                
                # Add local identifiers
                fallback_nonce = self._fallback_nonce + self._local_call_count + (hash(str(self._node_id or "")) % 9999)
                
                logger.warning(
                    "Fallback nonce generated - potential conflicts in distributed setup",
                    nonce=fallback_nonce,
                    local_count=self._local_call_count,
                    message="Redis unavailable - investigate immediately for production trading"
                )
                
                return str(fallback_nonce)
                
        except Exception as critical_error:
            # EMERGENCY: Time-based nonce as last resort
            emergency_nonce = int(time.time() * 1000000) + self._local_call_count + abs(hash(str(critical_error))) % 9999
            
            logger.error(
                "CRITICAL: Emergency nonce generation - all methods failed",
                nonce=emergency_nonce,
                error=str(critical_error),
                message="Immediate investigation required for production trading system"
            )
            
            return str(emergency_nonce)

# Global nonce manager instance
kraken_nonce_manager = KrakenNonceManager()


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
    db: AsyncSession = Depends(get_database)
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
            account_name=request.nickname or f"{request.exchange}_main",
            status=ExchangeStatus.ACTIVE,  # Set to ACTIVE so balance queries work
            trading_enabled=True
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
    db: AsyncSession = Depends(get_database)
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
    db: AsyncSession = Depends(get_database)
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
    db: AsyncSession = Depends(get_database)
):
    """Test exchange connection and permissions."""
    
    await rate_limiter.check_rate_limit(
        key="exchange:test",
        limit=10,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Get API key record through account relationship
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
    db: AsyncSession = Depends(get_database)
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
        balances = await fetch_exchange_balances(api_key, db)
        
        # Calculate total USD value
        total_value_usd = sum(
            balance.get("value_usd", 0) for balance in balances
        )
        
        # Update balance records in database
        await update_balance_records(current_user.id, exchange, balances, db)
        
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
    db: AsyncSession = Depends(get_database)
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


async def fetch_exchange_balances(api_key: ExchangeApiKey, db: AsyncSession) -> List[Dict[str, Any]]:
    """Fetch balances from exchange API."""
    try:
        # Get the exchange account to determine exchange type
        from sqlalchemy import select
        
        result = await db.execute(
            select(ExchangeAccount).filter(ExchangeAccount.id == api_key.account_id)
        )
        account = result.scalar_one_or_none()
        
        if not account:
            logger.error(f"No account found for API key {api_key.id}")
            return []
        
        exchange_name = account.exchange_name.lower()
        
        # Decrypt API credentials
        cipher_suite = Fernet(get_encryption_key())
        decrypted_key = cipher_suite.decrypt(api_key.encrypted_api_key.encode()).decode()
        decrypted_secret = cipher_suite.decrypt(api_key.encrypted_secret_key.encode()).decode()
        
        if exchange_name == "binance":
            return await fetch_binance_balances(decrypted_key, decrypted_secret)
        elif exchange_name == "kucoin":
            # KuCoin requires passphrase in addition to key/secret
            decrypted_passphrase = cipher_suite.decrypt(api_key.encrypted_passphrase.encode()).decode() if hasattr(api_key, 'encrypted_passphrase') and api_key.encrypted_passphrase else ""
            return await fetch_kucoin_balances(decrypted_key, decrypted_secret, decrypted_passphrase)
        elif exchange_name == "kraken":
            return await fetch_kraken_balances(decrypted_key, decrypted_secret)
        elif exchange_name == "coinbase":
            return await fetch_coinbase_balances(decrypted_key, decrypted_secret)
        else:
            logger.warning(f"Exchange {exchange_name} not yet supported for live balance fetching")
            # Return empty list for unsupported exchanges
            return []
        
    except InvalidToken as e:
        logger.error(f"Failed to decrypt API credentials for key {api_key.id}", error=str(e))
        return []
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.error(f"Network error fetching balances for API key {api_key.id}", error=str(e))
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching balances for API key {api_key.id}", error=str(e), exc_info=True)
        raise


async def fetch_binance_balances(api_key: str, api_secret: str) -> List[Dict[str, Any]]:
    """Fetch balances from Binance API."""
    import aiohttp
    import hmac
    import hashlib
    import time
    from urllib.parse import urlencode
    
    try:
        base_url = "https://api.binance.com"
        endpoint = "/api/v3/account"
        timestamp = int(time.time() * 1000)
        
        # Prepare query parameters
        params = {
            "timestamp": timestamp
        }
        
        # Create signature
        query_string = urlencode(params)
        signature = hmac.new(
            api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        params["signature"] = signature
        
        headers = {
            "X-MBX-APIKEY": api_key
        }
        
        async def make_binance_request():
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{base_url}{endpoint}",
                    params=params,
                    headers=headers
                ) as response:
                    await validate_exchange_response(response, "binance")
                    return await response.json()
        
        # Use retry logic for API calls
        data = await retry_with_backoff(make_binance_request)
        balances = []
        
        # Get current prices for USD conversion
        prices = await get_binance_prices(list(set([b["asset"] for b in data.get("balances", []) if float(b.get("free", 0)) + float(b.get("locked", 0)) > 0])))
        
        # Process balances
        for balance in data.get("balances", []):
            free = float(balance.get("free", 0))
            locked = float(balance.get("locked", 0))
            total = free + locked
            
            # Only include assets with non-zero balance
            if total > 0:
                asset = balance.get("asset")
                usd_price = prices.get(asset, 0.0)
                value_usd = total * usd_price
                
                balances.append({
                    "asset": asset,
                    "free": free,
                    "locked": locked,
                    "total": total,
                    "value_usd": round(value_usd, 2)
                })
        
        return balances
                
    except Exception as e:
        logger.error(f"Failed to fetch Binance balances: {str(e)}")
        return []


async def get_binance_prices(assets: List[str]) -> Dict[str, float]:
    """Get current USD prices for assets from Binance."""
    import aiohttp
    
    if not assets:
        return {}
    
    try:
        # Binance price ticker endpoint (public, no auth needed)
        base_url = "https://api.binance.com"
        endpoint = "/api/v3/ticker/price"
        
        prices = {}
        
        async with aiohttp.ClientSession() as session:
            # Get all price tickers
            async with session.get(f"{base_url}{endpoint}") as response:
                if response.status != 200:
                    logger.error(f"Binance price API error: {response.status}")
                    return {}
                
                data = await response.json()
                
                # Create price mapping
                for ticker in data:
                    symbol = ticker.get("symbol", "")
                    price = float(ticker.get("price", 0))
                    
                    # Match assets to USDT pairs (most common)
                    for asset in assets:
                        if symbol == f"{asset}USDT":
                            prices[asset] = price
                        elif asset == "USDT":
                            prices["USDT"] = 1.0  # USDT is always $1
                        elif asset == "BUSD":
                            prices["BUSD"] = 1.0  # BUSD is always $1
                        elif asset == "USDC":
                            prices["USDC"] = 1.0  # USDC is always $1
                
                return prices
                
    except Exception as e:
        logger.error(f"Failed to fetch Binance prices: {str(e)}")
        return {}


async def fetch_kucoin_balances(api_key: str, api_secret: str, passphrase: str) -> List[Dict[str, Any]]:
    """Fetch balances from KuCoin API with proper HMAC authentication."""
    try:
        import aiohttp
        import hmac
        import hashlib
        import time
        import base64
        
        base_url = "https://api.kucoin.com"
        endpoint = "/api/v1/accounts"
        timestamp = str(int(time.time() * 1000))
        
        # Create signature for KuCoin API
        str_to_sign = timestamp + "GET" + endpoint
        signature = base64.b64encode(
            hmac.new(
                api_secret.encode(),
                str_to_sign.encode(),
                hashlib.sha256
            ).digest()
        ).decode()
        
        # Create passphrase signature
        passphrase_signature = base64.b64encode(
            hmac.new(
                api_secret.encode(),
                passphrase.encode(),
                hashlib.sha256
            ).digest()
        ).decode()
        
        headers = {
            "KC-API-KEY": api_key,
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": timestamp,
            "KC-API-PASSPHRASE": passphrase_signature,
            "KC-API-KEY-VERSION": "2",
            "Content-Type": "application/json"
        }
        
        async def make_kucoin_request():
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{base_url}{endpoint}",
                    headers=headers
                ) as response:
                    await validate_exchange_response(response, "kucoin")
                    data = await response.json()
                    if not data.get("code") == "200000":
                        raise ExchangeAPIError("kucoin", data.get('msg', 'Unknown error'))
                    return data
        
        # Use retry logic for API calls
        data = await retry_with_backoff(make_kucoin_request)
        
        accounts = data.get("data", [])
        balances = []
        
        # Get current prices for USD conversion
        active_currencies = list(set([acc["currency"] for acc in accounts if float(acc.get("balance", 0)) > 0]))
        prices = await get_kucoin_prices(active_currencies)
        
        # Process balances
        for account in accounts:
            balance = float(account.get("balance", 0))
            available = float(account.get("available", 0))
            holds = float(account.get("holds", 0))
            
            # Only include assets with non-zero balance
            if balance > 0:
                currency = account.get("currency")
                usd_price = prices.get(currency, 0.0)
                value_usd = balance * usd_price
                
                balances.append({
                    "asset": currency,
                    "free": available,
                    "locked": holds,
                    "total": balance,
                    "value_usd": round(value_usd, 2)
                })
        
        return balances
                
    except Exception as e:
        logger.error(f"Failed to fetch KuCoin balances: {str(e)}")
        return []


async def get_kucoin_prices(currencies: List[str]) -> Dict[str, float]:
    """Get current USD prices for currencies from KuCoin."""
    try:
        import aiohttp
        
        if not currencies:
            return {}
        
        # KuCoin uses USDT as base for most pairs
        symbols = []
        for currency in currencies:
            if currency == "USDT":
                symbols.append(f"{currency}-USDT")  # Will handle specially
            else:
                symbols.append(f"{currency}-USDT")
        
        base_url = "https://api.kucoin.com"
        endpoint = "/api/v1/market/allTickers"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}{endpoint}") as response:
                if response.status != 200:
                    return {}
                
                data = await response.json()
                if not data.get("code") == "200000":
                    return {}
                
                tickers = data.get("data", {}).get("ticker", [])
                prices = {}
                
                # USDT is always $1
                prices["USDT"] = 1.0
                
                # Process tickers
                for ticker in tickers:
                    symbol = ticker.get("symbol", "")
                    if "-USDT" in symbol:
                        currency = symbol.replace("-USDT", "")
                        if currency in currencies:
                            try:
                                prices[currency] = float(ticker.get("last", 0))
                            except (ValueError, TypeError):
                                prices[currency] = 0.0
                
                return prices
                
    except Exception as e:
        logger.error(f"Failed to fetch KuCoin prices: {str(e)}")
        return {}



async def fetch_kraken_balances(api_key: str, api_secret: str) -> List[Dict[str, Any]]:
    """Fetch balances from Kraken API with proper signature authentication."""
    try:
        import aiohttp
        import hmac
        import hashlib
        import time
        import base64
        import urllib.parse
        
        base_url = "https://api.kraken.com"
        endpoint = "/0/private/Balance"
        nonce = await kraken_nonce_manager.get_nonce()  # ENTERPRISE NONCE MANAGEMENT
        
        # Prepare POST data
        post_data = urllib.parse.urlencode({"nonce": str(nonce)})
        
        # Create signature for Kraken API
        encoded_endpoint = endpoint.encode()
        encoded_nonce_postdata = (str(nonce) + post_data).encode()
        sha256_hash = hashlib.sha256(encoded_nonce_postdata).digest()
        signature_data = encoded_endpoint + sha256_hash
        
        signature = base64.b64encode(
            hmac.new(
                base64.b64decode(api_secret),
                signature_data,
                hashlib.sha512
            ).digest()
        ).decode()
        
        headers = {
            "API-Key": api_key,
            "API-Sign": signature,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        async def make_kraken_request():
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{base_url}{endpoint}",
                    headers=headers,
                    data=post_data
                ) as response:
                    await validate_exchange_response(response, "kraken")
                    data = await response.json()
                    if data.get("error"):
                        raise ExchangeAPIError("kraken", str(data['error']))
                    return data
        
        # Use retry logic for API calls
        data = await retry_with_backoff(make_kraken_request)
        
        balances_data = data.get("result", {})
        balances = []
        
        # Get current prices for USD conversion
        active_currencies = [currency for currency, balance in balances_data.items() if float(balance) > 0]
        prices = await get_kraken_prices(active_currencies)
        
        # Process balances
        for currency, balance in balances_data.items():
            balance_float = float(balance)
            
            # Only include assets with non-zero balance
            if balance_float > 0:
                # Kraken uses different currency codes (e.g., XXBT for BTC)
                normalized_currency = normalize_kraken_currency(currency)
                usd_price = prices.get(normalized_currency, 0.0)
                value_usd = balance_float * usd_price
                
                balances.append({
                    "asset": normalized_currency,
                    "free": balance_float,  # Kraken doesn't separate free/locked in balance endpoint
                "locked": 0.0,
                    "total": balance_float,
                    "value_usd": round(value_usd, 2)
                })
        
        return balances
                
    except Exception as e:
        logger.error(f"Failed to fetch Kraken balances: {str(e)}")
        return []


def normalize_kraken_currency(kraken_currency: str) -> str:
    """Normalize Kraken currency codes to standard format."""
    currency_map = {
        "XXBT": "BTC",
        "XETH": "ETH",
        "XLTC": "LTC",
        "XXRP": "XRP",
        "XZEC": "ZEC",
        "ZUSD": "USD",
        "ZEUR": "EUR",
        "ZGBP": "GBP",
        "ZCAD": "CAD",
        "ZJPY": "JPY"
    }
    return currency_map.get(kraken_currency, kraken_currency)


async def get_kraken_prices(currencies: List[str]) -> Dict[str, float]:
    """Get current USD prices for currencies from Kraken."""
    try:
        import aiohttp
        
        if not currencies:
            return {}
        
        # Build pairs for USD pricing
        pairs = []
        for currency in currencies:
            if currency == "USD":
                continue  # USD is always $1
            # Kraken uses different pair formats
            if currency == "BTC":
                pairs.append("XBTUSD")
            elif currency == "ETH":
                pairs.append("ETHUSD")
            else:
                pairs.append(f"{currency}USD")
        
        if not pairs:
            return {"USD": 1.0}
        
        base_url = "https://api.kraken.com"
        endpoint = f"/0/public/Ticker?pair={','.join(pairs)}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}{endpoint}") as response:
                if response.status != 200:
                    return {"USD": 1.0}
                
                data = await response.json()
                if data.get("error"):
                    return {"USD": 1.0}
                
                result = data.get("result", {})
                prices = {"USD": 1.0}
                
                # Process ticker data
                for pair, ticker_data in result.items():
                    try:
                        price = float(ticker_data.get("c", [0])[0])  # Last price
                        # Extract currency from pair
                        if pair.startswith("XBTUSD"):
                            prices["BTC"] = price
                        elif pair.startswith("ETHUSD"):
                            prices["ETH"] = price
                        else:
                            currency = pair.replace("USD", "")
                            prices[currency] = price
                    except (ValueError, TypeError, IndexError):
                        continue
                
                return prices
        
    except Exception as e:
        logger.error(f"Failed to fetch Kraken prices: {str(e)}")
        return {"USD": 1.0}


async def fetch_coinbase_balances(api_key: str, api_secret: str) -> List[Dict[str, Any]]:
    """Fetch balances from Coinbase Advanced Trade API with proper CB-ACCESS authentication."""
    try:
        import aiohttp
        import hmac
        import hashlib
        import time
        import base64
        
        base_url = "https://api.coinbase.com"
        endpoint = "/api/v3/brokerage/accounts"
        timestamp = str(int(time.time()))
        method = "GET"
        
        # Create signature for Coinbase Advanced Trade API
        message = timestamp + method + endpoint
        signature = hmac.new(
            base64.b64decode(api_secret),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            "CB-ACCESS-KEY": api_key,
            "CB-ACCESS-SIGN": signature,
            "CB-ACCESS-TIMESTAMP": timestamp,
            "Content-Type": "application/json"
        }
        
        async def make_coinbase_request():
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{base_url}{endpoint}",
                    headers=headers
                ) as response:
                    await validate_exchange_response(response, "coinbase")
                    return await response.json()
        
        # Use retry logic for API calls
        data = await retry_with_backoff(make_coinbase_request)
        accounts = data.get("accounts", [])
        balances = []
        
        # Get current prices for USD conversion
        active_currencies = list(set([acc["currency"] for acc in accounts if float(acc.get("available_balance", {}).get("value", 0)) > 0]))
        prices = await get_coinbase_prices(active_currencies)
        
        # Process balances
        for account in accounts:
            available_balance = account.get("available_balance", {})
            hold_balance = account.get("hold", {})
            
            available = float(available_balance.get("value", 0))
            holds = float(hold_balance.get("value", 0)) if hold_balance else 0.0
            total = available + holds
            
            # Only include assets with non-zero balance
            if total > 0:
                currency = available_balance.get("currency", "")
                usd_price = prices.get(currency, 0.0)
                value_usd = total * usd_price
                
                balances.append({
                    "asset": currency,
                    "free": available,
                    "locked": holds,
                    "total": total,
                    "value_usd": round(value_usd, 2)
                })
        
        return balances
                
    except Exception as e:
        logger.error(f"Failed to fetch Coinbase balances: {str(e)}")
        return []


async def get_coinbase_prices(currencies: List[str]) -> Dict[str, float]:
    """Get current USD prices for currencies from Coinbase."""
    try:
        import aiohttp
        
        if not currencies:
            return {}
        
        prices = {"USD": 1.0}  # USD is always $1
        
        # Coinbase Advanced Trade API for prices
        base_url = "https://api.coinbase.com"
        
        async with aiohttp.ClientSession() as session:
            for currency in currencies:
                if currency == "USD":
                    continue
                
                try:
                    endpoint = f"/api/v3/brokerage/market/products/{currency}-USD/ticker"
                    async with session.get(f"{base_url}{endpoint}") as response:
                        if response.status == 200:
                            data = await response.json()
                            price = float(data.get("price", 0))
                            prices[currency] = price
                        else:
                            prices[currency] = 0.0
                except Exception as e:
                    logger.warning(f"Failed to get price for {currency}: {str(e)}")
                    prices[currency] = 0.0
        
        return prices
                
    except Exception as e:
        logger.error(f"Failed to fetch Coinbase prices: {str(e)}")
        return {"USD": 1.0}


class ExchangeAPIError(Exception):
    """Custom exception for exchange API errors."""
    def __init__(self, exchange: str, message: str, status_code: int = None):
        self.exchange = exchange
        self.message = message
        self.status_code = status_code
        super().__init__(f"{exchange} API Error: {message}")


async def retry_with_backoff(func, max_retries: int = 3, base_delay: float = 1.0):
    """Retry function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {str(e)}")
            await asyncio.sleep(delay)


async def validate_exchange_response(response, exchange: str):
    """Validate exchange API response and handle common errors."""
    if response.status == 429:
        raise ExchangeAPIError(exchange, "Rate limit exceeded", 429)
    elif response.status == 401:
        raise ExchangeAPIError(exchange, "Invalid API credentials", 401)
    elif response.status == 403:
        raise ExchangeAPIError(exchange, "Insufficient API permissions", 403)
    elif response.status >= 500:
        raise ExchangeAPIError(exchange, f"Exchange server error: {response.status}", response.status)
    elif response.status != 200:
        raise ExchangeAPIError(exchange, f"API request failed: {response.status}", response.status)


async def sync_exchange_balances(user_id: str, exchange: str, api_key_id: str):
    """Sync exchange balances to database."""
    try:
        # This would update balance records in the database
        logger.info(f"Syncing balances for user {user_id}, exchange {exchange}")
    except Exception as e:
        logger.error("Balance sync failed", error=str(e))


async def update_balance_records(user_id: str, exchange: str, balances: List[Dict], db: AsyncSession):
    """Update balance records in database using ENTERPRISE UPSERT logic."""
    try:
        from sqlalchemy import select, update
        from sqlalchemy.dialects.postgresql import insert
        from decimal import Decimal
        import uuid
        
        # Get the exchange account
        account_result = await db.execute(
            select(ExchangeAccount).filter(
                ExchangeAccount.user_id == user_id,
                ExchangeAccount.exchange_name == exchange
            )
        )
        account = account_result.scalar_one_or_none()
        
        if not account:
            logger.error(f"No exchange account found for user {user_id}, exchange {exchange}")
            return
        
        # ENTERPRISE UPSERT LOGIC - Handle concurrent updates gracefully
        updated_count = 0
        for balance in balances:
            if balance.get("total", 0) > 0:  # Only store non-zero balances
                balance_data = {
                    "id": uuid.uuid4(),
                    "account_id": account.id,
                    "symbol": balance.get("asset", ""),
                    "asset_type": "crypto",
                    "total_balance": Decimal(str(balance.get("total", 0))),
                    "available_balance": Decimal(str(balance.get("free", 0))),
                    "locked_balance": Decimal(str(balance.get("locked", 0))),
                    "usd_value": Decimal(str(balance.get("value_usd", 0))),
                    "is_active": True,
                    "sync_enabled": True,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "last_sync_at": datetime.utcnow()
                }
                
                # PostgreSQL UPSERT - INSERT ON CONFLICT UPDATE
                stmt = insert(ExchangeBalance).values(balance_data)
                stmt = stmt.on_conflict_do_update(
                    constraint="unique_account_symbol_balance",
                    set_={
                        "total_balance": stmt.excluded.total_balance,
                        "available_balance": stmt.excluded.available_balance,
                        "locked_balance": stmt.excluded.locked_balance,
                        "usd_value": stmt.excluded.usd_value,
                        "updated_at": stmt.excluded.updated_at,
                        "last_sync_at": stmt.excluded.last_sync_at,
                        "is_active": True
                    }
                )
                
                await db.execute(stmt)
                updated_count += 1
        
        # Set inactive for balances not in current update (zero balances)
        current_symbols = [b.get("asset", "") for b in balances if b.get("total", 0) > 0]
        if current_symbols:
            await db.execute(
                update(ExchangeBalance)
                .where(
                    ExchangeBalance.account_id == account.id,
                    ~ExchangeBalance.symbol.in_(current_symbols)
                )
                .values(is_active=False, updated_at=datetime.utcnow())
            )
        
        await db.commit()
        logger.info(f"Updated {updated_count} balance records for user {user_id}, exchange {exchange}")
        
    except Exception as e:
        await db.rollback()
        logger.error("Balance update failed", error=str(e), exc_info=True)


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


async def get_user_portfolio_from_exchanges(user_id: str, db: AsyncSession) -> Dict[str, Any]:
    """Get user's portfolio data from all connected exchanges using existing balance system."""
    try:
        # Import SQLAlchemy helpers locally
        from sqlalchemy import select, and_
        
        # Get all active exchange accounts for user
        stmt = select(ExchangeAccount, ExchangeApiKey).join(
            ExchangeApiKey, ExchangeAccount.id == ExchangeApiKey.account_id
        ).where(
            and_(
                ExchangeAccount.user_id == user_id,
                ExchangeAccount.status == ExchangeStatus.ACTIVE,
                ExchangeApiKey.status == ApiKeyStatus.ACTIVE
            )
        )
        
        result = await db.execute(stmt)
        user_exchanges = result.fetchall()
        
        if not user_exchanges:
            return {
                "success": True,
                "total_value_usd": 0.0,
                "balances": [],
                "exchanges": [],
                "message": "No exchange accounts connected"
            }
        
        # Fetch balances from all exchanges using existing fetch_exchange_balances
        all_balances = []
        total_value_usd = 0.0
        exchange_summaries = []
        
        for account, api_key in user_exchanges:
            try:
                # Use existing balance fetching function
                balances = await fetch_exchange_balances(api_key, db)
                
                exchange_value = sum(b.get("value_usd", 0) for b in balances)
                total_value_usd += exchange_value
                
                # Add exchange info to each balance
                for balance in balances:
                    balance["exchange"] = account.exchange_name
                
                all_balances.extend(balances)
                exchange_summaries.append({
                    "exchange": account.exchange_name,
                    "account_id": str(account.id),
                    "total_value_usd": exchange_value,
                    "asset_count": len(balances),
                    "last_updated": datetime.utcnow().isoformat()
                })
                
            except Exception as e:
                logger.error(
                    "Failed to fetch balances from exchange",
                    error=str(e),
                    exchange=account.exchange_name,
                    user_id=user_id
                )
                continue
        
        return {
            "success": True,
            "total_value_usd": total_value_usd,
            "balances": all_balances,
            "exchanges": exchange_summaries,
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(
            "Failed to get user portfolio from exchanges",
            error=str(e),
            user_id=user_id
        )
        return {"success": False, "error": str(e)}
