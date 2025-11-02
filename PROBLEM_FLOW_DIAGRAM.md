# Problem Flow Diagram

## Current (Broken) Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ API Endpoint: POST /opportunities/discover                      │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │ 1. Register lookup (sync)      │ ✅ Line 229
         │    _scan_lookup[scan_id] = key │
         └────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │ 2. Schedule background task    │ ⏱️ Line 255
         │    (NOT awaited)               │
         └────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │ 3. Return scan_id immediately  │ ✅ Line 258
         │    {scan_id: "scan_xxx"}       │
         └────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────┐
    │ CLIENT: Calls status endpoint           │
    │ GET /opportunities/status/scan_xxx      │
    └─────────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────┐
    │ Status Endpoint                         │
    └─────────────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │ 4. Resolve cache_key from      │ ✅ Works
         │    lookup (scan_id → cache_key)│
         └────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │ 5. Check in-memory cache       │ ❌ FAILS!
         │    opportunity_cache[cache_key]│
         │    → Returns None              │
         └────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │ 6. Return "not_found"          │ ❌ Line 303
         │    {status: "not_found"}        │
         └────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────┐
    │ Background Task (running separately)     │
    └─────────────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │ 7. Create cache entry          │ ✅ Line 867
         │    (2+ seconds later)          │
         │    opportunity_cache[key] = ...│
         └────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │ 8. NOW status endpoint works  │ ✅
         │    (but too late!)             │
         └────────────────────────────────┘
```

## The Gap

```
Time 0.0s:  Lookup registered ✅
Time 0.0s:  scan_id returned ✅
Time 0.1s:  Status endpoint called
Time 0.1s:  Cache entry checked ❌ (doesn't exist yet!)
Time 0.1s:  Returns "not_found" ❌
Time 2.0s:  Background task creates cache entry ✅
Time 2.0s:  Status endpoint NOW works ✅
```

**The gap: 0.1s to 2.0s where status endpoint fails**

## Fixed Flow (Proposed)

```
┌─────────────────────────────────────────────────────────────────┐
│ API Endpoint: POST /opportunities/discover                      │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │ 1. Register lookup (sync)      │ ✅
         └────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │ 2. Create PLACEHOLDER cache    │ ✅ NEW!
         │    entry (sync)                 │
         │    opportunity_cache[key] = {   │
         │      scan_id, status: "init"    │
         │    }                            │
         └────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │ 3. Schedule background task    │ ⏱️
         └────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │ 4. Return scan_id              │ ✅
         └────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────┐
    │ CLIENT: Calls status endpoint           │
    │ GET /opportunities/status/scan_xxx      │
    └─────────────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │ 5. Resolve cache_key           │ ✅
         └────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │ 6. Check cache                 │ ✅ WORKS!
         │    → Finds placeholder entry   │
         └────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │ 7. Return "scanning" status   │ ✅
         │    {status: "scanning"}        │
         └────────────────────────────────┘
```

## Key Difference

**Before:** Cache entry created asynchronously (2+ seconds delay)  
**After:** Placeholder cache entry created synchronously (immediate)

## Why This Works

1. ✅ Status endpoint finds cache entry immediately
2. ✅ Returns "scanning" instead of "not_found"
3. ✅ Background task updates cache entry as scan progresses
4. ✅ No timing gap - always works
