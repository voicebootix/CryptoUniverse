# Implementation Prompt: Critical Performance Fixes

## Context

Analysis of Render production logs reveals critical performance and reliability issues affecting the opportunity discovery system. All fixes listed below must be implemented immediately as they are causing:
- Database queries taking 1.2-1.4 seconds (16x slower than acceptable)
- Kraken API complete failure due to nonce errors
- Strategy execution timeouts (150-160 seconds, causing incomplete scans)
- Overall scan performance 16.8x slower than target (2.8 minutes vs 10 seconds)
- External API rate limiting and connectivity failures

---

## FIX 1: Database Performance Optimization (CRITICAL)

### Problem
Render logs show:
```
Slow database query detected: duration=1.3789114952087402 statement=SELECT users.id, ...
Very slow database query detected: duration=1.2276194095611572 statement=SELECT users.id, ...
duration=0.803619384765625 statement=SELECT exchange_accounts.id, ...
```

### Root Cause
Missing or inefficient database indexes on frequently queried columns causing full table scans.

### Evidence
- **File:** `app/models/user.py` (lines 62-154)
  - `User` model has indexes on `email`, `id`, `tenant_id`, `referral_code` but may need composite indexes
  - Composite index exists: `idx_users_auth_lookup` on `(email, status, is_active, is_verified)` but query pattern may not match
  
- **File:** `app/models/exchange.py` (lines 61-140)
  - `ExchangeAccount` model has indexes on `user_id`, `exchange_name`, `status`
  - Composite indexes exist but may not cover all query patterns

### Implementation Tasks

#### Task 1.1: Create Alembic Migration for Missing Indexes

**File:** Create new migration file `alembic/versions/XXX_add_performance_indexes_critical.py`

```python
"""Add critical performance indexes for slow queries

Revision ID: add_perf_indexes_critical
Revises: <latest_revision>
Create Date: <current_date>
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # User authentication queries - ensure email + is_active composite index
    op.create_index(
        'idx_users_email_active_perf',
        'users',
        ['email', 'is_active'],
        unique=False,
        if_not_exists=True
    )
    
    # User lookup by id + status for portfolio queries
    op.create_index(
        'idx_users_id_status_perf',
        'users',
        ['id', 'status'],
        unique=False,
        if_not_exists=True
    )
    
    # Exchange accounts: user_id + exchange_name + status (very common query pattern)
    op.create_index(
        'idx_exchange_accounts_user_exchange_status_perf',
        'exchange_accounts',
        ['user_id', 'exchange_name', 'status'],
        unique=False,
        if_not_exists=True
    )
    
    # Exchange accounts: user_id + status (for active account lookups)
    op.create_index(
        'idx_exchange_accounts_user_status_perf',
        'exchange_accounts',
        ['user_id', 'status'],
        unique=False,
        if_not_exists=True
    )

def downgrade():
    op.drop_index('idx_users_email_active_perf', table_name='users', if_exists=True)
    op.drop_index('idx_users_id_status_perf', table_name='users', if_exists=True)
    op.drop_index('idx_exchange_accounts_user_exchange_status_perf', table_name='exchange_accounts', if_exists=True)
    op.drop_index('idx_exchange_accounts_user_status_perf', table_name='exchange_accounts', if_exists=True)
```

#### Task 1.2: Optimize ORM Queries Using select_related/joinedload

**File:** `app/api/v1/endpoints/auth.py` (or wherever user authentication queries occur)

**Find:** All queries like `SELECT users.id, users.email, users.is_active FROM users WHERE users.id = $1`

**Replace with:** Use `selectinload()` or `joinedload()` to eagerly load relationships:

```python
# BEFORE (causes N+1 queries):
result = await session.execute(
    select(User).where(User.id == user_id)
)
user = result.scalar_one_or_none()

# AFTER (single query with joins):
result = await session.execute(
    select(User)
    .where(User.id == user_id)
    .options(selectinload(User.exchange_accounts))
)
user = result.scalar_one_or_none()
```

**Files to search and optimize:**
- `app/api/v1/endpoints/auth.py` - User authentication queries
- `app/services/portfolio_risk_core.py` - Portfolio aggregation queries
- Any file using `select(User)` or `select(ExchangeAccount)` without eager loading

#### Task 1.3: Add Query Result Caching for User Data

**File:** `app/services/user_opportunity_discovery.py` or create `app/services/user_cache.py`

**Add:** Redis-based caching for frequently accessed user data:

```python
import json
from app.core.redis import get_redis_client

async def get_cached_user(user_id: str, db: AsyncSession) -> Optional[User]:
    """Get user with Redis caching."""
    redis = await get_redis_client()
    cache_key = f"user:{user_id}"
    
    # Try cache first
    if redis:
        cached = await redis.get(cache_key)
        if cached:
            user_data = json.loads(cached)
            # Reconstruct User object or return dict
            return user_data
    
    # Cache miss - query database
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.exchange_accounts))
    )
    user = result.scalar_one_or_none()
    
    # Cache for 5 minutes
    if redis and user:
        await redis.setex(
            cache_key,
            300,  # 5 minutes
            json.dumps({
                "id": str(user.id),
                "email": user.email,
                "is_active": user.is_active,
                # ... other frequently accessed fields
            })
        )
    
    return user
```

---

## FIX 2: Kraken API Nonce Error Resolution (CRITICAL)

### Problem
Render logs show:
```
kraken API Error: EAPI:Invalid nonce
Attempt 1 failed: EAPI:Invalid nonce
Attempt 2 failed: EAPI:Invalid nonce
Attempt 3 failed: EAPI:Invalid nonce
Attempt 4 failed: EAPI:Invalid nonce
failed_exchanges=1
```

### Root Cause
Kraken requires strictly increasing nonces. Current implementation has race conditions or nonce collisions in concurrent requests.

### Evidence
- **File:** `app/services/real_market_data.py` (lines 726-741)
  - `_get_kraken_nonce()` uses Redis `INCR` but falls back to `time.time() * 1000` which can cause collisions
  - No mutex/lock around nonce generation for concurrent requests
  
- **File:** `app/api/v1/endpoints/exchanges.py` (lines 63-317)
  - `KrakenNonceManager` exists but may not be used consistently
  - `trade_execution.py` imports it but may have synchronization issues

- **File:** `app/services/trade_execution.py` (lines 484-486)
  - Uses `kraken_nonce_manager.get_nonce()` but may have timing issues

### Implementation Tasks

#### Task 2.1: Fix Nonce Generation to Ensure Strictly Increasing Values

**File:** `app/services/real_market_data.py` (lines 726-741)

**Current Code:**
```python
async def _get_kraken_nonce(self) -> int:
    """Generate a Kraken API nonce with Redis coordination and time-based fallback."""
    try:
        redis = await redis_manager.get_client()
        if redis:
            nonce_value = await redis.incr("kraken_nonce")
            if nonce_value:
                return int(nonce_value)
    except Exception as redis_error:
        self.logger.warning(
            "Redis unavailable for Kraken nonce",
            error=str(redis_error)
        )
    return int(time.time() * 1000)  # ← PROBLEM: Can cause collisions
```

**Replace with:**
```python
import asyncio

class KrakenNonceGenerator:
    """Thread-safe Kraken nonce generator with Redis coordination."""
    def __init__(self):
        self._lock = asyncio.Lock()
        self._local_counter = 0
        self._last_redis_nonce = 0
    
    async def get_nonce(self) -> int:
        """Get next strictly increasing nonce."""
        async with self._lock:
            try:
                redis = await redis_manager.get_client()
                if redis:
                    # Use Redis INCR for distributed coordination
                    nonce_value = await redis.incr("kraken_nonce")
                    if nonce_value:
                        self._last_redis_nonce = int(nonce_value)
                        return self._last_redis_nonce
            except Exception as redis_error:
                self.logger.warning(
                    "Redis unavailable for Kraken nonce, using local counter",
                    error=str(redis_error)
                )
            
            # Fallback: use timestamp + local counter to ensure uniqueness
            # Timestamp in milliseconds ensures 1000 requests/second max
            timestamp_ms = int(time.time() * 1000)
            self._local_counter += 1
            # Combine timestamp with counter to ensure strict increase
            # Format: timestamp_ms * 10000 + counter (allows 10k requests/second)
            fallback_nonce = timestamp_ms * 10000 + (self._local_counter % 10000)
            
            # Ensure fallback is always greater than last Redis nonce
            if fallback_nonce <= self._last_redis_nonce:
                fallback_nonce = self._last_redis_nonce + 1
            
            return fallback_nonce

# Global instance
_kraken_nonce_gen = KrakenNonceGenerator()

async def _get_kraken_nonce(self) -> int:
    """Generate a Kraken API nonce with Redis coordination."""
    return await _kraken_nonce_gen.get_nonce()
```

#### Task 2.2: Ensure Consistent Use of Nonce Manager Across All Kraken Calls

**File:** `app/services/trade_execution.py` (lines 484-498)

**Verify:** All Kraken API calls use the nonce manager consistently:

```python
# Ensure this pattern is used everywhere:
from app.api.v1.endpoints.exchanges import kraken_nonce_manager

# In _execute_kraken_order or any Kraken API call:
nonce = await kraken_nonce_manager.get_nonce()  # ← Must be awaited
params = {
    "nonce": str(nonce),  # ← Must be string
    # ... other params
}
```

**Search for:** All files that make Kraken API calls and ensure they all use `kraken_nonce_manager.get_nonce()`

**Files to check:**
- `app/services/trade_execution.py`
- `app/services/real_market_data.py`
- `app/services/portfolio_risk_core.py` (if it fetches Kraken balances)

#### Task 2.3: Add Mutex/Lock to KrakenNonceManager

**File:** `app/api/v1/endpoints/exchanges.py` (lines 63-317)

**Ensure:** `KrakenNonceManager.get_nonce()` has proper async locking:

```python
async def get_nonce(self) -> int:
    """Get next nonce with distributed coordination."""
    if self._lock is None:
        self._lock = asyncio.Lock()
    
    async with self._lock:  # ← CRITICAL: Ensure this exists
        # ... nonce generation logic
```

**Verify:** The `_lock` is properly initialized as `asyncio.Lock()` and used in all nonce generation paths.

---

## FIX 3: Strategy Execution Timeout Mitigation (CRITICAL)

### Problem
Render logs show:
```
❌ STEP X: Strategy: AI Breakout Trading error_type=TimeoutError ... status=failed
❌ STEP X: Strategy: AI Scalping error_type=TimeoutError ... status=failed
❌ STEP X: Strategy: AI Market Making error_type=TimeoutError ... status=failed
❌ STEP X: Strategy: AI Complex Derivatives error_type=TimeoutError ... status=failed
❌ STEP X: Strategy: AI Statistical Arbitrage error_type=TimeoutError ... status=failed
❌ STEP X: Strategy: AI Options Strategies error_type=TimeoutError ... status=failed
```

Timeout duration: **150-160 seconds** (2.5-2.6 minutes), causing incomplete scan results.

### Root Cause
Strategies have timeout of 180 seconds (`per_strategy_timeout_s = max(10.0, min(180.0, ...))`) but strategies don't check timeout during execution, leading to wasted time.

### Evidence
- **File:** `app/services/user_opportunity_discovery.py` (lines 1128-1158)
  - Timeout set to max 180 seconds: `per_strategy_timeout_s = max(10.0, min(180.0, self._scan_response_budget / batches))`
  - Strategies wrapped in `asyncio.wait_for()` but no internal timeout checks
  - Strategies run to completion or timeout, no early exit

### Implementation Tasks

#### Task 3.1: Reduce Strategy Timeout from 180s to 30s

**File:** `app/services/user_opportunity_discovery.py` (line 1132)

**Current Code:**
```python
per_strategy_timeout_s = max(10.0, min(180.0, self._scan_response_budget / batches))
```

**Replace with:**
```python
# Reduce timeout from 180s to 30s to prevent long-running strategies from blocking scans
per_strategy_timeout_s = max(10.0, min(30.0, self._scan_response_budget / batches))
```

#### Task 3.2: Add Timeout Checks Within Strategy Execution Loops

**File:** `app/services/user_opportunity_discovery.py` (lines 1154-1158)

**Current Code:**
```python
result = await asyncio.wait_for(
    self._scan_strategy_opportunities(
        strategy_info, discovered_assets, user_profile, scan_id, portfolio_result
    ),
    timeout=per_strategy_timeout_s
)
```

**Replace with:** Pass timeout context to strategy scanning:

```python
async def _scan_strategy_opportunities(
    self,
    strategy_info: Dict,
    discovered_assets: Set[str],
    user_profile: UserOpportunityProfile,
    scan_id: str,
    portfolio_result: Dict,
    timeout_seconds: float = 30.0,  # ← Add timeout parameter
    start_time: Optional[float] = None  # ← Add start time for elapsed check
) -> Dict[str, Any]:
    """Scan strategy with timeout awareness."""
    if start_time is None:
        start_time = time.time()
    
    # Check elapsed time at key points in the function
    elapsed = time.time() - start_time
    if elapsed > (timeout_seconds * 0.8):  # Exit at 80% of timeout
        self.logger.warning(
            "Strategy approaching timeout, returning partial results",
            strategy=strategy_info.get("name"),
            elapsed_seconds=elapsed,
            timeout_seconds=timeout_seconds
        )
        return {
            "success": False,
            "error": "timeout_approaching",
            "opportunities": [],
            "partial": True
        }
    
    # ... rest of strategy scanning logic
    # Add elapsed time checks before expensive operations (API calls, calculations)
```

**Update the call site:**
```python
result = await asyncio.wait_for(
    self._scan_strategy_opportunities(
        strategy_info,
        discovered_assets,
        user_profile,
        scan_id,
        portfolio_result,
        timeout_seconds=per_strategy_timeout_s,  # ← Pass timeout
        start_time=start_time  # ← Pass start time
    ),
    timeout=per_strategy_timeout_s
)
```

#### Task 3.3: Add Timeout Checks in Strategy Calculation Methods

**File:** `app/services/trading_strategies.py` (or wherever strategy calculations occur)

**Find:** All methods that perform expensive calculations (e.g., `calculate_opportunities`, `analyze_market`, etc.)

**Add:** Timeout checks before expensive operations:

```python
async def calculate_opportunities(self, symbol: str, start_time: float, timeout_seconds: float) -> List[Dict]:
    """Calculate opportunities with timeout awareness."""
    elapsed = time.time() - start_time
    if elapsed > (timeout_seconds * 0.8):
        return []  # Early exit
    
    # Before expensive API calls:
    elapsed = time.time() - start_time
    if elapsed > (timeout_seconds * 0.7):
        self.logger.warning(f"Skipping {symbol} due to timeout approaching")
        return []
    
    # ... perform calculations
```

---

## FIX 4: CoinGecko Rate Limit Handling (HIGH PRIORITY)

### Problem
Render logs show:
```
API CoinGecko_Volume rate limited
API CoinGecko_Top250 rate limited
Market data API timed out api=coingecko symbol=ALPACA
```

### Root Cause
Rate limit checking exists but doesn't respect `Retry-After` headers or queue requests properly.

### Evidence
- **File:** `app/services/market_data_feeds.py` (lines 461-491, 940-993)
  - `_check_rate_limit()` exists but may not handle `Retry-After` headers
  - Rate limit errors are caught but requests aren't queued for later retry

### Implementation Tasks

#### Task 4.1: Implement Retry-After Header Handling

**File:** `app/services/market_data_feeds.py` (lines 979-993)

**Current Code:**
```python
if response.status == 429:
    retry_after = int(response.headers.get("Retry-After", 60))
    error_msg = f"API error: 429 - Rate limited (retry after {retry_after}s)"
    logger.debug(f"CoinGecko rate limited", symbol=symbol, retry_after=retry_after)
```

**Replace with:**
```python
if response.status == 429:
    retry_after = int(response.headers.get("Retry-After", 60))
    error_msg = f"API error: 429 - Rate limited (retry after {retry_after}s)"
    logger.warning(f"CoinGecko rate limited", symbol=symbol, retry_after=retry_after)
    
    # Store rate limit info in Redis for coordinated rate limiting
    redis = await get_redis_client()
    if redis:
        rate_limit_key = f"rate_limit:coingecko:resets_at"
        reset_timestamp = time.time() + retry_after
        await redis.setex(rate_limit_key, retry_after + 10, str(reset_timestamp))
    
    # Raise rate limit error with retry_after for caller to handle
    raise MarketDataRateLimitError(
        message=f"CoinGecko rate limited",
        retry_after=retry_after
    )
```

#### Task 4.2: Add Request Queuing for Rate-Limited APIs

**File:** `app/services/market_data_feeds.py`

**Add:** Queue system for rate-limited requests:

```python
import asyncio
from collections import deque

class RateLimitQueue:
    """Queue for rate-limited API requests."""
    def __init__(self):
        self._queues = {}  # api_name -> deque of (callback, args, kwargs)
        self._locks = {}   # api_name -> asyncio.Lock
    
    async def add_request(self, api_name: str, callback, *args, **kwargs):
        """Add request to queue."""
        if api_name not in self._queues:
            self._queues[api_name] = deque()
            self._locks[api_name] = asyncio.Lock()
        
        self._queues[api_name].append((callback, args, kwargs))
    
    async def process_queue(self, api_name: str):
        """Process queued requests when rate limit resets."""
        if api_name not in self._queues:
            return
        
        async with self._locks[api_name]:
            while self._queues[api_name]:
                callback, args, kwargs = self._queues[api_name].popleft()
                try:
                    await callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Queued request failed: {e}")

# Global queue instance
_rate_limit_queue = RateLimitQueue()

# In get_price or other methods, when rate limited:
try:
    return await self._fetch_price_from_coingecko(symbol)
except MarketDataRateLimitError as e:
    # Queue request for later
    await _rate_limit_queue.add_request(
        "coingecko",
        self._fetch_price_from_coingecko,
        symbol
    )
    # Schedule queue processing after retry_after
    asyncio.create_task(self._process_queue_after_delay("coingecko", e.retry_after))
    # Return cached/stale data or raise
    raise
```

#### Task 4.3: Prioritize Critical Symbols Over Non-Critical

**File:** `app/services/market_data_feeds.py` (anywhere symbols are fetched)

**Add:** Symbol priority system:

```python
# Define critical symbols (BTC, ETH, etc.)
CRITICAL_SYMBOLS = {"BTC", "ETH", "USDT", "USDC", "BNB", "SOL", "XRP", "ADA"}

async def get_price(self, symbol: str, priority: str = "normal") -> Dict:
    """Get price with priority handling."""
    is_critical = symbol.upper() in CRITICAL_SYMBOLS or priority == "critical"
    
    try:
        return await self._fetch_price(symbol)
    except MarketDataRateLimitError as e:
        if is_critical:
            # For critical symbols, wait and retry immediately
            await asyncio.sleep(e.retry_after)
            return await self._fetch_price(symbol)
        else:
            # For non-critical, queue or return cached
            await _rate_limit_queue.add_request("coingecko", self._fetch_price, symbol)
            # Return cached data if available
            return self._get_cached_price(symbol)
```

---

## FIX 5: CoinCap Connectivity Failure Handling (MEDIUM PRIORITY)

### Problem
Render logs show:
```
API CoinCap_Top200 failed error=Cannot connect to host api.coincap.io:443 ssl:default [Name or service not known]
```

### Root Cause
DNS resolution failure or network connectivity issue. No fallback mechanism.

### Implementation Tasks

#### Task 5.1: Add Fallback to Alternative Data Sources

**File:** `app/services/market_data_feeds.py` (wherever CoinCap is called)

**Add:** Fallback logic:

```python
async def get_top_assets(self, limit: int = 200) -> List[Dict]:
    """Get top assets with CoinCap fallback."""
    try:
        return await self._fetch_from_coincap(f"/assets?limit={limit}")
    except Exception as e:
        if "Cannot connect" in str(e) or "Name or service not known" in str(e):
            logger.warning(f"CoinCap unavailable, falling back to CoinGecko", error=str(e))
            # Fallback to CoinGecko
            try:
                return await self._fetch_from_coingecko(f"/coins/markets?vs_currency=usd&order=market_cap_desc&per_page={limit}")
            except Exception as e2:
                logger.error(f"All data sources failed", coincap_error=str(e), coingecko_error=str(e2))
                # Return cached data or empty list
                return self._get_cached_top_assets(limit) or []
        raise
```

#### Task 5.2: Add DNS Resolution Check and Retry Logic

**File:** `app/services/market_data_feeds.py`

**Add:** Connection health check:

```python
import socket
import aiohttp

async def _check_coincap_connectivity(self) -> bool:
    """Check if CoinCap API is reachable."""
    try:
        # DNS resolution test
        socket.getaddrinfo("api.coincap.io", 443, type=socket.SOCK_STREAM)
        
        # HTTP connectivity test
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.coincap.io/v2/assets?limit=1",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
    except Exception as e:
        logger.warning(f"CoinCap connectivity check failed: {e}")
        return False

# Before making CoinCap requests:
if not await self._check_coincap_connectivity():
    logger.warning("CoinCap unavailable, using fallback")
    return await self._fetch_from_coingecko(...)
```

---

## FIX 6: Database Connection Pool Tuning (CRITICAL)

### Problem
Render logs show:
```
Critical failure in portfolio aggregation
asyncio.exceptions.CancelledError
TimeoutError in SQLAlchemy/asyncpg
```

### Root Cause
Database connection pool may be exhausted or timeout values too low for slow queries.

### Implementation Tasks

#### Task 6.1: Increase Database Connection Pool Size and Timeout

**File:** `app/core/database.py` (or wherever database engine is configured)

**Find:** Database engine configuration

**Update:**
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import NullPool, QueuePool

# Increase pool size and timeout
engine = create_async_engine(
    database_url,
    pool_size=20,  # Increase from default (usually 5)
    max_overflow=10,  # Allow 10 extra connections
    pool_timeout=30,  # Wait up to 30s for connection (increase from default 30s)
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_pre_ping=True,  # Verify connections before using
    echo=False,
    future=True
)
```

#### Task 6.2: Add Connection Health Monitoring

**File:** `app/core/database.py`

**Add:**
```python
import asyncio
from sqlalchemy import text

async def check_database_health() -> Dict[str, Any]:
    """Check database connection health."""
    try:
        async with get_database() as db:
            result = await db.execute(text("SELECT 1"))
            return {
                "status": "healthy",
                "pool_size": db.bind.pool.size(),
                "checked_in": db.bind.pool.checkedin(),
                "checked_out": db.bind.pool.checkedout(),
                "overflow": db.bind.pool.overflow()
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
```

---

## Summary of All Files to Modify

1. **Database Performance:**
   - Create: `alembic/versions/XXX_add_performance_indexes_critical.py`
   - Modify: `app/api/v1/endpoints/auth.py` (add eager loading)
   - Modify: `app/services/portfolio_risk_core.py` (add eager loading)
   - Create: `app/services/user_cache.py` (optional caching layer)

2. **Kraken Nonce:**
   - Modify: `app/services/real_market_data.py` (lines 726-741)
   - Modify: `app/api/v1/endpoints/exchanges.py` (ensure lock usage)
   - Verify: `app/services/trade_execution.py` (consistency check)

3. **Strategy Timeouts:**
   - Modify: `app/services/user_opportunity_discovery.py` (lines 1132, 1154-1158)
   - Modify: `app/services/trading_strategies.py` (add timeout checks in calculation methods)

4. **CoinGecko Rate Limits:**
   - Modify: `app/services/market_data_feeds.py` (lines 979-993, add queue system)

5. **CoinCap Connectivity:**
   - Modify: `app/services/market_data_feeds.py` (add fallback logic)

6. **Database Connection Pool:**
   - Modify: `app/core/database.py` (increase pool size, add health checks)

---

## Testing Requirements

After implementing each fix:

1. **Database Performance:** Run queries and verify duration < 100ms for indexed queries
2. **Kraken Nonce:** Test concurrent Kraken API calls, verify no "Invalid nonce" errors
3. **Strategy Timeouts:** Verify strategies complete or fail fast (< 30s), no 150s timeouts
4. **Rate Limits:** Test under rate limit conditions, verify queuing works
5. **CoinCap:** Test with CoinCap unavailable, verify fallback works
6. **Connection Pool:** Monitor connection pool metrics, verify no exhaustion

---

## Expected Outcomes

After all fixes:
- Database queries: < 100ms (down from 1.2-1.4s)
- Kraken API: 100% success rate (from 100% failure)
- Strategy timeouts: < 30s (down from 150-160s)
- Overall scan duration: < 60s (down from 168s / 2.8 minutes)
- External API reliability: Improved with fallbacks and rate limit handling
