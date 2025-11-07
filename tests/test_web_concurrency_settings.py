"""Tests for the automatic Gunicorn concurrency heuristics."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/app")

from app.core import config


def make_settings(**overrides):
    """Helper to instantiate Settings with required defaults."""

    base_kwargs = {
        "SECRET_KEY": "secret",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/app",
    }
    base_kwargs.update(overrides)
    return config.Settings(**base_kwargs)


def test_explicit_web_concurrency_is_respected():
    settings = make_settings(WEB_CONCURRENCY=5)
    assert settings.recommended_web_concurrency == 5


def test_cpu_based_recommendation_without_memory_cap(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config.os, "cpu_count", lambda: 4)
    monkeypatch.setattr(
        config.Settings,
        "_read_cgroup_memory_limit_bytes",
        staticmethod(lambda: None),
    )

    settings = make_settings(WORKER_MULTIPLIER=1.5, WORKER_MIN=1, WORKER_MAX=6)
    # 4 cores * 1.5 => 6 (bounded by WORKER_MAX)
    assert settings.recommended_web_concurrency == 6


def test_memory_cap_reduces_worker_count(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config.os, "cpu_count", lambda: 8)
    monkeypatch.setattr(
        config.Settings,
        "_read_cgroup_memory_limit_bytes",
        staticmethod(lambda: 1024 * 1024 * 1024),
    )

    settings = make_settings(
        WORKER_MULTIPLIER=2.0,
        WORKER_MIN=1,
        WORKER_MAX=8,
        WORKER_MEMORY_FOOTPRINT_MB=512,
    )

    # Memory cap = 1024 MB -> floor(1024 / 512) = 2 workers
    assert settings.recommended_web_concurrency == 2


def test_legacy_workers_env_is_honored(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config.os, "cpu_count", lambda: 2)
    monkeypatch.setattr(
        config.Settings,
        "_read_cgroup_memory_limit_bytes",
        staticmethod(lambda: None),
    )

    settings = make_settings(WORKERS=3)
    assert settings.recommended_web_concurrency == 3
