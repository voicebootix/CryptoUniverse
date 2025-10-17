# Signal Intelligence Delivery Feature Integration Plan

## 1. Purpose & Immediate Launch Objective
- Deliver an enterprise-grade **Signal Intelligence** programme in a single deployment cycle that reuses the existing 5-phase orchestration instead of staging phased rollouts.
- Provide manual execution signals, assisted follow-up inside chat, and optional autonomous execution triggers without duplicating current AI or billing logic.
- Ensure enrolment, delivery, and auditing work uniformly across Telegram, web UI, and API entry points from day one.

## 2. Architectural Alignment with Existing Systems
- **UnifiedChatService** remains the command surface for all user-facing conversations; it already holds references to the chat AI layer, master controller, credit ledger touch points, and interface-aware routing so it can surface signal enrolment, confirmations, and escalations without new adapters.【F:app/services/unified_chat_service.py†L155-L206】
- **ChatAIService** continues to handle natural-language responses while the 5-phase pipeline runs validations; signal announcements should use this service for conversational context and the AI Consensus stack for execution readiness.【F:app/services/chat_ai_service.py†L1-L198】
- **MasterSystemController** supplies the validated 5-phase orchestration—Market Analysis → Strategy → Portfolio Risk → AI Consensus → Execution—which the signal dispatcher will call in "analysis only" mode to keep insights aligned with autonomous trading telemetry.【F:app/services/master_controller.py†L2750-L2839】
- **BackgroundServiceManager** already coordinates scheduled workloads and will host the signal scanning loop alongside existing health, market sync, and autonomous tasks to guarantee consistent operations management.【F:app/services/background.py†L1-L177】
- **Strategy & Credit infrastructure** (UserStrategyAccess, CreditLedger, marketplace services) continue to enforce entitlement, pricing, and credit debits so the signal feature shares auditing and governance controls with live trading.【F:app/models/strategy_access.py†L1-L184】【F:app/services/credit_ledger.py†L1-L200】
- **Telegram Commander & API endpoints** already manage secure messaging, webhook orchestration, and user-level permissions, making them the delivery and onboarding backbone for signal alerts.【F:app/services/telegram_commander.py†L1-L200】【F:app/api/v1/endpoints/telegram.py†L1-L200】

## 3. Data Model Extensions (Single Migration)
Create one Alembic migration that introduces the following PostgreSQL tables without mock placeholders:
- `signal_channels` — primary key UUID, `strategy_bundle_id` (FK to strategy catalogue or marketplace), `name`, `description`, `default_cadence_seconds`, `min_confidence`, `auto_execution_allowed`, `metadata` JSONB, `created_at`, `updated_at`.
- `signal_subscriptions` — UUID PK, FK to `users` and `signal_channels`, `delivery_interfaces` JSONB (web/chat/telegram/webhook flags), `cadence_override_seconds`, `credit_plan` (enum: per_alert, monthly, enterprise), `status` (active, paused, cancelled), `credits_reserved`, `last_delivery_at`, `created_at`, `updated_at`.
- `signal_events` — UUID PK, FK to `signal_channels`, `phase_snapshot` JSONB (5-phase outputs), `symbol`, `direction`, `confidence_score`, `risk_band`, `suggested_size_usd`, `stop_loss`, `take_profit`, `created_at`.
- `signal_delivery_logs` — UUID PK, FK to `signal_events` and `signal_subscriptions`, `interface`, `delivery_status`, `credits_consumed`, `execution_triggered` (boolean), `delivered_at`, `acknowledged_at`, `error_detail`.
Add foreign-key constraints back to `user_strategy_access` for entitlement checks and indexes on `(channel_id, created_at)` and `(subscription_id, delivered_at)` to keep auditing fast.【F:app/models/strategy_access.py†L36-L184】

## 4. Services & Workflows
- **SignalEvaluationService** (new module) orchestrates the 5-phase pipeline via `MasterSystemController.execute_5_phase_autonomous_cycle`, capturing the phase outputs but flagging the request as `analysis_only=True` to skip live orders while still logging risk and consensus metrics.【F:app/services/master_controller.py†L2754-L2831】
- **SignalChannelService** centralises channel metadata management, entitlement validation against `UserStrategyAccess`, and credit reservation using `CreditLedger.consume_credits` so pricing rules stay consistent.【F:app/models/strategy_access.py†L36-L184】【F:app/services/credit_ledger.py†L164-L200】
- **SignalDeliveryService** plugs into Telegram Commander, Unified Chat sessions, and webhook emitters:
  - Telegram deliveries call `TelegramCommanderService.send_alert` with a dedicated `signal` template containing price targets and inline buttons for "Acknowledge", "Execute via Bot", and "Snooze" actions.
  - Web/UI deliveries push structured messages into active chat sessions using `UnifiedChatService` session context so the Chat AI immediately follows up with rationale and options.【F:app/services/unified_chat_service.py†L155-L206】
  - API/webhook deliveries reuse the existing signed webhook framework from system alerts to satisfy enterprise audit requirements.
- **SignalExecutionBridge** funnels user acknowledgements back into the 5-phase execution path: manual confirmations keep the event logged; "execute" responses call `MasterSystemController` with the captured opportunity payload so trading reuses the existing guardrails.【F:app/services/master_controller.py†L2754-L2831】

## 5. User Onboarding & Channel Management (Immediate Availability)
### Web & Chat Interfaces
1. Extend the unified chat intent map with a `"signal_center"` intent that lists available channels filtered by `UserStrategyAccess` and remaining credits. The conversation is rendered through `ChatAIService` so messaging stays natural while the master controller supplies confidence data.【F:app/services/unified_chat_service.py†L155-L206】【F:app/services/chat_ai_service.py†L33-L198】
2. When a user opts in, UnifiedChatService issues a backend call to `/signals/subscribe` (new API endpoint) that writes the subscription row, reserves credits through `CreditLedger`, and seeds the chat session context with subscription metadata for future reference.【F:app/services/credit_ledger.py†L164-L200】
3. Subsequent signals appear inline inside the active session with structured cards (strategy, timeframe, stop/target, credit cost). Chat AI handles conversational explanations, and the user can trigger execution or snooze without leaving the interface.【F:app/services/chat_ai_service.py†L33-L198】

### Telegram Onboarding
1. Augment the `/connect` flow to include signal preferences—frequency, eligible strategies, default position sizing—stored on the `UserTelegramConnection` record alongside existing notification/trading flags.【F:app/api/v1/endpoints/telegram.py†L115-L200】
2. Register `/signals` and `/signalsettings` commands inside Telegram Commander to toggle subscriptions, review usage, and change thresholds. Command handlers consult `SignalChannelService` for entitlement and credit checks before acknowledging.【F:app/services/telegram_commander.py†L1-L200】
3. Deliver alerts via `send_alert` with inline keyboard buttons mapped to webhook callbacks; acknowledgements and execution requests update `signal_delivery_logs` and optionally invoke UnifiedChatService to mirror the update inside the user’s primary conversation thread for cross-channel consistency.【F:app/services/telegram_commander.py†L1-L200】【F:app/services/unified_chat_service.py†L155-L206】

### API & Enterprise Hooks
- Introduce `/signals/channels`, `/signals/subscribe`, `/signals/events`, and `/signals/deliveries` endpoints secured with the same auth stack as trading endpoints so programmatic clients can manage subscriptions and retrieve historical performance for compliance dashboards.
- Offer webhook registration per subscription with HMAC signatures identical to existing alerting flows to guarantee parity with current enterprise SLAs.

## 6. Signal Operations Pipeline (Single Deployment Checklist)
1. **Schema Migration** – Deploy the Alembic migration for all signal tables and update SQLAlchemy models in one release.
2. **Service Wiring** – Register `SignalEvaluationService`, `SignalChannelService`, `SignalDeliveryService`, and `SignalExecutionBridge` with dependency injection factories so they can be reused by chat, API, and background tasks.
3. **Background Scheduler** – Add a `signal_dispatch` entry to `BackgroundServiceManager.start_all` with Redis locks to honour per-channel cadence without colliding with existing autonomous cycles.【F:app/services/background.py†L138-L177】
4. **Unified Chat Enhancements** – Extend session context schemas, intents, and message builders to surface signal enrolment and delivery while leveraging `ChatAIService` for narrative responses.【F:app/services/unified_chat_service.py†L155-L206】【F:app/services/chat_ai_service.py†L33-L198】
5. **Telegram Command Updates** – Implement new command handlers, webhook callbacks, and message templates using the existing commander so alerts share authentication, throttling, and auditing paths.【F:app/services/telegram_commander.py†L1-L200】【F:app/api/v1/endpoints/telegram.py†L1-L200】
6. **Credit & Billing Integration** – Configure pricing in the marketplace admin so channel activation reserves credits and each delivered signal posts a usage transaction through `CreditLedger.consume_credits` with metadata referencing the event ID.【F:app/services/credit_ledger.py†L164-L200】
7. **Monitoring & Analytics** – Extend observability dashboards with metrics sourced from `signal_delivery_logs` (delivery latency, acknowledgements, execution rate) and correlate with existing trading KPIs for compliance reporting.

## 7. Security, Compliance, and Reliability Controls
- Enforce entitlement checks before scheduling or delivering any signal; subscriptions inherit the same revocation paths as strategy access for instant shutdowns.【F:app/models/strategy_access.py†L36-L184】
- Apply credit sufficiency checks at both subscription time and each delivery to prevent overdrafts, leveraging `InsufficientCreditsError` handling already present in the ledger.【F:app/services/credit_ledger.py†L164-L200】
- Maintain a full audit chain via `signal_delivery_logs`, storing Telegram callback payloads, chat acknowledgements, and webhook retries for regulatory review.
- Integrate with the emergency stop mechanisms in MasterSystemController so operations can pause signal generation during market stress with the same kill-switch used for autonomous trading.【F:app/services/master_controller.py†L2754-L2831】
- Use the existing rate limiter and Telegram authentication tokens to ensure that high-volume signal bursts remain compliant with platform constraints while keeping user data protected.【F:app/api/v1/endpoints/telegram.py†L115-L200】

This single-release integration plan keeps Signal Intelligence tightly coupled with the existing enterprise AI trading stack, delivering immediate value across chat, web, and Telegram without redundant services or placeholder logic.
