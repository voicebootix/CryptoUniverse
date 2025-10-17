# Signal Intelligence Delivery – CTO Action Checklist

This checklist enumerates the concrete work required to ship the Signal Intelligence delivery feature in a single release while reusing existing orchestration, chat, billing, and automation systems. Each item is production-critical; owners are accountable for completion before launch.

## 1. Data Model & Persistence
- [ ] **Create Alembic migration** introducing `signal_channels`, `signal_subscriptions`, `signal_events`, and `signal_delivery_logs` tables with UUID PKs, FK links to `users`, `user_strategy_access`, and indexes on `(channel_id, created_at)` and `(subscription_id, delivered_at)`.
- [ ] **Implement SQLAlchemy models** in `app/models/signal_channel.py` (new file) covering ORM classes, relationships to `User`, `UserStrategyAccess`, and credit metadata.
- [ ] **Register metadata imports** inside `app/models/__init__.py` so the new models participate in migrations and session binding.
- [ ] **Seed initial channel definitions** via a data migration or management command leveraging existing marketplace strategy IDs to guarantee day-one availability.

## 2. Service Layer Construction
- [ ] **Build `SignalChannelService`** in `app/services/signal_channel_service.py` handling channel CRUD, entitlement validation via `UserStrategyAccess`, and credit plan evaluation using `CreditLedger`.
- [ ] **Implement `SignalEvaluationService`** wrapping `MasterSystemController.execute_5_phase_autonomous_cycle(..., analysis_only=True)` to capture the five-phase snapshot without issuing orders.
- [ ] **Add `SignalDeliveryService`** coordinating message templates for Unified Chat, Telegram Commander, and webhook payloads, persisting delivery outcomes to `signal_delivery_logs`.
- [ ] **Create `SignalExecutionBridge`** routing acknowledgements and execute commands back into `MasterSystemController` with captured `SignalEvent` payloads.
- [ ] **Wire dependency factories** within `app/services/__init__.py` or relevant DI containers so background tasks, API endpoints, and chat flows can request these services consistently.

## 3. Background Scheduling & Automation
- [ ] **Extend `BackgroundServiceManager`** to register a `signal_dispatch` scheduled job with Redis locking, per-channel cadence enforcement, and error isolation consistent with existing autonomous jobs.
- [ ] **Implement dispatcher loop** that loads eligible channels, evaluates opportunities through `SignalEvaluationService`, records `SignalEvent` entries, and hands them to `SignalDeliveryService`.
- [ ] **Integrate emergency stop hooks** to respect MasterSystemController kill switches and market-halt flags before processing any signal batch.

## 4. API Surface & Webhooks
- [ ] **Expose REST endpoints** under `app/api/v1/endpoints/signals.py`: `/signals/channels`, `/signals/subscribe`, `/signals/events`, `/signals/deliveries`, and webhook callback handlers for acknowledgements and executions.
- [ ] **Register routes** in the FastAPI router assembly (`app/api/v1/router.py`) with authentication and rate limiting mirroring trading endpoints.
- [ ] **Serialize responses** using Pydantic schemas in `app/schemas/signal.py`, ensuring confidence scores, risk bands, and pricing metadata match database representations.
- [ ] **Reuse existing webhook signer** utilities to emit HMAC-secured payloads for enterprise subscribers; add tests covering signature verification.

## 5. Unified Chat & Web Experience
- [ ] **Update intent map** inside `UnifiedChatService` to include a `signal_center` flow listing available channels based on `UserStrategyAccess` and remaining credits.
- [ ] **Persist chat session context** with active signal subscriptions so responses can reference current status, recent deliveries, and credit consumption.
- [ ] **Extend message builders** to render structured cards (strategy, timeframe, stop/target, credit cost) and actionable buttons for acknowledge, execute, and snooze options.
- [ ] **Ensure ChatAIService prompts** incorporate signal explanations by injecting the phase snapshot summaries for conversational clarity.

## 6. Telegram Integration
- [ ] **Enhance `/connect` wizard** in `app/api/v1/endpoints/telegram.py` to capture signal preferences (frequency, eligible strategies, default size) and persist them alongside existing connection data.
- [ ] **Register `/signals` and `/signalsettings` commands** in `TelegramCommanderService`, delegating to `SignalChannelService` for validation and state updates.
- [ ] **Implement inline keyboards** for deliveries that post back to webhook callbacks, updating `signal_delivery_logs` and triggering execution or snooze actions.
- [ ] **Mirror Telegram actions** into Unified Chat sessions to keep multi-channel conversations synchronized.

## 7. Credit & Billing Integration
- [ ] **Configure credit reservation** when subscriptions are created, using `CreditLedger.consume_credits` to lock required balances per plan.
- [ ] **Debit credits per delivery** with granular metadata linking `signal_delivery_logs` to ledger transactions for auditability.
- [ ] **Update marketplace administration** tooling or seed scripts so pricing tiers for signal channels appear in the existing strategy marketplace UI.
- [ ] **Add insufficient credit handling paths** with automated notifications (chat + email) prompting top-ups before suspending deliveries.

## 8. Observability, Compliance, and QA
- [ ] **Add metrics collection** exporting delivery latency, acknowledgement rate, execution conversion, and failure counts to the monitoring stack (Prometheus/Grafana dashboards).
- [ ] **Create audit queries** and admin endpoints to review historical signals, including Telegram callback payloads and webhook retries.
- [ ] **Develop automated tests** covering migrations, service orchestration, API contract, chat flows, Telegram commands, credit debits, and kill-switch behaviour.
- [ ] **Perform penetration and load testing** focused on Telegram webhook bursts, background dispatcher throughput, and concurrent execution requests.

## 9. Launch & Operations Readiness
- [ ] **Draft runbooks** detailing dispatcher recovery, credit reconciliation, and manual override procedures for the operations team.
- [ ] **Train support staff** on onboarding scripts for web, Telegram, and enterprise API customers.
- [ ] **Execute end-to-end dry run** from subscription to autonomous execution in staging with production-like credentials and exchanges.
- [ ] **Sign off launch review** confirming all checklist items are complete, metrics dashboards are green, and rollback plans are documented.

Completing this list ensures the Signal Intelligence feature is production-ready, auditable, and aligned with Crypto Universe’s enterprise standards on day one.
