from __future__ import annotations

from datetime import datetime
import os
import sys
import uuid
from decimal import Decimal
from pathlib import Path
import types
from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest


sys.path.append(str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_marketplace.db")

pytest.importorskip("aiosqlite")

from sqlalchemy import text  # noqa: E402

from app.core.caching import cache_manager  # noqa: E402
from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.models.strategy_submission import (  # noqa: E402
    ComplexityLevel,
    PricingModel,
    RiskLevel,
    StrategyStatus,
    SupportLevel,
    StrategySubmission,
)
from app.models.user import User, UserRole  # noqa: E402
from app.services.strategy_marketplace_service import (  # noqa: E402
    StrategyMarketplaceService,
)
import app.services.strategy_submission_service as strategy_submission_module
from app.services.strategy_submission_service import (  # noqa: E402
    StrategySubmissionService,
)
from app.models.copy_trading import StrategyPublisher  # noqa: E402
from app.models.trading import TradingStrategy  # noqa: E402
from app.models.tenant import Tenant  # noqa: E402
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler  # noqa: E402


if not hasattr(SQLiteTypeCompiler, "visit_UUID"):
    def _visit_uuid(_, __, **_kw):  # pragma: no cover - sqlite shim
        return "CHAR(36)"

    SQLiteTypeCompiler.visit_UUID = _visit_uuid  # type: ignore[attr-defined]


_TABLE_CREATE_ORDER = [
    Tenant.__table__,
    User.__table__,
    StrategySubmission.__table__,
    StrategyPublisher.__table__,
    TradingStrategy.__table__,
]

_TABLE_DROP_ORDER = list(reversed(_TABLE_CREATE_ORDER))


@pytest.fixture(autouse=True)
async def _reset_database() -> None:
    async with engine.begin() as conn:
        for table in _TABLE_DROP_ORDER:
            await conn.run_sync(table.drop, checkfirst=True)
        for table in _TABLE_CREATE_ORDER:
            await conn.run_sync(table.create, checkfirst=True)
        created_tables = await conn.run_sync(
            lambda connection: connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        )
        expected_table_names = {table.name for table in _TABLE_CREATE_ORDER}
        assert expected_table_names.issubset({name for (name,) in created_tables}), created_tables
    try:
        yield
    finally:
        async with engine.begin() as conn:
            for table in _TABLE_DROP_ORDER:
                await conn.run_sync(table.drop, checkfirst=True)


@pytest.mark.asyncio()
async def test_published_submission_appears_in_marketplace(monkeypatch) -> None:
    original_cache_state = cache_manager.enabled
    cache_manager.enabled = False

    submission_service = StrategySubmissionService()
    marketplace_service = StrategyMarketplaceService()
    marketplace_service.strategy_pricing = {}

    fake_store: Dict[str, Any] = {"unrelated:key": {"value": "keep"}}

    class FakeRedisClient:
        def __init__(self, store: Dict[str, Any]):
            self.store = store

        async def delete(self, *keys: str) -> int:
            removed = 0
            for raw_key in keys:
                key = (
                    raw_key.decode("utf-8")
                    if isinstance(raw_key, (bytes, bytearray))
                    else str(raw_key)
                )
                if key in self.store:
                    del self.store[key]
                    removed += 1
            return removed

        async def scan_iter(self, match: str | None = None, _count: int | None = None):
            prefix = ""
            if match:
                prefix = match[:-1] if match.endswith("*") else match
            for key in list(self.store.keys()):
                if not match or key.startswith(prefix):
                    yield key

    class FakeRedisManager:
        def __init__(self, client: FakeRedisClient):
            self._client = client

        async def get_client(self) -> FakeRedisClient:
            return self._client

    class FakeRedisCacheManager:
        def __init__(self, manager: FakeRedisManager):
            self.redis = manager

    try:
        async with AsyncSessionLocal() as session:
            tables = await session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            table_names = {row[0] for row in tables}
            expected_tables = {table.name for table in _TABLE_CREATE_ORDER}
            missing_tables = expected_tables.difference(table_names)
            if missing_tables:
                async with engine.begin() as ensure_conn:
                    for table in _TABLE_CREATE_ORDER:
                        if table.name in missing_tables:
                            await ensure_conn.run_sync(table.create, checkfirst=True)
                tables = await session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                )
                table_names = {row[0] for row in tables}
            assert expected_tables.issubset(table_names)
            publisher_email = f"publisher-{uuid.uuid4()}@example.com"
            reviewer_email = f"reviewer-{uuid.uuid4()}@example.com"

            publisher = User(
                email=publisher_email,
                hashed_password="hashed",
                role=UserRole.TRADER,
            )
            reviewer = User(
                email=reviewer_email,
                hashed_password="hashed",
                role=UserRole.ADMIN,
            )
            session.add_all([publisher, reviewer])
            await session.commit()
            await session.refresh(publisher)
            await session.refresh(reviewer)
            publisher_uuid = publisher.id
            reviewer_uuid = reviewer.id
            publisher_id = str(publisher_uuid)
            reviewer_id = str(reviewer_uuid)

            fake_store[f"marketplace:{publisher_id}:ai_True:community_True"] = {
                "success": True
            }
            fake_client = FakeRedisClient(fake_store)
            fake_manager = FakeRedisManager(fake_client)
            fake_cache_manager = FakeRedisCacheManager(fake_manager)

            monkeypatch.setattr(
                strategy_submission_module, "redis_cache_manager", fake_cache_manager
            )
            monkeypatch.setattr(
                strategy_submission_module.cache_manager,
                "delete",
                AsyncMock(return_value=0),
            )

            user_rows = await session.execute(text("SELECT id FROM users"))
            existing_user_ids = {str(uuid.UUID(row[0])) for row in user_rows}
            assert publisher_id in existing_user_ids
            assert reviewer_id in existing_user_ids

            source_strategy_id = str(uuid.uuid4())
            submission = StrategySubmission(
                user_id=str(publisher_uuid),
                name="Community Momentum",
                description="A momentum strategy from the community",
                category="momentum",
                risk_level=RiskLevel.MEDIUM,
                expected_return_min=0.10,
                expected_return_max=0.20,
                required_capital=Decimal("1000"),
                pricing_model=PricingModel.FREE,
                status=StrategyStatus.SUBMITTED,
                submitted_at=datetime.utcnow(),
                tags={},
                target_audience={},
                complexity_level=ComplexityLevel.BEGINNER,
                support_level=SupportLevel.BASIC,
                strategy_config={
                    "source_strategy_id": source_strategy_id,
                    submission_service.REVIEW_STATE_KEY: StrategyStatus.SUBMITTED.value,
                    submission_service.REVIEW_HISTORY_KEY: [
                        {
                            "action": "submitted",
                            "reviewer": None,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    ],
                },
            )
            session.add(submission)
            await session.commit()
            await session.refresh(submission)

            reviewer_stub = types.SimpleNamespace(
                id=str(reviewer_uuid), email=reviewer_email
            )

            await submission_service.review_submission(
                submission_id=submission.id,
                reviewer=reviewer_stub,
                action="approve",
                comment="Looks good",
                db=session,
            )

        original_live_performance = marketplace_service._get_live_performance

        async def _fake_live_performance(_strategy_id: str, session=None):  # type: ignore[override]
            return {
                "data_quality": "no_data",
                "status": "no_trades",
                "total_trades": 0,
                "total_pnl": 0.0,
                "win_rate": 0.0,
                "badges": [],
            }

        marketplace_service._get_live_performance = _fake_live_performance  # type: ignore[assignment]

        try:
            strategies = await marketplace_service.get_marketplace_strategies(
                user_id=publisher_id,
                include_ai_strategies=False,
                include_community_strategies=True,
            )
        finally:
            marketplace_service._get_live_performance = original_live_performance
    finally:
        cache_manager.enabled = original_cache_state

    assert strategies["success"] is True
    names = {item["name"] for item in strategies["strategies"]}
    assert "Community Momentum" in names
    assert strategies["community_strategies_count"] == 1
    assert "unrelated:key" in fake_store
    assert all(not key.startswith("marketplace:") for key in fake_store)
