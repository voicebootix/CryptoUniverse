# Persona Leverage Reference

Each AI trading persona in CryptoUniverse has a fixed maximum-leverage ceiling
that is set at startup and governs every trade it places.  
The table below shows those values with the exact source lines where they are
defined, so you can verify the numbers directly in the codebase.

---

## Leverage ceilings per persona

| Persona name | Trading mode | `max_leverage` | Source – leverage | Source – persona name |
|---|---|---|---|---|
| Warren – Conservative Financial Advisor | `conservative` | **1×** | `app/services/master_controller.py:126` | `app/services/conversational_ai_orchestrator.py:215` |
| Alex – Strategic Portfolio Manager | `balanced` | **3×** | `app/services/master_controller.py:142` | `app/services/conversational_ai_orchestrator.py:224` |
| Hunter – Aggressive Growth Manager | `aggressive` | **5×** | `app/services/master_controller.py:158` | `app/services/conversational_ai_orchestrator.py:233` |
| Apex – Ultimate Performance Manager | `beast_mode` | **10×** | `app/services/master_controller.py:174` | `app/services/conversational_ai_orchestrator.py:242` |

---

## Where the numbers live

### 1 · `app/services/master_controller.py` — `MasterSystemController.__init__`

The `TradingModeConfig` dataclass (line 61) holds `max_leverage: float`.  
`MasterSystemController.__init__` (line 89) builds `self.mode_configs` (line 120)
with one entry per `TradingMode`:

```
line 121-136  TradingMode.CONSERVATIVE  → max_leverage=1.0
line 137-152  TradingMode.BALANCED      → max_leverage=3.0
line 153-168  TradingMode.AGGRESSIVE    → max_leverage=5.0
line 169-185  TradingMode.BEAST_MODE    → max_leverage=10.0
```

The leverage value is enforced at trade time in
`TradingStrategiesService._calculate_leveraged_position_size`
(`app/services/trading_strategies.py:643`).

### 2 · `app/services/conversational_ai_orchestrator.py` — `_initialize_personalities`

`ConversationalAIOrchestrator._initialize_personalities` (line 211) maps each
`TradingMode` to its human-readable persona identity:

```
line 214-222  TradingMode.CONSERVATIVE  → "Warren - Conservative Financial Advisor"
line 223-231  TradingMode.BALANCED      → "Alex - Strategic Portfolio Manager"
line 232-240  TradingMode.AGGRESSIVE    → "Hunter - Aggressive Growth Manager"
line 241-249  TradingMode.BEAST_MODE    → "Apex - Ultimate Performance Manager"
```

The same mapping is also present in `UnifiedChatService.personalities`
(`app/services/unified_chat_service.py`), which is the service used by the chat
endpoints.  Both dictionaries are built from the same `TradingMode` enum so they
stay in sync.
