# Manual Trading Dashboard Evidence

This note highlights the concrete parts of `frontend/src/pages/dashboard/ManualTradingPage.tsx` that implement the manual trading enhancements requested for parity with the chat-based AI workflow. Line numbers reference the current repository revision.

## Shared backend data and session lifecycle
- The page consumes the same portfolio, exchange, strategy, AI consensus, credit, and chat session stores used by the chat UI, guaranteeing live backend data rather than mock placeholders (`usePortfolioStore`, `useStrategies`, `useAIConsensus`, `useCredits`, and `useChatStore`). See lines 113-168 of the component.
- `ensureSessionId` wraps `initializeSession()` with a promise guard so concurrent callers reuse one initialization and share the resulting chat session ID (lines 215-241).

## Streaming AI workflow parity
- `runLiveWorkflow` opens the `/unified-chat/stream` SSE endpoint, logs each phase, streams incremental content, and persists AI metadata for later actions (lines 420-512).
- Completion logic updates credits, refreshes portfolio data, and caches the AI summary for actionable decisions (lines 500-505).
- The message handler never injects mock data; it simply forwards the real-time stream into the manual dashboard.

## Manual triggers for every AI action
- `handleConsensusAction` exposes the same opportunity scanning, trade validation, risk assessment, portfolio review, market analysis, and final consensus calls that the chat assistant provides (lines 612-729).
- Strategy execution is wired through `useStrategies` so any unlocked or purchased strategy can be run directly (lines 1473-1507).
- `applyAiRecommendationToTrade` lets operators push AI-suggested parameters into the manual trade form, while `handleTradeSubmit` executes live orders through `/trading/execute` (lines 550-593, 1392-1437).

## Real-time telemetry and transparency
- The workflow tab shows the phase visualizer, live streaming log, historical log list, AI summary, and insights feed, mirroring the chat-side transparency (lines 1338-1469).
- The risk tab surfaces live positions, AI system health, consensus history, and websocket market data so operators can track balances and scans in real time (lines 1566-1692).
- Credits are refreshed after each AI call or trade, keeping the single credit ledger in sync (lines 503-505, 584-586, 732-734).

These references demonstrate that the manual dashboard now exercises the same backend-driven capabilities as the chat workflow while presenting the AI process step-by-step with live data streams.
