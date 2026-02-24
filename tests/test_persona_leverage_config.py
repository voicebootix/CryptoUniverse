"""
Tests that verify the leverage ceilings assigned to each AI trading persona.

These tests serve as the coding proof (source of truth) referenced in the
feature request: they assert the exact max_leverage values hard-coded in
``MasterSystemController.mode_configs`` and confirm that every persona
defined in ``UnifiedChatService.personalities`` is covered.
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.master_controller import MasterSystemController, TradingMode
from app.services.unified_chat_service import UnifiedChatService


# ---------------------------------------------------------------------------
# Expected leverage values – these are the authoritative assertions.
# If the business decides to change a leverage ceiling the test must be
# updated deliberately so the change is visible in the review history.
# ---------------------------------------------------------------------------
EXPECTED_LEVERAGE = {
    TradingMode.CONSERVATIVE: 1.0,
    TradingMode.BALANCED: 3.0,
    TradingMode.AGGRESSIVE: 5.0,
    TradingMode.BEAST_MODE: 10.0,
}


def test_all_trading_modes_have_leverage_config():
    """Every TradingMode must have an entry in mode_configs."""
    controller = MasterSystemController()
    for mode in TradingMode:
        assert mode in controller.mode_configs, (
            f"TradingMode.{mode.name} is missing from MasterSystemController.mode_configs"
        )


def test_persona_leverage_values_match_expected():
    """
    The max_leverage for each trading mode must equal the documented values.
    This is the source-of-truth assertion: Conservative=1x, Balanced=3x,
    Aggressive=5x, BeastMode=10x.
    """
    controller = MasterSystemController()
    for mode, expected_leverage in EXPECTED_LEVERAGE.items():
        actual = controller.mode_configs[mode].max_leverage
        assert actual == pytest.approx(expected_leverage), (
            f"TradingMode.{mode.name}: expected max_leverage={expected_leverage}, got {actual}"
        )


def test_every_persona_has_a_name():
    """Each trading mode must map to a named persona in UnifiedChatService."""
    service = UnifiedChatService()
    for mode in TradingMode:
        assert mode in service.personalities, (
            f"TradingMode.{mode.name} has no entry in UnifiedChatService.personalities"
        )
        name = service.personalities[mode].get("name", "")
        assert name, (
            f"TradingMode.{mode.name} persona has an empty name"
        )


def test_persona_names_are_correct():
    """The persona names must match the documented values."""
    service = UnifiedChatService()
    expected_names = {
        TradingMode.CONSERVATIVE: "Warren",
        TradingMode.BALANCED: "Alex",
        TradingMode.AGGRESSIVE: "Hunter",
        TradingMode.BEAST_MODE: "Apex",
    }
    for mode, expected_first_name in expected_names.items():
        full_name = service.personalities[mode]["name"]
        assert full_name.startswith(expected_first_name), (
            f"TradingMode.{mode.name}: expected persona name starting with "
            f"'{expected_first_name}', got '{full_name}'"
        )


def test_leverage_increases_with_risk():
    """Leverage ceiling must be strictly increasing from Conservative to Beast Mode."""
    controller = MasterSystemController()
    ordered_modes = [
        TradingMode.CONSERVATIVE,
        TradingMode.BALANCED,
        TradingMode.AGGRESSIVE,
        TradingMode.BEAST_MODE,
    ]
    leverages = [controller.mode_configs[m].max_leverage for m in ordered_modes]
    for i in range(len(leverages) - 1):
        assert leverages[i] < leverages[i + 1], (
            f"Expected leverage to increase from {ordered_modes[i].name} "
            f"({leverages[i]}) to {ordered_modes[i + 1].name} ({leverages[i + 1]})"
        )
