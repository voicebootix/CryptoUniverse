import asyncio
from pathlib import Path
import os
import sys
from typing import Optional
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
        "strategy_analysis": {
            "core": {"expected_return": 0.12, "risk_level": 0.18, "sharpe_ratio": 1.2}
        },
        "optimization_summary": {"portfolio_value": 12000.0},
    }

    monkeypatch.setattr(
        discovery_module.trading_strategies_service,
        "execute_strategy",
        AsyncMock(return_value=fake_response),
    )

    capital_payload = {
        "deployable_capital_usd": 10000.0,
        "capital_basis_used_usd": 10000.0,
        "components": {"portfolio_value_usd": 10000.0},
        "inputs": {},
        "credit_profile": None,
        "assumptions": ["Test capital override"],
        "fallback_used": False,
        "calculation_timestamp": "2024-01-01T00:00:00Z",
    }

    monkeypatch.setattr(
        service,
        "_estimate_user_deployable_capital",
        AsyncMock(return_value=capital_payload),
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

    capital_assumptions = metadata["capital_assumptions"]
    assert capital_assumptions["deployable_capital_usd"] == pytest.approx(10000.0)
    assert capital_assumptions["components"]["portfolio_value_usd"] == pytest.approx(10000.0)

    projection = metadata["profit_projection"]
    assert projection["expected_profit_usd"] == pytest.approx(1200.0)
    assert projection["risk_spread_pct"] == pytest.approx(18.0)

    assert metadata["risk_metrics"]["normalized_risk_spread_pct"] == pytest.approx(18.0)
    assert metadata["return_assumptions"]["source"] == "improvement_potential"

    assert opportunity.profit_potential_usd == pytest.approx(1200.0)
    assert opportunity.risk_level == "medium"
    assert opportunity.confidence_score == pytest.approx(77.0)


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
        "strategy_analysis": {
            "core": {"expected_return": 0.12, "risk_level": 0.2, "sharpe_ratio": 1.0}
        },
    }

    monkeypatch.setattr(
        discovery_module.trading_strategies_service,
        "execute_strategy",
        AsyncMock(return_value=fake_response),
    )

    capital_payload = {
        "deployable_capital_usd": 10000.0,
        "capital_basis_used_usd": 10000.0,
        "components": {"portfolio_value_usd": 10000.0},
        "inputs": {},
        "credit_profile": None,
        "assumptions": ["Test capital override"],
        "fallback_used": False,
        "calculation_timestamp": "2024-01-01T00:00:00Z",
    }

    monkeypatch.setattr(
        service,
        "_estimate_user_deployable_capital",
        AsyncMock(return_value=capital_payload),
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

    metadata = opportunity.metadata
    assert metadata["improvement_potential"] == pytest.approx(0.12)
    assert metadata["normalized_improvement"] == pytest.approx(0.12)


@pytest.mark.asyncio
async def test_portfolio_optimization_uses_cash_balance_when_portfolio_zero(monkeypatch):
    service = UserOpportunityDiscoveryService()

    fake_recommendation = {
        "strategy": "Core",
        "symbol": "ETHUSDT",
        "action": "buy",
        "target_weight": "10%",
        "amount": "10%",
        "improvement_potential": "8%",
    }

    fake_response = {
        "success": True,
        "execution_result": {
            "rebalancing_recommendations": [fake_recommendation]
        },
        "strategy_analysis": {
            "core": {"expected_return": 0.08, "risk_level": 0.18, "sharpe_ratio": 1.1}
        },
        "optimization_summary": {},
    }

    monkeypatch.setattr(
        discovery_module.trading_strategies_service,
        "execute_strategy",
        AsyncMock(return_value=fake_response),
    )

    portfolio_snapshot = {
        "success": True,
        "function": "get_portfolio",
        "portfolio": {
            "total_value_usd": 0.0,
            "balances": [{"asset": "USDT", "value_usd": 2500.0}],
        },
    }

    monkeypatch.setattr(
        discovery_module.portfolio_risk_service,
        "get_portfolio",
        AsyncMock(return_value=portfolio_snapshot),
    )

    profile = UserOpportunityProfile(
        user_id="non-uuid-user",
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

    # Trade sizing should use the actual cash-based deployable capital (10% of $2,500)
    assert opportunity.required_capital_usd == pytest.approx(250.0)

    metadata = opportunity.metadata
    capital_assumptions = metadata["capital_assumptions"]

    assert capital_assumptions["deployable_capital_usd"] == pytest.approx(2500.0)
    assert capital_assumptions["capital_basis_used_usd"] == pytest.approx(2500.0)
    assert capital_assumptions["components"]["cash_balance_usd"] == pytest.approx(2500.0)
    assert capital_assumptions["fallback_used"] is False

    assert metadata["trade_value_usd"] == pytest.approx(250.0)


@pytest.mark.asyncio
@pytest.mark.parametrize("capital", [1000.0, 25000.0, 100000.0], ids=["low", "medium", "high"])
async def test_portfolio_optimization_profit_scales_with_capital(monkeypatch, capital):
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
        "strategy_analysis": {
            "core": {"expected_return": 0.12, "risk_level": 0.18, "sharpe_ratio": 1.2}
        },
    }

    monkeypatch.setattr(
        discovery_module.trading_strategies_service,
        "execute_strategy",
        AsyncMock(return_value=fake_response),
    )

    capital_payload = {
        "deployable_capital_usd": capital,
        "capital_basis_used_usd": capital,
        "components": {"portfolio_value_usd": capital},
        "inputs": {},
        "credit_profile": None,
        "assumptions": ["Test capital override"],
        "fallback_used": False,
        "calculation_timestamp": "2024-01-01T00:00:00Z",
    }

    monkeypatch.setattr(
        service,
        "_estimate_user_deployable_capital",
        AsyncMock(return_value=capital_payload),
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

    expected_profit = capital * 0.12
    projection = opportunity.metadata["profit_projection"]

    assert opportunity.profit_potential_usd == pytest.approx(expected_profit)
    assert projection["expected_profit_usd"] == pytest.approx(expected_profit)
    assert projection["capital_basis_usd"] == pytest.approx(capital)
    assert projection["best_case_profit_usd"] > expected_profit
    assert projection["worst_case_profit_usd"] < expected_profit

    capital_assumptions = opportunity.metadata["capital_assumptions"]
    assert capital_assumptions["deployable_capital_usd"] == pytest.approx(capital)



@pytest.mark.asyncio
async def test_discover_opportunities_returns_partial_then_final(monkeypatch):
    service = UserOpportunityDiscoveryService()
    service._scan_response_budget = 0.01
    user_id = "user-partial"

    async def fake_execute(
        user_id: str,
        force_refresh: bool = False,
        include_strategy_recommendations: bool = True,
        *,
        existing_scan_id: Optional[str] = None,
        **kwargs,
    ):
        await asyncio.sleep(0.005)
        cache_key = kwargs["cache_key"]
        partial_payload = {
            "success": True,
            "opportunities": [],
            "metadata": {"scan_state": "partial"},
        }
        await service._update_cached_scan_result(cache_key, partial_payload, partial=True)
        await asyncio.sleep(0.05)
        final_payload = {
            "success": True,
            "opportunities": ["complete"],
            "metadata": {"scan_state": "complete"},
        }
        await service._update_cached_scan_result(cache_key, final_payload, partial=False)
        return final_payload

    monkeypatch.setattr(service, "_execute_opportunity_discovery", fake_execute)

    initial_result = await service.discover_opportunities_for_user(user_id)
    assert initial_result["metadata"]["scan_state"] == "pending"

    await asyncio.sleep(0.02)

    partial_result = await service.discover_opportunities_for_user(user_id)
    assert partial_result["metadata"]["scan_state"] == "partial"

    await asyncio.sleep(0.06)

    final_result = await service.discover_opportunities_for_user(user_id)
    assert final_result["metadata"]["scan_state"] == "complete"
    assert final_result["opportunities"] == ["complete"]


@pytest.mark.asyncio
async def test_admin_snapshot_used_when_portfolio_empty(monkeypatch):
    service = UserOpportunityDiscoveryService()

    primary_mock = AsyncMock(return_value={"success": True, "active_strategies": []})
    admin_portfolio = {
        "success": True,
        "active_strategies": [
            {
                "strategy_id": "ai_spot_momentum_strategy",
                "credit_cost_monthly": 45,
            }
        ],
        "total_monthly_cost": 45,
        "total_strategies": 1,
    }
    admin_mock = AsyncMock(return_value=admin_portfolio)

    monkeypatch.setattr(
        discovery_module.strategy_marketplace_service,
        "get_user_strategy_portfolio",
        primary_mock,
    )
    monkeypatch.setattr(
        discovery_module.strategy_marketplace_service,
        "get_admin_portfolio_snapshot",
        admin_mock,
    )

    profile = await service._build_user_opportunity_profile("admin-user")

    assert profile.active_strategy_count == 1
    assert profile.total_monthly_strategy_cost == 45
    admin_mock.assert_awaited_once()
    primary_mock.assert_not_awaited()
