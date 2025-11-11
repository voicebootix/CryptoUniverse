import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/app")

from app.services import user_opportunity_discovery as discovery_module
from app.services.user_opportunity_discovery import UserOpportunityDiscoveryService


def _make_service() -> UserOpportunityDiscoveryService:
    return object.__new__(UserOpportunityDiscoveryService)


def test_stage_timeout_respects_worker_budget(monkeypatch):
    monkeypatch.setattr(
        discovery_module,
        "settings",
        types.SimpleNamespace(GUNICORN_TIMEOUT=200),
        raising=False,
    )
    service = _make_service()
    assert pytest.approx(115.0, rel=1e-6) == service._calculate_strategy_stage_timeout(100.0)


def test_stage_timeout_falls_back_when_timeout_invalid(monkeypatch):
    monkeypatch.setattr(
        discovery_module,
        "settings",
        types.SimpleNamespace(GUNICORN_TIMEOUT=-5),
        raising=False,
    )
    service = _make_service()
    assert pytest.approx(65.0, rel=1e-6) == service._calculate_strategy_stage_timeout(50.0)


def test_stage_timeout_caps_above_worker_budget(monkeypatch):
    monkeypatch.setattr(
        discovery_module,
        "settings",
        types.SimpleNamespace(GUNICORN_TIMEOUT=120),
        raising=False,
    )
    service = _make_service()
    assert pytest.approx(100.0, rel=1e-6) == service._calculate_strategy_stage_timeout(1000.0)
