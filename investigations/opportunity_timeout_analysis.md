# Opportunity Discovery Chat Timeout Investigation

## Summary
- **Environment:** Production deployment at `cryptouniverse.onrender.com` and frontend `cryptouniverse-frontend.onrender.com` (Render).
- **User Account:** `admin@cryptouniverse.com` / `AdminPass123!`.
- **Focus:** Chat messages that ask the AI money manager to "find opportunities" hang until the client times out. Streaming responses on the frontend fail for the same request type.
- **Latest trace correlation:** A follow-up Render-hosted trace (205 s successful responses, 490 s client timeout on another phrasing, HTTP 405s on `/chat/quick/opportunities`) reproduces the same slow synchronous opportunity discovery path rather than exposing a new defect. The "streaming" success recorded after ~180 s still reflects the delayed generator handoff described below, so the new trace aligns with the original diagnosis.

## Reproduction Steps
1. Authenticate via REST API:
   - `POST /api/v1/auth/login` succeeds and returns an access token (HTTP 200).【29622d†L1-L5】
2. Start a chat session:
   - `POST /api/v1/chat/message` with `"Hello"` returns immediately (HTTP 200) with a greeting and session ID (`eb712753-c295-48a3-9ea6-bfcc00e02468`).【fae607†L1-L4】
3. Ask for opportunities in the same session:
   - `POST /api/v1/chat/message` with `"Find some trading opportunities for me"` does not return before the 120 s client timeout and raises `ReadTimeoutError` on the client side.【78468a†L1-L45】

## Backend Findings
- `UnifiedChatService.process_message` performs four steps before it can send a response. Even in streaming mode it waits for `_gather_context_data(...)` to finish before returning the async generator that feeds SSE/WebSocket responses.【F:app/services/unified_chat_service.py†L1344-L1462】
- When the detected intent is `OPPORTUNITY_DISCOVERY`, `_gather_context_data` calls `user_opportunity_discovery.discover_opportunities_for_user(...)` directly and awaits the full discovery pipeline. The method only uses cached data if a prior scan succeeded; otherwise it performs a fresh scan before streaming can start.【F:app/services/unified_chat_service.py†L2209-L2315】
- `UserOpportunityDiscoveryService` is tuned for long-running scans. Its `_scan_response_budget` allows up to 150 s for a scan, it spins up concurrent tasks for every strategy, and it touches multiple subsystems (portfolio cache, asset discovery, optimization).【F:app/services/user_opportunity_discovery.py†L86-L153】【F:app/services/user_opportunity_discovery.py†L431-L500】
- The service starts new scans with `asyncio.create_task(...)` and then waits up to `_scan_response_budget` seconds for them to finish. Without cached results this means the chat request blocks until the scan completes. If the scan overruns, the chat call will also run past common HTTP timeouts (Render's ingress and the browser both default below 150 s).【F:app/services/user_opportunity_discovery.py†L431-L493】

## Frontend Findings
- The React chat UI opens an SSE connection to `/api/v1/unified-chat/stream` and expects to receive `processing` / `progress` events quickly. It passes the JWT token in the query string per `get_current_user_sse` requirements.【F:frontend/src/components/chat/ChatInterface.tsx†L295-L358】【F:app/api/dependencies/sse_auth.py†L20-L71】
- If the SSE stream fails it falls back to the REST endpoint `/unified-chat/message`, but the fallback uses the same synchronous backend path and therefore inherits the long-running call and timeout.【F:frontend/src/components/chat/ChatInterface.tsx†L404-L451】
- Because the backend does not return the SSE generator until after `_gather_context_data` completes, the browser never receives the initial event; the EventSource eventually emits `error`, triggering the fallback (which still times out).

### Relation to the new trace output
- The automated script's "✅ HTTP streaming working (183.60s, 10 chunks)" entry is consistent with `_gather_context_data` finishing only after opportunity discovery and then yielding cached progress chunks; the 183 s delay maps to the same blocking call chain documented above.【F:app/services/unified_chat_service.py†L1344-L1462】【F:app/services/unified_chat_service.py†L2209-L2315】
- Mixed results (20 s vs. 205 s vs. 490 s + timeout) mirror the `_scan_response_budget` and cache behavior in `UserOpportunityDiscoveryService`: cached runs return within ~20 s, uncached runs wait the full scan, and overruns exceed client limits.【F:app/services/user_opportunity_discovery.py†L86-L153】【F:app/services/user_opportunity_discovery.py†L431-L500】
- The repeated HTTP 405 on `/chat/quick/opportunities` reflects that the deployed API only exposes the quick helper at the versioned path `/api/v1/unified-chat/quick/opportunities`; calling the unprefixed `/chat/...` route therefore misses the FastAPI registration (POST handler lives on the versioned router).【F:app/api/v1/endpoints/unified_chat.py†L803-L832】【F:app/api/v1/router.py†L36-L52】

## Root Cause Hypothesis
1. **Synchronous opportunity discovery pipeline:** Opportunity scanning is engineered as a lengthy batch job (up to 150 s). The unified chat endpoint awaits the entire scan—even in streaming mode—before yielding the first byte to the client. Requests that lack cached results therefore exceed client/server timeouts.
2. **Streaming lifecycle mismatch:** Progress events are emitted only after the slow discovery call returns, so SSE/WebSocket streams cannot open in time. Frontend streaming then fails, and the REST fallback also stalls, producing the observed timeout.

## Suggested Next Steps
- Decouple opportunity discovery from the chat request. Options:
  - Kick off the discovery task in the background (similar to `/api/v1/opportunities/discover`) and immediately return cached/placeholder content with polling instructions.
  - Or allow streaming to begin before discovery finishes by yielding a generator that polls the in-progress task and emits progress updates while the scan runs.
- Lower `_scan_response_budget` or make it configurable so HTTP requests do not wait longer than platform limits.
- Ensure the frontend surfaces a clear message when the backend reports `status: scanning` so users are guided to retry/poll instead of hanging indefinitely.

These changes would keep the enterprise opportunity pipeline intact while preventing chat clients and SSE streams from hitting hard timeouts.
