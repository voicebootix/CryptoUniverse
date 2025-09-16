"""
ENTERPRISE OPPORTUNITY DISCOVERY API ENDPOINTS

RESTful API endpoints for the new User Opportunity Discovery system.
Provides programmatic access to strategy-based opportunity scanning.

NO MOCK DATA - PRODUCTION READY

Author: CTO Assistant
Date: 2025-09-12
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

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


@router.post("/discover", response_model=OpportunityDiscoveryResponse)
async def discover_opportunities(
    request: OpportunityDiscoveryRequest,
    current_user: User = Depends(get_current_user)
):
    """
    ENTERPRISE Opportunity Discovery - Main endpoint.
    
    Discovers trading opportunities based on user's purchased strategies
    and enterprise asset discovery across thousands of assets.
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
        logger.info("🔍 ENTERPRISE Opportunity Discovery API called",
                   user_id=str(current_user.id),
                   force_refresh=request.force_refresh)
        
        # Initialize discovery service
        await user_opportunity_discovery.async_init()
        
        # Run opportunity discovery
        discovery_result = await user_opportunity_discovery.discover_opportunities_for_user(
            user_id=str(current_user.id),
            force_refresh=request.force_refresh,
            include_strategy_recommendations=request.include_strategy_recommendations
        )
        
        if not discovery_result.get("success"):
            # Return error but with structured response, including validated fallback opportunities
            raw_fallback_opportunities = discovery_result.get("fallback_opportunities", [])
            
            # Validate fallback opportunities using the same validation as success path
            validated_fallback_opportunities = []
            fallback_validation_errors = []
            
            for i, opp in enumerate(raw_fallback_opportunities):
                try:
                    validated_fallback_opportunities.append(OpportunityResponse(**opp))
                except ValidationError as e:
                    logger.warning("Skipping malformed fallback opportunity data",
                                 opportunity_index=i,
                                 validation_error=str(e),
                                 opportunity_data=opp,
                                 user_id=str(current_user.id))
                    fallback_validation_errors.append({
                        "index": i,
                        "error": str(e),
                        "data": opp
                    })
            
            # Log summary if we had fallback validation errors
            if fallback_validation_errors:
                logger.warning("Fallback opportunity validation summary",
                             total_fallback_opportunities=len(raw_fallback_opportunities),
                             valid_fallback_opportunities=len(validated_fallback_opportunities),
                             validation_errors_count=len(fallback_validation_errors),
                             user_id=str(current_user.id))
            
            return OpportunityDiscoveryResponse(
                success=False,
                scan_id=discovery_result.get("scan_id", "error"),
                user_id=str(current_user.id),
                opportunities=validated_fallback_opportunities,
                total_opportunities=len(validated_fallback_opportunities),
                user_profile={},
                strategy_performance={},
                asset_discovery={},
                strategy_recommendations=[],
                execution_time_ms=discovery_result.get("execution_time_ms", 0),
                last_updated=datetime.utcnow().isoformat(),
                error=discovery_result.get("error", "Unknown error"),
                fallback_used=discovery_result.get("fallback_used", False)
            )
        
        # Apply filters if specified
        opportunities = discovery_result.get("opportunities", [])
        
        if request.filter_by_risk_level:
            opportunities = [
                opp for opp in opportunities 
                if opp.get("risk_level") == request.filter_by_risk_level
            ]
        
        if request.min_profit_potential is not None:
            opportunities = [
                opp for opp in opportunities
                if opp.get("profit_potential_usd", 0) >= request.min_profit_potential
            ]
        
        if request.max_required_capital is not None:
            opportunities = [
                opp for opp in opportunities
                if opp.get("required_capital_usd", float('inf')) <= request.max_required_capital
            ]
        
        if request.preferred_timeframes:
            opportunities = [
                opp for opp in opportunities
                if any(timeframe in opp.get("estimated_timeframe", "") 
                      for timeframe in request.preferred_timeframes)
            ]
        
        if request.opportunity_type:
            opportunities = [
                opp for opp in opportunities
                if opp.get("opportunity_type") in request.opportunity_type
            ]
        
        # Convert to response format with validation error handling
        opportunity_responses = []
        validation_errors = []
        
        for i, opp in enumerate(opportunities):
            try:
                opportunity_responses.append(OpportunityResponse(**opp))
            except ValidationError as e:
                logger.warning("Skipping malformed opportunity data",
                             opportunity_index=i,
                             validation_error=str(e),
                             opportunity_data=opp,
                             user_id=str(current_user.id))
                validation_errors.append({
                    "index": i,
                    "error": str(e),
                    "data": opp
                })
        
        # Log summary if we had validation errors
        if validation_errors:
            logger.warning("Opportunity validation summary",
                         total_opportunities=len(opportunities),
                         valid_opportunities=len(opportunity_responses),
                         validation_errors_count=len(validation_errors),
                         user_id=str(current_user.id))
        
        return OpportunityDiscoveryResponse(
            success=True,
            scan_id=discovery_result["scan_id"],
            user_id=discovery_result["user_id"],
            opportunities=opportunity_responses,
            total_opportunities=len(opportunity_responses),
            signal_analysis=discovery_result.get("signal_analysis"),
            threshold_transparency=discovery_result.get("threshold_transparency"),
            user_profile=discovery_result.get("user_profile", {}),
            strategy_performance=discovery_result.get("strategy_performance", {}),
            asset_discovery=discovery_result.get("asset_discovery", {}),
            strategy_recommendations=discovery_result.get("strategy_recommendations", []),
            execution_time_ms=discovery_result.get("execution_time_ms", 0),
            last_updated=discovery_result.get("last_updated", datetime.utcnow().isoformat())
        )
        
    except Exception as e:
        logger.error("Opportunity discovery API failed",
                    error=str(e),
                    user_id=str(current_user.id),
                    exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Opportunity discovery failed: {str(e)}"
        )


@router.get("/status")
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