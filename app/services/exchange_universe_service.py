"""Exchange and symbol universe management for market analysis services.

This module centralises how the platform determines which exchanges and
symbols should be queried for a given user.  It provides a Redis-backed
cache with an in-memory fallback so request-path code can obtain the
required universe without blocking on discovery queries.  When user
context is unavailable the service falls back to platform defaults and a
volume-ranked symbol list sourced from the existing discovery modules.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.logging import LoggerMixin
from app.core.redis import get_redis_client
from app.models.exchange import ExchangeAccount, ExchangeStatus

EXCHANGE_CACHE_TTL = 300  # 5 minutes
SYMBOL_CACHE_TTL = 900    # 15 minutes


@dataclass
class _CacheEntry:
    value: Sequence[str] | Tuple[str, int]
    expires_at: float


class ExchangeUniverseService(LoggerMixin):
    """Resolve user-scoped exchange and symbol universes with caching."""

    def __init__(self) -> None:
        self._redis = None
        self._redis_lock = asyncio.Lock()
        self._exchange_cache: dict[str, _CacheEntry] = {}
        self._symbol_cache: dict[str, _CacheEntry] = {}
        self._user_asset_cache: dict[str, _CacheEntry] = {}

    async def _ensure_redis(self) -> None:
        if self._redis:
            return
        async with self._redis_lock:
            if self._redis:
                return
            try:
                self._redis = await get_redis_client()
            except Exception as exc:  # pragma: no cover - optional dependency
                self.logger.warning("Redis unavailable for exchange universe", error=str(exc))
                self._redis = None

    async def get_user_exchanges(
        self,
        user_id: Optional[str],
        requested_exchanges: Optional[Iterable[str]] = None,
        *,
        default_exchanges: Optional[Sequence[str]] = None,
    ) -> List[str]:
        """Return the exchanges that should be queried for the user."""

        normalized_request = self._normalize_list(requested_exchanges)
        if normalized_request:
            return normalized_request

        cache_key = f"exchanges:{user_id or 'global'}"
        cached = await self._get_cached_value(self._exchange_cache, cache_key)
        if cached is not None:
            return list(cached)

        exchanges: List[str] = []
        if user_id:
            exchanges = await self._load_user_exchanges(user_id)

        if not exchanges:
            exchanges = list(default_exchanges or [])

        if not exchanges:
            # Fallback to platform defaults if nothing else is available
            exchanges = ["binance", "kraken", "kucoin"]

        await self._set_cached_value(self._exchange_cache, cache_key, exchanges, EXCHANGE_CACHE_TTL)
        await self._store_in_redis(cache_key, exchanges, EXCHANGE_CACHE_TTL)
        return exchanges

    async def get_symbol_universe(
        self,
        user_id: Optional[str],
        requested_symbols: Optional[Iterable[str]],
        exchanges: Sequence[str],
        *,
        asset_types: Sequence[str] | None = None,
        limit: Optional[int] = None,
    ) -> List[str]:
        """Return the symbol universe for the user and exchanges."""

        normalized_request = self._normalize_list(requested_symbols)
        if normalized_request:
            return normalized_request[:limit] if limit else normalized_request

        asset_prefs = await self._get_user_asset_preferences(user_id)
        effective_limit = limit or (asset_prefs.symbol_limit if asset_prefs else None)
        min_tier = asset_prefs.max_tier if asset_prefs else "tier_retail"

        key_components = [user_id or "global", ",".join(sorted(exchanges)), min_tier]
        if asset_types:
            key_components.append(",".join(sorted(asset_types)))
        cache_key = "symbols:" + "|".join(key_components)

        cached = await self._get_cached_value(self._symbol_cache, cache_key)
        if cached is not None:
            cached_list = list(cached)
            return cached_list[:effective_limit] if effective_limit else cached_list

        symbols = await self._load_user_symbols(
            user_id,
            exchanges,
            asset_types or ("spot",),
            min_tier,
            effective_limit,
        )
        if not symbols:
            symbols = await self._fallback_symbols(effective_limit, min_tier)

        await self._set_cached_value(self._symbol_cache, cache_key, symbols, SYMBOL_CACHE_TTL)
        await self._store_in_redis(cache_key, symbols, SYMBOL_CACHE_TTL)
        return symbols

    async def invalidate_user(self, user_id: str) -> None:
        """Purge cached universes for the supplied user."""

        keys_to_delete = [
            key
            for key in list(self._exchange_cache.keys()) + list(self._symbol_cache.keys())
            if key.startswith(f"exchanges:{user_id}") or key.startswith(f"symbols:{user_id}")
        ]

        for key in keys_to_delete:
            self._exchange_cache.pop(key, None)
            self._symbol_cache.pop(key, None)
        self._user_asset_cache.pop(f"asset_prefs:{user_id}", None)

        await self._ensure_redis()
        if self._redis:
            async with self._redis.pipeline(transaction=False) as pipe:
                for key in keys_to_delete:
                    await pipe.delete(key)
                await pipe.execute()

    # ------------------------------------------------------------------
    # Internal helpers

    async def _load_user_exchanges(self, user_id: str) -> List[str]:
        """Fetch active exchanges for the user from cache or database."""

        redis_key = f"exchanges:{user_id}"
        redis_values = await self._read_from_redis(redis_key)
        if redis_values is not None:
            return redis_values

        accounts = await self._fetch_exchange_accounts(user_id)
        exchanges = sorted({acc.exchange_name.lower() for acc in accounts})

        await self._store_in_redis(redis_key, exchanges, EXCHANGE_CACHE_TTL)
        return exchanges

    async def _load_user_symbols(
        self,
        user_id: Optional[str],
        exchanges: Sequence[str],
        asset_types: Sequence[str],
        min_tier: str,
        limit: Optional[int],
    ) -> List[str]:
        redis_key = "symbols:" + "|".join(
            [
                user_id or "global",
                ",".join(sorted(exchanges)),
                ",".join(sorted(asset_types)),
                min_tier,
            ]
        )
        redis_values = await self._read_from_redis(redis_key)
        if redis_values is not None:
            return redis_values[:limit] if limit else redis_values

        accounts = await self._fetch_exchange_accounts(user_id) if user_id else []
        symbol_set: set[str] = set()

        for account in accounts:
            if account.exchange_name.lower() not in exchanges:
                continue
            allowed = account.allowed_symbols or []
            for symbol in allowed:
                if isinstance(symbol, str) and symbol:
                    symbol_set.add(symbol.upper())

        symbols: List[str] = await self._rank_symbols_by_volume(symbol_set, min_tier, limit)

        if not symbols:
            symbols = await self._fallback_symbols(limit, min_tier)

        await self._store_in_redis(redis_key, symbols, SYMBOL_CACHE_TTL)
        return symbols

    async def _fetch_exchange_accounts(self, user_id: Optional[str]) -> List[ExchangeAccount]:
        if not user_id:
            return []

        try:
            user_uuid = uuid.UUID(str(user_id))
        except (TypeError, ValueError):
            return []

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ExchangeAccount)
                .where(ExchangeAccount.user_id == user_uuid)
                .where(ExchangeAccount.status == ExchangeStatus.ACTIVE)
                .where(ExchangeAccount.trading_enabled.is_(True))
            )
            return list(result.scalars().all())

    async def _fallback_symbols(self, limit: Optional[int], min_tier: str) -> List[str]:
        """Best-effort discovery for dynamic symbols when user data is absent."""

        try:
            from app.services.dynamic_asset_filter import enterprise_asset_filter

            if not getattr(enterprise_asset_filter, "session", None):
                await enterprise_asset_filter.async_init()

            assets = await enterprise_asset_filter.get_top_assets(
                count=limit or 50,
                min_tier=min_tier,
            )
            symbols = [asset.symbol.upper() for asset in assets if getattr(asset, "symbol", None)]
            if symbols:
                return symbols
        except Exception as exc:  # pragma: no cover - optional dependency
            self.logger.warning("Enterprise asset filter failed", error=str(exc))

        try:
            from app.services.simple_asset_discovery import simple_asset_discovery

            await simple_asset_discovery.async_init()
            symbols = await simple_asset_discovery.get_top_assets(count=limit or 30)
            if symbols:
                return [symbol.upper() for symbol in symbols]
        except Exception as exc:  # pragma: no cover - optional dependency
            self.logger.warning("Simple asset discovery failed", error=str(exc))

        # Final fallback – if upstream discovery fails return an empty list so
        # callers can decide how to proceed without introducing hard-coded
        # assets that may not exist on the user's exchanges.
        return []

    async def _read_from_redis(self, key: str) -> Optional[List[str]]:
        await self._ensure_redis()
        if not self._redis:
            return None

        try:
            raw = await self._redis.get(key)
            if not raw:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode()
            data = json.loads(raw)
            if isinstance(data, list):
                return [str(item).upper() for item in data if isinstance(item, str)]
        except Exception as exc:  # pragma: no cover - best effort only
            self.logger.warning("Failed to read exchange universe cache", error=str(exc))
        return None

    async def _store_in_redis(self, key: str, values: Sequence[str], ttl: int) -> None:
        await self._ensure_redis()
        if not self._redis:
            return
        try:
            await self._redis.setex(key, ttl, json.dumps(list(values)))
        except Exception as exc:  # pragma: no cover - best effort only
            self.logger.warning("Failed to persist exchange universe cache", error=str(exc))

    async def _get_cached_value(
        self,
        cache: dict[str, _CacheEntry],
        key: str,
    ) -> Optional[Sequence[str] | Tuple[str, int]]:
        entry = cache.get(key)
        if not entry:
            return None
        if entry.expires_at < time.monotonic():
            cache.pop(key, None)
            return None
        return entry.value

    async def _set_cached_value(
        self,
        cache: dict[str, _CacheEntry],
        key: str,
        values: Sequence[str] | Tuple[str, int],
        ttl: int,
    ) -> None:
        cache[key] = _CacheEntry(value=tuple(values), expires_at=time.monotonic() + ttl)

    def _normalize_list(self, values: Optional[Iterable[str]]) -> List[str]:
        if not values:
            return []
        if isinstance(values, str):
            values = values.split(",")
        normalized = []
        for item in values:
            if not item:
                continue
            normalized.append(str(item).strip())
        # Preserve order but remove duplicates
        seen = set()
        unique = []
        for item in normalized:
            if item.lower() in seen:
                continue
            seen.add(item.lower())
            unique.append(item)
        return unique

    async def _get_asset_filter(self):  # pragma: no cover - exercised via higher level tests
        try:
            from app.services.dynamic_asset_filter import enterprise_asset_filter

            if not getattr(enterprise_asset_filter, "session", None):
                await enterprise_asset_filter.async_init()

            return enterprise_asset_filter
        except Exception as exc:
            self.logger.warning("Asset filter unavailable", error=str(exc))
            return None

    async def _get_user_asset_preferences(self, user_id: Optional[str]) -> Optional["_UserAssetPreferences"]:
        if not user_id:
            return None

        cache_key = f"asset_prefs:{user_id}"
        cached = await self._get_cached_value(self._user_asset_cache, cache_key)
        if cached is not None:
            return _UserAssetPreferences(*cached)

        tier_mapping: dict[str, Tuple[str, int]] = {
            "basic": ("tier_retail", 50),
            "pro": ("tier_professional", 200),
            "enterprise": ("tier_institutional", 1000),
        }

        tier_name = "basic"
        try:
            from app.services.strategy_marketplace_service import strategy_marketplace_service

            portfolio = await strategy_marketplace_service.get_user_strategy_portfolio(user_id)
            if portfolio.get("success"):
                strategies = portfolio.get("active_strategies", [])
                total_cost = portfolio.get("total_monthly_cost", 0)

                if len(strategies) >= 10 and total_cost >= 300:
                    tier_name = "enterprise"
                elif len(strategies) >= 5 and total_cost >= 100:
                    tier_name = "pro"
        except Exception as exc:
            self.logger.warning(
                "Failed to determine user asset tier", user_id=user_id, error=str(exc)
            )

        max_tier, symbol_limit = tier_mapping.get(tier_name, ("tier_retail", 50))
        prefs = _UserAssetPreferences(max_tier=max_tier, symbol_limit=symbol_limit)

        await self._set_cached_value(
            self._user_asset_cache,
            cache_key,
            (prefs.max_tier, prefs.symbol_limit),
            SYMBOL_CACHE_TTL,
        )
        return prefs

    async def _rank_symbols_by_volume(
        self,
        symbols: Iterable[str],
        min_tier: str,
        limit: Optional[int],
    ) -> List[str]:
        normalized: List[str] = []
        seen = set()
        for symbol in symbols:
            if not symbol:
                continue
            upper = str(symbol).upper()
            if upper in seen:
                continue
            seen.add(upper)
            normalized.append(upper)

        if not normalized:
            return []

        asset_filter = await self._get_asset_filter()
        if not asset_filter:
            return normalized[:limit] if limit else normalized

        try:
            asset_map = await asset_filter.get_assets_for_symbol_list(normalized)
        except Exception as exc:
            self.logger.warning("Symbol ranking failed", error=str(exc))
            return normalized[:limit] if limit else normalized

        priority_map = {tier.name: tier.priority for tier in asset_filter.VOLUME_TIERS}
        allowed_priority = priority_map.get(min_tier, priority_map.get("tier_any", 99))

        filtered = [
            symbol
            for symbol in normalized
            if priority_map.get(getattr(asset_map.get(symbol), "tier", "tier_any"), 99)
            <= allowed_priority
        ]

        if not filtered:
            filtered = normalized

        filtered.sort(
            key=lambda sym: getattr(asset_map.get(sym), "volume_24h_usd", 0),
            reverse=True,
        )

        return filtered[:limit] if limit else filtered


@dataclass
class _UserAssetPreferences:
    max_tier: str
    symbol_limit: int


exchange_universe_service = ExchangeUniverseService()

