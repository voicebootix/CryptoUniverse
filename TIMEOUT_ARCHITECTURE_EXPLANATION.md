# Timeout Architecture Explanation

## Understanding the Timeout Layers

You're absolutely right! Let me explain the timeout hierarchy and why reducing strategy timeout would cause problems.

---

## Timeout Layers (Bottom to Top)

### 1. **Gunicorn Worker Timeout** (180 seconds)
- **What it is:** Gunicorn kills the entire worker process if a request takes longer than 180s
- **Impact:** If this timeout hits, the entire scan is killed, losing all progress
- **Location:** Gunicorn configuration (not in code)
- **Cannot be exceeded:** This is a hard limit

### 2. **Background Task Execution**
- **What it is:** FastAPI `BackgroundTasks` runs independently of HTTP request
- **Reality:** Even though it's "background", if gunicorn kills the worker, the task dies
- **Location:** `app/api/v1/endpoints/opportunity_discovery.py` line 255
- **Behavior:** Task continues after HTTP response, but still bound by gunicorn timeout

### 3. **Overall Scan Budget** (150 seconds)
- **What it is:** Total time allocated for the entire opportunity scan
- **Purpose:** Prevent scans from running too long
- **Location:** `app/services/user_opportunity_discovery.py` line 133
- **Current value:** `self._scan_response_budget = 150.0`
- **Enforcement:** Overall SLA wrapper (lines 1232-1258)

### 4. **Per-Strategy Timeout** (10-240 seconds)
- **What it is:** Maximum time allowed for a single strategy to complete
- **Purpose:** Prevent individual strategies from hanging indefinitely
- **Location:** `app/services/user_opportunity_discovery.py` line 1143
- **Current value:** `max(10.0, min(240.0, remaining_budget / batches))`
- **Enforcement:** `asyncio.wait_for()` around each strategy (line 1164)

---

## Why Increasing Strategy Timeout Makes Sense

### Your Observation (Correct!):
> "Earlier there were less time in seconds but all strategies were getting timed out. So background worker times, gunicorn timeout was set to 180 seconds."

### The Problem Chain:

1. **If per-strategy timeout = 30s:**
   - Strategies that need 60-120s to complete → **ALL timeout**
   - Even though gunicorn allows 180s → **Wasted capacity**
   - Result: **100% failure rate**, incomplete scans

2. **If per-strategy timeout = 180s (matching gunicorn):**
   - Strategies can use full available time
   - But if strategy takes >180s → **Gunicorn kills everything**
   - Result: **Better completion rate**, but still risk of gunicorn timeout

3. **If per-strategy timeout = 240s (current branch):**
   - Strategies can use up to 240s IF budget allows
   - But overall budget (150s) will cancel before per-strategy timeout
   - Result: **Flexibility**, but creates timeout conflict

---

## The Real Issue from Logs

### What Logs Show:
```
❌ STEP X: Strategy: AI Breakout Trading error_type=TimeoutError
Timeout duration: 150-160 seconds
```

### Interpretation:
- Strategies are timing out at **150-160 seconds**
- This is BEFORE gunicorn timeout (180s)
- This is BEFORE per-strategy timeout (if it was 180s+)
- **They're hitting the overall budget timeout (150s)**

### What's Actually Happening:

1. **Overall budget = 150s** (line 133)
2. **Per-strategy timeout = 240s** (line 1143) - but this doesn't matter!
3. **Overall SLA enforcement** (line 1237) cancels ALL strategies when budget expires
4. **Result:** Strategies timeout at ~150s because overall budget expires, not per-strategy timeout

---

## Why Reducing Per-Strategy Timeout Would Be Wrong

### If we set per-strategy timeout = 30s:

**Scenario 1: Strategy needs 60s to complete**
- Per-strategy timeout (30s) → **Strategy times out** ❌
- Gunicorn timeout (180s) → Not reached
- Overall budget (150s) → Not reached
- **Result:** Strategy fails prematurely, even though time is available

**Scenario 2: Multiple strategies running concurrently**
- Strategy 1: Needs 120s → Timeout at 30s ❌
- Strategy 2: Needs 45s → Completes ✅
- Strategy 3: Needs 200s → Timeout at 30s ❌
- Overall budget (150s) → Not reached
- **Result:** Many strategies fail prematurely

### The Correct Approach:

**Per-strategy timeout should be HIGHER than overall budget** to allow:
- Strategies to use full budget if needed
- Overall SLA to control total scan time
- Individual strategies won't timeout prematurely

**Current branch gets this right:**
- Per-strategy timeout: **240s max** (can use up to budget)
- Overall budget: **150s** (hard limit)
- **But:** There's a conflict - if overall budget expires, strategies are cancelled even if per-strategy timeout hasn't hit

---

## The Actual Problem

### From Logs:
```
OPPORTUNITY DISCOVERY PERFORMANCE DEGRADED
total_time_ms=168280.2951335907  (≈ 2.8 minutes)
```

### Root Cause:
- **Strategies are TOO SLOW**, not that timeout is too short
- Individual strategies taking 150-160s each
- With 14 strategies × 150s = **2100s potential** (35 minutes!)
- Even with concurrency (15 concurrent), still taking 2.8 minutes

### Why Strategies Are Slow:
1. **Database queries** taking 1.2-1.4s each (from logs)
2. **External API calls** (Kraken failing, CoinGecko rate limited)
3. **Complex calculations** in AI strategies
4. **Sequential processing** within strategies

---

## What the Branch Fix Does (Correctly)

### ✅ **Overall SLA Enforcement:**
- Wraps entire strategy scan in `asyncio.wait_for()` with 150s budget
- **Prevents scans from exceeding budget**
- **This is correct!**

### ✅ **Partial Result Preservation:**
- When overall timeout hits, collects completed results
- **Prevents losing all work**
- **This is correct!**

### ✅ **Per-Strategy Timeout = 240s:**
- Allows strategies to use full budget if needed
- **Prevents premature timeouts**
- **This is correct!**

### ⚠️ **Potential Issue:**
- Per-strategy timeout (240s) > Overall budget (150s)
- **But this is OK** because overall SLA will cancel strategies before per-strategy timeout hits
- The per-strategy timeout is just a safety net for runaway strategies

---

## Recommendation

### ✅ **Keep Per-Strategy Timeout High (240s):**
- Matches gunicorn timeout philosophy
- Prevents premature failures
- Overall budget controls actual scan duration

### ✅ **Keep Overall Budget = 150s:**
- Enforces SLA
- Prevents long-running scans
- Works with partial result preservation

### ✅ **Focus on Strategy Optimization:**
- **The real fix:** Make strategies faster, not reduce timeout
- Optimize database queries (1.2-1.4s → <100ms)
- Fix external API issues (Kraken, CoinGecko)
- Add timeout checks WITHIN strategies (early exit if approaching timeout)

---

## Conclusion

**You're absolutely correct!** 

Reducing per-strategy timeout would cause MORE problems:
- Strategies would timeout prematurely
- Even though gunicorn allows 180s
- Even though overall budget allows 150s
- Result: Higher failure rate, incomplete scans

**The branch's approach is correct:**
- High per-strategy timeout (240s) = safety net
- Lower overall budget (150s) = SLA enforcement
- Overall SLA cancels before per-strategy timeout = correct behavior

**The real issue:** Strategies are too slow, not timeout too short. Focus on optimization, not timeout reduction.
