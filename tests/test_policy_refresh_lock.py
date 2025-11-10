import asyncio
import copy

import pytest

from app.services.user_opportunity_discovery import (
    UserOpportunityDiscoveryService,
    strategy_scanning_policy_service,
)


@pytest.mark.asyncio
async def test_refresh_strategy_symbol_policies_initializes_lock(monkeypatch):
    service = UserOpportunityDiscoveryService()
    service._policy_refresh_lock = None
    service._base_strategy_symbol_policies = {"test": {"enabled": True}}
    service.strategy_symbol_policies = copy.deepcopy(service._base_strategy_symbol_policies)

    async def fake_get_policy_overrides():
        return {"test": {"enabled": False, "max_symbols": 5}}

    monkeypatch.setattr(
        strategy_scanning_policy_service,
        "get_policy_overrides",
        fake_get_policy_overrides,
    )

    await service._refresh_strategy_symbol_policies(force=True)

    assert service._policy_refresh_lock is not None
    assert service.strategy_symbol_policies["test"]["enabled"] is False
    assert service.strategy_symbol_policies["test"]["max_symbols"] == 5


@pytest.mark.asyncio
async def test_refresh_strategy_symbol_policies_uses_existing_lock(monkeypatch):
    service = UserOpportunityDiscoveryService()
    lock = asyncio.Lock()
    service._policy_refresh_lock = lock
    service._base_strategy_symbol_policies = {"alpha": {"enabled": True}}
    service.strategy_symbol_policies = copy.deepcopy(service._base_strategy_symbol_policies)

    first_call = True

    async def fake_get_policy_overrides():
        nonlocal first_call
        if first_call:
            first_call = False
            await asyncio.sleep(0)
            return {"alpha": {"enabled": True}}
        return {}

    monkeypatch.setattr(
        strategy_scanning_policy_service,
        "get_policy_overrides",
        fake_get_policy_overrides,
    )

    await service._refresh_strategy_symbol_policies(force=True)

    assert service._policy_refresh_lock is lock
    assert service.strategy_symbol_policies["alpha"]["enabled"] is True
