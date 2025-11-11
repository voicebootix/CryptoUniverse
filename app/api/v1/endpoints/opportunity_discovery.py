"""
ENTERPRISE OPPORTUNITY DISCOVERY API ENDPOINTS

RESTful API endpoints for the new User Opportunity Discovery system.
Provides programmatic access to strategy-based opportunity scanning.

NO MOCK DATA - PRODUCTION READY

Author: CTO Assistant
Date: 2025-09-12
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, field_validator, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_database
from app.api.v1.endpoints.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.services.user_opportunity_discovery import user_opportunity_discovery
from app.services.user_onboarding_service import user_onboarding_service
from app.services.rate_limit import rate_limiter

settings = get_settings()
logger = structlog.get_logger(__name__)

router = APIRouter()


# Request/Response Models
class OpportunityDiscoveryRequest(BaseModel):
    """Request model for opportunity discovery."""
    force_refresh: bool = False
    include_strategy_recommendations: bool = True
    filter_by_risk_level: Optional[str] = None  # low, medium, high, very_high
    min_profit_potential: Optional[float] = None  # USD
    max_required_capital: Optional[float] = None  # USD
    preferred_timeframes: Optional[List[str]] = None  # ["1h", "4h", "24h", "7d"]
    opportunity_type: Optional[List[str]] = None  # Filter by specific opportunity types
    strategy_types: Optional[List[str]] = None  # Legacy alias for opportunity_type (backward compatibility)
    symbols: Optional[List[str]] = None
    asset_tiers: Optional[List[str]] = None
    strategy_ids: Optional[List[str]] = None

    @field_validator("symbols", "asset_tiers", "strategy_ids", mode="before")
    @classmethod
    def normalize_list_values(cls, value):
        if value is None:
            return None

        if isinstance(value, str):
            items = [segment.strip() for segment in value.split(",")]
        elif isinstance(value, (list, tuple, set)):
            items = []
            for entry in value:
                if entry is None:
                    continue
                if isinstance(entry, str):
                    candidate = entry.strip()
                else:
                    candidate = str(entry).strip()
                if candidate:
                    items.append(candidate)
        else:
            raise ValueError("List values must be provided as a sequence or comma-separated string")

        deduped: List[str] = []
        seen: Set[str] = set()
        for item in items:
            if not item:
                continue
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)

        return deduped or None

    def __init__(self, **data):
        # Handle backward compatibility: map strategy_types to opportunity_type
        if 'strategy_types' in data and 'opportunity_type' not in data:
            data['opportunity_type'] = data['strategy_types']
        super().__init__(**data)


class OpportunityResponse(BaseModel):
    """Response model for single opportunity."""
    strategy_id: str
    strategy_name: str
    opportunity_type: str
    symbol: str
    exchange: str
    profit_potential_usd: float
    confidence_score: float
    risk_level: str
    required_capital_usd: float
    estimated_timeframe: str
    entry_price: Optional[float]
    exit_price: Optional[float]
    metadata: Optional[Dict[str, Any]]
    discovered_at: datetime


class OpportunityDiscoveryResponse(BaseModel):
    """Response model for opportunity discovery."""
    success: bool
    scan_id: str
    user_id: str
    opportunities: List[OpportunityResponse]
    total_opportunities: int
    signal_analysis: Optional[Dict[str, Any]] = None
    threshold_transparency: Optional[Dict[str, Any]] = None
    user_profile: Dict[str, Any]
    strategy_performance: Dict[str, Any]
    asset_discovery: Dict[str, Any]
    strategy_recommendations: List[Dict[str, Any]]
    execution_time_ms: float
    last_updated: str
    
    # Optional fields for errors
    error: Optional[str] = None
    fallback_used: Optional[bool] = None


class UserOnboardingResponse(BaseModel):
    """Response model for user onboarding."""
    success: bool
    onboarding_id: str
    user_id: str
    results: Dict[str, Any]
    execution_time_ms: float
    onboarded_at: str
    next_steps: List[str]


@router.post("/discover")
async def discover_opportunities(
    request: OpportunityDiscoveryRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    ENTERPRISE Opportunity Discovery - Async Job Pattern.
    
    Initiates a background scan of trading opportunities.
    Returns immediately with scan_id for polling.
    
    This follows enterprise best practices for long-running operations:
    - No timeout issues (scan runs in background)
    - Real-time progress updates via polling
    - Scalable to any number of strategies
    - Better UX with progress indicators
    """
    
    # Enforce rate limiting per user
    rate_limit_passed = await rate_limiter.check_rate_limit(
        key=f"opportunity:discovery:{current_user.id}",
        limit=30,  # 30 requests per minute
        window=60,
        user_id=str(current_user.id)
    )
    
    if not rate_limit_passed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for opportunity discovery (30 requests per minute)",
            headers={"Retry-After": "60"}
        )
    
    try:
        logger.info("🔍 ENTERPRISE Opportunity Discovery API called (async mode)",
                   user_id=str(current_user.id),
                   force_refresh=request.force_refresh)
        
        # Initialize discovery service
        await user_opportunity_discovery.async_init()

        user_id_str = str(current_user.id)
        symbols = request.symbols or []
        asset_tiers = request.asset_tiers or []
        strategy_ids = request.strategy_ids or []
        filter_summary = user_opportunity_discovery._summarize_scan_filters(
            symbols=symbols,
            asset_tiers=asset_tiers,
            strategy_ids=strategy_ids,
        )
        cache_key = user_opportunity_discovery._build_scan_cache_key(
            user_id_str,
            symbols=symbols,
            asset_tiers=asset_tiers,
            strategy_ids=strategy_ids,
        )

        existing_task = user_opportunity_discovery._scan_tasks.get(cache_key)
        existing_scan_id = getattr(existing_task, "scan_id", None) if existing_task else None

        if existing_task and not existing_task.done() and not request.force_refresh:
            cached_entry = await user_opportunity_discovery._get_cached_scan_entry(
                user_id_str,
                scan_id=existing_scan_id,
            )
            if cached_entry:
                active_scan_id = cached_entry.payload.get("scan_id", existing_scan_id)
                poll_id = active_scan_id or existing_scan_id or f"scan_{uuid.uuid4().hex}"
                return {
                    "success": True,
                    "scan_id": poll_id,
                    "status": "scanning",
                    "message": "A scan is already in progress for this filter set",
                    "estimated_completion_seconds": 120,
                    "poll_url": f"/api/v1/opportunities/status/{poll_id}",
                    "progress": {
                        "strategies_completed": cached_entry.payload.get("metadata", {}).get("strategies_completed", 0),
                        "total_strategies": cached_entry.payload.get("metadata", {}).get("total_strategies", 14)
                    },
                    "filters": filter_summary,
                }

        scan_id = existing_scan_id or f"scan_{uuid.uuid4().hex}"

        await user_opportunity_discovery._register_scan_lookup(
            user_id_str,
            cache_key,
            scan_id,
        )

        await user_opportunity_discovery._prime_scan_placeholder(
            cache_key=cache_key,
            user_id=user_id_str,
            scan_id=scan_id,
            filter_summary=filter_summary,
            symbols=symbols or None,
            asset_tiers=asset_tiers or None,
            strategy_ids=strategy_ids or None,
        )

        # Start background scan (don't await!)
        async def run_discovery_background():
            try:
                await user_opportunity_discovery.discover_opportunities_for_user(
                    user_id=user_id_str,
                    force_refresh=request.force_refresh,
                    include_strategy_recommendations=request.include_strategy_recommendations,
                    symbols=symbols or None,
                    asset_tiers=asset_tiers or None,
                    strategy_ids=strategy_ids or None,
                    scan_id=scan_id,
                    cache_key=cache_key,
                )
            except Exception as e:
                logger.error("Background opportunity discovery failed",
                           user_id=user_id_str,
                           error=str(e),
                           exc_info=True)
        
        # Schedule background task
        background_tasks.add_task(run_discovery_background)
        
        # Return immediately with scan info
        return {
            "success": True,
            "scan_id": scan_id,
            "status": "initiated",
            "message": "Opportunity scan initiated successfully",
            "estimated_completion_seconds": 120,
            "poll_url": f"/api/v1/opportunities/status/{scan_id}",
            "results_url": f"/api/v1/opportunities/results/{scan_id}",
            "polling_interval_seconds": 3,
            "instructions": "Poll the status endpoint every 3 seconds to check progress",
            "filters": filter_summary,
        }
        
    except Exception as e:
        logger.error("Failed to initiate opportunity discovery",
                    error=str(e),
                    user_id=str(current_user.id),
                    exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate opportunity discovery: {str(e)}"
        )


@router.get("/status/{scan_id}")
async def get_scan_status(
    scan_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get the status of an ongoing opportunity discovery scan.
    
    Returns:
    - status: "not_found" | "scanning" | "complete" | "failed"
    - progress: {strategies_completed, total_strategies, opportunities_found_so_far}
    - partial_results: First 10 opportunities (if available)
    """
    try:
        user_id_str = str(current_user.id)

        # Get cached scan entry
        cached_entry = await user_opportunity_discovery._get_cached_scan_entry(
            user_id_str,
            scan_id=scan_id,
        )

        cache_key: Optional[str] = None
        if not cached_entry:
            # Attempt to resolve the cache key even if cached entry is missing. This allows us to
            # detect scans that are still warming up or whose placeholder has not been written yet.
            cache_key = await user_opportunity_discovery._resolve_scan_cache_key(
                user_id=user_id_str,
                scan_id=scan_id,
            )

            if cache_key:
                # Re-check using the cache key directly in case the entry was created between the
                # initial lookup and resolving the cache key (avoids transient race conditions).
                cached_entry = await user_opportunity_discovery._peek_cached_scan_entry(cache_key)

        not_found_response = {
            "success": False,
            "status": "not_found",
            "message": "No scan found for this user. Please initiate a new scan.",
        }

        if not cached_entry:
            if cache_key:
                in_progress = await user_opportunity_discovery.has_active_scan_task(cache_key)
                if not in_progress:
                    return not_found_response

                progress_payload = {
                    "strategies_completed": 0,
                    "total_strategies": 0,
                    "opportunities_found_so_far": 0,
                    "percentage": 0,
                }

                message = (
                    "Scan is initializing. No results are available yet." if in_progress else
                    "Scan registration found but no cached progress yet."
                )

                return {
                    "success": True,
                    "status": "scanning",
                    "scan_id": scan_id,
                    "message": message,
                    "progress": progress_payload,
                    "partial_results": [],
                    "estimated_time_remaining_seconds": 120,
                }

            return not_found_response

        # Check if scan is still in progress
        if cached_entry.partial:
            metadata = cached_entry.payload.get("metadata", {})
            opportunities = cached_entry.payload.get("opportunities", [])
            
            return {
                "success": True,
                "status": "scanning",
                "scan_id": cached_entry.payload.get("scan_id", scan_id),
                "message": "Scan in progress",
                "progress": {
                    "strategies_completed": metadata.get("strategies_completed", 0),
                    "total_strategies": metadata.get("total_strategies", 14),
                    "opportunities_found_so_far": len(opportunities),
                    "percentage": int((metadata.get("strategies_completed", 0) / max(1, metadata.get("total_strategies", 14))) * 100)
                },
                "partial_results": opportunities[:10],  # First 10 opportunities
                "estimated_time_remaining_seconds": max(0, 120 - metadata.get("elapsed_seconds", 0))
            }
        
        # Scan is complete
        return {
            "success": True,
            "status": "complete",
            "scan_id": cached_entry.payload.get("scan_id", scan_id),
            "message": "Scan completed successfully",
            "total_opportunities": len(cached_entry.payload.get("opportunities", [])),
            "results_url": f"/api/v1/opportunities/results/{scan_id}"
        }
        
    except Exception as e:
        logger.error("Failed to get scan status",
                    error=str(e),
                    user_id=str(current_user.id),
                    scan_id=scan_id,
                    exc_info=True)
        
        return {
            "success": False,
            "status": "failed",
            "message": f"Failed to get scan status: {str(e)}"
        }


@router.get("/results/{scan_id}", response_model=OpportunityDiscoveryResponse)
async def get_scan_results(
    scan_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get the complete results of a finished opportunity discovery scan.
    
    Returns full opportunity list with all metadata.
    Raises 404 if scan is not complete yet.
    """
    try:
        # Get cached scan entry
        cached_entry = await user_opportunity_discovery._get_cached_scan_entry(
            str(current_user.id),
            scan_id=scan_id,
        )
        
        if not cached_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No scan results found. Please initiate a new scan."
            )
        
        if cached_entry.partial:
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="Scan is still in progress. Please poll the status endpoint."
            )
        
        # Convert opportunities to response format
        opportunities = cached_entry.payload.get("opportunities", [])
        opportunity_responses = []
        
        for opp in opportunities:
            try:
                opportunity_responses.append(OpportunityResponse(**opp))
            except ValidationError as e:
                logger.warning("Skipping malformed opportunity in results",
                             validation_error=str(e),
                             user_id=str(current_user.id))
        
        return OpportunityDiscoveryResponse(
            success=True,
            scan_id=cached_entry.payload.get("scan_id", scan_id),
            user_id=str(current_user.id),
            opportunities=opportunity_responses,
            total_opportunities=len(opportunity_responses),
            signal_analysis=cached_entry.payload.get("signal_analysis"),
            threshold_transparency=cached_entry.payload.get("threshold_transparency"),
            user_profile=cached_entry.payload.get("user_profile", {}),
            strategy_performance=cached_entry.payload.get("strategy_performance", {}),
            asset_discovery=cached_entry.payload.get("asset_discovery", {}),
            strategy_recommendations=cached_entry.payload.get("strategy_recommendations", []),
            execution_time_ms=cached_entry.payload.get("execution_time_ms", 0),
            last_updated=cached_entry.payload.get("last_updated", datetime.utcnow().isoformat())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get scan results",
                    error=str(e),
                    user_id=str(current_user.id),
                    scan_id=scan_id,
                    exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve scan results: {str(e)}"
        )


@router.get("/user-status")
async def get_discovery_status(
    current_user: User = Depends(get_current_user)
):
    """Get user's opportunity discovery status and profile."""
    
    try:
        # Get user onboarding status
        onboarding_status = await user_onboarding_service.check_user_onboarding_status(
            str(current_user.id)
        )
        
        # Get last discovery info from cache
        from app.core.redis import get_redis_client
        redis = await get_redis_client()
        
        last_scan_info = None
        if redis:
            last_scan_key = f"user_opportunity_last_scan:{current_user.id}"
            last_scan_timestamp = await redis.get(last_scan_key)
            
            if last_scan_timestamp:
                try:
                    decoded_timestamp = last_scan_timestamp.decode()
                    last_scan_info = {
                        "last_scan": decoded_timestamp,
                        "time_since_last_scan": (
                            datetime.utcnow() - 
                            datetime.fromisoformat(decoded_timestamp)
                        ).total_seconds()
                    }
                except (UnicodeDecodeError, AttributeError, TypeError, ValueError) as e:
                    logger.warning("Failed to parse last scan timestamp",
                                 timestamp_value=last_scan_timestamp,
                                 error=str(e),
                                 user_id=str(current_user.id))
                    # Set sensible default when parsing fails
                    last_scan_info = {
                        "last_scan": None,
                        "time_since_last_scan": None,
                        "parse_error": "Invalid timestamp format"
                    }
        
        return {
            "success": True,
            "user_id": str(current_user.id),
            "onboarding_status": onboarding_status,
            "last_scan_info": last_scan_info,
            "discovery_available": onboarding_status.get("onboarded", False),
            "recommendations": {
                "next_action": "Discover opportunities" if onboarding_status.get("onboarded") else "Complete onboarding",
                "estimated_opportunities": "3-50+ based on your strategies" if onboarding_status.get("active_strategies", 0) > 0 else "Get free strategies first"
            }
        }
        
    except Exception as e:
        logger.error("Discovery status check failed",
                    error=str(e),
                    user_id=str(current_user.id))
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status check failed: {str(e)}"
        )


@router.post("/onboard", response_model=UserOnboardingResponse)
async def trigger_user_onboarding(
    referral_code: Optional[str] = None,
    welcome_package: str = "standard",
    current_user: User = Depends(get_current_user)
):
    """Trigger user onboarding process (3 free strategies + credit account)."""
    
    # Enforce rate limiting for onboarding per user
    rate_limit_passed = await rate_limiter.check_rate_limit(
        key=f"opportunity:onboard:{current_user.id}",
        limit=5,  # 5 onboarding attempts per hour
        window=3600,
        user_id=str(current_user.id)
    )
    
    if not rate_limit_passed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for user onboarding (5 attempts per hour)",
            headers={"Retry-After": "3600"}
        )
    
    try:
        logger.info("🚀 User onboarding triggered via API",
                   user_id=str(current_user.id),
                   referral_code=bool(referral_code))
        
        onboarding_result = await user_onboarding_service.onboard_new_user(
            user_id=str(current_user.id),
            referral_code=referral_code,
            welcome_package=welcome_package
        )
        
        if not onboarding_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=onboarding_result.get("error", "Onboarding failed")
            )
        
        return UserOnboardingResponse(
            success=True,
            onboarding_id=onboarding_result["onboarding_id"],
            user_id=onboarding_result["user_id"],
            results=onboarding_result.get("results", {}),
            execution_time_ms=onboarding_result.get("execution_time_ms", 0),
            onboarded_at=onboarding_result.get("onboarded_at", datetime.utcnow().isoformat()),
            next_steps=onboarding_result.get("next_steps", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("User onboarding API failed",
                    error=str(e),
                    user_id=str(current_user.id),
                    exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Onboarding failed: {str(e)}"
        )


@router.get("/metrics")
async def get_discovery_metrics(
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Get opportunity discovery metrics (Admin only)."""
    
    try:
        from app.core.redis import get_redis_client
        redis = await get_redis_client()
        
        if not redis:
            return {"success": False, "error": "Redis not available"}
        
        # Get error metrics
        today = datetime.utcnow().strftime('%Y-%m-%d')
        error_key = f"opportunity_discovery_errors:{today}"
        daily_errors = await redis.get(error_key) or 0
        
        # Get performance metrics (would need to be implemented)
        metrics = {
            "success": True,
            "daily_errors": int(daily_errors) if daily_errors else 0,
            "system_status": "operational",
            "last_updated": datetime.utcnow().isoformat()
        }
        
        return metrics
        
    except Exception as e:
        logger.error("Metrics retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Metrics retrieval failed: {str(e)}"
        )


@router.post("/test-discovery")
async def test_discovery_system(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Test the opportunity discovery system (Admin only)."""
    
    try:
        async def run_test_discovery():
            """Run test discovery in background."""
            try:
                test_result = await user_opportunity_discovery.discover_opportunities_for_user(
                    user_id=str(current_user.id),
                    force_refresh=True,
                    include_strategy_recommendations=True
                )
                
                logger.info("🧪 Test discovery completed",
                           success=test_result.get("success"),
                           opportunities_found=len(test_result.get("opportunities", [])))
                           
            except Exception as test_error:
                logger.error("Test discovery failed", error=str(test_error))
        
        def start_test_discovery():
            """Synchronous wrapper to schedule async test discovery."""
            try:
                # Schedule the async task in the event loop
                task = asyncio.create_task(run_test_discovery())
                
                # Add done callback to log any unhandled exceptions
                def log_task_result(future):
                    try:
                        if future.exception():
                            logger.error("Background test discovery task failed", 
                                       error=str(future.exception()),
                                       user_id=str(current_user.id))
                    except Exception as callback_error:
                        logger.error("Error in task completion callback", error=str(callback_error))
                
                task.add_done_callback(log_task_result)
                
            except Exception as schedule_error:
                logger.error("Failed to schedule test discovery task", error=str(schedule_error))
        
        background_tasks.add_task(start_test_discovery)
        
        return {
            "success": True,
            "message": "Test discovery started in background",
            "test_user_id": str(current_user.id)
        }
        
    except Exception as e:
        logger.error("Test discovery setup failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test setup failed: {str(e)}"
        )