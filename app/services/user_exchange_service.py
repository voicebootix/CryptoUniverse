"""
User Exchange Service - Enterprise Grade

Bridges the sophisticated per-user exchange management system with trade execution.
Handles user-specific API credential retrieval, exchange routing, and real-time
trading operations across multiple exchanges per user.

This service eliminates the legacy global API key model and implements
enterprise-grade per-user exchange credential management.
"""

import asyncio
import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

import aiohttp
import structlog
from cryptography.fernet import Fernet
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_database
from app.core.logging import LoggerMixin
from app.models.exchange import ExchangeAccount, ExchangeApiKey, ExchangeBalance, ExchangeStatus, ApiKeyStatus
from app.models.user import User

settings = get_settings()
logger = structlog.get_logger(__name__)


@dataclass
class UserExchangeCredentials:
    """Container for decrypted user exchange credentials."""
    exchange_name: str
    api_key: str
    secret_key: str
    passphrase: Optional[str] = None
    is_sandbox: bool = False
    account_id: str = ""
    permissions: List[str] = None


@dataclass
class ExchangeOrderParams:
    """Standardized order parameters for all exchanges."""
    symbol: str
    side: str  # BUY, SELL
    quantity: Decimal
    order_type: str = "MARKET"  # MARKET, LIMIT, STOP_LOSS
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: str = "GTC"
    reduce_only: bool = False


class UserExchangeService(LoggerMixin):
    """
    Enterprise-grade user exchange service.
    
    Manages per-user exchange credentials, routing, and execution
    with full security, audit trails, and production-ready features.
    """
    
    def __init__(self):
        self.encryption_key = self._get_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        self.exchange_clients = {}
        self.rate_limits = {}
        
    def _get_encryption_key(self) -> bytes:
        """Get consistent encryption key for API credentials."""
        if hasattr(settings, 'ENCRYPTION_KEY') and settings.ENCRYPTION_KEY:
            return settings.ENCRYPTION_KEY.encode()
        else:
            # Generate consistent key from SECRET_KEY
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'cryptouniverse_enterprise_salt',
                iterations=100000,
            )
            return base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
    
    async def get_user_exchange_credentials(
        self, 
        user_id: str, 
        exchange_name: str,
        require_trading_enabled: bool = True
    ) -> Optional[UserExchangeCredentials]:
        """
        Get decrypted exchange credentials for user.
        
        Args:
            user_id: User ID
            exchange_name: Exchange name (binance, kraken, kucoin, etc.)
            require_trading_enabled: Whether to require trading to be enabled
            
        Returns:
            UserExchangeCredentials or None if not found/not enabled
        """
        try:
            async for db in get_database():
                # Get active exchange account with API key
                stmt = select(ExchangeApiKey, ExchangeAccount).join(
                    ExchangeAccount, ExchangeApiKey.account_id == ExchangeAccount.id
                ).where(
                    and_(
                        ExchangeAccount.user_id == user_id,
                        ExchangeAccount.exchange_name == exchange_name.lower(),
                        ExchangeAccount.status == ExchangeStatus.ACTIVE,
                        ExchangeApiKey.status == ApiKeyStatus.ACTIVE,
                        ExchangeApiKey.is_validated == True
                    )
                )
                
                if require_trading_enabled:
                    stmt = stmt.where(ExchangeAccount.trading_enabled == True)
                
                result = await db.execute(stmt)
                row = result.first()
                
                if not row:
                    self.logger.warning(
                        "No active exchange credentials found",
                        user_id=user_id,
                        exchange=exchange_name,
                        require_trading=require_trading_enabled
                    )
                    return None
                
                api_key, account = row
                
                # Decrypt credentials
                decrypted_api_key = self.cipher_suite.decrypt(api_key.encrypted_api_key.encode()).decode()
                decrypted_secret_key = self.cipher_suite.decrypt(api_key.encrypted_secret_key.encode()).decode()
                decrypted_passphrase = None
                
                if api_key.encrypted_passphrase:
                    decrypted_passphrase = self.cipher_suite.decrypt(api_key.encrypted_passphrase.encode()).decode()
                
                return UserExchangeCredentials(
                    exchange_name=account.exchange_name,
                    api_key=decrypted_api_key,
                    secret_key=decrypted_secret_key,
                    passphrase=decrypted_passphrase,
                    is_sandbox=account.is_simulation,
                    account_id=str(account.id),
                    permissions=api_key.permissions or []
                )
                
        except Exception as e:
            self.logger.error(
                "Failed to get user exchange credentials",
                error=str(e),
                user_id=user_id,
                exchange=exchange_name
            )
            return None
    
    async def get_user_exchange_for_symbol(
        self, 
        user_id: str, 
        symbol: str,
        preferred_exchange: Optional[str] = None
    ) -> Optional[UserExchangeCredentials]:
        """
        Get best user exchange for trading a specific symbol.
        
        Args:
            user_id: User ID
            symbol: Trading symbol (BTC/USDT, ETH/USD, etc.)
            preferred_exchange: Preferred exchange if specified
            
        Returns:
            Best exchange credentials for the symbol
        """
        try:
            async for db in get_database():
                # Get all active user exchanges
                stmt = select(ExchangeApiKey, ExchangeAccount).join(
                    ExchangeAccount, ExchangeApiKey.account_id == ExchangeAccount.id
                ).where(
                    and_(
                        ExchangeAccount.user_id == user_id,
                        ExchangeAccount.status == ExchangeStatus.ACTIVE,
                        ExchangeAccount.trading_enabled == True,
                        ExchangeApiKey.status == ApiKeyStatus.ACTIVE,
                        ExchangeApiKey.is_validated == True
                    )
                )
                
                result = await db.execute(stmt)
                exchanges = result.fetchall()
                
                if not exchanges:
                    self.logger.warning("No active exchanges found for user", user_id=user_id)
                    return None
                
                # If preferred exchange specified, try to use it
                if preferred_exchange:
                    for api_key, account in exchanges:
                        if account.exchange_name.lower() == preferred_exchange.lower():
                            if await self._symbol_supported_on_exchange(symbol, account.exchange_name):
                                return await self._create_credentials_object(api_key, account)
                
                # Otherwise, find best exchange for symbol
                for api_key, account in exchanges:
                    if await self._symbol_supported_on_exchange(symbol, account.exchange_name):
                        return await self._create_credentials_object(api_key, account)
                
                self.logger.warning(
                    "No exchange supports symbol for user",
                    user_id=user_id,
                    symbol=symbol,
                    available_exchanges=[acc.exchange_name for _, acc in exchanges]
                )
                return None
                
        except Exception as e:
            self.logger.error(
                "Failed to get user exchange for symbol",
                error=str(e),
                user_id=user_id,
                symbol=symbol
            )
            return None
    
    async def _create_credentials_object(
        self, 
        api_key: ExchangeApiKey, 
        account: ExchangeAccount
    ) -> UserExchangeCredentials:
        """Create credentials object with decrypted keys."""
        decrypted_api_key = self.cipher_suite.decrypt(api_key.encrypted_api_key.encode()).decode()
        decrypted_secret_key = self.cipher_suite.decrypt(api_key.encrypted_secret_key.encode()).decode()
        decrypted_passphrase = None
        
        if api_key.encrypted_passphrase:
            decrypted_passphrase = self.cipher_suite.decrypt(api_key.encrypted_passphrase.encode()).decode()
        
        return UserExchangeCredentials(
            exchange_name=account.exchange_name,
            api_key=decrypted_api_key,
            secret_key=decrypted_secret_key,
            passphrase=decrypted_passphrase,
            is_sandbox=account.is_simulation,
            account_id=str(account.id),
            permissions=api_key.permissions or []
        )
    
    async def _symbol_supported_on_exchange(self, symbol: str, exchange: str) -> bool:
        """Check if symbol is supported on exchange."""
        # Normalize symbol for different exchange formats
        normalized_symbol = self._normalize_symbol_for_exchange(symbol, exchange)
        
        # Check with exchange API
        if exchange.lower() == "binance":
            return await self._check_binance_symbol_support(normalized_symbol)
        elif exchange.lower() == "kraken":
            return await self._check_kraken_symbol_support(normalized_symbol)
        elif exchange.lower() == "kucoin":
            return await self._check_kucoin_symbol_support(normalized_symbol)
        
        # Default to true for unknown exchanges (will fail gracefully later)
        return True
    
    def _normalize_symbol_for_exchange(self, symbol: str, exchange: str) -> str:
        """Normalize symbol format for specific exchange."""
        symbol = symbol.upper().replace("/", "")
        
        if exchange.lower() == "binance":
            return symbol  # BTCUSDT
        elif exchange.lower() == "kraken":
            # Convert to Kraken format (XBTUSD, ETHUSD)
            if symbol.startswith("BTC"):
                return symbol.replace("BTC", "XBT")
            return symbol
        elif exchange.lower() == "kucoin":
            # Convert to KuCoin format (BTC-USDT)
            if len(symbol) >= 6:
                base = symbol[:-4]
                quote = symbol[-4:]
                return f"{base}-{quote}"
            return symbol
        
        return symbol
    
    async def _check_binance_symbol_support(self, symbol: str) -> bool:
        """Check if symbol is supported on Binance."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.binance.com/api/v3/exchangeInfo",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        return False
                    
                    data = await response.json()
                    symbols = [s["symbol"] for s in data.get("symbols", [])]
                    return symbol in symbols
        except Exception as e:
            self.logger.warning(f"Failed to check Binance symbol support: {e}")
            return True  # Assume supported if check fails
    
    async def _check_kraken_symbol_support(self, symbol: str) -> bool:
        """Check if symbol is supported on Kraken."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.kraken.com/0/public/AssetPairs",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        return False
                    
                    data = await response.json()
                    pairs = list(data.get("result", {}).keys())
                    return symbol in pairs
        except Exception as e:
            self.logger.warning(f"Failed to check Kraken symbol support: {e}")
            return True
    
    async def _check_kucoin_symbol_support(self, symbol: str) -> bool:
        """Check if symbol is supported on KuCoin."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.kucoin.com/api/v1/symbols",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        return False
                    
                    data = await response.json()
                    symbols = [s["symbol"] for s in data.get("data", [])]
                    return symbol in symbols
        except Exception as e:
            self.logger.warning(f"Failed to check KuCoin symbol support: {e}")
            return True
    
    async def execute_user_trade(
        self,
        user_id: str,
        order_params: ExchangeOrderParams,
        preferred_exchange: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute trade using user's exchange credentials.
        
        Args:
            user_id: User ID
            order_params: Standardized order parameters
            preferred_exchange: Preferred exchange for execution
            
        Returns:
            Execution result with order details
        """
        try:
            # Get user exchange credentials
            credentials = await self.get_user_exchange_for_symbol(
                user_id, order_params.symbol, preferred_exchange
            )
            
            if not credentials:
                return {
                    "success": False,
                    "error": f"No exchange credentials found for user {user_id} to trade {order_params.symbol}"
                }
            
            # Check trading permissions
            if not self._has_trading_permission(credentials, order_params):
                return {
                    "success": False,
                    "error": f"Insufficient permissions for trading {order_params.symbol} on {credentials.exchange_name}"
                }
            
            # Execute on specific exchange
            if credentials.exchange_name.lower() == "binance":
                return await self._execute_binance_order(credentials, order_params)
            elif credentials.exchange_name.lower() == "kraken":
                return await self._execute_kraken_order(credentials, order_params)
            elif credentials.exchange_name.lower() == "kucoin":
                return await self._execute_kucoin_order(credentials, order_params)
            else:
                return {
                    "success": False,
                    "error": f"Exchange {credentials.exchange_name} not yet implemented"
                }
                
        except Exception as e:
            self.logger.error(
                "User trade execution failed",
                error=str(e),
                user_id=user_id,
                symbol=order_params.symbol
            )
            return {"success": False, "error": str(e)}
    
    def _has_trading_permission(
        self, 
        credentials: UserExchangeCredentials, 
        order_params: ExchangeOrderParams
    ) -> bool:
        """Check if user has trading permission for the operation."""
        required_permissions = {
            "binance": ["spot_trade"] if order_params.order_type != "FUTURES" else ["futures_trade"],
            "kraken": ["trade"],
            "kucoin": ["trade", "general"]
        }
        
        exchange_perms = required_permissions.get(credentials.exchange_name.lower(), ["trade"])
        user_perms = [p.lower() for p in credentials.permissions]
        
        return any(perm in user_perms for perm in exchange_perms)
    
    async def _execute_binance_order(
        self, 
        credentials: UserExchangeCredentials, 
        order_params: ExchangeOrderParams
    ) -> Dict[str, Any]:
        """Execute order on Binance using user credentials."""
        try:
            base_url = "https://api.binance.com" if not credentials.is_sandbox else "https://testnet.binance.vision"
            endpoint = "/api/v3/order"
            
            # Prepare order parameters
            timestamp = int(time.time() * 1000)
            params = {
                "symbol": order_params.symbol.replace("/", "").replace("-", ""),
                "side": order_params.side.upper(),
                "type": order_params.order_type.upper(),
                "quantity": str(order_params.quantity),
                "timestamp": timestamp
            }
            
            # Add price for limit orders
            if order_params.order_type.upper() == "LIMIT" and order_params.price:
                params["price"] = str(order_params.price)
                params["timeInForce"] = order_params.time_in_force
            
            # Add stop price for stop orders
            if order_params.order_type.upper() in ["STOP_LOSS", "STOP_LIMIT"] and order_params.stop_price:
                params["stopPrice"] = str(order_params.stop_price)
            
            # Create signature
            query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = hmac.new(
                credentials.secret_key.encode("utf-8"),
                query_string.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()
            
            headers = {
                "X-MBX-APIKEY": credentials.api_key,
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Execute order
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{base_url}{endpoint}",
                    headers=headers,
                    data=f"{query_string}&signature={signature}"
                ) as response:
                    result = await response.json()
                    
                    if response.status != 200:
                        error_msg = result.get("msg", result.get("error", "Unknown Binance error"))
                        self.logger.error(
                            "Binance order execution failed",
                            error=error_msg,
                            status_code=response.status,
                            user_id=credentials.account_id
                        )
                        return {"success": False, "error": error_msg}
                    
                    # Process successful response
                    fills = result.get("fills", [])
                    total_fee = sum(float(fill["commission"]) for fill in fills)
                    avg_price = float(result.get("price", 0))
                    
                    if fills:
                        # Calculate weighted average price from fills
                        total_qty = sum(float(fill["qty"]) for fill in fills)
                        if total_qty > 0:
                            avg_price = sum(float(fill["price"]) * float(fill["qty"]) for fill in fills) / total_qty
                    
                    return {
                        "success": True,
                        "exchange": "binance",
                        "order_id": str(result["orderId"]),
                        "client_order_id": result.get("clientOrderId"),
                        "symbol": result["symbol"],
                        "side": result["side"],
                        "order_type": result["type"],
                        "executed_quantity": float(result["executedQty"]),
                        "execution_price": avg_price,
                        "total_fee": total_fee,
                        "fee_asset": fills[0]["commissionAsset"] if fills else "USDT",
                        "status": result["status"],
                        "timestamp": datetime.utcnow().isoformat(),
                        "fills": fills,
                        "raw_response": result
                    }
                    
        except Exception as e:
            self.logger.error(
                "Binance order execution error",
                error=str(e),
                user_id=credentials.account_id,
                symbol=order_params.symbol
            )
            return {"success": False, "error": str(e)}
    
    async def _execute_kraken_order(
        self, 
        credentials: UserExchangeCredentials, 
        order_params: ExchangeOrderParams
    ) -> Dict[str, Any]:
        """Execute order on Kraken using user credentials."""
        try:
            base_url = "https://api.kraken.com"
            endpoint = "/0/private/AddOrder"
            
            # Prepare order parameters
            nonce = str(int(time.time() * 1000000))
            params = {
                "nonce": nonce,
                "pair": self._normalize_symbol_for_exchange(order_params.symbol, "kraken"),
                "type": order_params.side.lower(),
                "ordertype": order_params.order_type.lower(),
                "volume": str(order_params.quantity)
            }
            
            if order_params.order_type.upper() == "LIMIT" and order_params.price:
                params["price"] = str(order_params.price)
            
            # Create signature
            post_data = "&".join([f"{k}={v}" for k, v in params.items()])
            encoded = (nonce + post_data).encode()
            message = endpoint.encode() + hashlib.sha256(encoded).digest()
            signature = hmac.new(
                base64.b64decode(credentials.secret_key),
                message,
                hashlib.sha512
            )
            
            headers = {
                "API-Key": credentials.api_key,
                "API-Sign": base64.b64encode(signature.digest()).decode(),
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Execute order
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{base_url}{endpoint}",
                    headers=headers,
                    data=post_data
                ) as response:
                    result = await response.json()
                    
                    if response.status != 200 or result.get("error"):
                        error_msg = ", ".join(result.get("error", ["Unknown Kraken error"]))
                        self.logger.error(
                            "Kraken order execution failed",
                            error=error_msg,
                            user_id=credentials.account_id
                        )
                        return {"success": False, "error": error_msg}
                    
                    # Process successful response
                    order_result = result.get("result", {})
                    order_ids = order_result.get("txid", [])
                    
                    return {
                        "success": True,
                        "exchange": "kraken",
                        "order_id": order_ids[0] if order_ids else "unknown",
                        "symbol": order_params.symbol,
                        "side": order_params.side,
                        "order_type": order_params.order_type,
                        "executed_quantity": float(order_params.quantity),
                        "execution_price": float(order_params.price or 0),
                        "total_fee": 0.0,  # Kraken fees calculated separately
                        "status": "NEW",
                        "timestamp": datetime.utcnow().isoformat(),
                        "raw_response": result
                    }
                    
        except Exception as e:
            self.logger.error(
                "Kraken order execution error",
                error=str(e),
                user_id=credentials.account_id
            )
            return {"success": False, "error": str(e)}
    
    async def _execute_kucoin_order(
        self, 
        credentials: UserExchangeCredentials, 
        order_params: ExchangeOrderParams
    ) -> Dict[str, Any]:
        """Execute order on KuCoin using user credentials."""
        try:
            base_url = "https://api.kucoin.com"
            endpoint = "/api/v1/orders"
            
            # Prepare order body
            timestamp = str(int(time.time() * 1000))
            body = {
                "clientOid": str(uuid.uuid4()),
                "side": order_params.side.lower(),
                "symbol": self._normalize_symbol_for_exchange(order_params.symbol, "kucoin"),
                "type": order_params.order_type.lower(),
                "size": str(order_params.quantity)
            }
            
            if order_params.order_type.upper() == "LIMIT" and order_params.price:
                body["price"] = str(order_params.price)
            
            body_json = json.dumps(body)
            
            # Create signature
            str_to_sign = timestamp + "POST" + endpoint + body_json
            signature = base64.b64encode(
                hmac.new(
                    credentials.secret_key.encode("utf-8"),
                    str_to_sign.encode("utf-8"),
                    hashlib.sha256
                ).digest()
            ).decode()
            
            # Create passphrase signature
            passphrase_signature = base64.b64encode(
                hmac.new(
                    credentials.secret_key.encode("utf-8"),
                    credentials.passphrase.encode("utf-8"),
                    hashlib.sha256
                ).digest()
            ).decode()
            
            headers = {
                "KC-API-KEY": credentials.api_key,
                "KC-API-SIGN": signature,
                "KC-API-TIMESTAMP": timestamp,
                "KC-API-PASSPHRASE": passphrase_signature,
                "KC-API-KEY-VERSION": "2",
                "Content-Type": "application/json"
            }
            
            # Execute order
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{base_url}{endpoint}",
                    headers=headers,
                    data=body_json
                ) as response:
                    result = await response.json()
                    
                    if response.status != 200 or result.get("code") != "200000":
                        error_msg = result.get("msg", "Unknown KuCoin error")
                        self.logger.error(
                            "KuCoin order execution failed",
                            error=error_msg,
                            user_id=credentials.account_id
                        )
                        return {"success": False, "error": error_msg}
                    
                    # Process successful response
                    order_data = result.get("data", {})
                    
                    return {
                        "success": True,
                        "exchange": "kucoin",
                        "order_id": order_data.get("orderId", "unknown"),
                        "symbol": order_params.symbol,
                        "side": order_params.side,
                        "order_type": order_params.order_type,
                        "executed_quantity": float(order_params.quantity),
                        "execution_price": float(order_params.price or 0),
                        "total_fee": 0.0,  # KuCoin fees calculated separately
                        "status": "ACTIVE",
                        "timestamp": datetime.utcnow().isoformat(),
                        "raw_response": result
                    }
                    
        except Exception as e:
            self.logger.error(
                "KuCoin order execution error",
                error=str(e),
                user_id=credentials.account_id
            )
            return {"success": False, "error": str(e)}
    
    async def get_user_portfolio_balances(self, user_id: str) -> Dict[str, Any]:
        """
        Get real portfolio balances from all user's connected exchanges.
        
        Args:
            user_id: User ID
            
        Returns:
            Aggregated portfolio data from all exchanges
        """
        try:
            async for db in get_database():
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
                
                # Fetch balances from all exchanges
                all_balances = []
                total_value_usd = 0.0
                exchange_summaries = []
                
                for account, api_key in user_exchanges:
                    try:
                        credentials = await self._create_credentials_object(api_key, account)
                        
                        if credentials.exchange_name.lower() == "binance":
                            balances = await self._fetch_binance_balances(credentials)
                        elif credentials.exchange_name.lower() == "kraken":
                            balances = await self._fetch_kraken_balances(credentials)
                        elif credentials.exchange_name.lower() == "kucoin":
                            balances = await self._fetch_kucoin_balances(credentials)
                        else:
                            balances = []
                        
                        exchange_value = sum(b.get("value_usd", 0) for b in balances)
                        total_value_usd += exchange_value
                        
                        all_balances.extend([{**b, "exchange": credentials.exchange_name} for b in balances])
                        exchange_summaries.append({
                            "exchange": credentials.exchange_name,
                            "account_id": credentials.account_id,
                            "total_value_usd": exchange_value,
                            "asset_count": len(balances),
                            "last_updated": datetime.utcnow().isoformat()
                        })
                        
                    except Exception as e:
                        self.logger.error(
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
            self.logger.error(
                "Failed to get user portfolio balances",
                error=str(e),
                user_id=user_id
            )
            return {"success": False, "error": str(e)}
    
    async def _fetch_binance_balances(self, credentials: UserExchangeCredentials) -> List[Dict[str, Any]]:
        """Fetch real balances from Binance."""
        try:
            base_url = "https://api.binance.com" if not credentials.is_sandbox else "https://testnet.binance.vision"
            endpoint = "/api/v3/account"
            timestamp = int(time.time() * 1000)
            
            params = {"timestamp": timestamp}
            query_string = f"timestamp={timestamp}"
            signature = hmac.new(
                credentials.secret_key.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            headers = {"X-MBX-APIKEY": credentials.api_key}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{base_url}{endpoint}?{query_string}&signature={signature}",
                    headers=headers
                ) as response:
                    if response.status != 200:
                        return []
                    
                    data = await response.json()
                    balances = []
                    
                    # Get current prices for USD conversion
                    prices = await self._get_binance_prices()
                    
                    for balance in data.get("balances", []):
                        free = float(balance.get("free", 0))
                        locked = float(balance.get("locked", 0))
                        total = free + locked
                        
                        if total > 0:
                            asset = balance.get("asset")
                            usd_price = prices.get(f"{asset}USDT", prices.get(f"{asset}BUSD", 0.0))
                            
                            # Handle stablecoins
                            if asset in ["USDT", "BUSD", "USDC"]:
                                usd_price = 1.0
                            
                            value_usd = total * usd_price
                            
                            balances.append({
                                "asset": asset,
                                "free": free,
                                "locked": locked,
                                "total": total,
                                "usd_price": usd_price,
                                "value_usd": round(value_usd, 2)
                            })
                    
                    return balances
                    
        except Exception as e:
            self.logger.error(f"Failed to fetch Binance balances: {e}")
            return []
    
    async def _fetch_kraken_balances(self, credentials: UserExchangeCredentials) -> List[Dict[str, Any]]:
        """Fetch real balances from Kraken."""
        try:
            base_url = "https://api.kraken.com"
            endpoint = "/0/private/Balance"
            
            nonce = str(int(time.time() * 1000000))
            params = {"nonce": nonce}
            post_data = f"nonce={nonce}"
            
            # Create signature
            encoded = (nonce + post_data).encode()
            message = endpoint.encode() + hashlib.sha256(encoded).digest()
            signature = hmac.new(
                base64.b64decode(credentials.secret_key),
                message,
                hashlib.sha512
            )
            
            headers = {
                "API-Key": credentials.api_key,
                "API-Sign": base64.b64encode(signature.digest()).decode(),
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{base_url}{endpoint}",
                    headers=headers,
                    data=post_data
                ) as response:
                    if response.status != 200:
                        return []
                    
                    data = await response.json()
                    
                    if data.get("error"):
                        self.logger.error(f"Kraken balance error: {data['error']}")
                        return []
                    
                    balances = []
                    balance_data = data.get("result", {})
                    
                    # Get current prices
                    prices = await self._get_kraken_prices()
                    
                    for asset, balance_str in balance_data.items():
                        balance = float(balance_str)
                        if balance > 0:
                            # Normalize asset name
                            normalized_asset = asset.replace("X", "").replace("Z", "")
                            usd_price = prices.get(f"{normalized_asset}USD", 0.0)
                            
                            balances.append({
                                "asset": normalized_asset,
                                "free": balance,
                                "locked": 0.0,  # Kraken doesn't separate free/locked in balance endpoint
                                "total": balance,
                                "usd_price": usd_price,
                                "value_usd": round(balance * usd_price, 2)
                            })
                    
                    return balances
                    
        except Exception as e:
            self.logger.error(f"Failed to fetch Kraken balances: {e}")
            return []
    
    async def _fetch_kucoin_balances(self, credentials: UserExchangeCredentials) -> List[Dict[str, Any]]:
        """Fetch real balances from KuCoin."""
        try:
            base_url = "https://api.kucoin.com"
            endpoint = "/api/v1/accounts"
            
            timestamp = str(int(time.time() * 1000))
            str_to_sign = timestamp + "GET" + endpoint
            
            signature = base64.b64encode(
                hmac.new(
                    credentials.secret_key.encode("utf-8"),
                    str_to_sign.encode("utf-8"),
                    hashlib.sha256
                ).digest()
            ).decode()
            
            passphrase_signature = base64.b64encode(
                hmac.new(
                    credentials.secret_key.encode("utf-8"),
                    credentials.passphrase.encode("utf-8"),
                    hashlib.sha256
                ).digest()
            ).decode()
            
            headers = {
                "KC-API-KEY": credentials.api_key,
                "KC-API-SIGN": signature,
                "KC-API-TIMESTAMP": timestamp,
                "KC-API-PASSPHRASE": passphrase_signature,
                "KC-API-KEY-VERSION": "2"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{base_url}{endpoint}",
                    headers=headers
                ) as response:
                    if response.status != 200:
                        return []
                    
                    data = await response.json()
                    
                    if data.get("code") != "200000":
                        self.logger.error(f"KuCoin balance error: {data.get('msg')}")
                        return []
                    
                    balances = []
                    accounts = data.get("data", [])
                    
                    # Get current prices
                    prices = await self._get_kucoin_prices()
                    
                    # Group by currency and sum balances
                    currency_balances = {}
                    for account in accounts:
                        currency = account.get("currency")
                        balance = float(account.get("balance", 0))
                        available = float(account.get("available", 0))
                        holds = float(account.get("holds", 0))
                        
                        if currency not in currency_balances:
                            currency_balances[currency] = {"total": 0, "available": 0, "locked": 0}
                        
                        currency_balances[currency]["total"] += balance
                        currency_balances[currency]["available"] += available
                        currency_balances[currency]["locked"] += holds
                    
                    for currency, bal in currency_balances.items():
                        if bal["total"] > 0:
                            usd_price = prices.get(f"{currency}-USDT", 0.0)
                            if currency in ["USDT", "USDC"]:
                                usd_price = 1.0
                            
                            balances.append({
                                "asset": currency,
                                "free": bal["available"],
                                "locked": bal["locked"],
                                "total": bal["total"],
                                "usd_price": usd_price,
                                "value_usd": round(bal["total"] * usd_price, 2)
                            })
                    
                    return balances
                    
        except Exception as e:
            self.logger.error(f"Failed to fetch KuCoin balances: {e}")
            return []
    
    async def _get_binance_prices(self) -> Dict[str, float]:
        """Get current prices from Binance."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.binance.com/api/v3/ticker/price") as response:
                    if response.status != 200:
                        return {}
                    
                    data = await response.json()
                    return {ticker["symbol"]: float(ticker["price"]) for ticker in data}
        except Exception:
            return {}
    
    async def _get_kraken_prices(self) -> Dict[str, float]:
        """Get current prices from Kraken."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.kraken.com/0/public/Ticker") as response:
                    if response.status != 200:
                        return {}
                    
                    data = await response.json()
                    result = data.get("result", {})
                    prices = {}
                    
                    for pair, ticker in result.items():
                        if "c" in ticker:  # Current price
                            prices[pair] = float(ticker["c"][0])
                    
                    return prices
        except Exception:
            return {}
    
    async def _get_kucoin_prices(self) -> Dict[str, float]:
        """Get current prices from KuCoin."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.kucoin.com/api/v1/market/allTickers") as response:
                    if response.status != 200:
                        return {}
                    
                    data = await response.json()
                    tickers = data.get("data", {}).get("ticker", [])
                    
                    return {ticker["symbol"]: float(ticker["last"]) for ticker in tickers if "last" in ticker}
        except Exception:
            return {}
    
    async def get_user_exchange_summary(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive summary of user's exchange connections."""
        try:
            async for db in get_database():
                stmt = select(ExchangeAccount, ExchangeApiKey).join(
                    ExchangeApiKey, ExchangeAccount.id == ExchangeApiKey.account_id
                ).where(ExchangeAccount.user_id == user_id)
                
                result = await db.execute(stmt)
                exchanges = result.fetchall()
                
                summary = {
                    "total_exchanges": len(exchanges),
                    "active_exchanges": 0,
                    "total_balance_usd": 0.0,
                    "exchanges": [],
                    "trading_enabled_count": 0,
                    "sandbox_count": 0
                }
                
                for account, api_key in exchanges:
                    is_active = (
                        account.status == ExchangeStatus.ACTIVE and 
                        api_key.status == ApiKeyStatus.ACTIVE
                    )
                    
                    if is_active:
                        summary["active_exchanges"] += 1
                    
                    if account.trading_enabled:
                        summary["trading_enabled_count"] += 1
                    
                    if account.is_simulation:
                        summary["sandbox_count"] += 1
                    
                    exchange_info = {
                        "exchange_name": account.exchange_name,
                        "account_name": account.account_name,
                        "is_active": is_active,
                        "trading_enabled": account.trading_enabled,
                        "is_sandbox": account.is_simulation,
                        "last_used": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
                        "permissions": api_key.permissions,
                        "success_rate": api_key.success_rate if hasattr(api_key, 'success_rate') else 100.0
                    }
                    
                    summary["exchanges"].append(exchange_info)
                
                return summary
                
        except Exception as e:
            self.logger.error(
                "Failed to get user exchange summary",
                error=str(e),
                user_id=user_id
            )
            return {"success": False, "error": str(e)}


# Global service instance
user_exchange_service = UserExchangeService()


# FastAPI dependency
async def get_user_exchange_service() -> UserExchangeService:
    """Dependency injection for FastAPI."""
    return user_exchange_service