# Database Connection Attempts Analysis

## Problem: Why 15 Attempts Instead of 3?

### Current Configuration

**Line 80 in `start.sh`:**
```python
max_attempts = int(os.getenv("DB_MAX_ATTEMPTS", "15"))
```

**Default:** 15 attempts (configurable via `DB_MAX_ATTEMPTS` env var)

### Why It Changed

Looking at git history, PR #396 "Restore database readiness tuning" (commit `a9c1170f`) introduced a more robust database connection strategy with:

1. **Progressive Timeout Strategy** (Line 114):
   ```python
   connect_timeout = min(base_connect_timeout + (attempt - 1) * 5, max_connect_timeout)
   ```
   - Attempt 1: 10s timeout
   - Attempt 2: 15s timeout
   - Attempt 3: 20s timeout
   - Attempt 4: 25s timeout
   - Attempt 5+: 30s timeout (max)

2. **Exponential Backoff Delays** (Line 129):
   ```python
   delay = min(max_retry_delay, (2 ** (attempt - 1)) + random.uniform(0, 1))
   ```
   - Attempt 1→2: ~1s delay
   - Attempt 2→3: ~2s delay
   - Attempt 3→4: ~4s delay
   - Attempt 4→5: ~8s delay
   - Attempt 5→6: ~16s delay
   - Attempt 6+: ~30s delay (max)

3. **TCP Port Probe** (Lines 118-131):
   - Additional 3s timeout for TCP probe before actual connection
   - If TCP probe fails, retry with exponential backoff

### Why It's Taking So Long

**Current Deployment Logs Show:**
- Attempt 1: Failed after 10.21s timeout
- Attempt 2: Failed after 15.20s timeout
- Attempt 3: Failed after 20.20s timeout
- Attempt 4: Failed after 25.21s timeout
- Attempts 5-15: Still retrying...

**Total Time So Far:** ~70+ seconds (and counting)

### Root Causes

1. **Supabase Connection Pooler Latency**
   - Supabase uses a connection pooler (`aws-0-ap-southeast-1.pooler.supabase.com`)
   - During cold starts or high load, the pooler can be slow to respond
   - SSL handshake adds additional latency

2. **Progressive Timeout Strategy**
   - Each attempt waits progressively longer (10s → 30s)
   - This is intentional to handle slow database responses
   - But it means failed attempts take longer

3. **TCP Probe Overhead**
   - TCP probe runs before each connection attempt
   - Adds 3s overhead per attempt
   - If TCP probe fails, it retries with exponential backoff

4. **Exponential Backoff**
   - Delays between attempts increase exponentially
   - This prevents overwhelming the database
   - But extends total connection time

### Why It Used to Connect in 3 Attempts

**Previous Configuration (likely):**
- Simpler retry logic with fixed timeout (e.g., 10s)
- Fewer attempts (3-5)
- No TCP probe overhead
- Simpler backoff strategy

**Why It Changed:**
- More robust handling of slow database responses
- Better handling of Supabase connection pooler issues
- Progressive timeout strategy to handle varying network conditions
- TCP probe to detect network issues early

### The Real Problem

**The database connection is actually timing out**, which suggests:

1. **Network Latency Issues**
   - Supabase pooler might be slow to respond
   - SSL handshake might be slow
   - Network path might have high latency

2. **Connection Pool Exhaustion**
   - Supabase pooler might be at capacity
   - Other instances might be holding connections
   - Pooler might need time to allocate new connections

3. **Cold Start Issues**
   - Database pooler might be cold
   - First connection after inactivity takes longer
   - SSL context initialization adds overhead

### Solutions

#### Option 1: Reduce Max Attempts (Quick Fix)
Set environment variable:
```bash
DB_MAX_ATTEMPTS=5
```

#### Option 2: Reduce Timeouts (Faster Failures)
Set environment variables:
```bash
DB_CONNECT_TIMEOUT=5
DB_MAX_CONNECT_TIMEOUT=15
```

#### Option 3: Disable TCP Probe (Reduce Overhead)
The TCP probe adds 3s overhead per attempt. If network is reliable, you can skip it.

#### Option 4: Optimize Supabase Connection
- Use direct connection instead of pooler (if available)
- Check Supabase connection pooler status
- Verify SSL configuration is optimal

### Recommendation

**For Production:**
- Keep 15 attempts but reduce timeouts:
  ```bash
  DB_CONNECT_TIMEOUT=5
  DB_MAX_CONNECT_TIMEOUT=15
  DB_MAX_ATTEMPTS=10
  ```

**For Faster Deployments:**
- Reduce attempts but keep progressive timeout:
  ```bash
  DB_MAX_ATTEMPTS=5
  DB_CONNECT_TIMEOUT=10
  DB_MAX_CONNECT_TIMEOUT=20
  ```

### Expected Behavior

With current settings:
- **Best case:** 1 attempt (~10s) if database responds quickly
- **Typical case:** 2-3 attempts (~25-40s) with normal latency
- **Worst case:** 5-10 attempts (~2-5 minutes) with slow database

The current deployment is experiencing the "worst case" scenario, which suggests:
- Database pooler is slow/unresponsive
- Network latency is high
- SSL handshake is slow
- Connection pool might be exhausted

