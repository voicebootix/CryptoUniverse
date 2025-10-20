# Opportunity Discovery Verification Notes

This document summarizes the repository-based review confirming the behaviour outlined in external screenshots and highlighting the one contradiction observed.

## Follow-up Claim Review ("backend finds real opportunities but only streams templates")
- The chat service streams opportunity-discovery progress and, once results exist, builds the AI prompt from the real `opportunities`, strategy performance, portfolio optimisation snapshot, and user profile contained in `context_data` (see `app/services/unified_chat_service.py`, lines 2961-3014 and 3431-3698).
- A template/fallback response is emitted only if the opportunity payload is missing—triggered by the explicit guard that logs a warning before returning the canned "Please wait" message (`app/services/unified_chat_service.py`, lines 3792-3809).
- Opportunity discovery itself aggregates real strategy scanner output into the cached payload that the chat layer consumes; when scanners return opportunities the final response stores them and marks the scan complete rather than leaving the placeholder (`app/services/user_opportunity_discovery.py`, lines 687-705 and 913-1004).
- Therefore the repository contradicts the claim that the backend "sends templates instead of real opportunity data" when opportunities are found. Any template output implies the discovery payload never received populated results (e.g., the scan failed or returned empty), which must be investigated at runtime.

- Runtime log snippets from Render that allegedly show populated opportunities cannot be verified from the repository alone; confirming them requires access to the deployment environment.

### Why a user can still see the template response
- The chat prompt only falls back to the template when `_build_response_prompt` is invoked without a populated opportunity payload; this occurs when the cached discovery record still reports a `scan_state` of `pending` or `partial`, or when the backend never persisted the completed payload before the chat reply was generated (`app/services/unified_chat_service.py`, lines 2607-2668 and 3795-3808).
- The refresh loop treats any empty or errored scan as partial, so exceptions during strategy scanning, missing active strategies, or credit/portfolio failures leave the cache in the placeholder state that produces the template (`app/services/unified_chat_service.py`, lines 1349-1387; `app/services/user_opportunity_discovery.py`, lines 669-742 and 913-1004).
- Once a non-partial payload is cached, later chat responses reuse it and build the detailed opportunity prompt; continually seeing the template indicates the background job never completed, so deployment logs must be checked for discovery failures or absent strategy data.

## Confirmed Behaviours
- The unified chat service launches opportunity discovery in a background refresh, emits staged progress updates such as `scanning_strategies`, and seeds the UI with a placeholder message (“Scanning your active strategies for new opportunities…”).
- `discover_opportunities_for_user` first yields a pending payload, then iterates across active strategies, caching results and assembling the final response. Users lacking active strategies receive the fallback message about activating free strategies.
- The strategy marketplace catalog explicitly sets the `risk_management` and `portfolio_optimization` strategies to zero base cost and zero per-execution cost, ensuring they remain free.

## Contradiction Identified
- The FastAPI router defines `/api/v1/auth/login` as a POST handler; there is no logic that would cause the application to respond with “Only GET requests are allowed.” Any such response must originate from deployment-specific configuration, not the repository implementation.

## Deployment Caveats
- Runtime issues observed on Render—such as red toast errors, WebSocket failures, or HTTP 403 responses—cannot be conclusively validated through static code analysis and must be investigated within the deployment environment.
