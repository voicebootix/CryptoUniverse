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
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, WebSocket, WebSocketDisconnect
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
from app.services.profit_sharing_service import profit_sharing_service

settings = get_settings()
logger = structlog.get_logger(__name__)

router = APIRouter()

# Constants for magic numbers
DEFAULT_CONFIDENCE_THRESHOLD = 75.0
MIN_CONFIDENCE_THRESHOLD = 50.0
MAX_CONFIDENCE_THRESHOLD = 95.0
FINAL_DECISION_MIN_CONFIDENCE = 85.0
WEIGHT_SUM_TOLERANCE = 0.01
MIN_MODEL_WEIGHT = 0
MAX_MODEL_WEIGHT = 1
EXACT_WEIGHT_SUM = 1.0


def flatten_ai_consensus_result(result: Dict[str, Any], function: str) -> Dict[str, Any]:
    """
    Flatten nested AI consensus result for UnifiedAI processing.
    
    Args:
        result: Raw AI consensus result with nested function-specific data
        function: Function name (analyze_opportunity, validate_trade, etc.)
        
    Returns:
        Flattened result with top-level consensus_score, recommendation, etc.
    """
    
    # Get the function-specific nested data
    function_data = result.get(function, {})
    
    # Extract top-level fields, preferring function-specific data
    flattened = {
        "success": result.get("success", False),
        "consensus_score": function_data.get("consensus_score") or result.get("consensus_score", 0),
        "recommendation": function_data.get("recommendation") or result.get("recommendation", "HOLD"),
        "reasoning": function_data.get("reasoning") or result.get("reasoning", ""),
        "confidence_threshold_met": function_data.get("confidence_threshold_met") or result.get("confidence_threshold_met", False),
        "model_responses": function_data.get("model_responses") or result.get("model_responses", []),
        "cost_summary": function_data.get("cost_summary") or result.get("cost_summary", {}),
        "timestamp": function_data.get("timestamp") or result.get("timestamp", ""),
        "function": function,
        "raw_result": result  # Keep original for debugging
    }
    
    return flattened


async def _track_successful_api_call(
    endpoint: str,
    actual_cost: float,
    user_id: str,
    response_time_ms: float,
    metadata: Dict[str, Any]
) -> None:
    """Helper function to track successful API calls."""
    await api_cost_tracker.track_api_call(
        provider=APIProvider.OPENAI_GPT4,
        endpoint=endpoint,
        method="POST",
        cost_usd=actual_cost,
        user_id=user_id,
        response_time_ms=response_time_ms,
        success=True,
        metadata=metadata
    )


async def _track_failed_api_call(
    endpoint: str,
    user_id: str,
    error_message: str
) -> None:
    """Helper function to track failed API calls."""
    await api_cost_tracker.track_api_call(
        provider=APIProvider.OPENAI_GPT4,
        endpoint=endpoint,
        method="POST",
        cost_usd=0.0,
        user_id=user_id,
        success=False,
        error_message=error_message
    )


async def _process_ai_consensus_result(
    result: Dict[str, Any],
    function_name: str,
    user_id: str
) -> None:
    """Helper function to process AI consensus results through unified AI manager."""
    flattened_result = flatten_ai_consensus_result(result, function_name)
    await unified_ai_manager.process_ai_consensus_result(
        user_id=user_id,
        function=function_name,
        result=flattened_result,
        interface=InterfaceType.WEB_UI
    )


# Request/Response Models
class AIConsensusRequest(BaseModel):
    """Base AI consensus request."""
    analysis_request: Optional[str] = None  # JSON string or direct data - made optional
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
    ai_models: str = "all"  # "all", "gpt4_claude", "cost_optimized"
    
    @field_validator('confidence_threshold')
    @classmethod
    def validate_confidence_threshold(cls, v):
        if not MIN_CONFIDENCE_THRESHOLD <= v <= MAX_CONFIDENCE_THRESHOLD:
            raise ValueError(f'Confidence threshold must be between {MIN_CONFIDENCE_THRESHOLD} and {MAX_CONFIDENCE_THRESHOLD}')
        return v
    
    @field_validator('ai_models')
    @classmethod
    def validate_ai_models(cls, v):
        valid_strategies = ["all", "gpt4_claude", "cost_optimized"]
        if v not in valid_strategies:
            raise ValueError(f'AI models strategy must be one of: {valid_strategies}')
        return v


class AIPricingResponse(BaseModel):
    success: bool
    opportunity_scan_cost: float
    validation_cost: float
    execution_cost: float
    per_call_estimate: float
    platform_fee_percentage: float
    credit_to_profit_ratio: float
    credit_to_dollar_cost: float


@router.get("/pricing", response_model=AIPricingResponse)
async def get_ai_pricing_configuration(
    current_user: User = Depends(get_current_user)
):
    """Return AI operation pricing derived from the credit and profit-sharing configuration."""

    await rate_limiter.check_rate_limit(
        key="ai:pricing",
        limit=120,
        window=60,
        user_id=str(current_user.id)
    )

    try:
        await profit_sharing_service.ensure_pricing_loaded()
        pricing_config = await profit_sharing_service.get_current_pricing_config()

        platform_fee_percentage = float(pricing_config.get("platform_fee_percentage", 25.0))
        credit_to_profit_ratio = float(pricing_config.get("credit_to_profit_ratio", 4.0))
        credit_to_dollar_cost = float(pricing_config.get("credit_to_dollar_cost", 1.0))

        # Derive AI feature costs from credit pricing. These values remain small to reflect per-call usage.
        per_call_estimate = round(credit_to_dollar_cost * 0.05, 2) or 0.05
        opportunity_scan_cost = round(max(1.0, credit_to_dollar_cost * 1.0), 2)
        validation_cost = round(max(0.5, credit_to_dollar_cost * 0.5), 2)
        execution_cost = round(max(2.0, credit_to_dollar_cost * 2.0), 2)

        return AIPricingResponse(
            success=True,
            opportunity_scan_cost=opportunity_scan_cost,
            validation_cost=validation_cost,
            execution_cost=execution_cost,
            per_call_estimate=per_call_estimate,
            platform_fee_percentage=platform_fee_percentage,
            credit_to_profit_ratio=credit_to_profit_ratio,
            credit_to_dollar_cost=credit_to_dollar_cost,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error(
            "Failed to load AI pricing configuration",
            user_id=str(current_user.id),
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load AI pricing configuration"
        ) from exc


class OpportunityAnalysisRequest(AIConsensusRequest):
    """Opportunity analysis request."""
    symbol: str = "BTC/USDT"
    analysis_type: str = "opportunity"  # opportunity, technical, fundamental
    timeframe: str = "4h"
    include_risk_metrics: bool = True
    
    def get_analysis_data(self) -> Dict[str, Any]:
        """Get analysis data from either analysis_request or individual fields."""
        if self.analysis_request:
            try:
                return json.loads(self.analysis_request)
            except json.JSONDecodeError:
                pass
        
        return {
            "symbol": self.symbol,
            "analysis_type": self.analysis_type,
            "timeframe": self.timeframe,
            "include_risk_metrics": self.include_risk_metrics
        }


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
        if abs(total - EXACT_WEIGHT_SUM) > WEIGHT_SUM_TOLERANCE:
            raise ValueError(f'AI model weights must sum to {EXACT_WEIGHT_SUM}, got {total:.3f}')
        
        # Validate individual weights
        for model, weight in v.items():
            if model not in ["gpt4", "claude", "gemini"]:
                raise ValueError(f'Invalid AI model: {model}. Must be one of: gpt4, claude, gemini')
            if not MIN_MODEL_WEIGHT <= weight <= MAX_MODEL_WEIGHT:
                raise ValueError(f'Weight for {model} must be between {MIN_MODEL_WEIGHT} and {MAX_MODEL_WEIGHT}, got {weight}')
        
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
    
    # Rate limiting handled by middleware - no manual calls needed
    
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
        
        # Get analysis data from request
        analysis_data = request.get_analysis_data()
        analysis_data.update({
            "user_id": str(current_user.id),
            "timestamp": call_start_time.isoformat()
        })
        
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
        
        # Track API cost with helper function
        actual_cost = result.get("opportunity_analysis", {}).get("cost_summary", {}).get("total_cost", 0)
        await _track_successful_api_call(
            endpoint="/ai-consensus/analyze-opportunity",
            actual_cost=actual_cost,
            user_id=str(current_user.id),
            response_time_ms=response_time_ms,
            metadata={
                "symbol": request.symbol,
                "confidence_threshold": request.confidence_threshold,
                "ai_models": request.ai_models
            }
        )
        
        # Process result through unified AI manager
        await _process_ai_consensus_result(
            result=result,
            function_name="analyze_opportunity",
            user_id=str(current_user.id)
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
        
        # Track failed API call with helper function
        await _track_failed_api_call(
            endpoint="/ai-consensus/analyze-opportunity",
            user_id=str(current_user.id),
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
    
    # Rate limiting handled by middleware - no manual calls needed
    
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
        
        # Track API cost with helper function
        actual_cost = result.get("trade_validation", {}).get("cost_summary", {}).get("total_cost", 0)
        await _track_successful_api_call(
            endpoint="/ai-consensus/validate-trade",
            actual_cost=actual_cost,
            user_id=str(current_user.id),
            response_time_ms=response_time_ms,
            metadata={"trade_data": request.trade_data}
        )
        
        # Process result through unified AI manager
        await _process_ai_consensus_result(
            result=result,
            function_name="validate_trade",
            user_id=str(current_user.id)
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
    
    # Rate limiting handled by middleware - no manual calls needed
    
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
        
        # Flatten result for unified AI manager processing
        flattened_result = flatten_ai_consensus_result(result, "risk_assessment")
        
        # Feed to unified AI manager
        await unified_ai_manager.process_ai_consensus_result(
            user_id=str(current_user.id),
            function="risk_assessment",
            result=flattened_result,
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
    
    # Rate limiting handled by middleware - no manual calls needed
    
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
        
        # Flatten result for unified AI manager processing
        flattened_result = flatten_ai_consensus_result(result, "portfolio_review")
        
        # Feed to unified AI manager
        await unified_ai_manager.process_ai_consensus_result(
            user_id=str(current_user.id),
            function="portfolio_review",
            result=flattened_result,
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
    
    # Rate limiting handled by middleware - no manual calls needed
    
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
        
        # Flatten result for unified AI manager processing
        flattened_result = flatten_ai_consensus_result(result, "market_analysis")
        
        # Feed to unified AI manager
        await unified_ai_manager.process_ai_consensus_result(
            user_id=str(current_user.id),
            function="market_analysis",
            result=flattened_result,
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
    
    # Rate limiting handled by middleware - no manual calls needed
    
    try:
        call_start_time = datetime.utcnow()
        
        # Use existing AI consensus service for final decision
        result = await ai_consensus_service.consensus_decision(
            decision_request=json.dumps(request.decision_context),
            confidence_threshold=max(request.confidence_threshold, FINAL_DECISION_MIN_CONFIDENCE),  # Higher threshold for final decisions
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
        
        # Flatten result for unified AI manager processing
        flattened_result = flatten_ai_consensus_result(result, "consensus_decision")
        
        # Feed to unified AI manager for execution
        await unified_ai_manager.process_ai_consensus_result(
            user_id=str(current_user.id),
            function="consensus_decision",
            result=flattened_result,
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
    
    # Rate limiting handled by middleware - no manual calls needed
    
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


# WebSocket endpoint for real-time AI consensus updates
@router.websocket("/ws")
async def ai_consensus_websocket(
    websocket: WebSocket
):
    """WebSocket endpoint for real-time AI consensus updates."""
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif message.get("type") == "subscribe":
                # Subscribe to AI consensus updates
                await websocket.send_json({
                    "type": "subscribed",
                    "message": "Subscribed to AI consensus updates"
                })
            else:
                # Echo back for now
                await websocket.send_json({
                    "type": "ai_consensus_update",
                    "data": message
                })
                
    except WebSocketDisconnect:
        logger.info("AI consensus WebSocket disconnected")
    except Exception as e:
        logger.error(f"AI consensus WebSocket error: {e}")
        await websocket.close()