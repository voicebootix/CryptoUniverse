import os
from pathlib import Path

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("APP_NAME", "TestApp")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ALLOWED_HOSTS", "*")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("COINMARKETCAP_API_KEY", "test")
os.environ.setdefault("DEEPGRAM_API_KEY", "test")
os.environ.setdefault("ANTHROPIC_MODEL", "claude-3")
os.environ.setdefault("OPENAI_MODEL", "gpt-4")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in os.sys.path:
    os.sys.path.append(str(ROOT))

from app.services.portfolio_risk import OptimizationStrategy
from app.services.portfolio_risk_core import PortfolioRiskService


@pytest.mark.asyncio
async def test_analyze_rebalancing_strategies_returns_complete_payload():
    service = PortfolioRiskService()

    result = await service.analyze_rebalancing_strategies("integration-test-user")

    assert result["success"] is True
    assert result["analysis_type"] == "multi_strategy_rebalance"
    assert result["needs_rebalancing"] is True

    strategy_rankings = result["strategy_rankings"]
    assert len(strategy_rankings) == len(OptimizationStrategy)
    assert {entry["strategy"] for entry in strategy_rankings} == {
        strategy.value for strategy in OptimizationStrategy
    }

    assert result["recommended_trades"], "Expected at least one recommended trade"
    assert result["execution_plan"]["execution_ready"] is True
    assert result["recommended_strategy"] in {
        strategy.value for strategy in OptimizationStrategy
    }
    assert result["analysis_metrics"]["baseline_expected_return"] is not None
