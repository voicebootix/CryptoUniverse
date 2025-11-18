# CryptoUniverse – Source Documentation Pack (Claude Code Edition)
## PART 4: Remaining 30% Work & Task Breakdown

---

**← [Back to PART 3: Live Status](./DOCUMENTATION_PART_3_Live_Status.md)**

---

## 5. REMAINING 30% – TASK BREAKDOWN

This section converts all missing/buggy areas into **concrete, actionable tasks** ready to be turned into Jira/Linear/Trello tickets.

---

## 5.1 DEBUGGING TASKS (🔴 Fix Existing Issues)

### TASK-001: Fix "Method Not Allowed" Endpoint Errors

**Priority:** 🔴 CRITICAL
**Effort:** 2-4 hours
**Assigned To:** Backend Developer

**Problem:**
Multiple endpoints return `{"detail": "Method Not Allowed"}` despite code existing:
- `/api/v1/health/full`
- `/api/v1/exchanges`
- `/api/v1/paper-trading/status`
- `/api/v1/system/monitoring/metrics`
- `/api/v1/diagnostics/system`

**Root Cause:**
HTTP method mismatch in route registration (e.g., endpoint uses `@router.post()` but frontend calls GET).

**Steps to Reproduce:**
```bash
curl -X GET https://cryptouniverse.onrender.com/api/v1/exchanges \
  -H "Authorization: Bearer <valid_jwt>"
# Returns: {"detail": "Method Not Allowed"}
```

**Where to Start:**
1. Open `app/api/v1/endpoints/exchanges.py`
2. Check HTTP method decorators for each route
3. Compare with `app/api/v1/router.py` route registration
4. Fix method mismatches

**Expected Fix:**
```python
# BEFORE (incorrect):
@router.post("")
async def list_exchanges(...):
    ...

# AFTER (correct):
@router.get("")
async def list_exchanges(...):
    ...
```

**Acceptance Criteria:**
- [ ] All endpoints respond with 200 OK or proper error (not 405)
- [ ] Test all 30+ endpoints with curl
- [ ] Update API documentation
- [ ] Deploy and verify on production

**Files to Modify:**
- `app/api/v1/endpoints/exchanges.py`
- `app/api/v1/endpoints/paper_trading.py`
- `app/api/v1/endpoints/diagnostics.py`
- `app/api/v1/endpoints/system_monitoring.py`
- `app/api/v1/endpoints/health.py`

---

### TASK-002: Fix Health Check Authentication Requirement

**Priority:** 🟡 HIGH
**Effort:** 1-2 hours
**Assigned To:** Backend Developer

**Problem:**
Health check endpoints require JWT authentication, preventing external monitoring tools (Render, Datadog, etc.) from checking system health.

```bash
curl https://cryptouniverse.onrender.com/api/v1/health/ping
# Returns: {"detail": "Missing authorization header"}
# Expected: {"status": "ok"}
```

**Root Cause:**
`AuthMiddleware` applied globally to all `/api/v1/*` routes, including health checks.

**Where to Start:**
- File: `main.py` (middleware registration)
- File: `app/middleware/auth.py` (AuthMiddleware)
- File: `app/api/v1/endpoints/health.py`

**Expected Fix:**
```python
# main.py
# Add health check routes BEFORE applying auth middleware
app.include_router(health.router, prefix="/health", tags=["Health"])

# OR: Configure AuthMiddleware to exclude /health paths
auth_middleware = AuthMiddleware(
    exclude_paths=["/health", "/docs", "/openapi.json"]
)
```

**Acceptance Criteria:**
- [ ] `/api/v1/health/ping` returns 200 OK without auth
- [ ] `/api/v1/health/full` returns 200 OK without auth
- [ ] `/api/v1/health/database` still works
- [ ] All other endpoints still require auth
- [ ] External monitoring can access health checks

---

### TASK-003: Fix User Profile Endpoint (/auth/me)

**Priority:** 🟡 HIGH
**Effort:** 2-3 hours
**Assigned To:** Backend Developer

**Problem:**
```bash
GET /api/v1/auth/me
Authorization: Bearer <valid_jwt>
Response: {"detail": "Authentication service error"}
```

Valid JWT token, but endpoint fails to retrieve user profile.

**Root Cause (Hypothesis):**
- Database query failing (user not found)
- Tenant isolation filtering user incorrectly
- JWT `sub` claim not matching user_id format

**Where to Start:**
- File: `app/api/v1/endpoints/auth.py` → `get_current_user()` function
- File: `app/api/dependencies/auth.py` → user lookup logic
- File: `app/middleware/auth.py` → JWT parsing

**Debugging Steps:**
1. Add logging to `get_current_user()`:
   ```python
   logger.info("JWT sub claim", sub=token_payload.get("sub"))
   logger.info("User lookup", user_id=user_id)
   ```
2. Test with admin JWT: `sub: "7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af"`
3. Check if user exists in database:
   ```sql
   SELECT * FROM users WHERE id = '7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af';
   ```
4. Verify tenant_id filtering not excluding admin user

**Expected Fix:**
Fix database query or tenant filtering to allow admin user lookup.

**Acceptance Criteria:**
- [ ] `/auth/me` returns user profile with valid JWT
- [ ] Returns `user_id`, `email`, `role`, `credits`, etc.
- [ ] Works for all roles (admin, trader, viewer)
- [ ] Error messages more specific (not generic "service error")

---

### TASK-004: Enable Live Market Data Feeds

**Priority:** 🔴 CRITICAL
**Effort:** 8-16 hours
**Assigned To:** Backend Developer + Data Engineer

**Problem:**
All portfolio positions show `change_24h_pct: 0.0`, indicating no live price updates.
All strategies show `live_performance: "no_data"`.

**Root Cause:**
- Market data feeds not running
- Exchange APIs not connected
- Background jobs not scheduled (Celery)

**Where to Start:**
- File: `app/services/market_data_feeds.py` (85KB) - Price feed service
- File: `app/services/unified_price_service.py` (31KB) - Price aggregation
- File: `app/services/background.py` (89KB) - Background tasks
- File: `app/tasks/` - Celery task definitions

**Implementation Steps:**

**Step 1: Enable Real-Time Price Feeds**
```python
# app/services/market_data_feeds.py
async def start_price_feed_loop():
    """Continuously fetch prices every 60 seconds"""
    while True:
        try:
            await fetch_all_prices()
            await update_portfolio_positions()
            await asyncio.sleep(60)
        except Exception as e:
            logger.error("Price feed error", error=str(e))
            await asyncio.sleep(10)
```

**Step 2: Connect to Exchange Price APIs**
```python
# Use CCXT to fetch prices
import ccxt

exchange = ccxt.binance()
ticker = exchange.fetch_ticker('BTC/USDT')
# ticker = {'last': 95234.56, 'change': 2.34, ...}
```

**Step 3: Update Portfolio Positions**
```python
# app/services/portfolio_risk.py
async def update_position_prices():
    """Update all user positions with current prices"""
    positions = await get_all_positions()
    for position in positions:
        current_price = await get_current_price(position.symbol)
        position.current_value = position.amount * current_price
        position.change_24h_pct = calculate_change(...)
        await session.commit()
```

**Step 4: Schedule Background Job**
```python
# app/tasks/market_data.py
from celery import Celery

celery = Celery('cryptouniverse')

@celery.task
def update_prices_task():
    asyncio.run(update_position_prices())

# Schedule every 60 seconds
celery.conf.beat_schedule = {
    'update-prices': {
        'task': 'app.tasks.market_data.update_prices_task',
        'schedule': 60.0,
    },
}
```

**Acceptance Criteria:**
- [ ] Portfolio positions show live 24h price changes
- [ ] Prices update every 60 seconds (or faster)
- [ ] At least BTC, ETH, top 20 coins have live data
- [ ] Cache prices in Redis (60-second TTL)
- [ ] Background job runs reliably
- [ ] Error handling if exchange API fails

**Estimated Data Sources:**
- CoinGecko API (free tier: 50 calls/min)
- Binance Public API (free, no auth required)
- CCXT library (unified interface)

---

### TASK-005: Connect Real Exchange APIs for Trading

**Priority:** 🟡 HIGH
**Effort:** 16-24 hours
**Assigned To:** Backend Developer + Security Engineer

**Problem:**
No live trading occurring. All strategies show 0 trades executed.

**Requirements:**
1. User connects exchange account (Binance, Kraken, etc.)
2. Store API keys securely (already encrypted with AES-256)
3. Execute real trades via CCXT
4. Handle order lifecycle (placed → filled → completed)
5. Update portfolio in real-time

**Implementation Steps:**

**Step 1: Exchange Connection Flow**
```python
# app/api/v1/endpoints/exchanges.py

@router.post("/connect")
async def connect_exchange(
    exchange_name: str,
    api_key: str,
    api_secret: str,
    current_user: User = Depends(get_current_user)
):
    """Store encrypted exchange credentials"""
    # Encrypt API keys
    encrypted_key = encrypt(api_key)
    encrypted_secret = encrypt(api_secret)

    # Test connection
    exchange = ccxt.binance({'apiKey': api_key, 'secret': api_secret})
    balance = exchange.fetch_balance()

    # Store in database
    exchange_account = ExchangeAccount(
        user_id=current_user.id,
        exchange_name=exchange_name,
        api_key_encrypted=encrypted_key,
        api_secret_encrypted=encrypted_secret,
        is_active=True
    )
    await session.add(exchange_account)
    await session.commit()
```

**Step 2: Order Execution**
```python
# app/services/trade_execution.py

async def execute_market_order(
    user_id: str,
    symbol: str,
    side: str,  # "buy" or "sell"
    amount: float,
    exchange_name: str = "binance"
):
    """Execute market order on user's exchange account"""

    # Get user's exchange credentials
    exchange_account = await get_exchange_account(user_id, exchange_name)
    api_key = decrypt(exchange_account.api_key_encrypted)
    api_secret = decrypt(exchange_account.api_secret_encrypted)

    # Initialize CCXT exchange
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret
    })

    # Execute order
    order = exchange.create_market_order(
        symbol=symbol,
        side=side,
        amount=amount
    )

    # Store trade record
    trade = Trade(
        user_id=user_id,
        order_id=order['id'],
        symbol=symbol,
        side=side,
        amount=amount,
        price=order['price'],
        status="completed"
    )
    await session.add(trade)
    await session.commit()

    return trade
```

**Step 3: Deduct Credits**
```python
# After trade execution
await deduct_credits(user_id, credits_per_execution=1)
```

**Security Checklist:**
- [ ] API keys encrypted at rest (AES-256)
- [ ] API keys never logged
- [ ] API keys transmitted over HTTPS only
- [ ] Exchange connection tested before storage
- [ ] User can revoke exchange access
- [ ] Implement withdrawal whitelist (if supported by exchange)
- [ ] Rate limit trade execution (prevent spam)

**Acceptance Criteria:**
- [ ] User can connect Binance account via UI
- [ ] User can execute test trade (0.01 BTC)
- [ ] Trade appears in portfolio immediately
- [ ] Credits deducted correctly
- [ ] Order history stored in database
- [ ] Exchange API errors handled gracefully

---

## 5.2 COMPLETION TASKS (⚠️ Finish Partially Built Features)

### TASK-006: Complete OAuth Social Login

**Priority:** 🟡 MEDIUM
**Effort:** 8-12 hours
**Assigned To:** Backend + Frontend Developer

**What's Done:**
- OAuth service code exists (`app/services/oauth.py`)
- Google OAuth provider implemented
- GitHub OAuth provider implemented

**What's Missing:**
- OAuth app credentials (client ID/secret)
- Frontend "Sign in with Google" button
- OAuth callback route testing
- Account linking (if user already exists)

**Implementation Steps:**

**Step 1: Create OAuth Apps**
1. **Google OAuth:**
   - Go to https://console.cloud.google.com
   - Create project "CryptoUniverse"
   - Enable OAuth 2.0
   - Set redirect URI: `https://cryptouniverse.onrender.com/api/v1/auth/oauth/google/callback`
   - Get Client ID + Secret

2. **GitHub OAuth:**
   - Go to https://github.com/settings/developers
   - Create OAuth App "CryptoUniverse"
   - Set redirect URI: `https://cryptouniverse.onrender.com/api/v1/auth/oauth/github/callback`
   - Get Client ID + Secret

**Step 2: Add to Environment**
```bash
# .env
GOOGLE_OAUTH_CLIENT_ID=<from_google_console>
GOOGLE_OAUTH_CLIENT_SECRET=<from_google_console>
GITHUB_OAUTH_CLIENT_ID=<from_github>
GITHUB_OAUTH_CLIENT_SECRET=<from_github>
```

**Step 3: Frontend Integration**
```tsx
// frontend/src/pages/auth/LoginPage.tsx

<button onClick={() => handleGoogleLogin()}>
  <GoogleIcon />
  Sign in with Google
</button>

function handleGoogleLogin() {
  window.location.href = 'https://cryptouniverse.onrender.com/api/v1/auth/oauth/google';
}
```

**Step 4: Test OAuth Flow**
1. User clicks "Sign in with Google"
2. Redirected to Google consent screen
3. User approves permissions
4. Google redirects to `/auth/oauth/google/callback`
5. Backend creates/links user account
6. Backend issues JWT token
7. Frontend receives token, redirects to dashboard

**Acceptance Criteria:**
- [ ] "Sign in with Google" button works
- [ ] "Sign in with GitHub" button works
- [ ] New users created automatically via OAuth
- [ ] Existing users linked to OAuth account
- [ ] OAuth users skip email verification
- [ ] OAuth login faster than email/password

---

### TASK-007: Complete Stripe Payment Integration

**Priority:** 🟡 MEDIUM
**Effort:** 12-16 hours
**Assigned To:** Backend + Frontend Developer

**What's Done:**
- Stripe SDK integrated (`stripe==7.8.0`)
- Credit purchase endpoint exists
- Webhook handling implemented

**What's Missing:**
- Stripe test account setup
- Live webhook testing
- Payment UI flow (frontend)
- Receipt generation
- Subscription billing (monthly credits)

**Implementation Steps:**

**Step 1: Set Up Stripe Account**
1. Create Stripe account: https://dashboard.stripe.com/register
2. Get API keys (test mode):
   - Publishable key: `pk_test_...`
   - Secret key: `sk_test_...`
3. Create webhook endpoint:
   - URL: `https://cryptouniverse.onrender.com/api/v1/payments/webhook`
   - Events: `payment_intent.succeeded`, `payment_intent.failed`
   - Get webhook secret: `whsec_...`

**Step 2: Environment Configuration**
```bash
# .env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

**Step 3: Backend Payment Flow**
```python
# app/api/v1/endpoints/credits.py

@router.post("/purchase")
async def purchase_credits(
    amount_usd: float,  # e.g., $100
    current_user: User = Depends(get_current_user)
):
    """Create Stripe payment intent for credit purchase"""
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Create payment intent
    intent = stripe.PaymentIntent.create(
        amount=int(amount_usd * 100),  # Convert to cents
        currency="usd",
        metadata={
            "user_id": str(current_user.id),
            "credits": int(amount_usd / 0.10)  # $0.10 per credit
        }
    )

    return {
        "client_secret": intent.client_secret,
        "credits_to_add": int(amount_usd / 0.10)
    }
```

**Step 4: Frontend Payment UI**
```tsx
// frontend/src/pages/dashboard/CreditBillingCenter.tsx

import { loadStripe } from '@stripe/stripe-js';
import { Elements, CardElement } from '@stripe/react-stripe-js';

const stripePromise = loadStripe('pk_test_...');

function PurchaseCredits() {
  const [amount, setAmount] = useState(100);

  async function handlePurchase() {
    // Get payment intent from backend
    const { client_secret } = await api.post('/credits/purchase', { amount });

    // Confirm payment with Stripe
    const { error } = await stripe.confirmCardPayment(client_secret, {
      payment_method: { card: cardElement }
    });

    if (!error) {
      alert('Credits purchased successfully!');
      refreshBalance();
    }
  }

  return (
    <Elements stripe={stripePromise}>
      <CardElement />
      <button onClick={handlePurchase}>
        Purchase ${amount} (= {amount / 0.10} credits)
      </button>
    </Elements>
  );
}
```

**Step 5: Webhook Handler**
```python
# app/api/v1/endpoints/payments.py

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    import stripe
    event = stripe.Webhook.construct_event(
        payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )

    if event.type == "payment_intent.succeeded":
        payment_intent = event.data.object
        user_id = payment_intent.metadata.user_id
        credits = int(payment_intent.metadata.credits)

        # Add credits to user account
        await add_credits(user_id, credits)
        logger.info("Credits added", user_id=user_id, credits=credits)

    return {"status": "success"}
```

**Acceptance Criteria:**
- [ ] User can purchase credits with credit card
- [ ] Test mode: Use test card `4242 4242 4242 4242`
- [ ] Credits added immediately after payment
- [ ] Webhook receives payment confirmation
- [ ] Receipt emailed to user
- [ ] Payment history viewable in dashboard
- [ ] Refunds supported (manual for now)

---

### TASK-008: Implement Copy Trading Signal Distribution

**Priority:** 🟢 LOW (Future Feature)
**Effort:** 24-40 hours
**Assigned To:** Backend Developer + Infrastructure Engineer

**What's Done:**
- Signal generation engine (`signal_generation_engine.py`)
- Signal delivery service (`signal_delivery_service.py`)
- Profit sharing calculations (`profit_sharing_service.py`)
- Database models for signals

**What's Missing:**
- Real-time signal broadcasting (WebSocket or SSE)
- Follower auto-execution
- Signal latency monitoring
- Fraud detection (fake signals)
- Dispute resolution flow

**Implementation Steps:**

**Step 1: Signal Generation**
```python
# When trader executes strategy, generate signal
signal = Signal(
    publisher_id=trader.id,
    strategy_id=strategy.id,
    signal_type="BUY",
    symbol="BTC/USDT",
    entry_price=95000,
    stop_loss=93000,
    take_profit=98000,
    timestamp=datetime.utcnow()
)
await broadcast_signal(signal)
```

**Step 2: Signal Broadcast (WebSocket)**
```python
# app/services/signal_delivery_service.py

async def broadcast_signal(signal: Signal):
    """Send signal to all followers via WebSocket"""
    followers = await get_strategy_followers(signal.strategy_id)

    for follower in followers:
        await websocket_manager.send_to_user(follower.id, {
            "type": "trading_signal",
            "data": signal.dict()
        })
```

**Step 3: Auto-Execution (Follower Side)**
```python
# Frontend WebSocket handler
socket.on('trading_signal', async (signal) => {
  if (autoExecuteEnabled) {
    await api.post('/trading/execute', {
      symbol: signal.symbol,
      side: signal.signal_type,
      amount: calculatePositionSize(signal)
    });
  } else {
    showNotification('New signal from ' + signal.publisher_name);
  }
});
```

**Step 4: Profit Sharing**
```python
# When follower closes position, calculate profit share
follower_profit = position.pnl
publisher_share = follower_profit * 0.30  # 30% to publisher
platform_share = follower_profit * 0.00  # 0% to platform (for now)

await transfer_credits(
    from_user=follower_id,
    to_user=publisher_id,
    amount=publisher_share
)
```

**Acceptance Criteria:**
- [ ] Publisher executes trade → signal generated
- [ ] Followers receive signal within 100ms
- [ ] Follower can auto-execute or manual confirm
- [ ] Profit sharing calculated accurately
- [ ] Publisher dashboard shows earnings
- [ ] Signal history stored for audit

---

## 5.3 REFACTOR / CLEANUP TASKS (🔧 Technical Debt)

### TASK-009: Consolidate Chat Services

**Priority:** 🟢 LOW
**Effort:** 8-12 hours
**Assigned To:** Backend Developer

**Problem:**
Multiple chat service implementations found:
- `unified_chat_service.py` (216KB) - Main chat service
- `ai_chat_engine.py` (116KB) - AI chat engine
- `chat_service_adapters.py` (26KB) - Adapters
- `chat_service_adapters_fixed.py` (61KB) - Fixed adapters
- `conversational_ai_orchestrator.py` (42KB) - Orchestrator

**Why This Matters:**
- Duplicate code = harder maintenance
- Confusing for new developers
- Potential bugs if changes not synced

**Steps:**
1. Analyze all 5 chat service files
2. Identify overlapping functionality
3. Create single unified chat service
4. Migrate all endpoints to use unified service
5. Archive old files (don't delete, move to `/archive`)
6. Update imports across codebase

**Acceptance Criteria:**
- [ ] Single `chat_service.py` (or keep `unified_chat_service.py`)
- [ ] All chat endpoints work after refactor
- [ ] No duplicate logic
- [ ] Test coverage for chat features

---

### TASK-010: Remove Dead Code and Old Versions

**Priority:** 🟢 LOW
**Effort:** 4-8 hours
**Assigned To:** Any Developer

**Files to Review:**
- `admin.py.backup` (30KB) - Backup file in production
- `ai_chat_engine_fixes.py` (9KB) - Hotfix file
- `chat_service_adapters_fixed.py` (61KB) - "Fixed" version
- `app-minimal.py` - Minimal app version (unused?)
- `start-minimal.py` - Minimal start script (unused?)

**Steps:**
1. Search for `.backup`, `.old`, `_fixed`, `_v2` files
2. Verify they're not imported anywhere
3. Move to `/archive` folder or delete
4. Update documentation

**Acceptance Criteria:**
- [ ] No backup/temp files in production code
- [ ] All imports working
- [ ] Git history preserved

---

### TASK-011: Add Comprehensive Test Coverage

**Priority:** 🟡 MEDIUM
**Effort:** 40-60 hours
**Assigned To:** QA Engineer + Developers

**Current State:**
- Tests exist in `tests/` directory
- `conftest.py` set up correctly
- But coverage is incomplete

**Target Coverage:**
- **Unit Tests:** 80%+ coverage
- **Integration Tests:** 60%+ coverage
- **E2E Tests:** Critical user flows

**Tests to Add:**

**Authentication Tests:**
```python
# tests/api/test_auth.py

def test_login_success():
    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "TestPass123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_invalid_password():
    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "WrongPassword"
    })
    assert response.status_code == 401
```

**Trading Tests:**
```python
# tests/services/test_trading_strategies.py

async def test_execute_strategy():
    user = await create_test_user(credits=100)
    strategy = await create_test_strategy()

    result = await execute_strategy(
        user_id=user.id,
        strategy_id=strategy.id,
        symbol="BTC/USDT",
        amount=0.01
    )

    assert result.success == True
    assert result.credits_used == 1

    # Verify credits deducted
    user_credits = await get_credit_balance(user.id)
    assert user_credits == 99
```

**Acceptance Criteria:**
- [ ] 80% unit test coverage
- [ ] All API endpoints have tests
- [ ] All services have tests
- [ ] CI/CD runs tests automatically
- [ ] Test documentation updated

---

## 5.4 SUMMARY: TASK PRIORITY MATRIX

### Critical (Start Immediately)

| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| TASK-001: Fix Method Not Allowed | 🔴 Critical | 2-4h | Unblocks 6+ endpoints |
| TASK-004: Enable Market Data | 🔴 Critical | 8-16h | Shows live portfolio data |

### High Priority (This Week)

| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| TASK-002: Fix Health Auth | 🟡 High | 1-2h | Enables monitoring |
| TASK-003: Fix /auth/me | 🟡 High | 2-3h | Fixes user profile |
| TASK-005: Connect Exchanges | 🟡 High | 16-24h | Enables live trading |

### Medium Priority (This Month)

| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| TASK-006: Complete OAuth | 🟡 Medium | 8-12h | Better UX |
| TASK-007: Stripe Payments | 🟡 Medium | 12-16h | Revenue generation |
| TASK-011: Add Tests | 🟡 Medium | 40-60h | Code quality |

### Low Priority (This Quarter)

| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| TASK-008: Copy Trading | 🟢 Low | 24-40h | Future feature |
| TASK-009: Consolidate Chat | 🟢 Low | 8-12h | Code cleanliness |
| TASK-010: Remove Dead Code | 🟢 Low | 4-8h | Code cleanliness |

---

## 5.5 ESTIMATED TIMELINE

**Sprint 1 (Week 1-2): Critical Fixes**
- TASK-001: Fix endpoint routing (4h)
- TASK-002: Fix health checks (2h)
- TASK-003: Fix /auth/me (3h)
- TASK-004: Enable market data (16h)
- **Total: ~25 hours**

**Sprint 2 (Week 3-4): Live Trading**
- TASK-005: Connect exchanges (24h)
- TASK-011: Add critical tests (20h)
- **Total: ~44 hours**

**Sprint 3 (Week 5-8): Payments & OAuth**
- TASK-006: Complete OAuth (12h)
- TASK-007: Stripe integration (16h)
- TASK-011: More tests (20h)
- **Total: ~48 hours**

**Sprint 4+ (Month 3+): Enhancements**
- TASK-008: Copy trading (40h)
- TASK-009: Code cleanup (12h)
- TASK-010: Dead code removal (8h)
- **Total: ~60 hours**

**Grand Total: ~177 hours (4-5 weeks of work for 1 full-time developer)**

---

**← [Back to PART 3: Live Status](./DOCUMENTATION_PART_3_Live_Status.md)**
**→ [Continue to PART 5: Developer Guide](./DOCUMENTATION_PART_5_Developer_Guide.md)**

---

**Generated by:** Claude Code (Anthropic)
**Task Format:** Ready for Jira/Linear/Trello
**Estimates:** Based on experienced developer (mid-senior level)
