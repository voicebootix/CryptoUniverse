import asyncio
from pathlib import Path
import sys
from typing import Any

import os
import pytest
import types

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

if "aiosqlite" not in sys.modules:
    import sqlite3

    stub_aiosqlite = types.ModuleType("aiosqlite")
    stub_aiosqlite.connect = None  # pragma: no cover - placeholder for SQLAlchemy import
    for attr in (
        "DatabaseError",
        "Error",
        "IntegrityError",
        "NotSupportedError",
        "OperationalError",
        "ProgrammingError",
    ):
        setattr(stub_aiosqlite, attr, getattr(sqlite3, attr))
    stub_aiosqlite.sqlite_version = sqlite3.sqlite_version
    stub_aiosqlite.sqlite_version_info = sqlite3.sqlite_version_info
    stub_aiosqlite.PARSE_COLNAMES = sqlite3.PARSE_COLNAMES
    stub_aiosqlite.PARSE_DECLTYPES = sqlite3.PARSE_DECLTYPES
    stub_aiosqlite.Binary = sqlite3.Binary
    sys.modules["aiosqlite"] = stub_aiosqlite

from app.services import trading_strategies
from app.services.market_analysis_core import MarketAnalysisService
from app.services.trading_strategies import TradingStrategiesService


class _StubSession:
    async def __aenter__(self) -> "_StubSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def execute(self, _statement: Any) -> "_StubResult":
        return _StubResult()


class _StubResult:
    def first(self):
        return None

    def scalars(self):
        return self


class _StubExecutor:
    def __init__(self, *args, **kwargs):
        pass


class _StubAnalyzer:
    def __init__(self, *args, **kwargs):
        pass


@pytest.mark.asyncio
async def test_strategy_performance_requires_real_data(monkeypatch):
    monkeypatch.setattr(trading_strategies, "TradeExecutionService", _StubExecutor)
    monkeypatch.setattr(trading_strategies, "MarketAnalysisService", _StubAnalyzer)
    monkeypatch.setattr(trading_strategies, "AsyncSessionLocal", lambda: _StubSession())

    service = TradingStrategiesService()

    data = await service._get_strategy_performance_data(None, "30d", "test-user")
    assert data["data_quality"] == "no_data"
    assert "total_return" not in data

    summary = await service.strategy_performance(None, "30d", user_id="test-user")
    assert summary["success"] is False
    assert summary["data_quality"] == "no_data"
    assert summary["status"] == "no_data_available"
    analysis = summary["strategy_performance_analysis"]
    assert analysis["performance_metrics"] == {}
    assert analysis.get("error")


@pytest.mark.asyncio
async def test_technical_analysis_marks_missing_data(monkeypatch):
    service = MarketAnalysisService()

    async def _no_data(*_args, **_kwargs):
        return []

    monkeypatch.setattr(service, "_get_historical_price_data", _no_data)

    result = await service.technical_analysis("BTC/USDT")
    assert result["success"] is False
    symbol_payload = result["technical_analysis"]["BTC/USDT"]
    assert symbol_payload["data_quality"] == "no_data"
    assert symbol_payload["analysis"] == {}
    assert symbol_payload["signals"] == {}
