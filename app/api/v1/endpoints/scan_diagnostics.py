"""
Enhanced Diagnostic Endpoint for Opportunity Scan Metrics

Provides detailed metrics and logging for debugging user-initiated opportunity scans.
Admin-only endpoint for production troubleshooting.

Author: CTO Assistant
Date: 2025-10-22
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.redis import get_redis_client
from app.api.v1.endpoints.auth import get_current_user, require_role
from app.models.user import User, UserRole

logger = structlog.get_logger(__name__)
router = APIRouter()


class ScanMetricsResponse(BaseModel):
    """Response model for scan metrics."""
    success: bool
    latest_scan: Optional[Dict[str, Any]] = None
    daily_stats: Optional[Dict[str, Any]] = None
    recent_scans: List[Dict[str, Any]] = []
    system_health: Dict[str, Any]
    timestamp: str


class DetailedScanLog(BaseModel):
    """Detailed scan log entry."""
    scan_id: str
    user_id: str
    status: str
    opportunities_found: int
    strategies_scanned: int
    execution_time_ms: float
    timestamp: str
    error: Optional[str] = None


class ScanLifecycleResponse(BaseModel):
    """Response model for scan lifecycle tracking."""
    success: bool
    scan_id: str
    current_phase: Optional[str] = None
    current_status: Optional[str] = None
    last_updated: Optional[str] = None
    phases: Dict[str, Any] = {}
    is_stuck: bool = False
    stuck_duration_seconds: Optional[float] = None
    timestamp: str


@router.get("/scan-metrics", response_model=ScanMetricsResponse)
async def get_scan_metrics(
    user_id: Optional[str] = Query(None, description="Filter by specific user ID"),
    include_daily_stats: bool = Query(True, description="Include daily aggregated statistics"),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """
    Get detailed opportunity scan metrics for debugging.

    **Admin Only**

    Returns:
    - Latest scan details
    - Daily aggregated statistics
    - Recent scan history
    - System health indicators
    """

    try:
        redis = await get_redis_client()

        if not redis:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis not available - cannot retrieve metrics"
            )

        response_data = {
            "success": True,
            "latest_scan": None,
            "daily_stats": None,
            "recent_scans": [],
            "system_health": {},
            "timestamp": datetime.utcnow().isoformat()
        }

        # Get latest scan metrics
        try:
            metrics_key = "service_metrics:user_initiated_scans"
            latest_scan_data = await redis.get(metrics_key)

            if latest_scan_data:
                response_data["latest_scan"] = json.loads(latest_scan_data)
                logger.info("📊 Retrieved latest scan metrics",
                           scan_id=response_data["latest_scan"].get("scan_id"))
        except Exception as e:
            logger.warning("Failed to retrieve latest scan metrics", error=str(e))

        # Get daily statistics
        if include_daily_stats:
            try:
                today = datetime.utcnow().strftime('%Y-%m-%d')
                stats_key = f"opportunity_scan_stats:{today}"

                stats = await redis.hgetall(stats_key)

                if stats:
                    # Decode Redis hash
                    decoded_stats = {}
                    for key, value in stats.items():
                        try:
                            k = key.decode() if isinstance(key, bytes) else key
                            v = value.decode() if isinstance(value, bytes) else value

                            # Try to convert numeric values
                            try:
                                if '.' in str(v):
                                    decoded_stats[k] = float(v)
                                else:
                                    decoded_stats[k] = int(v)
                            except (ValueError, TypeError):
                                decoded_stats[k] = v
                        except Exception as decode_error:
                            logger.debug("Failed to decode stat",
                                       key=key,
                                       error=str(decode_error))

                    response_data["daily_stats"] = {
                        "date": today,
                        "stats": decoded_stats,
                        "success_rate": (
                            decoded_stats.get("successful_scans", 0) /
                            max(1, decoded_stats.get("total_scans", 1)) * 100
                        ) if decoded_stats.get("total_scans") else 0
                    }

                    logger.info("📈 Retrieved daily scan statistics",
                               total_scans=decoded_stats.get("total_scans"),
                               success_rate=response_data["daily_stats"]["success_rate"])
            except Exception as e:
                logger.warning("Failed to retrieve daily statistics", error=str(e))

        # Get recent scans for specific user (if requested)
        if user_id:
            try:
                # Look for user-specific scan cache
                user_scan_pattern = f"user_opportunities:{user_id}:*"
                recent_scans = []

                async for cache_key in redis.scan_iter(match=user_scan_pattern, count=10):
                    try:
                        cached_data = await redis.get(cache_key)
                        if cached_data:
                            data = json.loads(cached_data)

                            # Extract scan info
                            payload = data.get("payload", data)
                            scan_info = {
                                "scan_id": payload.get("scan_id", "unknown"),
                                "opportunities_count": len(payload.get("opportunities", [])),
                                "execution_time_ms": payload.get("execution_time_ms", 0),
                                "last_updated": payload.get("last_updated", "unknown"),
                                "cache_key": cache_key.decode() if isinstance(cache_key, bytes) else cache_key
                            }
                            recent_scans.append(scan_info)

                            if len(recent_scans) >= 5:  # Limit to 5 most recent
                                break
                    except Exception as parse_error:
                        logger.debug("Failed to parse cached scan", error=str(parse_error))

                response_data["recent_scans"] = recent_scans
                logger.info(f"🔍 Retrieved {len(recent_scans)} recent scans for user",
                           user_id=user_id)
            except Exception as e:
                logger.warning("Failed to retrieve recent scans", error=str(e))

        # System health indicators
        try:
            # Check error counts
            today = datetime.utcnow().strftime('%Y-%m-%d')
            error_key = f"opportunity_discovery_errors:{today}"
            daily_errors = await redis.get(error_key) or b'0'

            response_data["system_health"] = {
                "redis_connected": True,
                "daily_errors": int(daily_errors) if daily_errors else 0,
                "status": "healthy" if (int(daily_errors) if daily_errors else 0) < 10 else "degraded",
                "last_check": datetime.utcnow().isoformat()
            }
        except Exception as e:
            response_data["system_health"] = {
                "redis_connected": False,
                "error": str(e),
                "status": "unhealthy"
            }

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve scan metrics",
                    error=str(e),
                    exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve scan metrics: {str(e)}"
        )


@router.get("/scan-history/{user_id}")
async def get_user_scan_history(
    user_id: str,
    limit: int = Query(10, ge=1, le=50, description="Number of scans to retrieve"),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """
    Get detailed scan history for a specific user.

    **Admin Only**

    Returns chronological list of user's opportunity scans with full details.
    """

    try:
        redis = await get_redis_client()

        if not redis:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis not available"
            )

        # Search for all user scans
        user_scan_pattern = f"user_opportunities:{user_id}:*"
        scan_history = []

        async for cache_key in redis.scan_iter(match=user_scan_pattern):
            try:
                cached_data = await redis.get(cache_key)
                if cached_data:
                    data = json.loads(cached_data)
                    payload = data.get("payload", data)

                    scan_entry = {
                        "scan_id": payload.get("scan_id", "unknown"),
                        "user_id": user_id,
                        "opportunities_count": len(payload.get("opportunities", [])),
                        "strategies_scanned": len(payload.get("strategy_performance", {}).get("active_strategies", [])),
                        "execution_time_ms": payload.get("execution_time_ms", 0),
                        "last_updated": payload.get("last_updated"),
                        "user_profile": payload.get("user_profile", {}),
                        "asset_discovery": payload.get("asset_discovery", {}),
                        "partial": data.get("partial", False),
                        "cache_key": cache_key.decode() if isinstance(cache_key, bytes) else cache_key
                    }

                    scan_history.append(scan_entry)

                    if len(scan_history) >= limit:
                        break
            except Exception as parse_error:
                logger.debug("Failed to parse scan history entry",
                           error=str(parse_error))

        # Sort by timestamp (most recent first)
        scan_history.sort(
            key=lambda x: x.get("last_updated", ""),
            reverse=True
        )

        logger.info(f"📜 Retrieved scan history",
                   user_id=user_id,
                   scans_found=len(scan_history))

        return {
            "success": True,
            "user_id": user_id,
            "total_scans": len(scan_history),
            "scans": scan_history[:limit],
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve scan history",
                    user_id=user_id,
                    error=str(e),
                    exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve scan history: {str(e)}"
        )


@router.delete("/clear-scan-cache/{user_id}")
async def clear_user_scan_cache(
    user_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """
    Clear all cached scan data for a specific user.

    **Admin Only**

    Useful for debugging or forcing fresh scans.
    """

    try:
        redis = await get_redis_client()

        if not redis:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis not available"
            )

        # Find and delete all user scan cache entries
        user_scan_pattern = f"user_opportunities:{user_id}:*"
        deleted_count = 0

        async for cache_key in redis.scan_iter(match=user_scan_pattern):
            await redis.delete(cache_key)
            deleted_count += 1

        # Also clear last scan timestamp
        last_scan_key = f"user_opportunity_last_scan:{user_id}"
        await redis.delete(last_scan_key)

        logger.info("🗑️ Cleared user scan cache",
                   user_id=user_id,
                   entries_deleted=deleted_count)

        return {
            "success": True,
            "user_id": user_id,
            "entries_deleted": deleted_count,
            "message": f"Cleared {deleted_count} cache entries for user",
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to clear scan cache",
                    user_id=user_id,
                    error=str(e),
                    exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear scan cache: {str(e)}"
        )


@router.get("/scan-lifecycle/{scan_id}", response_model=ScanLifecycleResponse)
async def get_scan_lifecycle(
    scan_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """
    Get detailed lifecycle tracking for a specific scan.

    **Admin Only**

    Shows which phase the scan is in, whether it's stuck, and detailed progression through each phase.
    This is the PRIMARY diagnostic tool for understanding why scans fail or timeout.
    """

    try:
        redis = await get_redis_client()

        if not redis:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis not available"
            )

        lifecycle_key = f"scan_lifecycle:{scan_id}"

        # Get all lifecycle data
        lifecycle_data = await redis.hgetall(lifecycle_key)

        if not lifecycle_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No lifecycle data found for scan {scan_id}"
            )

        # Decode Redis hash
        decoded_data = {}
        for key, value in lifecycle_data.items():
            k = key.decode() if isinstance(key, bytes) else key
            v = value.decode() if isinstance(value, bytes) else value
            decoded_data[k] = v

        # Extract current state
        current_phase = decoded_data.get("current_phase")
        current_status = decoded_data.get("current_status")
        last_updated = decoded_data.get("last_updated")

        # Parse all phase data
        phases = {}
        for key, value in decoded_data.items():
            if key not in ["current_phase", "current_status", "last_updated"]:
                try:
                    phases[key] = json.loads(value)
                except json.JSONDecodeError:
                    phases[key] = value

        # Determine if scan is stuck
        is_stuck = False
        stuck_duration_seconds = None

        if last_updated and current_status == "in_progress":
            try:
                last_update_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                now = datetime.utcnow()
                stuck_duration = (now - last_update_time).total_seconds()

                # Consider stuck if no update in 120 seconds
                if stuck_duration > 120:
                    is_stuck = True
                    stuck_duration_seconds = stuck_duration

            except Exception as time_parse_error:
                logger.debug("Failed to parse time", error=str(time_parse_error))

        response = {
            "success": True,
            "scan_id": scan_id,
            "current_phase": current_phase,
            "current_status": current_status,
            "last_updated": last_updated,
            "phases": phases,
            "is_stuck": is_stuck,
            "stuck_duration_seconds": stuck_duration_seconds,
            "timestamp": datetime.utcnow().isoformat()
        }

        logger.info("📍 Retrieved scan lifecycle",
                   scan_id=scan_id,
                   current_phase=current_phase,
                   is_stuck=is_stuck)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve scan lifecycle",
                    scan_id=scan_id,
                    error=str(e),
                    exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve scan lifecycle: {str(e)}"
        )
