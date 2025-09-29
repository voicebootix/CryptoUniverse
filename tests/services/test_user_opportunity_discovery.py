import os
from pathlib import Path
import sys
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.services import user_opportunity_discovery as discovery_module
from app.services.user_opportunity_discovery import (
    UserOpportunityDiscoveryService,
    UserOpportunityProfile,
)


@pytest.mark.asyncio
async def test_portfolio_optimization_uses_value_change_for_capital(monkeypatch):
    service = UserOpportunityDiscoveryService()

    fake_recommendation = {
        "strategy": "Core",
        "symbol": "BTCUSDT",
        "action": "buy",
        "target_weight": "25%",
        "weight_change": "0.5%",
        "target_percentage": "25%",
        "value_change": 1500,
        "notional_usd": 1500,
        "urgency": "HIGH",
        "improvement_potential": "12%",
    }

    fake_response = {
        "success": True,
        "execution_result": {
            "rebalancing_recommendations": [fake_recommendation]
        },
    }

    monkeypatch.setattr(
        discovery_module.trading_strategies_service,
        "execute_strategy",
        AsyncMock(return_value=fake_response),
    )

    profile = UserOpportunityProfile(
        user_id="user-1",
        active_strategy_count=1,
        total_monthly_strategy_cost=0,
        user_tier="pro",
        max_asset_tier="tier_professional",
        opportunity_scan_limit=10,
        last_scan_time=None,
        strategy_fingerprint="abc123",
    )

    portfolio_result = {
        "active_strategies": [
            {"strategy_id": "ai_portfolio_optimization"}
        ]
    }

    opportunities = await service._scan_portfolio_optimization_opportunities(
        discovered_assets={},
        user_profile=profile,
        scan_id="scan-1",
        portfolio_result=portfolio_result,
    )

    assert len(opportunities) == 1
    opportunity = opportunities[0]

    assert opportunity.required_capital_usd == pytest.approx(1500.0)

    metadata = opportunity.metadata
    assert metadata["trade_value_usd"] == pytest.approx(1500.0)
    assert metadata["amount"] == pytest.approx(0.25)
    assert metadata["target_weight"] == pytest.approx(0.25)
    assert metadata["weight_change"] == pytest.approx(0.005)
    assert metadata["target_percentage"] == pytest.approx(25.0)
    assert metadata["improvement_potential"] == pytest.approx(0.12)
    assert metadata["normalized_improvement"] == pytest.approx(0.12)
    assert opportunity.profit_potential_usd == pytest.approx(1200.0)


@pytest.mark.asyncio
async def test_portfolio_optimization_normalizes_non_percent_improvement(monkeypatch):
    service = UserOpportunityDiscoveryService()

    fake_recommendation = {
        "strategy": "Core",
        "symbol": "BTCUSDT",
        "action": "buy",
        "target_weight": "25%",
        "weight_change": "0.5%",
        "target_percentage": "25%",
        "value_change": 1500,
        "notional_usd": 1500,
        "urgency": "HIGH",
        "improvement_potential": "12",  # No percent sign
    }

    fake_response = {
        "success": True,
        "execution_result": {
            "rebalancing_recommendations": [fake_recommendation]
        },
    }

    monkeypatch.setattr(
        discovery_module.trading_strategies_service,
        "execute_strategy",
        AsyncMock(return_value=fake_response),
    )

    profile = UserOpportunityProfile(
        user_id="user-1",
        active_strategy_count=1,
        total_monthly_strategy_cost=0,
        user_tier="pro",
        max_asset_tier="tier_professional",
        opportunity_scan_limit=10,
        last_scan_time=None,
        strategy_fingerprint="abc123",
    )

    portfolio_result = {}

    opportunities = await service._scan_portfolio_opportunities(
        discovered_assets=[],
        user_profile=profile,
        scan_id="scan-1",
        portfolio_result=portfolio_result,
    )

    assert len(opportunities) == 1
    opportunity = opportunities[0]

    metadata = opportunity.metadata
    # Test that "12" (without %) gets normalized to 0.12
    assert metadata["improvement_potential"] == pytest.approx(0.12)
    assert metadata["normalized_improvement"] == pytest.approx(0.12)
