from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple
import os
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/app")

from app.services import user_opportunity_discovery as discovery_module
from app.services.user_opportunity_discovery import (
    UserOpportunityDiscoveryService,
    UserOpportunityProfile,
)


@dataclass
class _MockAsset:
    exchange: str
    symbol: str
    volume_24h_usd: float = 0.0


@pytest.mark.asyncio
async def test_preload_price_universe_limits_batches(monkeypatch: pytest.MonkeyPatch) -> None:
    service = UserOpportunityDiscoveryService()
    profile = UserOpportunityProfile(
        user_id="user-123",
        active_strategy_count=5,
        total_monthly_strategy_cost=0,
        user_tier="enterprise",
        max_asset_tier="tier_institutional",
        opportunity_scan_limit=0,
        last_scan_time=None,
        strategy_fingerprint="abc",
    )

    assets: List[_MockAsset] = [
        _MockAsset(exchange="binance", symbol=f"ASSET{i}USDT", volume_24h_usd=1000 - i)
        for i in range(250)
    ]
    discovered_assets: Dict[str, List[Any]] = {"tier_institutional": assets}

    calls: List[Dict[str, Any]] = []

    async def fake_preload(pairs: List[Tuple[str, str]], *, ttl: int, concurrency: int) -> Dict[Tuple[str, str], Dict[str, float]]:
        calls.append({
            "pairs": list(pairs),
            "ttl": ttl,
            "concurrency": concurrency,
        })
        return {pair: {"price": 1.0} for pair in pairs}

    monkeypatch.setattr(
        discovery_module.market_analysis_service,
        "preload_exchange_prices",
        fake_preload,
        raising=False,
    )

    await service._preload_price_universe(discovered_assets, profile, "scan-test")

    assert calls, "Expected price preload to be invoked at least once"

    total_pairs = sum(len(call["pairs"]) for call in calls)
    assert total_pairs == 200

    for call in calls:
        assert call["concurrency"] == 50
        assert call["ttl"] == 60
        assert len(call["pairs"]) <= 50
