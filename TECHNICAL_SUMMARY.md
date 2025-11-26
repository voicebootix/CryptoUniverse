# CryptoUniverse Trading System – Technical Summary

## Overview

CryptoUniverse is a 5-phase autonomous trading system that generates signals via technical strategies, validates them through multi-AI consensus (GPT-4, Claude, Gemini), and applies persona-based risk profiles. Credits gate profit realization at 25% commission.

---

## Files & Modules Overview

| Component | Key Files | Main Classes/Functions |
|-----------|-----------|------------------------|
| **Signal Generation** | `app/services/signal_generation_engine.py` | `SignalGenerationEngine.generate_batch_signals()` |
| **Strategy Logic** | `app/services/trading_strategies.py` | 25+ strategies (momentum, breakout, mean-reversion, scalping) |
| **Signal Evaluation** | `app/services/signal_evaluation_service.py` | `SignalEvaluationService.evaluate()` |
| **AI Validation** | `app/services/ai_consensus_core.py` | `analyze_opportunity()`, `validate_trade()`, `consensus_decision()` |
| **Master Controller** | `app/services/master_controller.py` | `execute_5_phase_autonomous_cycle()` |
| **Credits** | `app/models/credit.py`, `app/services/credit_ledger.py` | `CreditAccount`, `consume_credits()` |
| **Personas** | `app/services/master_controller.py:43-185` | `TradingMode` configs (CONSERVATIVE → BEAST_MODE) |
| **Portfolio Risk** | `app/services/portfolio_risk_core.py` | Risk profile weights, Kelly Criterion sizing |

---

## Signal Generation Flow

1. **Data Fetch** – `market_data_coordinator.get_historical_data()` retrieves 200 OHLCV candles per symbol from exchanges (Binance, Kraken, KuCoin).

2. **Indicator Calculation** – `SignalGenerationEngine` computes RSI, MACD, EMA, SMA, VWAP, OBV on fetched data.

3. **Strategy Execution** – Four signal types generated in parallel:
   - **Momentum**: RSI 50–70 + MACD bullish + EMA crossover + volume >1.2×
   - **Breakout**: Price breaks 20-period high/low + 1.5× volume + RSI confirmation
   - **Mean Reversion**: RSI <30 or >70 + SMA/VWAP deviation
   - **Scalping**: Tight SL (0.5%), quick TP (1.5%)

4. **Signal Object Built** – Returns `BatchSignals` containing arrays per strategy type. Each signal includes: `symbol`, `side`, `entry_price`, `stop_loss`, `take_profit`, `confidence`, `strategy_id`.

5. **Caching** – Results cached in Redis for 15 minutes to minimize redundant computation.

6. **Evaluation & Selection** – `SignalEvaluationService` filters by channel's required strategies, selects highest-confidence signal, attaches `risk_band` from channel config.

---

## AI Validation Logic

**When Called:** AI validation occurs in **Phase 4** of the 5-phase pipeline—after strategy signal generation (Phase 2) and portfolio/risk sizing (Phase 3), but **before** order execution (Phase 5).

**Entry Point:** `master_controller.execute_5_phase_autonomous_cycle()` → Phase 4 calls `ai_consensus_core.validate_trade()`.

**How It Works:**
- Three models queried in parallel: GPT-4 Turbo (analytical), Claude 3 Opus (risk analysis, weight 1.1), Gemini 1.5 Pro (market analysis).
- Each returns a confidence score; scores aggregated using persona-specific weights.
- **Consensus threshold** varies by mode: 80% (Conservative) → 60% (Beast).
- AI can **reject** signals below threshold or **adjust** position sizing recommendations.
- Circuit breakers protect against API failures; fallback to next-best model if one fails.

---

## Parameters Sent to AI

The AI validation module receives a structured payload:

```python
{
    "symbol": "BTC/USDT",
    "side": "BUY",
    "entry_price": 67500.0,
    "stop_loss": 66000.0,
    "take_profit": 70000.0,
    "position_size_pct": 10.0,
    "strategy_type": "momentum",
    "confidence": 0.78,
    "timeframe": "1h",
    "indicators": {"rsi": 62, "macd_signal": "bullish", ...},
    "risk_metrics": {"volatility": 0.023, "correlation": 0.45},
    "current_pnl": 1250.0,
    "risk_mode": "balanced",
    "portfolio_exposure": 35.0
}
```

**AI Decision Logic:** Models evaluate entry/exit levels against current volatility, check indicator confluence, assess portfolio correlation risk, and compare against mode-specific thresholds. Claude weighs risk heavier; Gemini favors speed/opportunity detection.

---

## Persona / Risk Mode Behaviour

| Parameter | Conservative | Balanced | Aggressive | Beast Mode |
|-----------|-------------|----------|------------|------------|
| **Daily Target** | 1.5% | 3.5% | 7.5% | 25% |
| **Max Drawdown** | 5% | 10% | 20% | 50% |
| **Max Position** | 5% | 10% | 20% | 50% |
| **Max Leverage** | 1× | 3× | 5× | 10× |
| **AI Threshold** | 80% | 75% | 70% | 60% |
| **Stop Loss** | 2% | 5% | 7% | 0% (diamond hands) |
| **Scan Frequency** | 15 min | 10 min | 5 min | 1 min |
| **Emergency Stop** | 7% | 15% | 20% | 25% |

**AI Model Weights:**
- Conservative: GPT-4 0.4, Claude 0.4, Gemini 0.2 (accuracy-focused)
- Balanced: Equal 0.33 each
- Aggressive: GPT-4 0.3, Claude 0.3, Gemini 0.4 (speed-focused)
- Beast: GPT-4 0.35, Claude 0.35, Gemini 0.3

**Where Defined:** `master_controller.py` lines 43–185 (mode configs), `portfolio_risk_core.py` lines 1593–1633 (scoring weights).

---

## Credits & Usage Model

### Credit Deduction Triggers

| Event | Credits Debited | Function |
|-------|-----------------|----------|
| **Signal Delivered** | 5–8 per signal | `signal_delivery_service._debit_per_signal()` |
| **Profit Realized** | `profit × 0.25` | `profit_sharing_service.record_profit_realization()` |

### Core Logic

- **Commission Rate:** 25% – 1 credit = $1 commission = $4 profit potential unlocked.
- **Per-Signal Costs:** Standard plan 5–8 credits/signal; Enterprise 3–6 credits/signal.
- **Credit Ledger:** `credit_ledger.consume_credits()` decrements `CreditAccount.available_credits`, creates `CreditTransaction` (type=USAGE).

### Safeguards

- Signal delivery **blocked** if `available_credits < per_signal_cost`.
- Channel subscription requires minimum balance (e.g., 150 credits for Momentum Alpha, 300 for Breakout Pro).
- Credit expiration tracked via `expired_credits` field.

### Credit Flow
```
User Purchase → CreditAccount.total_credits ↑
Signal Delivery → available_credits ↓ (5-8)
Trade Profit Closed → available_credits ↓ (profit × 0.25)
```

---

*~870 words*
