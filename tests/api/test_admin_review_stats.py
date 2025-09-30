import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

sys.path.append(str(Path(__file__).resolve().parents[2]))

# Ensure environment configuration is applied before app imports settings
os.environ["SECRET_KEY"] = "test-secret"
os.environ["DATABASE_URL"] = "sqlite:///./test_review_stats.db"
os.environ.setdefault("ENVIRONMENT", "development")

pytest.importorskip("aiosqlite")

from app.models.strategy_submission import StrategyStatus
from app.models.user import User, UserRole, UserStatus
from app.api.v1.endpoints import admin as admin_endpoints
from app.services.strategy_submission_service import ReviewStats, StrategySubmissionService


if not hasattr(SQLiteTypeCompiler, "visit_UUID"):
    def _visit_uuid(_, __, **_kwargs):  # pragma: no cover - sqlite compatibility shim
        return "CHAR(36)"

    SQLiteTypeCompiler.visit_UUID = _visit_uuid  # type: ignore[attr-defined]


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one(self):
        return self._value

    def all(self):
        return self._value if isinstance(self._value, list) else []


class _FakeSession:
    def __init__(self, return_values):
        self.return_values = list(return_values)
        self.statements = []

    async def execute(self, stmt):
        self.statements.append(stmt)
        value = self.return_values.pop(0)
        return _FakeResult(value)


@pytest.mark.asyncio
async def test_get_review_stats_includes_changes_requested():
    service = StrategySubmissionService()

    fake_session = _FakeSession([4, 1, 0, 0, [], 3])
    reviewer = User(
        email="admin@example.com",
        hashed_password="hashed",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        is_active=True,
        is_verified=True,
    )

    stats = await service.get_review_stats(fake_session, reviewer)

    assert stats.total_pending == 4
    assert stats.my_assigned == 3

    pending_clause = fake_session.statements[0]._where_criteria[0].right
    assigned_clauses = fake_session.statements[-1]._where_criteria[0].clauses

    assert StrategyStatus.CHANGES_REQUESTED in pending_clause.value

    status_clause = None
    for clause in assigned_clauses:
        right = getattr(clause, "right", None)
        if right is not None and hasattr(right, "value") and isinstance(right.value, list):
            status_clause = right
            break

    assert status_clause is not None
    assert StrategyStatus.CHANGES_REQUESTED in status_clause.value


@pytest.mark.asyncio
async def test_admin_review_stats_endpoint_includes_changes_requested(monkeypatch):
    admin_user = User(
        email="admin@example.com",
        hashed_password="hashed",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        is_active=True,
        is_verified=True,
    )

    review_stats = ReviewStats(
        total_pending=4,
        under_review=1,
        approved_today=0,
        rejected_today=0,
        avg_review_time_hours=2,
        my_assigned=3,
    )

    monkeypatch.setattr(
        admin_endpoints.rate_limiter,
        "check_rate_limit",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        admin_endpoints.strategy_submission_service,
        "get_review_stats",
        AsyncMock(return_value=review_stats),
    )

    result = await admin_endpoints.get_strategy_review_stats(
        current_user=admin_user,
        db=None,
    )

    assert result.total_pending == 4
    assert result.my_assigned == 3
