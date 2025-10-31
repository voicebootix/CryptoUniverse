"""Service for managing strategy scanning policies."""

from __future__ import annotations

import asyncio
import copy
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.constants.opportunity import build_strategy_policy_baseline
from app.core.database import get_database_session
from app.core.logging import LoggerMixin
from app.models.opportunity import StrategyScanningPolicy


_UNSET = object()


class StrategyScanningPolicyService(LoggerMixin):
    """Provide cached access to strategy scanning policies with database overrides."""

    def __init__(self) -> None:
        super().__init__()
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_expiration: float = 0.0
        self._cache_ttl: float = 60.0
        self._lock = asyncio.Lock()

    async def _load_policies(self, force: bool = False) -> None:
        """Ensure local cache is populated from the database."""

        now = time.monotonic()
        if not force and now < self._cache_expiration:
            return

        async with self._lock:
            if not force and time.monotonic() < self._cache_expiration:
                return

            cache: Dict[str, Dict[str, Any]] = {}
            try:
                async with get_database_session() as session:
                    result = await session.execute(select(StrategyScanningPolicy))
                    for policy in result.scalars().all():
                        cache[policy.strategy_key] = {
                            "id": str(policy.id),
                            "strategy_key": policy.strategy_key,
                            "max_symbols": policy.max_symbols,
                            "chunk_size": policy.chunk_size,
                            "priority": policy.priority,
                            "enabled": bool(policy.enabled),
                            "created_at": policy.created_at,
                            "updated_at": policy.updated_at,
                        }
            except SQLAlchemyError as error:
                self.logger.error(
                    "Failed to load strategy scanning policies", error=str(error)
                )
                # Preserve existing cache but shorten expiry so we retry soon.
                self._cache_expiration = time.monotonic() + 30.0
                return

            self._cache = cache
            self._cache_expiration = time.monotonic() + self._cache_ttl

    def _baseline(self) -> Dict[str, Dict[str, Any]]:
        """Return baseline defaults merged with environment overrides."""

        return build_strategy_policy_baseline()

    async def get_policy_overrides(self) -> Dict[str, Dict[str, Any]]:
        """Return raw database overrides for use inside the discovery pipeline."""

        await self._load_policies()
        return copy.deepcopy(self._cache)

    def _compose_policy_view(
        self, strategy_key: str, baseline: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge baseline configuration with any persisted override for a strategy."""

        base_entry = baseline.get(
            strategy_key,
            {"strategy_key": strategy_key, "priority": 100, "enabled": True},
        )
        view = {
            "strategy_key": strategy_key,
            "max_symbols": base_entry.get("max_symbols"),
            "chunk_size": base_entry.get("chunk_size"),
            "priority": base_entry.get("priority", 100),
            "enabled": bool(base_entry.get("enabled", True)),
            "source": base_entry.get("source", "default"),
            "id": None,
            "created_at": None,
            "updated_at": None,
        }

        override = self._cache.get(strategy_key)
        if override:
            view.update(
                {
                    "id": override.get("id"),
                    "max_symbols": override.get("max_symbols"),
                    "chunk_size": override.get("chunk_size"),
                    "priority": override.get("priority", view["priority"]),
                    "enabled": bool(override.get("enabled", True)),
                    "created_at": override.get("created_at"),
                    "updated_at": override.get("updated_at"),
                    "source": "database",
                }
            )

        return view

    async def list_policies(self) -> List[Dict[str, Any]]:
        """Return combined view of default, config, and database policies."""

        await self._load_policies()
        baseline = self._baseline()

        policies: Dict[str, Dict[str, Any]] = {}
        all_keys = set(baseline.keys()) | set(self._cache.keys())
        for key in all_keys:
            policies[key] = self._compose_policy_view(key, baseline)

        sorted_policies = sorted(
            policies.values(),
            key=lambda item: (-(item.get("priority") or 0), item["strategy_key"]),
        )
        return sorted_policies

    async def get_policy_view(self, strategy_key: str) -> Dict[str, Any]:
        await self._load_policies()
        baseline = self._baseline()
        return self._compose_policy_view(strategy_key, baseline)

    @staticmethod
    def _normalize_int(value: Optional[Any], *, allow_zero: bool = False) -> Optional[int]:
        if value is None:
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        if parsed < 0:
            return None
        if parsed == 0 and not allow_zero:
            return None
        return parsed

    async def upsert_policy(
        self,
        strategy_key: str,
        *,
        max_symbols: Any = _UNSET,
        chunk_size: Any = _UNSET,
        priority: Any = _UNSET,
        enabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        key = str(strategy_key or "").strip().lower()
        if not key:
            raise ValueError("strategy_key must be provided")

        max_symbols_provided = max_symbols is not _UNSET
        chunk_size_provided = chunk_size is not _UNSET
        priority_provided = priority is not _UNSET

        max_symbols_value: Optional[int] = None
        if max_symbols_provided:
            max_symbols_value = self._normalize_int(max_symbols)

        chunk_size_value: Optional[int] = None
        if chunk_size_provided:
            chunk_size_value = self._normalize_int(chunk_size)

        priority_value: Optional[int] = None
        if priority_provided:
            priority_value = self._normalize_int(priority, allow_zero=True)
            if priority_value is None:
                priority_value = 100

        await self._load_policies()
        async with get_database_session() as session:
            result = await session.execute(
                select(StrategyScanningPolicy).where(
                    StrategyScanningPolicy.strategy_key == key
                )
            )
            policy = result.scalar_one_or_none()

            if policy:
                enabled_value = policy.enabled if enabled is None else bool(enabled)
                if max_symbols_provided:
                    policy.max_symbols = max_symbols_value
                if chunk_size_provided:
                    policy.chunk_size = chunk_size_value
                if priority_provided:
                    policy.priority = priority_value if priority_value is not None else 100
                policy.enabled = enabled_value
            else:
                enabled_value = True if enabled is None else bool(enabled)
                policy = StrategyScanningPolicy(
                    strategy_key=key,
                    max_symbols=max_symbols_value if max_symbols_provided else None,
                    chunk_size=chunk_size_value if chunk_size_provided else None,
                    priority=(
                        priority_value
                        if priority_provided and priority_value is not None
                        else 100
                    ),
                    enabled=enabled_value,
                )
                session.add(policy)

            await session.commit()
            await session.refresh(policy)

        await self._load_policies(force=True)
        return await self.get_policy_view(key)

    async def delete_policy(self, strategy_key: str) -> Dict[str, Any]:
        key = str(strategy_key or "").strip().lower()
        if not key:
            raise ValueError("strategy_key must be provided")

        await self._load_policies()
        async with get_database_session() as session:
            result = await session.execute(
                select(StrategyScanningPolicy).where(
                    StrategyScanningPolicy.strategy_key == key
                )
            )
            policy = result.scalar_one_or_none()
            if policy:
                await session.delete(policy)
                await session.commit()
            else:
                await session.rollback()

        await self._load_policies(force=True)
        return await self.get_policy_view(key)


strategy_scanning_policy_service = StrategyScanningPolicyService()
