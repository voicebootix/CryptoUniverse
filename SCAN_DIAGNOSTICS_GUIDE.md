# Opportunity Scan Diagnostics Guide

## Overview

This guide explains how to access and use the diagnostic endpoints for debugging user-initiated opportunity scans in your CryptoUniverse deployment.

## Quick Start

### 1. Run the Test Script

The easiest way to test the diagnostics is to use the provided Python script:

```bash
cd /Users/User/CryptoUniverse/CryptoUniverse
python test_scan_diagnostics.py
```

This script will:
- Authenticate as admin
- Initiate an opportunity scan
- Monitor scan progress in real-time
- Retrieve and display detailed metrics
- Show scan history

### 2. Manual API Testing

You can also test the endpoints manually using curl or any HTTP client.

## Available Diagnostic Endpoints

### 1. **Get Scan Metrics** (Admin Only)

Retrieve detailed metrics about opportunity scans including latest scan data, daily statistics, and system health.

```bash
GET /api/v1/scan-diagnostics/scan-metrics
```

**Query Parameters:**
- `user_id` (optional): Filter by specific user
- `include_daily_stats` (default: true): Include daily aggregated statistics

**Example:**
```bash
curl -k -X GET "https://cryptouniverse.onrender.com/api/v1/scan-diagnostics/scan-metrics" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "success": true,
  "latest_scan": {
    "scan_id": "user_discovery_...",
    "user_id": "...",
    "opportunities_discovered": 15,
    "strategies_scanned": 14,
    "execution_time_ms": 45230.5,
    "success": true,
    "timestamp": "2025-10-22T05:15:30.123456"
  },
  "daily_stats": {
    "date": "2025-10-22",
    "stats": {
      "total_scans": 10,
      "successful_scans": 9,
      "total_opportunities": 150,
      "total_strategies": 140,
      "avg_execution_time_ms": 42500.3
    },
    "success_rate": 90.0
  },
  "system_health": {
    "status": "healthy",
    "redis_connected": true,
    "daily_errors": 0
  }
}
```

### 2. **Get Scan History** (Admin Only)

Retrieve detailed scan history for a specific user.

```bash
GET /api/v1/scan-diagnostics/scan-history/{user_id}
```

**Query Parameters:**
- `limit` (default: 10, max: 50): Number of scans to retrieve

**Example:**
```bash
curl -k -X GET "https://cryptouniverse.onrender.com/api/v1/scan-diagnostics/scan-history/7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af?limit=5" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "success": true,
  "user_id": "7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af",
  "total_scans": 5,
  "scans": [
    {
      "scan_id": "scan_...",
      "opportunities_count": 15,
      "strategies_scanned": 14,
      "execution_time_ms": 45230.5,
      "last_updated": "2025-10-22T05:15:30",
      "user_profile": { ... },
      "asset_discovery": { ... },
      "partial": false
    }
  ]
}
```

### 3. **Clear Scan Cache** (Admin Only)

Clear all cached scan data for a specific user. Useful for debugging or forcing fresh scans.

```bash
DELETE /api/v1/scan-diagnostics/clear-scan-cache/{user_id}
```

**Example:**
```bash
curl -k -X DELETE "https://cryptouniverse.onrender.com/api/v1/scan-diagnostics/clear-scan-cache/7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "success": true,
  "user_id": "7a1ee8cd-bfc9-4e4e-85b2-69c8e91054af",
  "entries_deleted": 3,
  "message": "Cleared 3 cache entries for user"
}
```

## Monitoring a User-Initiated Scan

### Step 1: Initiate a Scan

```bash
POST /api/v1/opportunities/discover
Content-Type: application/json

{
  "force_refresh": true
}
```

Response includes `scan_id` for monitoring.

### Step 2: Poll Scan Status

```bash
GET /api/v1/opportunities/status/{scan_id}
```

Returns real-time progress:
```json
{
  "status": "scanning",
  "progress": {
    "strategies_completed": 5,
    "total_strategies": 14,
    "opportunities_found_so_far": 12,
    "percentage": 35
  }
}
```

### Step 3: Get Results When Complete

```bash
GET /api/v1/opportunities/results/{scan_id}
```

Returns full opportunity list with all metadata.

### Step 4: Review Diagnostic Metrics

```bash
GET /api/v1/scan-diagnostics/scan-metrics
```

Get detailed metrics including execution time, strategies scanned, and system health.

## Metrics Tracked in Redis

The system tracks the following metrics in Redis:

### 1. **Latest Scan Metrics** (1 hour TTL)
- Key: `service_metrics:user_initiated_scans`
- Contains: Latest scan details for quick diagnostic access

### 2. **Daily Statistics** (7 days TTL)
- Key: `opportunity_scan_stats:YYYY-MM-DD`
- Hash with atomic counters:
  - `total_scans`: Total scans today
  - `successful_scans`: Successful scans
  - `total_opportunities`: Total opportunities found
  - `total_strategies`: Total strategies scanned
  - `avg_execution_time_ms`: Running average execution time

### 3. **User Scan Cache**
- Key: `user_opportunities:{user_id}:*`
- Contains: Cached scan results for each user

### 4. **Daily Errors**
- Key: `opportunity_discovery_errors:YYYY-MM-DD`
- Counter for daily error tracking

## Logging

The opportunity discovery service uses `structlog` for structured logging. Key log events include:

### Scan Lifecycle
- `🔍 ENTERPRISE Opportunity Discovery API called` - Scan initiated
- `🎯 Scanning strategy opportunities` - Strategy scan started
- `✅ Strategy scan completed` - Strategy scan finished
- `📊 User-initiated scan metrics tracked (atomic)` - Metrics recorded

### Per-Strategy Logs
- `🔍 STRATEGY SCAN RESULT` - Individual strategy results
- `❌ No scanner found for strategy` - Strategy scanner not available
- `⚠️ Strategy scan failed` - Strategy scan error

### System Events
- `🔄 Fallback opportunities provided from cache` - Fallback mode activated
- Metrics include: `scan_id`, `user_id`, `opportunities`, `execution_time_ms`

## Debugging Tips

### Issue: Scan Takes Too Long

1. Check scan progress:
   ```bash
   GET /api/v1/opportunities/status/{scan_id}
   ```

2. Review metrics to see which strategies are slow:
   ```bash
   GET /api/v1/scan-diagnostics/scan-metrics
   ```

3. Check `avg_execution_time_ms` in daily stats

### Issue: No Opportunities Found

1. Check user's active strategies:
   ```bash
   GET /api/v1/strategies/active
   ```

2. Review user profile in scan history:
   ```bash
   GET /api/v1/scan-diagnostics/scan-history/{user_id}
   ```

3. Look for `user_profile.user_tier` and `asset_discovery` data

### Issue: Scan Failing

1. Check system health:
   ```bash
   GET /api/v1/scan-diagnostics/scan-metrics
   ```

2. Review daily error count in `system_health.daily_errors`

3. Check Redis connectivity in `system_health.redis_connected`

4. Clear cache and retry:
   ```bash
   DELETE /api/v1/scan-diagnostics/clear-scan-cache/{user_id}
   POST /api/v1/opportunities/discover (with force_refresh: true)
   ```

## Production Deployment

After making changes locally, deploy to Render:

```bash
# Commit changes
git add .
git commit -m "Add scan diagnostics endpoints"
git push origin main
```

Render will automatically deploy the changes.

## Testing After Deployment

Run the test script against production:

```bash
cd CryptoUniverse/CryptoUniverse
python test_scan_diagnostics.py
```

Or manually test endpoints:

```bash
# 1. Authenticate
TOKEN=$(curl -k -X POST "https://cryptouniverse.onrender.com/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@cryptouniverse.com","password":"AdminPass123!"}' \
  | jq -r .access_token)

# 2. Get metrics
curl -k -X GET "https://cryptouniverse.onrender.com/api/v1/scan-diagnostics/scan-metrics" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

## Security Notes

- All diagnostic endpoints require **Admin role**
- Endpoints are protected by JWT authentication
- Rate limiting is enforced on scan initiation endpoints
- Sensitive data is logged with structured logging for audit trails

## Support

For issues or questions about scan diagnostics:
1. Check the logs using the diagnostic endpoints
2. Review the metrics for anomalies
3. Clear cache if data seems stale
4. Contact system administrator with scan_id for investigation

---

**Last Updated:** 2025-10-22
**Author:** CTO Assistant
