import os
import sys
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import types

cache_module = types.ModuleType("app.core.caching")


class _StubCacheManager:
    async def delete(self, _key: str) -> None:
        return None


cache_module.cache_manager = _StubCacheManager()
sys.modules.setdefault("app.core.caching", cache_module)

from app.models.strategy_submission import StrategyStatus
from app.services.strategy_submission_service import StrategySubmissionService


@pytest.mark.asyncio
async def test_assign_submission_allows_reviewable_status(monkeypatch):
    service = StrategySubmissionService()
    submission = SimpleNamespace(
        id="submission-1",
        status=StrategyStatus.SUBMITTED,
        strategy_config={},
        reviewer_id=None,
        reviewed_at=None,
    )

    async def fake_get(submission_id, db_session):
        assert submission_id == "submission-1"
        return submission

    db = AsyncMock()
    reviewer = SimpleNamespace(id=uuid.uuid4(), email="admin@example.com")

    monkeypatch.setattr(service, "_get_submission_by_id", fake_get)

    updated_submission = await service.assign_submission("submission-1", reviewer, db)

    assert updated_submission is submission
    assert submission.status is StrategyStatus.UNDER_REVIEW
    assert submission.reviewer_id == str(reviewer.id)
    assert submission.strategy_config[service.REVIEW_STATE_KEY] == "under_review"
    db.commit.assert_awaited()
    db.refresh.assert_awaited_with(submission)


@pytest.mark.asyncio
async def test_assign_submission_rejects_finalised_status(monkeypatch):
    service = StrategySubmissionService()
    submission = SimpleNamespace(
        id="submission-2",
        status=StrategyStatus.PUBLISHED,
        strategy_config={},
        reviewer_id=None,
        reviewed_at=None,
    )

    async def fake_get(submission_id, db_session):
        return submission

    db = AsyncMock()
    reviewer = SimpleNamespace(id=uuid.uuid4(), email="admin@example.com")

    monkeypatch.setattr(service, "_get_submission_by_id", fake_get)

    with pytest.raises(ValueError) as excinfo:
        await service.assign_submission("submission-2", reviewer, db)

    assert "published" in str(excinfo.value)
    assert submission.reviewer_id is None
    assert submission.strategy_config == {}
    assert db.commit.await_count == 0
    assert db.refresh.await_count == 0
