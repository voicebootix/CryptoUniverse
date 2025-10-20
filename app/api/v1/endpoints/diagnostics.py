"""
Production diagnostics endpoint for troubleshooting request flow.
This helps identify exactly where requests are failing in the middleware stack.
"""

import time
from datetime import datetime
from typing import Dict, Any, List

import structlog
from fastapi import APIRouter, Request
from sqlalchemy import text

from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis_client
from app.services.rate_limit import rate_limiter

logger = structlog.get_logger(__name__)
router = APIRouter()



@router.get("/test-layers")
async def test_middleware_layers(request: Request):
    """
    Test each middleware layer independently to identify where requests fail.
    This endpoint bypasses authentication to test the stack.
    """
    logger.info(
        "diagnostics.test_layers_requested",
        path=str(request.url.path),
        client_ip=request.client.host if request.client else "unknown",
    )

    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "client_ip": request.client.host if request.client else "unknown",
        "headers_received": dict(request.headers),
        "layers": {},
        "timing": {},
    }

    # Test 1: Basic Response (proves server is responding)
    start = time.perf_counter()
    results["layers"]["basic_response"] = {
        "status": "passed",
        "message": "Server is responding to requests"
    }
    results["timing"]["basic_response_ms"] = round((time.perf_counter() - start) * 1000, 2)

    # Test 2: Request Logging Middleware
    start = time.perf_counter()
    try:
        # Check if request has been logged (would be in request.state if middleware ran)
        results["layers"]["request_logging"] = {
            "status": "passed" if hasattr(request.state, "_start_time") else "skipped",
            "message": "Request logging middleware executed" if hasattr(request.state, "_start_time") else "Request logging not active"
        }
    except Exception as e:
        results["layers"]["request_logging"] = {
            "status": "failed",
            "error": str(e)
        }
    results["timing"]["request_logging_ms"] = round((time.perf_counter() - start) * 1000, 2)

    # Test 3: Database Connection
    start = time.perf_counter()
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
            results["layers"]["database"] = {
                "status": "passed",
                "message": "Database connection successful"
            }
    except Exception as e:
        results["layers"]["database"] = {
            "status": "failed",
            "error": str(e),
            "type": type(e).__name__
        }
    results["timing"]["database_ms"] = round((time.perf_counter() - start) * 1000, 2)

    # Test 4: Redis Connection
    start = time.perf_counter()
    try:
        redis = await get_redis_client()
        if redis:
            await redis.ping()
            results["layers"]["redis"] = {
                "status": "passed",
                "message": "Redis connection successful"
            }
        else:
            results["layers"]["redis"] = {
                "status": "degraded",
                "message": "Redis not available - running in degraded mode"
            }
    except Exception as e:
        results["layers"]["redis"] = {
            "status": "failed",
            "error": str(e),
            "type": type(e).__name__
        }
    results["timing"]["redis_ms"] = round((time.perf_counter() - start) * 1000, 2)

    # Test 5: Rate Limiter State
    start = time.perf_counter()
    try:
        # Check if rate limiter is initialized
        if hasattr(rate_limiter, 'redis'):
            if rate_limiter.redis:
                results["layers"]["rate_limiter"] = {
                    "status": "passed",
                    "message": "Rate limiter initialized with Redis",
                    "redis_available": True
                }
            else:
                results["layers"]["rate_limiter"] = {
                    "status": "degraded",
                    "message": "Rate limiter running without Redis (fail-open mode)",
                    "redis_available": False
                }
        else:
            results["layers"]["rate_limiter"] = {
                "status": "not_initialized",
                "message": "Rate limiter not initialized"
            }
    except Exception as e:
        results["layers"]["rate_limiter"] = {
            "status": "error",
            "error": str(e),
            "type": type(e).__name__
        }
    results["timing"]["rate_limiter_ms"] = round((time.perf_counter() - start) * 1000, 2)

    # Test 6: Rate Limit Check (actual execution)
    start = time.perf_counter()
    try:
        # Try to execute a rate limit check
        can_proceed = await rate_limiter.check_rate_limit(
            key=f"diagnostic:{request.client.host}",
            limit=100,
            window=60
        )
        results["layers"]["rate_limit_check"] = {
            "status": "passed",
            "message": "Rate limit check executed successfully",
            "result": "allowed" if can_proceed else "blocked"
        }
    except Exception as e:
        results["layers"]["rate_limit_check"] = {
            "status": "failed",
            "error": str(e),
            "type": type(e).__name__,
            "message": "Rate limit check failed - this might be blocking login"
        }
    results["timing"]["rate_limit_check_ms"] = round((time.perf_counter() - start) * 1000, 2)

    # Test 7: Auth Middleware State
    start = time.perf_counter()
    try:
        # Check if auth middleware added user to request state
        if hasattr(request.state, "user"):
            results["layers"]["auth_middleware"] = {
                "status": "authenticated",
                "user": request.state.user
            }
        else:
            results["layers"]["auth_middleware"] = {
                "status": "not_authenticated",
                "message": "No authentication required for this endpoint"
            }
    except Exception as e:
        results["layers"]["auth_middleware"] = {
            "status": "error",
            "error": str(e)
        }
    results["timing"]["auth_middleware_ms"] = round((time.perf_counter() - start) * 1000, 2)

    # Calculate total time
    total_time = sum(v for k, v in results["timing"].items() if k.endswith("_ms"))
    results["timing"]["total_ms"] = round(total_time, 2)

    # Overall health assessment
    failed_layers = [k for k, v in results["layers"].items() if v.get("status") == "failed"]
    degraded_layers = [k for k, v in results["layers"].items() if v.get("status") == "degraded"]

    results["overall"] = {
        "health": "unhealthy" if failed_layers else ("degraded" if degraded_layers else "healthy"),
        "failed_layers": failed_layers,
        "degraded_layers": degraded_layers,
        "recommendation": _get_recommendation(failed_layers, degraded_layers)
    }

    logger.info(
        "diagnostics.test_layers_result",
        health=results["overall"].get("health"),
        failed_layers=failed_layers,
        degraded_layers=degraded_layers,
    )

    return results


@router.post("/test-login-flow")
async def test_login_flow(request: Request):
    """
    Trace the exact login flow to identify where it hangs.
    """
    logger.info(
        "diagnostics.test_login_flow_requested",
        path=str(request.url.path),
        client_ip=request.client.host if request.client else "unknown",
    )

    trace = {
        "timestamp": datetime.utcnow().isoformat(),
        "steps": [],
        "timing": {},
        "success": False
    }

    async def add_step(name: str, status: str, details: Any = None, error: Any = None):
        step = {
            "name": name,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        if details:
            step["details"] = details
        if error:
            step["error"] = str(error)
            step["error_type"] = type(error).__name__
        trace["steps"].append(step)
        return step

    # Step 1: Check if request received
    start = time.perf_counter()
    await add_step("request_received", "success", {
        "method": request.method,
        "path": request.url.path,
        "client": request.client.host if request.client else "unknown"
    })
    trace["timing"]["request_received_ms"] = round((time.perf_counter() - start) * 1000, 2)

    # Step 2: Check rate limiter
    start = time.perf_counter()
    try:
        client_ip = request.client.host if request.client else "127.0.0.1"

        # First check if rate limiter is initialized
        if not hasattr(rate_limiter, 'redis'):
            await add_step("rate_limiter_init", "failed",
                          details={"message": "Rate limiter not initialized"})
        else:
            await add_step("rate_limiter_init", "success",
                          details={"redis_available": rate_limiter.redis is not None})

        # Try the actual rate limit check
        try:
            await rate_limiter.check_rate_limit(
                key=f"test-login:{client_ip}",
                limit=5,
                window=300
            )
            await add_step("rate_limit_check", "success")
        except Exception as e:
            await add_step("rate_limit_check", "failed", error=e)

    except Exception as e:
        await add_step("rate_limiter", "failed", error=e)
    trace["timing"]["rate_limiter_ms"] = round((time.perf_counter() - start) * 1000, 2)

    # Step 3: Database query
    start = time.perf_counter()
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
            await add_step("database_query", "success")
    except Exception as e:
        await add_step("database_query", "failed", error=e)
    trace["timing"]["database_ms"] = round((time.perf_counter() - start) * 1000, 2)

    # Step 4: Check auth service
    start = time.perf_counter()
    try:
        from app.api.v1.endpoints.auth import auth_service
        # Just verify it exists and has required methods
        if hasattr(auth_service, 'verify_password'):
            await add_step("auth_service", "success",
                          details={"methods": ["verify_password", "create_access_token"]})
        else:
            await add_step("auth_service", "failed",
                          details={"message": "Auth service missing required methods"})
    except Exception as e:
        await add_step("auth_service", "failed", error=e)
    trace["timing"]["auth_service_ms"] = round((time.perf_counter() - start) * 1000, 2)

    # Calculate total
    trace["timing"]["total_ms"] = round(sum(v for k, v in trace["timing"].items() if k.endswith("_ms")), 2)

    # Determine success
    failed_steps = [s for s in trace["steps"] if s["status"] == "failed"]
    trace["success"] = len(failed_steps) == 0
    trace["failed_steps"] = [s["name"] for s in failed_steps]

    if not trace["success"]:
        trace["diagnosis"] = _diagnose_login_issue(failed_steps)

    logger.info(
        "diagnostics.test_login_flow_result",
        success=trace["success"],
        failed_steps=trace.get("failed_steps", []),
    )

    return trace

def _get_recommendation(failed_layers: List[str], degraded_layers: List[str]) -> str:
    """Get recommendation based on failed/degraded layers."""
    if "rate_limit_check" in failed_layers:
        return "Rate limiter is failing - this is likely blocking login requests. Check Redis connection and rate limiter initialization."
    elif "database" in failed_layers:
        return "Database connection failed - check database URL and connectivity."
    elif "redis" in failed_layers:
        return "Redis connection failed - system running in degraded mode. Check Redis URL and connectivity."
    elif degraded_layers:
        return f"System running in degraded mode due to: {', '.join(degraded_layers)}"
    else:
        return "All layers operational"


def _diagnose_login_issue(failed_steps: List[Dict]) -> str:
    """Diagnose login issue based on failed steps."""
    for step in failed_steps:
        if step["name"] == "rate_limit_check":
            return "Login is failing at rate limit check. The rate limiter may not be properly initialized or Redis connection is failing."
        elif step["name"] == "database_query":
            return "Database queries are failing. Check database connection and credentials."
        elif step["name"] == "auth_service":
            return "Auth service is not properly initialized."
    return "Unable to determine specific cause - check application logs"

