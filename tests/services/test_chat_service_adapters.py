import pytest

from app.services.chat_service_adapters_fixed import ChatServiceAdaptersFixed


@pytest.mark.asyncio
async def test_discover_opportunities_uses_analysis_payload(monkeypatch):
    adapter = ChatServiceAdaptersFixed()

    async def fake_market_overview():
        return {
            "sentiment": "Bullish",
            "trend": "Uptrend",
            "volatility": "Low",
        }

    async def fake_technical_analysis(_symbols: str):
        return {
            "analysis": {
                "BTC": {"signals": {"buy": 3, "sell": 0}},
                "ETH": {"signals": {"buy": 0, "sell": 2}},
            }
        }

    async def fake_market_sentiment(_symbols: str):
        return {"sentiment": {}, "overall_sentiment": "Positive"}

    monkeypatch.setattr(adapter, "get_market_overview", fake_market_overview)
    monkeypatch.setattr(adapter, "get_technical_analysis", fake_technical_analysis)
    monkeypatch.setattr(adapter, "get_market_sentiment", fake_market_sentiment)

    result = await adapter.discover_opportunities("user-123")

    assert result["opportunities"], "expected non-empty opportunities when buy signals exist"
    first = result["opportunities"][0]
    assert first["symbol"] == "BTC"
    assert first["confidence"] > 0
