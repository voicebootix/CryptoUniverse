import os
import sys
from pathlib import Path

import pytest
from types import SimpleNamespace


os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


from app.services.trading_strategies import trading_strategies_service
from app.services.user_opportunity_discovery import (
    UserOpportunityDiscoveryService,
    UserOpportunityProfile,
)


def test_normalize_confidence_score_handles_wide_ranges():
    service = UserOpportunityDiscoveryService()

    assert service._normalize_confidence_score(0.82) == pytest.approx(0.82)
    assert service._normalize_confidence_score(85) == pytest.approx(0.85)
    assert service._normalize_confidence_score(7500) == pytest.approx(0.75)
    assert service._normalize_confidence_score(None, fallback_strength=7.5) == pytest.approx(0.75)


def test_enrich_metadata_with_trade_details_fills_missing_levels():
    service = UserOpportunityDiscoveryService()

    metadata = service._enrich_metadata_with_trade_details(
        {},
        entry_price=100.0,
        stop_loss_price=None,
        take_profit_price=None,
        position_size_units=None,
        position_notional=1000.0,
        risk_amount=None,
        potential_profit=None,
        risk_reward_ratio=None,
        recommended_side="buy",
        price_snapshot={"current": 100.0},
        indicators=None,
        fallback_risk_percent=2.0,
    )

    assert metadata["stop_loss"] == pytest.approx(98.0)
    assert metadata["take_profit"] == pytest.approx(104.0)
    assert metadata["entry_price"] == pytest.approx(100.0)

    risk_metrics = metadata["risk_metrics"]
    assert risk_metrics["position_size"] == pytest.approx(10.0)
    assert risk_metrics["position_notional"] == pytest.approx(1000.0)
    assert risk_metrics["max_risk_usd"] == pytest.approx(20.0)
    assert risk_metrics["potential_gain_usd"] == pytest.approx(40.0)
    assert risk_metrics["risk_reward_ratio"] == pytest.approx(2.0)

    assert metadata["max_risk_percent"] == pytest.approx(2.0)
    assert metadata["potential_gain_percent"] == pytest.approx(4.0)


@pytest.mark.asyncio
async def test_ensure_price_snapshot_fetches_when_seed_missing(monkeypatch):
    service = UserOpportunityDiscoveryService()

    async def fake_resolve(symbol: str):
        assert symbol == "BTC/USDT"
        return "BTC/USDT", {"current": 123.45, "volume": 4321.0}

    monkeypatch.setattr(service, "_resolve_price_snapshot", fake_resolve)

    entry, snapshot = await service._ensure_price_snapshot("BTC/USDT", {}, seed_entry=None)

    assert entry == pytest.approx(123.45)
    assert snapshot["current"] == pytest.approx(123.45)


@pytest.mark.asyncio
async def test_portfolio_optimization_scanner_infers_trade_levels(monkeypatch):
    service = UserOpportunityDiscoveryService()

    user_profile = UserOpportunityProfile(
        user_id="user-1",
        active_strategy_count=1,
        total_monthly_strategy_cost=0,
        user_tier="basic",
        max_asset_tier="tier_retail",
        opportunity_scan_limit=None,
        last_scan_time=None,
        strategy_fingerprint="test",
    )

    discovered_assets = {
        "tier_retail": [SimpleNamespace(symbol="BTC", volume_24h_usd=1_000_000, exchange="binance")]
    }

    portfolio_result = {
        "active_strategies": [
            {"strategy_id": "ai_portfolio_optimization"},
        ]
    }

    async def fake_execute_strategy(function: str, *args, **kwargs):
        assert function == "portfolio_optimization"
        return {
            "success": True,
            "execution_result": {
                "rebalancing_recommendations": [
                    {
                        "strategy": "INITIAL_ALLOCATION",
                        "symbol": "BTC/USDT",
                        "action": "BUY",
                        "amount": 0.2,
                        "weight_change": 0.2,
                        "target_weight": 0.2,
                        "value_change": 2000.0,
                        "improvement_potential": 0.12,
                    }
                ]
            },
            "optimization_summary": {"expected_return": 0.1},
        }

    async def fake_resolve(symbol: str):
        return symbol.upper(), {"current": 25_000.0}

    async def fake_capital(*args, **kwargs):
        return {"deployable_capital_usd": 10_000.0}

    async def fake_position_context(*args, **kwargs):
        return {}, 50_000.0

    async def fake_history(*args, **kwargs):
        return {}

    async def fake_persist(*args, **kwargs):
        return None

    monkeypatch.setattr(trading_strategies_service, "execute_strategy", fake_execute_strategy)
    monkeypatch.setattr(service, "_resolve_price_snapshot", fake_resolve)
    monkeypatch.setattr(service, "_estimate_user_deployable_capital", fake_capital)
    monkeypatch.setattr(service, "_get_portfolio_position_context", fake_position_context)
    monkeypatch.setattr(service, "_get_portfolio_optimization_history", fake_history)
    monkeypatch.setattr(service, "_persist_portfolio_optimization_history", fake_persist)

    opportunities = await service._scan_portfolio_optimization_opportunities(
        discovered_assets,
        user_profile,
        "scan-123",
        portfolio_result,
    )

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity.entry_price and opportunity.entry_price > 0
    assert opportunity.metadata["stop_loss"] > 0
    assert opportunity.metadata["take_profit"] > 0
    assert opportunity.profit_potential_usd > 0


@pytest.mark.asyncio
async def test_spot_momentum_scanner_produces_enriched_trade(monkeypatch):
    service = UserOpportunityDiscoveryService()

    user_profile = UserOpportunityProfile(
        user_id="user-1",
        active_strategy_count=1,
        total_monthly_strategy_cost=0,
        user_tier="basic",
        max_asset_tier="tier_retail",
        opportunity_scan_limit=None,
        last_scan_time=None,
        strategy_fingerprint="test",
    )

    discovered_assets = {
        "tier_retail": [SimpleNamespace(symbol="BTC", volume_24h_usd=2_000_000, exchange="binance")]
    }

    portfolio_result = {
        "active_strategies": [
            {"strategy_id": "ai_spot_momentum_strategy"},
        ]
    }

    async def fake_execute_strategy(function: str, *args, **kwargs):
        assert function == "spot_momentum_strategy"
        return {
            "success": True,
            "signal": {"action": "BUY", "strength": 7.0, "confidence": 70},
            "indicators": {
                "price_snapshot": {"current": 100.0}
            },
            "risk_management": {
                "stop_loss_price": 98.0,
                "take_profit_price": 105.0,
                "position_size": 0.5,
                "position_notional": 50.0,
                "risk_amount": 1.0,
                "potential_profit": 2.5,
                "risk_reward_ratio": 2.5,
                "max_risk_percent": 2.0,
                "recommended_side": "buy",
            },
        }

    monkeypatch.setattr(trading_strategies_service, "execute_strategy", fake_execute_strategy)

    opportunities = await service._scan_spot_momentum_opportunities(
        discovered_assets,
        user_profile,
        "scan-xyz",
        portfolio_result,
    )

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity.entry_price and opportunity.entry_price > 0
    assert opportunity.metadata["stop_loss"] > 0
    assert opportunity.metadata["take_profit"] > 0
    assert opportunity.profit_potential_usd > 0


@pytest.mark.asyncio
async def test_spot_mean_reversion_scanner_produces_enriched_trade(monkeypatch):
    service = UserOpportunityDiscoveryService()

    user_profile = UserOpportunityProfile(
        user_id="user-1",
        active_strategy_count=1,
        total_monthly_strategy_cost=0,
        user_tier="basic",
        max_asset_tier="tier_retail",
        opportunity_scan_limit=None,
        last_scan_time=None,
        strategy_fingerprint="test",
    )

    discovered_assets = {
        "tier_retail": [SimpleNamespace(symbol="ETH", volume_24h_usd=1_500_000, exchange="binance")]
    }

    portfolio_result = {
        "active_strategies": [
            {"strategy_id": "ai_spot_mean_reversion"},
        ]
    }

    async def fake_execute_strategy(function: str, *args, **kwargs):
        assert function == "spot_mean_reversion"
        return {
            "success": True,
            "signal": {
                "action": "BUY",
                "z_score": -2.4,
                "confidence": 82,
                "entry_price": 50.0,
            },
            "indicators": {
                "price_snapshot": {"current": 50.0, "mean_price": 55.0},
            },
            "risk_management": {
                "stop_loss_price": 48.5,
                "take_profit_price": 56.0,
                "position_size": 1.2,
                "position_notional": 60.0,
                "risk_amount": 1.8,
                "potential_profit": 7.2,
                "risk_reward_ratio": 4.0,
            },
        }

    monkeypatch.setattr(trading_strategies_service, "execute_strategy", fake_execute_strategy)

    opportunities = await service._scan_spot_mean_reversion_opportunities(
        discovered_assets,
        user_profile,
        "scan-mean",
        portfolio_result,
    )

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity.entry_price and opportunity.entry_price > 0
    assert opportunity.metadata["stop_loss"] > 0
    assert opportunity.metadata["take_profit"] > 0
    assert opportunity.profit_potential_usd > 0


@pytest.mark.asyncio
async def test_spot_breakout_scanner_produces_enriched_trade(monkeypatch):
    service = UserOpportunityDiscoveryService()

    user_profile = UserOpportunityProfile(
        user_id="user-1",
        active_strategy_count=1,
        total_monthly_strategy_cost=0,
        user_tier="basic",
        max_asset_tier="tier_retail",
        opportunity_scan_limit=None,
        last_scan_time=None,
        strategy_fingerprint="test",
    )

    discovered_assets = {
        "tier_retail": [SimpleNamespace(symbol="SOL", volume_24h_usd=2_500_000, exchange="binance")]
    }

    portfolio_result = {
        "active_strategies": [
            {"strategy_id": "ai_spot_breakout_strategy"},
        ]
    }

    async def fake_execute_strategy(function: str, *args, **kwargs):
        assert function == "spot_breakout_strategy"
        return {
            "success": True,
            "signal": {
                "action": "BUY",
                "confidence": 78,
                "breakout_probability": 0.8,
            },
            "breakout_analysis": {
                "breakout_detected": True,
                "stop_loss": 95.0,
                "take_profit": 110.0,
                "support_levels": [{"price": 92.0}],
                "resistance_levels": [{"price": 105.0}],
            },
            "current_price": 100.0,
            "risk_management": {
                "entry_price": 100.0,
                "stop_loss_price": 95.0,
                "take_profit_price": 110.0,
                "position_size": 1.0,
                "position_notional": 100.0,
                "risk_amount": 5.0,
                "potential_profit": 10.0,
                "risk_reward_ratio": 2.0,
            },
            "indicators": {
                "price_snapshot": {"current": 100.0},
            },
        }

    monkeypatch.setattr(trading_strategies_service, "execute_strategy", fake_execute_strategy)

    opportunities = await service._scan_spot_breakout_opportunities(
        discovered_assets,
        user_profile,
        "scan-breakout",
        portfolio_result,
    )

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity.entry_price and opportunity.entry_price > 0
    assert opportunity.metadata["stop_loss"] > 0
    assert opportunity.metadata["take_profit"] > 0
    assert opportunity.profit_potential_usd > 0
