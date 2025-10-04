# Opportunity Scan Fix Evaluation

## Summary
Recent changes introduced the shared price cache and preloading pipeline in
`MarketAnalysisService` with the goal of accelerating opportunity discovery.
A manual review of the runtime paths shows that the fix still leaves the chat
scan vulnerable to multi-minute delays.

## Key findings

1. **Price preloading still performs hundreds of live HTTP calls.**
   `_preload_price_universe` gathers up to `user_profile.opportunity_scan_limit`
   assets (50–1000 depending on tier) and invokes
   `market_analysis_service.preload_exchange_prices` for each entry.
   Because every preload delegates to `get_exchange_price`, the system will
   issue one outbound request per asset/exchange pair whenever the cache is
   cold. With a 5-second timeout and concurrency fixed at 20, warming 1000
   pairs can still consume more than four minutes on a cold deployment.

2. **Price requests still fan out sequentially per exchange.**
   `get_exchange_price` looks up Redis/in-memory caches but, on a miss, calls
   `_fetch_symbol_price_uncached`, which performs a live REST request per
   exchange without batching. The cache does not help the first request and the
   preloader simply moves this latency earlier in the request lifecycle.

3. **Strategy scanners immediately read live prices when cache is cold.**
   The trading strategies now call the shared price cache, but when the cache
   is empty (Render cold start, new symbol, Redis flush) each strategy still
   blocks on the same `_fetch_symbol_price_uncached` path. With dozens of
   symbols per strategy, the chat flow continues to trigger hundreds of
   5-second waits before the model can respond.

4. **Frontend timeout window remains 180 seconds.**
   The Axios client used by the chat UI still aborts at three minutes, so the
   request will surface the "I'm having difficulty" fallback whenever the
   opportunity scan exceeds that window—precisely what happens during cold
   starts or slow upstream exchanges.

## Conclusion
The price cache and preload hooks reduce duplicate calls once data is warm, but
on the first request they still execute a large number of blocking outbound
calls. As a result, the Render deployment continues to time out before the chat
can return opportunities. Additional architectural changes (background
precomputation, tighter per-request budgets, or streaming partial results) are
needed before the issue can be considered resolved.
