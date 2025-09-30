from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import os
import sys

import numpy as np
import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import app.services.portfolio_risk as portfolio_risk_module  # noqa: E402  pylint: disable=wrong-import-position
from app.services.dynamic_asset_filter import (  # noqa: E402  pylint: disable=wrong-import-position
    AssetInfo,
)
from app.services.portfolio_risk import (  # noqa: E402  pylint: disable=wrong-import-position
    OptimizationStrategy,
    PortfolioOptimizationEngine,
)


def _build_ohlcv_series(prices: List[float], start: datetime = None) -> List[Dict[str, float]]:
    """Helper to craft deterministic OHLCV candles for tests."""

    start = start or datetime(2024, 1, 1)
    candles: List[Dict[str, float]] = []
    for index, close_price in enumerate(prices):
        timestamp = (start + timedelta(days=index)).isoformat()
        candles.append(
            {
                "timestamp": timestamp,
                "open": float(close_price),
                "high": float(close_price * 1.01),
                "low": float(close_price * 0.99),
                "close": float(close_price),
                "volume": float(1_000 + index),
            }
        )
    return candles


class StubMarketDataService:
    """Stubbed market data service providing deterministic candles."""

    def __init__(self, price_map: Dict[str, List[Dict[str, float]]]):
        self._price_map = price_map
        self.calls: Dict[str, int] = {}

    async def get_historical_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 180,
        exchange: str = "auto",
    ) -> List[Dict[str, float]]:
        self.calls[symbol] = self.calls.get(symbol, 0) + 1
        return self._price_map.get(symbol, [])


class StubAssetFilter:
    """Stub enterprise asset filter returning predetermined asset metadata."""

    def __init__(self, asset_map: Dict[str, AssetInfo]):
        self._asset_map = {symbol.upper(): info for symbol, info in asset_map.items()}
        self.session = object()
        self.calls: List[List[str]] = []

    async def async_init(self):
        self.session = object()

    async def get_assets_for_symbol_list(self, symbols: List[str]) -> Dict[str, AssetInfo]:
        requested = [symbol.upper() for symbol in symbols]
        self.calls.append(requested)
        return {
            symbol: self._asset_map[symbol]
            for symbol in requested
            if symbol in self._asset_map
        }


def _annualized_log_return(prices: List[float]) -> float:
    prices_array = np.array(prices, dtype=float)
    log_returns = np.log(prices_array[1:] / prices_array[:-1])
    return float(log_returns.mean() * 252.0)


def _portfolio_max_drawdown(prices_a: List[float], prices_b: List[float]) -> float:
    norm_a = np.array(prices_a, dtype=float) / prices_a[0]
    norm_b = np.array(prices_b, dtype=float) / prices_b[0]
    portfolio_curve = 0.5 * norm_a + 0.5 * norm_b
    cumulative_max = np.maximum.accumulate(portfolio_curve)
    drawdown = (portfolio_curve - cumulative_max) / cumulative_max
    return abs(float(drawdown.min()))


@pytest.mark.asyncio
async def test_get_optimization_inputs_uses_market_data_and_cache():
    btc_prices = [10000, 10200, 10150, 10300, 10450]
    eth_prices = [2000, 2050, 2100, 2200, 2300]

    stub_service = StubMarketDataService(
        {
            "BTC/USDT": _build_ohlcv_series(btc_prices),
            "ETH/USDT": _build_ohlcv_series(eth_prices),
        }
    )

    engine = PortfolioOptimizationEngine(market_data_service=stub_service)
    positions = [
        {"symbol": "BTC", "value_usd": 10000},
        {"symbol": "ETH", "value_usd": 9000},
    ]

    expected_returns, covariance_matrix = await engine._get_optimization_inputs(positions)

    # Initial fetch should hit the stub for both symbols
    assert stub_service.calls["BTC/USDT"] == 1
    assert stub_service.calls["ETH/USDT"] == 1

    expected_btc = _annualized_log_return(btc_prices)
    expected_eth = _annualized_log_return(eth_prices)

    assert expected_returns["BTC"] == pytest.approx(expected_btc, rel=1e-3)
    assert expected_returns["ETH"] == pytest.approx(expected_eth, rel=1e-3)

    btc_log = np.log(np.array(btc_prices[1:], dtype=float) / np.array(btc_prices[:-1], dtype=float))
    eth_log = np.log(np.array(eth_prices[1:], dtype=float) / np.array(eth_prices[:-1], dtype=float))
    manual_cov = np.cov(np.vstack([btc_log, eth_log]), bias=False) * 252.0

    assert covariance_matrix.shape == (2, 2)
    assert covariance_matrix[0, 0] == pytest.approx(manual_cov[0, 0], rel=1e-3)
    assert covariance_matrix[1, 1] == pytest.approx(manual_cov[1, 1], rel=1e-3)

    # Second call should use cached series and not increase call counts
    await engine._get_optimization_inputs(positions)
    assert stub_service.calls["BTC/USDT"] == 1
    assert stub_service.calls["ETH/USDT"] == 1


@pytest.mark.asyncio
async def test_equal_weight_expected_return_reflects_market_data():
    scenario_a = {
        "BTC/USDT": _build_ohlcv_series([30000, 30300, 30600, 31000, 31500]),
        "ETH/USDT": _build_ohlcv_series([2000, 1980, 2020, 2050, 2075]),
    }
    scenario_b = {
        "BTC/USDT": _build_ohlcv_series([30000, 30900, 31800, 33000, 34500]),
        "ETH/USDT": _build_ohlcv_series([2000, 2100, 2200, 2300, 2450]),
    }

    positions = [
        {"symbol": "BTC", "value_usd": 12000},
        {"symbol": "ETH", "value_usd": 8000},
    ]

    engine_a = PortfolioOptimizationEngine(market_data_service=StubMarketDataService(scenario_a))
    result_a = await engine_a.optimize_portfolio(
        {"positions": positions},
        OptimizationStrategy.EQUAL_WEIGHT,
    )

    ann_btc_a = _annualized_log_return([candle["close"] for candle in scenario_a["BTC/USDT"]])
    ann_eth_a = _annualized_log_return([candle["close"] for candle in scenario_a["ETH/USDT"]])
    equal_expected_a = 0.5 * (ann_btc_a + ann_eth_a)

    assert result_a.expected_return == pytest.approx(equal_expected_a, rel=1e-3)
    assert 0.4 <= result_a.confidence <= 0.99

    drawdown_a = _portfolio_max_drawdown(
        [candle["close"] for candle in scenario_a["BTC/USDT"]],
        [candle["close"] for candle in scenario_a["ETH/USDT"]],
    )
    assert result_a.max_drawdown_estimate == pytest.approx(drawdown_a, rel=1e-3)

    engine_b = PortfolioOptimizationEngine(market_data_service=StubMarketDataService(scenario_b))
    result_b = await engine_b.optimize_portfolio(
        {"positions": positions},
        OptimizationStrategy.EQUAL_WEIGHT,
    )

    ann_btc_b = _annualized_log_return([candle["close"] for candle in scenario_b["BTC/USDT"]])
    ann_eth_b = _annualized_log_return([candle["close"] for candle in scenario_b["ETH/USDT"]])
    equal_expected_b = 0.5 * (ann_btc_b + ann_eth_b)

    assert result_b.expected_return == pytest.approx(equal_expected_b, rel=1e-3)
    assert result_b.expected_return > result_a.expected_return
    assert result_b.sharpe_ratio > result_a.sharpe_ratio


@pytest.mark.asyncio
async def test_max_sharpe_uses_dynamic_asset_liquidity(monkeypatch):
    now = datetime.utcnow()
    asset_map = {
        "BTC": AssetInfo(
            symbol="BTC",
            exchange="binance",
            volume_24h_usd=500_000_000.0,
            price_usd=30000.0,
            market_cap_usd=None,
            tier="tier_institutional",
            last_updated=now,
            metadata={"source": "test"},
        ),
        "DOGE": AssetInfo(
            symbol="DOGE",
            exchange="binance",
            volume_24h_usd=5_000_000.0,
            price_usd=0.1,
            market_cap_usd=None,
            tier="tier_retail",
            last_updated=now,
            metadata={"source": "test"},
        ),
    }

    stub_filter = StubAssetFilter(asset_map)
    monkeypatch.setattr(
        portfolio_risk_module,
        "enterprise_asset_filter",
        stub_filter,
        raising=False,
    )

    price_map = {
        "BTC/USDT": _build_ohlcv_series([30000, 31000, 32000, 33000, 34000]),
        "DOGE/USDT": _build_ohlcv_series([0.1, 0.11, 0.105, 0.11, 0.1125]),
    }

    engine = PortfolioOptimizationEngine(market_data_service=StubMarketDataService(price_map))
    engine._asset_filter = stub_filter

    positions = [
        {"symbol": "BTC", "value_usd": 15000},
        {"symbol": "DOGE", "value_usd": 5000},
    ]

    result = await engine.optimize_portfolio(
        {"positions": positions},
        OptimizationStrategy.MAX_SHARPE,
    )

    assert stub_filter.calls, "Expected dynamic asset filter to be invoked"
    assert {"BTC", "DOGE"} == set(stub_filter.calls[0])
    assert result.weights["BTC"] > result.weights["DOGE"]
    assert result.weights["BTC"] > 0.55
