# Market Analysis Service – Enterprise Remediation Plan

## 1. Production symptoms

- `MarketAnalysisService.realtime_price_tracking` still iterates a caller-supplied comma string, waits for **every** configured exchange request to finish per symbol, and only then drops into `get_market_snapshot`; with Render-level latency this blocks `/trading/market-overview` and the chat orchestrators that depend on it.【F:app/services/market_analysis_core.py†L265-L397】
- The exchange roster that path actually checks is the static `DynamicExchangeManager.exchange_configs`, so even though discovery logic exists elsewhere the hot path always touches the same three venues (Binance, Kraken, KuCoin).【F:app/services/market_analysis_core.py†L105-L145】
- `_check_rate_limit` in `market_data_feeds` treats `CircuitBreaker` instances like dictionaries, so `breaker.get(...)` raises and the primary price feed falls through to slow fallbacks on every call.【F:app/services/market_data_feeds.py†L243-L266】
- When the code finally reaches the CoinGecko batch fallback, `get_multiple_prices` performs a bare `aiohttp` request with no timeout or rate-limit short circuit, allowing Render requests to hang until the frontend drops the connection.【F:app/services/market_data_feeds.py†L472-L535】
- `discover_exchange_assets` calls `_discover_real_spot_assets` sequentially for each requested venue; each helper spins up two 10‑second calls per exchange before processing, so invoking discovery on the request path multiplies latency, and the results are not cached per user.【F:app/services/market_analysis_core.py†L2318-L2433】【F:app/services/market_analysis_core.py†L4051-L4310】

## 2. Architectural gaps versus the intended dynamic system

1. **User-specific exchange scoping is bypassed.** The master controller already looks up connected exchanges per user (`ExchangeAccount`) for coordinated arbitrage, but `realtime_price_tracking` ignores the `user_id` and probes every hard-coded venue.【F:app/services/master_controller.py†L1105-L1158】【F:app/services/market_analysis_core.py†L265-L397】
2. **Symbol universe never leaves the hot request path.** The discovery functions generate rich inventories, yet they are triggered synchronously by endpoints and do not persist their findings for reuse, forcing cold starts to redo the slow crawl.【F:app/services/market_analysis_core.py†L2318-L2433】
3. **Exchange adapters are not reusable.** `DynamicExchangeManager.fetch_from_exchange` creates a brand-new `aiohttp.ClientSession` per call, multiplying TLS handshakes and preventing connection pooling when scanning dozens of assets.【F:app/services/market_analysis_core.py†L131-L145】
4. **Hard-coded pair conversions persist.** Helper methods such as `_convert_to_binance_symbol` maintain a fixed whitelist, defeating the purpose of dynamic discovery and breaking less common assets returned by the scanners.【F:app/services/market_analysis_core.py†L913-L943】

## 3. Remediation blueprint (enterprise-grade, no fixed symbol limits)

### 3.1 Exchange & symbol registry

- Introduce a dedicated `ExchangeUniverseService` that resolves the active exchange list for a user. Populate it from `ExchangeAccount` (or tenancy configuration) and cache it per user in Redis with short TTLs; fall back to platform defaults only when a user has no active links.【F:app/services/master_controller.py†L1105-L1158】
- Build an `AssetRegistry` backed by Redis/PostgreSQL that stores, per `(user, exchange, asset_type)`, the last successful discovery result. Seed it asynchronously using the existing `_discover_*` routines, but never run them inline with API requests.【F:app/services/market_analysis_core.py†L2318-L2433】【F:app/services/market_analysis_core.py†L4051-L4310】
- Add an async background job (Render worker or FastAPI startup task) that refreshes each user’s connected exchanges on a rolling schedule (e.g., staggered cron) and republishes the discovered symbol list. When discovery fails, keep serving the last known good snapshot instead of blocking.

### 3.2 Request-path execution model

- Refactor `realtime_price_tracking` to accept structured inputs (`Iterable[SymbolDescriptor]`) instead of comma strings and fetch the user-specific exchange roster from the registry. Use `asyncio.Semaphore` plus `asyncio.wait_for` per exchange task to cap latency (e.g., 3–5 s) while still letting unlimited symbols flow through in batches.【F:app/services/market_analysis_core.py†L265-L397】
- Stream results back as soon as each symbol’s quorum completes (e.g., use `asyncio.as_completed`) and merge with cached snapshots so large universes are processed progressively rather than sequentially.
- Replace the per-call `ClientSession` creation in `DynamicExchangeManager` with lifetime-managed sessions keyed by exchange, honouring the API’s base URLs and credentials while enabling connection reuse.【F:app/services/market_analysis_core.py†L105-L145】

### 3.3 Resilient market-data feeds

- Rewrite `_check_rate_limit` to interrogate the existing `CircuitBreaker` instances (`await circuit_breaker._should_try()`) and store breaker open times alongside them, preventing AttributeErrors and re-enabling the fast primary feeds.【F:app/services/market_data_feeds.py†L243-L266】
- Wrap `get_multiple_prices` and other `aiohttp` calls in explicit `ClientTimeout` plus retry/backoff logic; on timeout, return cached registry data so chat and dashboard consumers still receive a bounded response time.【F:app/services/market_data_feeds.py†L472-L535】
- Expand symbol mapping to consult the `AssetRegistry` output instead of static dicts, falling back to static pairs only when a symbol has never been discovered.【F:app/services/market_analysis_core.py†L913-L943】

### 3.4 Opportunity & scanner alignment

- Adjust the chat opportunity flows to request symbols from the registry based on scenario (e.g., top 20 by rolling volume on the user’s exchanges) rather than a fixed “SMART_ADAPTIVE” placeholder, ensuring scans scale with each user’s footprint without artificial caps.【F:app/services/master_controller.py†L1105-L1158】
- Ensure arbitrage and inefficiency scanners operate on the same cached data so subsequent calls reuse the already-fetched orderbook/ticker snapshots, minimising duplicate upstream load.【F:app/services/market_analysis_core.py†L2435-L2648】

### 3.5 Operational safeguards

- Emit structured metrics (success counts, latency buckets) whenever discovery jobs or hot-path aggregations fall back to cached data, so Render monitoring can alert on real degradation instead of silent timeouts.
- Provide admin tooling to purge or pre-warm the registries, ensuring new deployments can repopulate discovery data before traffic hits the user-facing endpoints.

## 4. Validation strategy

1. Unit-test the refactored `_check_rate_limit` and new registry services to confirm open breakers and rate limits behave correctly under concurrency.【F:app/services/market_data_feeds.py†L243-L266】
2. Integration-test `realtime_price_tracking` with mocked slow exchanges to verify per-exchange timeouts and streaming responses prevent 180 s stalls even when dozens of symbols are requested.【F:app/services/market_analysis_core.py†L265-L397】
3. End-to-end smoke tests for `/trading/market-overview` and chat opportunity prompts to ensure they receive responses when CoinGecko and other upstreams are artificially delayed, exercising cache fallbacks instead of hanging.【F:app/services/market_data_feeds.py†L472-L535】

## 5. Expected outcome

Implementing the above restores a truly dynamic, user-scoped market-analysis flow: discovery runs in the background, hot requests pull from cached inventories, and every network call is guarded by explicit deadlines. The UI and chat layers regain sub-second responses without sacrificing breadth—the system can enumerate hundreds of assets per user because the work is scheduled outside the request lifecycle and reused across services.
