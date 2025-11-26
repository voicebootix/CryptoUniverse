# CryptoUniverse Trading System — Technical Summary

## Asset Universe

**Source hierarchy** (highest to lowest priority):
1. **User-specific settings** — `ExchangeAccount.allowed_symbols` per user, with tier limits (Basic: 50, Pro: 200, Enterprise: 1000 symbols)
2. **Dynamic exchange API fetch** — `dynamic_asset_filter.py` fetches 24h ticker data from 10+ exchanges (Binance, Kraken, KuCoin, Coinbase, Bybit, OKX, etc.)
3. **Hard-coded fallback** — `asset_config.py` contains 100+ base assets and 50+ canonical pairs

**Key files**: `app/services/dynamic_asset_filter.py`, `app/services/exchange_universe_service.py`, `app/core/asset_config.py`

> **Answer**: The system is designed for **dynamic/unlimited assets**. The asset list is not hard-coded — it's fetched from exchanges at runtime. Practical limits come from user tier caps and volume filters, not code constraints.

---

## New / Meme / Low-Liquidity Coins

**Volume tier filters** (`dynamic_asset_filter.py:66-74`):
- `tier_institutional`: $100M+
- `tier_emerging`: $100K+
- `tier_micro`: $10K+
- `tier_any`: No minimum (comprehensive fallback)

**Quote asset filter**: Only USDT, USDC, BUSD (primary) and BTC, ETH (secondary) pairs are processed.

**Behavior**:
- A **new coin IS included** if it exists on a connected exchange and meets the active volume tier
- A coin is **ignored** if: volume below tier threshold, quote currency not supported, or not listed on user's exchanges
- **No explicit whitelist/blacklist** exists — filtering is purely volume-based

> **Answer**: By default, new/meme coins are included in scans if they meet the volume tier threshold. The system uses dynamic discovery, not static lists.

---

## Strategy ↔ Asset Mapping

**Strategy definitions** (`trading_strategies.py`): 25+ platform strategies including `spot_momentum_strategy`, `spot_mean_reversion`, `futures_trade`, `funding_arbitrage`, `pairs_trading`, etc.

**Mapping logic**:
- Strategies are **not locked to specific symbols** — any strategy can run on any symbol of the correct market type
- User's active strategies (via subscription) × user's allowed symbols = execution matrix
- `MasterController` selects strategies based on market conditions (bullish + medium vol → momentum + futures)

> **Answer**: Yes, current strategies can run on **all supported coins**. There are no symbol-specific restrictions in strategy code. Constraints come from: (a) market type (spot vs futures), (b) user's symbol whitelist.

---

## Spot vs Futures

**Separation mechanism**:
- **Exchange API endpoints** are distinct — e.g., Binance spot: `api.binance.us/api/v3/ticker`, futures: `fapi.binance.com/fapi/v1/ticker`
- **Database permissions** per exchange account: `spot_read`, `spot_trade`, `futures_read`, `futures_trade`
- **Query parameter** `asset_types` filters market analysis (default: "spot,futures,options")

**Strategy code**: Same strategy modules serve both markets. The `MasterController` (lines 119-185) selects strategy lists like `["spot_momentum_strategy", "futures_trade"]` based on conditions.

> **Answer**: There is **clean separation at the data/permission layer**, but strategies share code. A spot strategy won't auto-run on futures — market type is explicit in the execution path.

---

## Autonomous Scan Loop

**Entry point**: `background.py:757-894` — `run_autonomous_cycles()`

**Execution flow**:
1. **Global scheduler** runs every 120s (adaptive: 30s high-vol, 300s no-users)
2. `MasterController.run_global_autonomous_cycle()` iterates all users with `autonomous_active:*` Redis keys
3. Calls `_run_user_autonomous_cycle()` per user
4. 5-phase execution: Market scan → AI consensus → Trade execution → Risk monitor → Performance tracking

**Key timing configs** (`background.py:50-60`):
- `autonomous_cycles`: 120s (adaptive)
- `market_data_sync`: 180s
- `risk_monitor`: 60s
- `balance_sync`: 600s

**Distributed lock**: Redis-based with Lua atomic release; prevents duplicate scans across workers.

> **Answer**: Signal computation for BTC/USDT is done **once globally**, then cached (15-min TTL). User cycles consume cached signals. Market data sync is global; per-user work is risk checks and trade execution only.

---

## Computation & Cost Drivers

| Component | What it does | Scales with |
|-----------|--------------|-------------|
| **Indicator calc** (`signal_generation_engine.py`) | RSI, MACD, EMA, volume analysis via `ta` library | # symbols × # timeframes |
| **Backtesting** (`signal_backtesting_service.py`) | 30-day historical test per strategy | # symbols × # strategies |
| **LLM calls** (`api_cost_tracker.py`) | GPT-4, Claude, Gemini consensus | # signals requiring AI validation |
| **Exchange API** | Ticker, orderbook, balance fetches | # exchanges × rate limits |
| **Portfolio risk** (`portfolio_risk_core.py`) | VaR, correlation matrix | # users × # positions |

**LLM pricing tracked**: OpenAI ($0.01/$0.03 per 1K tokens), Claude ($0.015/$0.075), Gemini ($0.0025)

> **Doubling assets** → indicator calc and backtesting scale linearly; cached signals amortize cost.
> **Doubling users** → balance sync, risk monitoring, and trade execution scale per-user; market data and signal generation are **shared globally**.

---

## Config & Practical Limits

**Key parameters**:
- `OPPORTUNITY_STRATEGY_SYMBOL_POLICIES`: per-strategy max symbols (e.g., `funding_arbitrage: max 250`)
- `MAX_SYMBOLS_PER_SYNC`: batch limit (default 100)
- Tier limits: Basic 50 / Pro 200 / Enterprise 1000 symbols per user

**Rate limits enforced** (`dynamic_asset_filter.py:84-151`):
- Binance: 1200/min, Kraken: 60/min, KuCoin: 300/min

**Practical bottlenecks**:
- Exchange rate limits cap how fast new symbols can be fetched
- `MAX_SYMBOLS_PER_SYNC` chunks large fetches
- Subscription tiers enforce per-user symbol caps

> **Contradiction to "unlimited"**: User tiers and exchange rate limits impose soft caps. System is architecturally unlimited but operationally bounded by external APIs and subscription model.
