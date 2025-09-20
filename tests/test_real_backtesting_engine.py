import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.services.real_backtesting_engine import RealBacktestingEngine
from app.services.real_market_data import real_market_data_service


@pytest.mark.asyncio
async def test_real_backtester_generates_trades_and_metrics(monkeypatch):
    engine = RealBacktestingEngine()

    base_date = datetime(2021, 1, 1)
    price = 100.0
    ohlcv_data = []

    # Construct deterministic price path with a clear trend reversal
    for day in range(25):
        timestamp = base_date + timedelta(days=day)
        ohlcv_data.append({
            "timestamp": timestamp.isoformat(),
            "open": price,
            "high": price + 5,
            "low": price - 5,
            "close": price,
            "volume": 1000 + day,
        })

        if day < 12:
            price += 4  # Uptrend
        else:
            price -= 6  # Downtrend to trigger exits

    monkeypatch.setattr(
        real_market_data_service,
        "get_historical_ohlcv",
        AsyncMock(return_value=ohlcv_data),
    )

    start_date = base_date.strftime("%Y-%m-%d")
    end_date = (base_date + timedelta(days=24)).strftime("%Y-%m-%d")

    result = await engine.run_backtest(
        strategy_id="test-strategy",
        strategy_func="spot_momentum_strategy",
        start_date=start_date,
        end_date=end_date,
        symbols=["BTC/USDT"],
        initial_capital=10000,
    )

    assert result["total_trades"] > 0
    assert any(trade["action"] == "BUY" for trade in result["trade_log"])
    assert any(trade["action"] == "SELL" for trade in result["trade_log"])
    assert result["final_capital"] != result["initial_capital"]
    assert result["equity_curve"], "Equity curve should capture portfolio evolution"
