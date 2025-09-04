"""
AI Consensus API Endpoints - Direct Access to AI Money Manager Brain

Exposes the 6 core AI consensus functions for direct user interaction:
1. analyze_opportunity - Multi-AI opportunity analysis with consensus scoring
2. validate_trade - Trade validation across multiple AI models  
3. risk_assessment - Comprehensive risk analysis with AI consensus
4. portfolio_review - Portfolio analysis with multi-AI insights
5. market_analysis - Market condition analysis with AI consensus
6. consensus_decision - Final decision making with weighted AI opinions

NO MOCK DATA - REAL AI CONSENSUS WITH COST TRACKING
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_database
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User

# Import existing services - NO DUPLICATION
from app.services.ai_consensus_core import ai_consensus_service
from app.services.unified_ai_manager import unified_ai_manager, InterfaceType
from app.services.master_controller import master_controller
from app.services.api_cost_tracker import api_cost_tracker, APIProvider
from app.services.emergency_manager import emergency_manager
from app.services.rate_limit import rate_limiter

settings = get_settings()
logger = structlog.get_logger(__name__)

router = APIRouter()


# Request/Response Models
class AIConsensusRequest(BaseModel):
    """Base AI consensus request."""
    analysis_request: str  # JSON string or direct data
    confidence_threshold: float = 75.0
    ai_models: str = "all"  # "all", "gpt4_claude", "cost_optimized"
    
    @field_validator('confidence_threshold')
    @classmethod
    def validate_confidence_threshold(cls, v):
        if not 50.0 <= v <= 95.0:
            raise ValueError('Confidence threshold must be between 50.0 and 95.0')
        return v
    
    @field_validator('ai_models')
    @classmethod
    def validate_ai_models(cls, v):
        valid_strategies = ["all", "gpt4_claude", "cost_optimized"]
        if v not in valid_strategies:
            raise ValueError(f'AI models strategy must be one of: {valid_strategies}')
        return v


class OpportunityAnalysisRequest(AIConsensusRequest):
    """Opportunity analysis request."""
    symbol: str = "BTC/USDT"
    analysis_type: str = "opportunity"  # opportunity, technical, fundamental
    timeframe: str = "4h"
    include_risk_metrics: bool = True


class TradeValidationRequest(AIConsensusRequest):
    """Trade validation request."""
    trade_data: Dict[str, Any]
    execution_urgency: str = "normal"  # normal, high, emergency


class RiskAssessmentRequest(AIConsensusRequest):
    """Risk assessment request."""
    portfolio_data: Dict[str, Any]
    risk_type: str = "comprehensive"  # comprehensive, market, liquidity, operational
    stress_test: bool = False


class PortfolioReviewRequest(AIConsensusRequest):
    """Portfolio review request."""
    portfolio_data: Dict[str, Any]
    review_type: str = "full"  # full, allocation, performance, rebalancing
    benchmark: Optional[str] = None


class MarketAnalysisRequest(AIConsensusRequest):
    """Market analysis request."""
    symbols: List[str] = ["BTC", "ETH", "SOL"]
    analysis_depth: str = "standard"  # quick, standard, deep
    include_sentiment: bool = True


class ConsensusDecisionRequest(AIConsensusRequest):
    """Final consensus decision request."""
    decision_context: Dict[str, Any]
    decision_type: str = "trade_execution"  # trade_execution, portfolio_rebalance, risk_action
    execution_timeline: str = "immediate"  # immediate, planned, conditional


class AIModelWeightsRequest(BaseModel):
    """AI model weights update request."""
    ai_model_weights: Dict[str, float]
    autonomous_frequency_minutes: Optional[int] = None
    
    @field_validator('ai_model_weights')
    @classmethod
    def validate_weights(cls, v):
        # Validate weights sum to 1.0
        total = sum(v.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f'AI model weights must sum to 1.0, got {total:.3f}')
        
        # Validate individual weights
        for model, weight in v.items():
            if model not in ["gpt4", "claude", "gemini"]:
                raise ValueError(f'Invalid AI model: {model}. Must be one of: gpt4, claude, gemini')
            if not 0 <= weight <= 1:
                raise ValueError(f'Weight for {model} must be between 0 and 1, got {weight}')
        
        return v


# AI Consensus Endpoints
@router.post("/analyze-opportunity")
async def analyze_opportunity_endpoint(
    request: OpportunityAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Analyze trading opportunity using multi-AI consensus.
    
    This endpoint provides institutional-grade opportunity analysis by:
    - Querying GPT-4, Claude, and Gemini in parallel
    - Calculating weighted consensus scores
    - Providing detailed reasoning and confidence metrics
    - Tracking API costs and performance
    """
    
    await rate_limiter.check_rate_limit(
        key="ai_consensus:analyze_opportunity",
        limit=20,
        window=60,
        user_id=str(current_user.id)
    )
    
    logger.info(
        "AI opportunity analysis requested",
        user_id=str(current_user.id),
        symbol=request.symbol,
        analysis_type=request.analysis_type,
        confidence_threshold=request.confidence_threshold
    )
    
    try:
        # Track API call start
        call_start_time = datetime.utcnow()
        
        # Prepare analysis data
        analysis_data = {
            "symbol": request.symbol,
            "analysis_type": request.analysis_type,
            "timeframe": request.timeframe,
            "include_risk_metrics": request.include_risk_metrics,
            "user_id": str(current_user.id),
            "timestamp": call_start_time.isoformat()
        }
        
        # Use existing AI consensus service - NO DUPLICATION
        result = await ai_consensus_service.analyze_opportunity(
            analysis_request=json.dumps(analysis_data),
            confidence_threshold=request.confidence_threshold,
            ai_models=request.ai_models,
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"AI consensus analysis failed: {result.get('error', 'Unknown error')}"
            )
        
        # Calculate response time
        response_time_ms = (datetime.utcnow() - call_start_time).total_seconds() * 1000
        
        # Track API cost
        actual_cost = result.get("opportunity_analysis", {}).get("cost_summary", {}).get("total_cost", 0)
        await api_cost_tracker.track_api_call(
            provider=APIProvider.OPENAI_GPT4,  # Primary provider
            endpoint="/ai-consensus/analyze-opportunity",
            method="POST",
            cost_usd=actual_cost,
            user_id=str(current_user.id),
            response_time_ms=response_time_ms,
            success=True,
            metadata={
                "symbol": request.symbol,
                "confidence_threshold": request.confidence_threshold,
                "ai_models": request.ai_models
            }
        )
        
        # Feed to unified AI manager for natural language explanation
        await unified_ai_manager.process_ai_consensus_result(
            user_id=str(current_user.id),
            function="analyze_opportunity",
            result=result,
            interface=InterfaceType.WEB_UI
        )
        
        return {
            "success": True,
            "function": "analyze_opportunity",
            "result": result,
            "response_time_ms": response_time_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("AI opportunity analysis failed", user_id=str(current_user.id), error=str(e))
        
        # Track failed API call
        await api_cost_tracker.track_api_call(
            provider=APIProvider.OPENAI_GPT4,
            endpoint="/ai-consensus/analyze-opportunity",
            method="POST",
            cost_usd=0.0,
            user_id=str(current_user.id),
            success=False,
            error_message=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI consensus analysis failed: {str(e)}"
        )


@router.post("/validate-trade")
async def validate_trade_endpoint(
    request: TradeValidationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Validate trading decision using multi-AI consensus.
    
    Provides institutional-grade trade validation with:
    - Multi-model consensus on trade quality
    - Risk-adjusted position sizing recommendations
    - Execution timing optimization
    - Comprehensive validation scoring
    """
    
    await rate_limiter.check_rate_limit(
        key="ai_consensus:validate_trade",
        limit=30,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        call_start_time = datetime.utcnow()
        
        # Use existing AI consensus service
        result = await ai_consensus_service.validate_trade(
            analysis_request=json.dumps(request.trade_data),
            confidence_threshold=request.confidence_threshold,
            ai_models=request.ai_models,
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Trade validation failed: {result.get('error', 'Unknown error')}"
            )
        
        response_time_ms = (datetime.utcnow() - call_start_time).total_seconds() * 1000
        
        # Track API cost
        actual_cost = result.get("trade_validation", {}).get("cost_summary", {}).get("total_cost", 0)
        await api_cost_tracker.track_api_call(
            provider=APIProvider.ANTHROPIC_CLAUDE,  # Claude specializes in validation
            endpoint="/ai-consensus/validate-trade",
            method="POST",
            cost_usd=actual_cost,
            user_id=str(current_user.id),
            response_time_ms=response_time_ms,
            success=True
        )
        
        # Feed to unified AI manager
        await unified_ai_manager.process_ai_consensus_result(
            user_id=str(current_user.id),
            function="validate_trade",
            result=result,
            interface=InterfaceType.WEB_UI
        )
        
        return {
            "success": True,
            "function": "validate_trade",
            "result": result,
            "response_time_ms": response_time_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Trade validation failed", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trade validation failed: {str(e)}"
        )


@router.post("/risk-assessment")
async def risk_assessment_endpoint(
    request: RiskAssessmentRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Perform comprehensive risk assessment using multi-AI consensus.
    
    Features:
    - Multi-dimensional risk analysis (market, liquidity, operational)
    - Stress testing scenarios
    - Portfolio concentration analysis
    - Risk mitigation recommendations
    """
    
    await rate_limiter.check_rate_limit(
        key="ai_consensus:risk_assessment",
        limit=15,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        call_start_time = datetime.utcnow()
        
        # Use existing AI consensus service
        result = await ai_consensus_service.risk_assessment(
            analysis_request=json.dumps(request.portfolio_data),
            confidence_threshold=request.confidence_threshold,
            ai_models=request.ai_models,
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Risk assessment failed: {result.get('error', 'Unknown error')}"
            )
        
        response_time_ms = (datetime.utcnow() - call_start_time).total_seconds() * 1000
        
        # Track API cost
        actual_cost = result.get("risk_assessment", {}).get("cost_summary", {}).get("total_cost", 0)
        await api_cost_tracker.track_api_call(
            provider=APIProvider.ANTHROPIC_CLAUDE,  # Claude specializes in risk analysis
            endpoint="/ai-consensus/risk-assessment",
            method="POST",
            cost_usd=actual_cost,
            user_id=str(current_user.id),
            response_time_ms=response_time_ms,
            success=True
        )
        
        # Check if emergency conditions are detected
        risk_score = result.get("risk_assessment", {}).get("risk_score", 0)
        if risk_score > 75:  # High risk threshold
            # Assess emergency level
            emergency_level, _ = await emergency_manager.assess_emergency_level(
                user_id=str(current_user.id),
                portfolio_data=request.portfolio_data
            )
            
            result["emergency_assessment"] = {
                "emergency_level": emergency_level.value,
                "requires_action": emergency_level.value != "normal"
            }
        
        # Feed to unified AI manager
        await unified_ai_manager.process_ai_consensus_result(
            user_id=str(current_user.id),
            function="risk_assessment",
            result=result,
            interface=InterfaceType.WEB_UI
        )
        
        return {
            "success": True,
            "function": "risk_assessment",
            "result": result,
            "response_time_ms": response_time_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Risk assessment failed", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk assessment failed: {str(e)}"
        )


@router.post("/portfolio-review")
async def portfolio_review_endpoint(
    request: PortfolioReviewRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Perform comprehensive portfolio review using multi-AI consensus.
    
    NO HARDCODED ASSETS - Supports any portfolio composition with:
    - Asset allocation optimization
    - Rebalancing recommendations
    - Performance attribution analysis
    - Risk-return optimization
    """
    
    await rate_limiter.check_rate_limit(
        key="ai_consensus:portfolio_review",
        limit=10,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        call_start_time = datetime.utcnow()
        
        # Use existing AI consensus service - NO HARDCODED LIMITATIONS
        result = await ai_consensus_service.portfolio_review(
            analysis_request=json.dumps(request.portfolio_data),
            confidence_threshold=request.confidence_threshold,
            ai_models=request.ai_models,
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Portfolio review failed: {result.get('error', 'Unknown error')}"
            )
        
        response_time_ms = (datetime.utcnow() - call_start_time).total_seconds() * 1000
        
        # Track API cost
        actual_cost = result.get("portfolio_review", {}).get("cost_summary", {}).get("total_cost", 0)
        await api_cost_tracker.track_api_call(
            provider=APIProvider.GOOGLE_GEMINI,  # Gemini for analytical tasks
            endpoint="/ai-consensus/portfolio-review",
            method="POST",
            cost_usd=actual_cost,
            user_id=str(current_user.id),
            response_time_ms=response_time_ms,
            success=True
        )
        
        # Feed to unified AI manager
        await unified_ai_manager.process_ai_consensus_result(
            user_id=str(current_user.id),
            function="portfolio_review",
            result=result,
            interface=InterfaceType.WEB_UI
        )
        
        return {
            "success": True,
            "function": "portfolio_review",
            "result": result,
            "response_time_ms": response_time_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Portfolio review failed", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Portfolio review failed: {str(e)}"
        )


@router.post("/market-analysis")
async def market_analysis_endpoint(
    request: MarketAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Perform market analysis using multi-AI consensus.
    
    NO HARDCODED LIMITATIONS - Supports any market/asset with:
    - Multi-timeframe technical analysis
    - Sentiment analysis integration
    - Cross-asset correlation analysis
    - Market regime identification
    """
    
    await rate_limiter.check_rate_limit(
        key="ai_consensus:market_analysis",
        limit=25,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        call_start_time = datetime.utcnow()
        
        market_data = {
            "symbols": request.symbols,
            "analysis_depth": request.analysis_depth,
            "include_sentiment": request.include_sentiment,
            "user_id": str(current_user.id)
        }
        
        # Use existing AI consensus service - NO HARDCODED ASSETS
        result = await ai_consensus_service.market_analysis(
            analysis_request=json.dumps(market_data),
            confidence_threshold=request.confidence_threshold,
            ai_models=request.ai_models,
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Market analysis failed: {result.get('error', 'Unknown error')}"
            )
        
        response_time_ms = (datetime.utcnow() - call_start_time).total_seconds() * 1000
        
        # Track API cost
        actual_cost = result.get("market_analysis", {}).get("cost_summary", {}).get("total_cost", 0)
        await api_cost_tracker.track_api_call(
            provider=APIProvider.GOOGLE_GEMINI,  # Gemini for market analysis
            endpoint="/ai-consensus/market-analysis",
            method="POST",
            cost_usd=actual_cost,
            user_id=str(current_user.id),
            response_time_ms=response_time_ms,
            success=True
        )
        
        # Feed to unified AI manager
        await unified_ai_manager.process_ai_consensus_result(
            user_id=str(current_user.id),
            function="market_analysis",
            result=result,
            interface=InterfaceType.WEB_UI
        )
        
        return {
            "success": True,
            "function": "market_analysis",
            "result": result,
            "response_time_ms": response_time_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Market analysis failed", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Market analysis failed: {str(e)}"
        )


@router.post("/consensus-decision")
async def consensus_decision_endpoint(
    request: ConsensusDecisionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Make final consensus decision using all AI models.
    
    NO HARDCODED LIMITATIONS - Supports any investment decision with:
    - Highest confidence threshold (85%+)
    - Final execution recommendations
    - Risk-adjusted position sizing
    - Execution timing optimization
    """
    
    await rate_limiter.check_rate_limit(
        key="ai_consensus:consensus_decision",
        limit=10,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        call_start_time = datetime.utcnow()
        
        # Use existing AI consensus service for final decision
        result = await ai_consensus_service.consensus_decision(
            decision_request=json.dumps(request.decision_context),
            confidence_threshold=max(request.confidence_threshold, 85.0),  # Higher threshold for final decisions
            ai_models=request.ai_models,
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Consensus decision failed: {result.get('error', 'Unknown error')}"
            )
        
        response_time_ms = (datetime.utcnow() - call_start_time).total_seconds() * 1000
        
        # Track API cost for all models (consensus uses all)
        actual_cost = result.get("consensus_decision", {}).get("cost_summary", {}).get("total_cost", 0)
        await api_cost_tracker.track_api_call(
            provider=APIProvider.OPENAI_GPT4,  # Primary for final decisions
            endpoint="/ai-consensus/consensus-decision",
            method="POST",
            cost_usd=actual_cost,
            user_id=str(current_user.id),
            response_time_ms=response_time_ms,
            success=True,
            metadata={
                "decision_type": request.decision_type,
                "execution_timeline": request.execution_timeline,
                "final_recommendation": result.get("final_recommendation", "HOLD")
            }
        )
        
        # Feed to unified AI manager for execution
        await unified_ai_manager.process_ai_consensus_result(
            user_id=str(current_user.id),
            function="consensus_decision",
            result=result,
            interface=InterfaceType.WEB_UI
        )
        
        return {
            "success": True,
            "function": "consensus_decision",
            "result": result,
            "response_time_ms": response_time_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Consensus decision failed", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Consensus decision failed: {str(e)}"
        )


# AI Model Configuration Endpoints
@router.get("/models/weights")
async def get_user_ai_model_weights(
    current_user: User = Depends(get_current_user)
):
    """Get user's current AI model weights and autonomous frequency."""
    
    try:
        # Use enhanced master controller method
        result = await master_controller.get_user_ai_model_weights(str(current_user.id))
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to get AI model weights")
            )
        
        return result
        
    except Exception as e:
        logger.error("Failed to get AI model weights", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get AI model weights: {str(e)}"
        )


@router.post("/models/weights")
async def update_user_ai_model_weights(
    request: AIModelWeightsRequest,
    current_user: User = Depends(get_current_user)
):
    """Update user's custom AI model weights and autonomous frequency."""
    
    await rate_limiter.check_rate_limit(
        key="ai_consensus:update_weights",
        limit=5,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Use enhanced master controller method
        result = await master_controller.update_user_ai_model_weights(
            user_id=str(current_user.id),
            ai_model_weights=request.ai_model_weights,
            autonomous_frequency_minutes=request.autonomous_frequency_minutes
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to update AI model weights")
            )
        
        logger.info(
            "AI model weights updated via API",
            user_id=str(current_user.id),
            weights=request.ai_model_weights,
            frequency=request.autonomous_frequency_minutes
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update AI model weights", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update AI model weights: {str(e)}"
        )


# Real-time Status Endpoints
@router.get("/status/real-time")
async def get_real_time_ai_status(
    current_user: User = Depends(get_current_user)
):
    """Get real-time AI consensus service status."""
    
    try:
        # Get comprehensive AI status from existing service
        result = await ai_consensus_service.health_check()
        
        # Add user-specific information
        user_weights = await master_controller.get_user_ai_model_weights(str(current_user.id))
        result["user_config"] = user_weights
        
        # Add emergency status
        emergency_status = await emergency_manager.get_emergency_status(str(current_user.id))
        result["emergency_status"] = emergency_status
        
        return result
        
    except Exception as e:
        logger.error("Failed to get AI status", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get AI status: {str(e)}"
        )


@router.get("/cost-summary")
async def get_user_cost_summary(
    period: str = "daily",
    current_user: User = Depends(get_current_user)
):
    """Get user's AI consensus API cost summary."""
    
    try:
        # Get user-specific cost summary
        result = await api_cost_tracker.get_user_cost_summary(
            user_id=str(current_user.id),
            period=period
        )
        
        return result
        
    except Exception as e:
        logger.error("Failed to get cost summary", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cost summary: {str(e)}"
        )


# Emergency Controls
@router.post("/emergency/stop")
async def emergency_stop_ai(
    current_user: User = Depends(get_current_user)
):
    """Emergency stop for AI consensus operations."""
    
    try:
        # Use master controller emergency stop
        result = await master_controller.emergency_stop(
            user_id=str(current_user.id),
            reason="user_initiated_emergency_stop"
        )
        
        logger.critical(
            "AI consensus emergency stop via API",
            user_id=str(current_user.id)
        )
        
        return result
        
    except Exception as e:
        logger.error("Emergency stop failed", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Emergency stop failed: {str(e)}"
        )


@router.post("/emergency/resume")
async def resume_ai_operations(
    current_user: User = Depends(get_current_user)
):
    """Resume AI consensus operations after emergency stop."""
    
    try:
        # Use master controller resume
        result = await master_controller.resume_operations(str(current_user.id))
        
        logger.info(
            "AI consensus operations resumed via API",
            user_id=str(current_user.id)
        )
        
        return result
        
    except Exception as e:
        logger.error("Resume operations failed", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resume operations failed: {str(e)}"
        )