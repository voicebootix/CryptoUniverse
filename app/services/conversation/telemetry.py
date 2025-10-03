"""Telemetry helpers for unified conversation flows."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict

import structlog

from app.core.redis import get_redis_client

logger = structlog.get_logger(__name__)


@dataclass
class TelemetryRecord:
    user_id: str
    interface: str
    intent: str
    request: str
    confidence: float
    resolution: Dict[str, Any]
    state_summary: Dict[str, Any]
    outcome: str
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        return payload


class ConversationTelemetry:
    """Persist telemetry for auditing and future tuning."""

    def __init__(self) -> None:
        self._redis_lock = asyncio.Lock()
        self._redis = None

    async def record(
        self,
        *,
        user_id: str,
        interface: str,
        intent: str,
        request: str,
        confidence: float,
        resolution: Dict[str, Any],
        state_summary: Dict[str, Any],
        outcome: str,
    ) -> None:
        record = TelemetryRecord(
            user_id=user_id,
            interface=interface,
            intent=intent,
            request=request,
            confidence=confidence,
            resolution=resolution,
            state_summary=state_summary,
            outcome=outcome,
        )

        logger.info("conversation_flow", **record.to_dict())

        redis = await self._get_redis()
        if redis:
            key = f"telemetry:conversation:{user_id}"
            await redis.lpush(key, json.dumps(record.to_dict()))
            await redis.ltrim(key, 0, 199)

    async def _get_redis(self):
        if self._redis:
            return self._redis
        async with self._redis_lock:
            if self._redis:
                return self._redis
            try:
                self._redis = await get_redis_client()
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.debug("telemetry_redis_unavailable", error=str(exc))
                self._redis = None
        return self._redis


conversation_telemetry = ConversationTelemetry()
