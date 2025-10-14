"""Resilient runtime state coordination helpers.

Provides in-process fallbacks for coordination flags that are usually stored in
Redis so that critical safety flows can continue operating when Redis is
unavailable. The coordinator intentionally keeps the API very small – it only
caches simple key/value pairs and hash-like dictionaries – and is designed to be
used alongside the existing Redis writes.  Consumers should continue to attempt
Redis operations first and then rely on this coordinator when Redis is down or
returns empty data.
"""

from __future__ import annotations

import asyncio
import copy
import time
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import structlog

logger = structlog.get_logger(__name__)


class ResilientStateCoordinator:
    """Thread-safe fallback cache for coordination flags.

    The cache stores two different categories of runtime data:

    * *Values* – scalar values such as the emergency stop flag for a user.
    * *Hashes* – dictionary style blobs such as the autonomous configuration for
      a user.

    All entries support optional TTL semantics that mimic Redis key expiry.  The
    coordinator never tries to be the source of truth – it simply makes a best
    effort to retain the most recent successful state so trading safeguards can
    keep functioning when Redis is degraded.
    """

    def __init__(self) -> None:
        self._value_cache: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._value_expiry: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._hash_cache: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
        self._hash_expiry: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _purge_expired(self, namespace: str) -> None:
        now = time.time()

        value_expiry = self._value_expiry.get(namespace)
        if value_expiry:
            expired_keys = [key for key, expiry in value_expiry.items() if expiry <= now]
            for key in expired_keys:
                self._value_cache[namespace].pop(key, None)
                value_expiry.pop(key, None)

        hash_expiry = self._hash_expiry.get(namespace)
        if hash_expiry:
            expired_keys = [key for key, expiry in hash_expiry.items() if expiry <= now]
            for key in expired_keys:
                self._hash_cache[namespace].pop(key, None)
                hash_expiry.pop(key, None)

    # ------------------------------------------------------------------
    # Value helpers
    # ------------------------------------------------------------------
    async def cache_value(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """Store a scalar value in the fallback cache."""

        async with self._lock:
            self._purge_expired(namespace)
            self._value_cache[namespace][key] = copy.deepcopy(value)
            if ttl:
                self._value_expiry[namespace][key] = time.time() + ttl
            else:
                self._value_expiry[namespace].pop(key, None)

    async def get_value(self, namespace: str, key: str) -> Any:
        """Retrieve a value from the fallback cache if it exists."""

        async with self._lock:
            self._purge_expired(namespace)
            if key not in self._value_cache.get(namespace, {}):
                return None
            return copy.deepcopy(self._value_cache[namespace][key])

    async def clear_value(self, namespace: str, key: str) -> None:
        async with self._lock:
            self._value_cache[namespace].pop(key, None)
            self._value_expiry[namespace].pop(key, None)

    # ------------------------------------------------------------------
    # Hash helpers
    # ------------------------------------------------------------------
    async def cache_hash(
        self,
        namespace: str,
        key: str,
        mapping: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> None:
        """Store a dictionary in the fallback cache."""

        async with self._lock:
            self._purge_expired(namespace)
            self._hash_cache[namespace][key] = copy.deepcopy(mapping)
            if ttl:
                self._hash_expiry[namespace][key] = time.time() + ttl
            else:
                self._hash_expiry[namespace].pop(key, None)

    async def get_hash(self, namespace: str, key: str) -> Dict[str, Any]:
        """Retrieve a dictionary from the fallback cache."""

        async with self._lock:
            self._purge_expired(namespace)
            data = self._hash_cache.get(namespace, {}).get(key)
            return copy.deepcopy(data) if data is not None else {}

    async def clear_hash(self, namespace: str, key: str) -> None:
        async with self._lock:
            self._hash_cache[namespace].pop(key, None)
            self._hash_expiry[namespace].pop(key, None)

    # ------------------------------------------------------------------
    # Discovery helpers
    # ------------------------------------------------------------------
    async def list_keys(self, namespace: str) -> List[str]:
        """Return all active keys across values and hashes for a namespace."""

        async with self._lock:
            self._purge_expired(namespace)
            value_keys = set(self._value_cache.get(namespace, {}).keys())
            hash_keys = set(self._hash_cache.get(namespace, {}).keys())
            return sorted(value_keys | hash_keys)

    async def any_active(self, entries: Iterable[Tuple[str, str]]) -> Optional[Tuple[str, str]]:
        """Return the first (namespace, key) pair that is active in the cache."""

        async with self._lock:
            for namespace, key in entries:
                self._purge_expired(namespace)
                if key in self._value_cache.get(namespace, {}):
                    return namespace, key
                if key in self._hash_cache.get(namespace, {}):
                    return namespace, key
        return None

    async def clear_namespace(self, namespace: str) -> None:
        async with self._lock:
            self._value_cache.pop(namespace, None)
            self._value_expiry.pop(namespace, None)
            self._hash_cache.pop(namespace, None)
            self._hash_expiry.pop(namespace, None)


# Shared singleton used across services
resilient_state_coordinator = ResilientStateCoordinator()

