import os
import sys
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")

from app.services import user_opportunity_discovery as discovery_module


@pytest.mark.asyncio
async def test_admin_scan_returns_opportunity_for_each_strategy(monkeypatch):
    service = discovery_module.UserOpportunityDiscoveryService()

    async def fake_async_init():
        service.redis = None

    monkeypatch.setattr(service, "async_init", fake_async_init)

    strategy_funcs = list(service.strategy_scanners.keys())
    active_strategies = [
        {
            "strategy_id": f"ai_{func}",
            "name": discovery_module.strategy_marketplace_service.ai_strategy_catalog.get(func, {}).get(
                "name", f"AI {func}"
            ),
        }
        for func in strategy_funcs
    ]

    portfolio_payload = {
        "success": True,
        "active_strategies": active_strategies,
        "total_strategies": len(active_strategies),
        "total_monthly_cost": sum(
            discovery_module.strategy_marketplace_service.ai_strategy_catalog.get(func, {}).get(
                "credit_cost_monthly", 0
            )
            for func in strategy_funcs
        ),
    }

    monkeypatch.setattr(
        discovery_module.strategy_marketplace_service,
        "get_user_strategy_portfolio",
        AsyncMock(return_value=portfolio_payload),
    )
    monkeypatch.setattr(
        discovery_module.strategy_marketplace_service,
        "get_admin_portfolio_snapshot",
        AsyncMock(return_value=portfolio_payload),
    )

    monkeypatch.setattr(service, "_get_cached_opportunities", AsyncMock(return_value=None))
    monkeypatch.setattr(service, "_cache_opportunities", AsyncMock())

    asset = SimpleNamespace(exchange="binance", symbol="BTCUSDT", volume_24h_usd=1_000_000)
    monkeypatch.setattr(
        discovery_module.enterprise_asset_filter,
        "discover_all_assets_with_volume_filtering",
        AsyncMock(return_value={"tier_institutional": [asset]}),
    )
    monkeypatch.setattr(service, "_preload_price_universe", AsyncMock())

    for func in strategy_funcs:
        async def fake_scanner(
            discovered_assets,
            user_profile,
            scan_id,
            portfolio_result,
            *,
            strategy_func=func,
        ):
            return [
                discovery_module.OpportunityResult(
                    strategy_id=f"ai_{strategy_func}",
                    strategy_name=f"AI {strategy_func.replace('_', ' ').title()}",
                    opportunity_type=strategy_func,
                    symbol=f"{strategy_func.upper()}-PAIR",
                    exchange="binance",
                    profit_potential_usd=100.0,
                    confidence_score=8.5,
                    risk_level="medium",
                    required_capital_usd=1000.0,
                    estimated_timeframe="24h",
                    entry_price=None,
                    exit_price=None,
                    metadata={
                        "signal_strength": 5.0,
                        "scanner": strategy_func,
                    },
                    discovered_at=datetime.utcnow(),
                )
            ]

        service.strategy_scanners[func] = fake_scanner

    result = await service._execute_opportunity_discovery("admin-user", force_refresh=True)

    assert result["metadata"]["scan_state"] == "complete"
    assert result["total_opportunities"] == len(strategy_funcs)

    discovered_ids = {opp["strategy_id"] for opp in result["opportunities"]}
    expected_ids = {f"ai_{func}" for func in strategy_funcs}
    assert discovered_ids == expected_ids

    assert len(discovered_ids) == len(strategy_funcs)
