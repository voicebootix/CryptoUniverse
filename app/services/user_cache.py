"""User caching utilities for reducing repeated database lookups."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.redis import get_redis_client
from app.models.user import User, UserRole, UserStatus

logger = structlog.get_logger(__name__)

_CACHE_TTL_SECONDS = 300


@dataclass
class CachedUserPayload:
    """Serializable payload stored in Redis for user lookups."""

    id: str
    email: str
    hashed_password: Optional[str]
    is_active: Optional[bool]
    is_verified: Optional[bool]
    role: Optional[str]
    status: Optional[str]
    tenant_id: Optional[str]
    last_login: Optional[str]
    exchange_accounts: Optional[List[dict]] = None

    @classmethod
    def from_model(cls, user: User) -> "CachedUserPayload":
        return cls(
            id=str(user.id),
            email=user.email,
            hashed_password=getattr(user, "hashed_password", None),
            is_active=user.is_active,
            is_verified=user.is_verified,
            role=user.role.value if getattr(user, "role", None) else None,
            status=user.status.value if getattr(user, "status", None) else None,
            tenant_id=str(user.tenant_id) if getattr(user, "tenant_id", None) else None,
            last_login=user.last_login.isoformat() if getattr(user, "last_login", None) else None,
            exchange_accounts=[
                {
                    "id": str(acc.id),
                    "user_id": str(acc.user_id),
                    "exchange_name": acc.exchange_name,
                    "account_type": getattr(acc, "account_type", None),
                    "status": acc.status.value if getattr(acc, "status", None) else None,
                }
                for acc in (getattr(user, "exchange_accounts", None) or [])
            ],
        )

    def hydrate_model(self) -> User:
        """Rehydrate a lightweight User model instance from cached data."""
        user = User()
        try:
            user.id = uuid.UUID(self.id)
        except Exception:
            user.id = self.id
        user.email = self.email
        user.hashed_password = self.hashed_password
        user.is_active = self.is_active
        user.is_verified = self.is_verified
        user.role = UserRole(self.role) if self.role else None
        user.status = UserStatus(self.status) if self.status else None
        user.tenant_id = uuid.UUID(self.tenant_id) if self.tenant_id else None
        if self.last_login:
            try:
                user.last_login = datetime.fromisoformat(self.last_login)
            except Exception:
                user.last_login = None

        # Reconstruct exchange accounts
        if self.exchange_accounts:
            from app.models.exchange import ExchangeAccount, ExchangeStatus
            user.exchange_accounts = []
            for acc_data in self.exchange_accounts:
                acc = ExchangeAccount()
                try:
                    acc.id = uuid.UUID(acc_data["id"]) if acc_data.get("id") else None
                except Exception:
                    acc.id = acc_data.get("id")
                try:
                    acc.user_id = uuid.UUID(acc_data["user_id"]) if acc_data.get("user_id") else None
                except Exception:
                    acc.user_id = acc_data.get("user_id")
                acc.exchange_name = acc_data.get("exchange_name")
                acc.account_type = acc_data.get("account_type")
                if acc_data.get("status"):
                    try:
                        acc.status = ExchangeStatus(acc_data["status"])
                    except Exception:
                        acc.status = None
                user.exchange_accounts.append(acc)

        return user


async def _hydrate_user_from_cache(raw: str) -> Optional[User]:
    try:
        payload_dict = json.loads(raw)
        payload = CachedUserPayload(**payload_dict)
        return payload.hydrate_model()
    except Exception as cache_error:
        logger.debug("Failed to hydrate cached user payload", error=str(cache_error))
        return None


async def get_cached_user(user_id: str, db: AsyncSession) -> Optional[User]:
    """Fetch a user with Redis caching to reduce database load."""
    redis = await get_redis_client()
    cache_key = f"user:{user_id}"

    if redis:
        cached = await redis.get(cache_key)
        if cached:
            user = await _hydrate_user_from_cache(cached)
            if user:
                logger.debug("User cache hit", user_id=user_id)
                # Merge cached user into session to make it persistent and allow mutations
                user = await db.merge(user)
                return user
            await redis.delete(cache_key)

    identifier: Any = user_id
    try:
        identifier = uuid.UUID(str(user_id))
    except Exception:
        identifier = str(user_id)

    stmt = (
        select(User)
        .where(User.id == identifier)
        .options(selectinload(User.exchange_accounts))
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if redis and user:
        payload = CachedUserPayload.from_model(user)
        try:
            await redis.setex(cache_key, _CACHE_TTL_SECONDS, json.dumps(asdict(payload)))
            logger.debug("User cached", user_id=user_id)
        except Exception as cache_error:
            logger.debug("Failed to cache user", user_id=user_id, error=str(cache_error))

    return user
