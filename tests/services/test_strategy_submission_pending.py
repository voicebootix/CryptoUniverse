from __future__ import annotations

from datetime import UTC, datetime
import os
import sys
import uuid
from pathlib import Path

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_strategy_pending.db")

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.models.strategy_submission import StrategyStatus, StrategySubmission
from app.models.user import User, UserRole
from app.services.strategy_submission_service import StrategySubmissionService


class _FakeScalarResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return list(self._items)


class _FakeSession:
    def __init__(self, items):
        self._items = items
        self.executed_statements = []

    async def execute(self, stmt):  # pragma: no cover - behaviour verified via assertions
        self.executed_statements.append(stmt)
        return _FakeScalarResult(self._items)


def _build_submission(
    *,
    service: StrategySubmissionService,
    publisher: User,
    status: StrategyStatus,
    submission_id: str | None = None,
) -> StrategySubmission:
    submission = StrategySubmission(
        id=submission_id or str(uuid.uuid4()),
        user_id=str(publisher.id),
        name="Strategy",  # minimal required fields for payload
        description="Test",
        category="algorithmic",
        status=status,
        submitted_at=datetime.now(UTC),
    )
    submission.user = publisher
    submission.reviewer = None
    submission.strategy_config = {
        service.REVIEW_STATE_KEY: status.value,
        service.REVIEW_HISTORY_KEY: [],
    }
    return submission


@pytest.mark.asyncio()
async def test_get_pending_submissions_includes_changes_requested() -> None:
    service = StrategySubmissionService()
    publisher = User(
        email="publisher@example.com",
        hashed_password="hashed",
        role=UserRole.TRADER,
    )

    changes_submission = _build_submission(
        service=service,
        publisher=publisher,
        status=StrategyStatus.CHANGES_REQUESTED,
        submission_id="changes",
    )

    submitted_submission = _build_submission(
        service=service,
        publisher=publisher,
        status=StrategyStatus.SUBMITTED,
        submission_id="submitted",
    )

    session = _FakeSession([changes_submission, submitted_submission])

    payload = await service.get_pending_submissions(session)  # type: ignore[arg-type]
    status_by_id = {item["id"]: item["status"] for item in payload}

    assert status_by_id["changes"] == "changes_requested"
    assert status_by_id["submitted"] == "submitted"

    filtered_payload = await service.get_pending_submissions(  # type: ignore[arg-type]
        session, status_filter="changes_requested"
    )
    filtered_ids = {item["id"] for item in filtered_payload}

    assert filtered_ids == {"changes"}

