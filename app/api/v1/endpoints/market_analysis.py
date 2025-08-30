"""
Market Analysis API Endpoints - Enterprise Grade

Provides comprehensive market analysis endpoints including real-time price tracking,
technical analysis, sentiment analysis, and arbitrage opportunities.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_database
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.services.market_analysis_core import MarketAnalysisService
from app.services.market_data_feeds import MarketDataFeeds, get_crypto_price, get_crypto_prices, get_market_overview
from app.services.health_monitor import health_monitor
from app.services.rate_limit import rate_limiter

settings = get_settings()
logger = structlog.get_logger(__name__)

router = APIRouter()

# Initialize services
market_analysis = MarketAnalysisService()
market_data_feeds = MarketDataFeeds()


# Request/Response Models
class PriceTrackingResponse(BaseModel):
    success: bool
    data: Dict[str, Any]
    metadata: Dict[str, Any]


class TechnicalAnalysisRequest(BaseModel):
    symbols: str
    timeframe: str = "1h"
    indicators: Optional[str] = None
    
    @field_validator('timeframe')
    @classmethod
    def validate_timeframe(cls, v):
        allowed = ["1m", "5m", "15m", "1h", "4h", "1d", "1w"]
        if v not in allowed:
            raise ValueError(f"Timeframe must be one of: {allowed}")
        return v


class SentimentAnalysisRequest(BaseModel):
    symbols: str
    timeframes: Optional[str] = "1h,4h,1d"


class ArbitrageRequest(BaseModel):
    symbols: str = "BTC,ETH,SOL"
    exchanges: str = "all"
    min_profit_bps: int = 5
    
    @field_validator('min_profit_bps')
    @classmethod
    def validate_min_profit(cls, v):
        if v < 1 or v > 1000:
            raise ValueError("min_profit_bps must be between 1 and 1000")
        return v


class MarketAssessmentRequest(BaseModel):
    symbols: str
    depth: str = "comprehensive"
    
    @field_validator('depth')
    @classmethod
    def validate_depth(cls, v):
        allowed = ["basic", "standard", "comprehensive", "deep"]
        if v not in allowed:
            raise ValueError(f"Depth must be one of: {allowed}")
        return v


# Market Analysis Endpoints

@router.get("/realtime-prices", response_model=PriceTrackingResponse)
async def get_realtime_prices(
    symbols: str = Query(..., description="Comma-separated list of symbols (e.g., BTC,ETH,SOL)"),
    exchanges: str = Query("all", description="Comma-separated list of exchanges or 'all'"),
    current_user: User = Depends(get_current_user)
):
    """Get real-time price tracking across multiple exchanges."""
    
    await rate_limiter.check_rate_limit(
        key="market:realtime_prices",
        limit=200,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        result = await market_analysis.realtime_price_tracking(
            symbols=symbols,
            exchanges=exchanges,
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to fetch real-time prices")
            )
        
        return PriceTrackingResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Real-time price tracking failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get real-time prices: {str(e)}"
        )


@router.post("/technical-analysis")
async def get_technical_analysis(
    request: TechnicalAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive technical analysis for symbols."""
    
    await rate_limiter.check_rate_limit(
        key="market:technical_analysis",
        limit=100,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        result = await market_analysis.technical_analysis(
            symbols=request.symbols,
            timeframe=request.timeframe,
            indicators=request.indicators,
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Technical analysis failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Technical analysis failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Technical analysis failed: {str(e)}"
        )


@router.post("/sentiment-analysis")
async def get_sentiment_analysis(
    request: SentimentAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """Get market sentiment analysis for symbols."""
    
    await rate_limiter.check_rate_limit(
        key="market:sentiment_analysis",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        result = await market_analysis.market_sentiment(
            symbols=request.symbols,
            timeframes=request.timeframes,
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Sentiment analysis failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Sentiment analysis failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sentiment analysis failed: {str(e)}"
        )


@router.post("/arbitrage-opportunities")
async def get_arbitrage_opportunities(
    request: ArbitrageRequest,
    current_user: User = Depends(get_current_user)
):
    """Get cross-exchange arbitrage opportunities."""
    
    await rate_limiter.check_rate_limit(
        key="market:arbitrage",
        limit=30,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        result = await market_analysis.cross_exchange_arbitrage_scanner(
            symbols=request.symbols,
            exchanges=request.exchanges,
            min_profit_bps=request.min_profit_bps,
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Arbitrage scan failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Arbitrage opportunities scan failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Arbitrage scan failed: {str(e)}"
        )


@router.post("/complete-assessment")
async def get_complete_market_assessment(
    request: MarketAssessmentRequest,
    current_user: User = Depends(get_current_user)
):
    """Get complete market assessment combining all analysis types."""
    
    await rate_limiter.check_rate_limit(
        key="market:complete_assessment",
        limit=20,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        result = await market_analysis.complete_market_assessment(
            symbols=request.symbols,
            depth=request.depth,
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Complete market assessment failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Complete market assessment failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Complete market assessment failed: {str(e)}"
        )


@router.get("/volatility-analysis")
async def get_volatility_analysis(
    symbols: str = Query(..., description="Comma-separated list of symbols"),
    timeframes: str = Query("1h,4h,1d", description="Comma-separated list of timeframes"),
    current_user: User = Depends(get_current_user)
):
    """Get volatility analysis for symbols."""
    
    await rate_limiter.check_rate_limit(
        key="market:volatility_analysis",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        result = await market_analysis.volatility_analysis(
            symbols=symbols,
            timeframes=timeframes,
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Volatility analysis failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Volatility analysis failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Volatility analysis failed: {str(e)}"
        )


@router.get("/support-resistance")
async def get_support_resistance(
    symbols: str = Query(..., description="Comma-separated list of symbols"),
    timeframes: str = Query("1h,4h,1d", description="Comma-separated list of timeframes"),
    current_user: User = Depends(get_current_user)
):
    """Get support and resistance levels for symbols."""
    
    await rate_limiter.check_rate_limit(
        key="market:support_resistance",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        result = await market_analysis.support_resistance_detection(
            symbols=symbols,
            timeframes=timeframes,
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Support/resistance analysis failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Support/resistance analysis failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Support/resistance analysis failed: {str(e)}"
        )


@router.get("/institutional-flows")
async def get_institutional_flows(
    symbols: str = Query(..., description="Comma-separated list of symbols"),
    timeframes: str = Query("1h,4h,1d", description="Comma-separated list of timeframes"),
    flow_types: str = Query("whale_tracking,institutional_trades,etf_flows", description="Types of flows to track"),
    current_user: User = Depends(get_current_user)
):
    """Get institutional flow tracking data."""
    
    await rate_limiter.check_rate_limit(
        key="market:institutional_flows",
        limit=30,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        result = await market_analysis.institutional_flow_tracker(
            symbols=symbols,
            timeframes=timeframes,
            flow_types=flow_types,
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Institutional flow tracking failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Institutional flow tracking failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Institutional flow tracking failed: {str(e)}"
        )


@router.get("/alpha-signals")
async def get_alpha_signals(
    symbols: str = Query(..., description="Comma-separated list of symbols"),
    strategies: str = Query("momentum,mean_reversion,breakout", description="Alpha generation strategies"),
    current_user: User = Depends(get_current_user)
):
    """Get alpha generation signals."""
    
    await rate_limiter.check_rate_limit(
        key="market:alpha_signals",
        limit=20,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        result = await market_analysis.alpha_generation_coordinator(
            symbols=symbols,
            strategies=strategies,
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Alpha signal generation failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Alpha signal generation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Alpha signal generation failed: {str(e)}"
        )


@router.get("/exchange-assets")
async def discover_exchange_assets(
    exchanges: str = Query("all", description="Comma-separated list of exchanges or 'all'"),
    asset_types: str = Query("spot,futures,options", description="Types of assets to discover"),
    current_user: User = Depends(get_current_user)
):
    """Discover available assets across exchanges."""
    
    await rate_limiter.check_rate_limit(
        key="market:exchange_assets",
        limit=10,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        result = await market_analysis.discover_exchange_assets(
            exchanges=exchanges,
            asset_types=asset_types,
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Asset discovery failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Asset discovery failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Asset discovery failed: {str(e)}"
        )


@router.get("/trending-coins")
async def get_trending_coins(
    limit: int = Query(10, ge=1, le=50, description="Number of trending coins to return"),
    current_user: User = Depends(get_current_user)
):
    """Get trending cryptocurrency coins."""
    
    await rate_limiter.check_rate_limit(
        key="market:trending",
        limit=30,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Initialize market data feeds if needed
        if not hasattr(market_data_feeds, 'redis') or market_data_feeds.redis is None:
            await market_data_feeds.async_init()
        
        result = await market_data_feeds.get_trending_coins(limit=limit)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to get trending coins")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Trending coins retrieval failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trending coins: {str(e)}"
        )


@router.get("/market-health")
async def get_market_health(
    current_user: User = Depends(get_current_user)
):
    """Get overall market and service health status."""
    
    await rate_limiter.check_rate_limit(
        key="market:health",
        limit=60,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Initialize health monitor if needed
        if not hasattr(health_monitor, 'redis') or health_monitor.redis is None:
            await health_monitor.initialize()
        
        # Get comprehensive health status
        health_result = await health_monitor.get_overall_health()
        return health_result
        
    except Exception as e:
        logger.error("Market health check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Market health check failed: {str(e)}"
        )


@router.get("/system-status")
async def get_detailed_system_status(
    current_user: User = Depends(get_current_user)
):
    """Get detailed system status including all components."""
    
    await rate_limiter.check_rate_limit(
        key="market:system_status",
        limit=30,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Initialize health monitor if needed
        if not hasattr(health_monitor, 'redis') or health_monitor.redis is None:
            await health_monitor.initialize()
        
        # Get detailed status
        api_health = await health_monitor.check_api_health()
        exchange_health = await health_monitor.check_exchange_health()
        service_health = await health_monitor.check_service_health()
        
        return {
            "success": True,
            "data": {
                "apis": api_health,
                "exchanges": exchange_health,
                "services": service_health,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error("System status check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"System status check failed: {str(e)}"
        )


@router.get("/single-price/{symbol}")
async def get_single_crypto_price(
    symbol: str,
    current_user: User = Depends(get_current_user)
):
    """Get real-time price for a single cryptocurrency."""
    
    await rate_limiter.check_rate_limit(
        key="market:single_price",
        limit=300,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        # Initialize market data feeds if needed
        if not hasattr(market_data_feeds, 'redis') or market_data_feeds.redis is None:
            await market_data_feeds.async_init()
        
        result = await get_crypto_price(symbol.upper())
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Price data not found for {symbol}"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Single price retrieval failed for {symbol}", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get price for {symbol}: {str(e)}"
        )


@router.get("/trend-analysis")
async def get_trend_analysis(
    symbols: str = Query(..., description="Comma-separated list of symbols"),
    timeframes: str = Query("1h,4h,1d", description="Comma-separated list of timeframes"),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive trend analysis."""
    
    await rate_limiter.check_rate_limit(
        key="market:trend_analysis",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        result = await market_analysis.trend_analysis(
            symbols=symbols,
            timeframes=timeframes,
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Trend analysis failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Trend analysis failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trend analysis failed: {str(e)}"
        )


@router.get("/volume-analysis")
async def get_volume_analysis(
    symbols: str = Query(..., description="Comma-separated list of symbols"),
    timeframes: str = Query("1h,4h,1d", description="Comma-separated list of timeframes"),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive volume analysis."""
    
    await rate_limiter.check_rate_limit(
        key="market:volume_analysis",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        result = await market_analysis.volume_analysis(
            symbols=symbols,
            timeframes=timeframes,
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Volume analysis failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Volume analysis failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Volume analysis failed: {str(e)}"
        )


@router.get("/momentum-indicators")
async def get_momentum_indicators(
    symbols: str = Query(..., description="Comma-separated list of symbols"),
    timeframes: str = Query("1h,4h,1d", description="Comma-separated list of timeframes"),
    indicators: str = Query("rsi,macd,stoch", description="Comma-separated list of indicators"),
    current_user: User = Depends(get_current_user)
):
    """Get momentum indicator analysis."""
    
    await rate_limiter.check_rate_limit(
        key="market:momentum_indicators",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        result = await market_analysis.momentum_indicators(
            symbols=symbols,
            timeframes=timeframes,
            indicators=indicators,
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Momentum indicators analysis failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Momentum indicators analysis failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Momentum indicators analysis failed: {str(e)}"
        )


@router.get("/market-inefficiencies")
async def get_market_inefficiencies(
    symbols: str = Query("BTC,ETH,SOL", description="Comma-separated list of symbols"),
    inefficiency_types: str = Query("spread,volume,time", description="Types of inefficiencies to scan"),
    current_user: User = Depends(get_current_user)
):
    """Scan for market inefficiencies across exchanges."""
    
    await rate_limiter.check_rate_limit(
        key="market:inefficiencies",
        limit=20,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        result = await market_analysis.market_inefficiency_scanner(
            symbols=symbols,
            inefficiency_types=inefficiency_types,
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Market inefficiency scan failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Market inefficiency scan failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Market inefficiency scan failed: {str(e)}"
        )


@router.get("/cross-asset-arbitrage")
async def get_cross_asset_arbitrage(
    asset_pairs: str = Query("BTC-ETH,ETH-BNB,BTC-SOL", description="Comma-separated asset pairs"),
    exchanges: str = Query("all", description="Comma-separated list of exchanges"),
    min_profit_bps: int = Query(5, description="Minimum profit in basis points"),
    current_user: User = Depends(get_current_user)
):
    """Get cross-asset arbitrage opportunities."""
    
    await rate_limiter.check_rate_limit(
        key="market:cross_asset_arbitrage",
        limit=20,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        result = await market_analysis.cross_asset_arbitrage(
            asset_pairs=asset_pairs,
            exchanges=exchanges,
            min_profit_bps=min_profit_bps,
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Cross-asset arbitrage analysis failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Cross-asset arbitrage analysis failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cross-asset arbitrage analysis failed: {str(e)}"
        )


@router.get("/spread-monitoring")
async def get_spread_monitoring(
    symbols: str = Query("BTC,ETH,SOL", description="Comma-separated list of symbols"),
    exchanges: str = Query("all", description="Comma-separated list of exchanges"),
    current_user: User = Depends(get_current_user)
):
    """Monitor bid-ask spreads across exchanges."""
    
    await rate_limiter.check_rate_limit(
        key="market:spread_monitoring",
        limit=30,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        result = await market_analysis.monitor_spreads(
            symbols=symbols,
            exchanges=exchanges,
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Spread monitoring failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Spread monitoring failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Spread monitoring failed: {str(e)}"
        )


@router.get("/cross-exchange-comparison")
async def get_cross_exchange_comparison(
    symbols: str = Query(..., description="Comma-separated list of symbols"),
    current_user: User = Depends(get_current_user)
):
    """Get cross-exchange price comparison."""
    
    await rate_limiter.check_rate_limit(
        key="market:cross_exchange",
        limit=50,
        window=60,
        user_id=str(current_user.id)
    )
    
    try:
        result = await market_analysis.realtime_price_tracking(
            symbols=symbols,
            exchanges="all",
            user_id=str(current_user.id)
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Cross-exchange comparison failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Cross-exchange comparison failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cross-exchange comparison failed: {str(e)}"
        )