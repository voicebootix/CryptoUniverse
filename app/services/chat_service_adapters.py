"""
Chat Service Adapters

Adapter methods to bridge between the chat engine and existing services.
These methods provide the interface expected by the chat integration while
working with the existing service implementations.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import structlog

from app.core.config import get_settings
from app.services.market_analysis_core import MarketAnalysisService
from app.services.trade_execution import TradeExecutionService
from app.services.trading_strategies import TradingStrategiesService
from app.services.portfolio_risk_core import PortfolioRiskService
from app.services.ai_consensus_core import AIConsensusService
from app.services.master_controller import MasterSystemController

settings = get_settings()
logger = structlog.get_logger(__name__)


class ChatServiceAdapters:
    """Adapter methods for chat integration with existing services."""
    
    def __init__(self):
        self.portfolio_risk = PortfolioRiskService()
        self.market_analysis = MarketAnalysisService()
        self.trade_executor = TradeExecutionService()
        self.trading_strategies = TradingStrategiesService()
        self.ai_consensus = AIConsensusService()
    
    async def get_portfolio_summary(self, user_id: str) -> Dict[str, Any]:
        """Get portfolio summary for chat interface."""
        try:
            # Use existing portfolio risk service
            portfolio_result = await self.portfolio_risk.get_portfolio(
                user_id=user_id,
                exchanges=["all"],
                include_balances=True
            )
            
            if not portfolio_result.get("success"):
                return {
                    "total_value": 0,
                    "daily_pnl": 0,
                    "total_pnl": 0,
                    "positions": [],
                    "risk_level": "Unknown"
                }
            
            portfolio_data = portfolio_result.get("portfolio", {})
            
            # Calculate summary metrics
            total_value = portfolio_data.get("total_value_usd", 0)
            positions = portfolio_data.get("positions", [])
            
            # Calculate daily P&L (simplified)
            daily_pnl = sum(pos.get("unrealized_pnl_24h", 0) for pos in positions)
            total_pnl = sum(pos.get("unrealized_pnl", 0) for pos in positions)
            
            # Format positions for chat
            formatted_positions = []
            for pos in positions[:10]:  # Top 10 positions
                formatted_positions.append({
                    "symbol": pos.get("symbol", "Unknown"),
                    "value": pos.get("value_usd", 0),
                    "percentage": (pos.get("value_usd", 0) / total_value * 100) if total_value > 0 else 0,
                    "pnl_percentage": pos.get("pnl_percentage", 0),
                    "quantity": pos.get("quantity", 0)
                })
            
            return {
                "total_value": total_value,
                "daily_pnl": daily_pnl,
                "total_pnl": total_pnl,
                "positions": formatted_positions,
                "risk_level": portfolio_data.get("risk_level", "Medium"),
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Portfolio summary failed", error=str(e), user_id=user_id)
            return {
                "total_value": 0,
                "daily_pnl": 0,
                "total_pnl": 0,
                "positions": [],
                "risk_level": "Unknown",
                "error": str(e)
            }
    
    async def comprehensive_risk_analysis(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive risk analysis for chat interface."""
        try:
            # Use existing risk analysis service
            risk_result = await self.portfolio_risk.risk_analysis(
                user_id=user_id,
                timeframe="24h",
                confidence_level=95.0,
                include_correlations=True
            )
            
            if not risk_result.get("success"):
                return {
                    "overall_risk": "Unknown",
                    "var_24h": 0,
                    "var_7d": 0,
                    "max_drawdown": 0,
                    "sharpe_ratio": 0,
                    "beta": 1.0,
                    "concentration_risk": "Unknown",
                    "volatility_risk": "Unknown",
                    "correlation_risk": "Unknown",
                    "liquidity_risk": "Unknown"
                }
            
            risk_data = risk_result.get("risk_analysis", {})
            
            return {
                "overall_risk": risk_data.get("overall_risk_level", "Medium"),
                "var_24h": risk_data.get("value_at_risk_24h", 0),
                "var_7d": risk_data.get("value_at_risk_7d", 0),
                "max_drawdown": risk_data.get("max_drawdown_percentage", 0),
                "sharpe_ratio": risk_data.get("sharpe_ratio", 0),
                "beta": risk_data.get("portfolio_beta", 1.0),
                "concentration_risk": risk_data.get("concentration_risk", "Medium"),
                "volatility_risk": risk_data.get("volatility_risk", "Medium"),
                "correlation_risk": risk_data.get("correlation_risk", "Medium"),
                "liquidity_risk": risk_data.get("liquidity_risk", "Low"),
                "recommendations": risk_data.get("risk_recommendations", [])
            }
            
        except Exception as e:
            logger.error("Risk analysis failed", error=str(e), user_id=user_id)
            return {
                "overall_risk": "Unknown",
                "error": str(e)
            }
    
    async def get_performance_metrics(self, user_id: str) -> Dict[str, Any]:
        """Get portfolio performance metrics."""
        try:
            # This would typically come from a performance tracking service
            # For now, we'll return mock data that would be realistic
            return {
                "total_return": 15.2,
                "annualized_return": 18.5,
                "volatility": 35.2,
                "sharpe_ratio": 0.85,
                "max_drawdown": -12.3,
                "win_rate": 68.5,
                "profit_factor": 1.45,
                "calmar_ratio": 1.5,
                "sortino_ratio": 1.2,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Performance metrics failed", error=str(e))
            return {}
    
    async def get_asset_analysis(self, symbol: str) -> Dict[str, Any]:
        """Get analysis for a specific asset."""
        try:
            # Use existing market analysis service
            analysis_result = await self.market_analysis.analyze_asset(
                symbol=symbol,
                timeframes=["1h", "4h", "1d"],
                include_technical=True,
                include_sentiment=True
            )
            
            if not analysis_result.get("success"):
                return {
                    "current_price": 0,
                    "trend": "Unknown",
                    "momentum": "Unknown",
                    "support_level": 0,
                    "resistance_level": 0,
                    "volatility": 0.5
                }
            
            analysis_data = analysis_result.get("analysis", {})
            
            return {
                "current_price": analysis_data.get("current_price", 0),
                "trend": analysis_data.get("trend_direction", "Neutral"),
                "momentum": analysis_data.get("momentum", "Neutral"),
                "support_level": analysis_data.get("support_levels", [0])[0] if analysis_data.get("support_levels") else 0,
                "resistance_level": analysis_data.get("resistance_levels", [0])[0] if analysis_data.get("resistance_levels") else 0,
                "volatility": analysis_data.get("volatility_score", 0.5),
                "volume_trend": analysis_data.get("volume_trend", "Normal"),
                "rsi": analysis_data.get("technical_indicators", {}).get("rsi", 50),
                "macd": analysis_data.get("technical_indicators", {}).get("macd", 0),
                "sentiment": analysis_data.get("sentiment_score", 0.5)
            }
            
        except Exception as e:
            logger.error("Asset analysis failed", symbol=symbol, error=str(e))
            return {
                "current_price": 0,
                "trend": "Unknown",
                "volatility": 0.5,
                "error": str(e)
            }
    
    async def analyze_rebalancing_needs(self, user_id: str, target_allocation: Optional[Dict] = None) -> Dict[str, Any]:
        """Analyze if portfolio needs rebalancing."""
        try:
            # Use existing portfolio optimization service
            optimization_result = await self.portfolio_risk.optimize_allocation(
                user_id=user_id,
                strategy="adaptive",  # Use adaptive strategy by default
                target_allocation=target_allocation,
                rebalance_threshold=0.05  # 5% threshold
            )
            
            if not optimization_result.get("success"):
                return {
                    "needs_rebalancing": False,
                    "deviation_score": 0,
                    "recommended_trades": []
                }
            
            optimization_data = optimization_result.get("optimization", {})
            
            # Check if rebalancing is needed
            needs_rebalancing = optimization_data.get("rebalancing_needed", False)
            deviation_score = optimization_data.get("deviation_percentage", 0)
            
            # Format recommended trades
            recommended_trades = []
            for trade in optimization_data.get("recommended_trades", []):
                recommended_trades.append({
                    "symbol": trade.get("symbol"),
                    "action": trade.get("action"),  # buy/sell
                    "amount": trade.get("amount_usd"),
                    "current_percentage": trade.get("current_allocation"),
                    "target_percentage": trade.get("target_allocation"),
                    "reason": trade.get("reason", "Portfolio optimization")
                })
            
            return {
                "needs_rebalancing": needs_rebalancing,
                "deviation_score": deviation_score,
                "recommended_trades": recommended_trades,
                "risk_reduction": optimization_data.get("risk_reduction_percentage", 0),
                "expected_improvement": optimization_data.get("expected_return_improvement", 0)
            }
            
        except Exception as e:
            logger.error("Rebalancing analysis failed", error=str(e), user_id=user_id)
            return {
                "needs_rebalancing": False,
                "error": str(e)
            }
    
    async def discover_opportunities(self, user_id: str, risk_tolerance: str = "balanced") -> Dict[str, Any]:
        """Discover market opportunities."""
        try:
            # Use existing market analysis and trading strategies services
            opportunities_result = await self.market_analysis.find_opportunities(
                risk_tolerance=risk_tolerance,
                min_confidence=70.0,
                max_results=10
            )
            
            if not opportunities_result.get("success"):
                return {
                    "opportunities": []
                }
            
            opportunities_data = opportunities_result.get("opportunities", [])
            
            # Format opportunities for chat
            formatted_opportunities = []
            for opp in opportunities_data:
                formatted_opportunities.append({
                    "symbol": opp.get("symbol"),
                    "confidence": opp.get("confidence_score", 0),
                    "potential_return": opp.get("expected_return", 0),
                    "timeframe": opp.get("timeframe", "Medium-term"),
                    "strategy": opp.get("strategy_type", "Growth"),
                    "risk_level": opp.get("risk_level", "Medium"),
                    "entry_price": opp.get("entry_price", 0),
                    "reason": opp.get("opportunity_reason", "Market analysis")
                })
            
            return {
                "opportunities": formatted_opportunities,
                "market_conditions": opportunities_result.get("market_context", {}),
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Opportunity discovery failed", error=str(e))
            return {
                "opportunities": [],
                "error": str(e)
            }
    
    async def get_comprehensive_analysis(self) -> Dict[str, Any]:
        """Get comprehensive market analysis."""
        try:
            # Use existing market analysis service
            analysis_result = await self.market_analysis.get_market_overview(
                include_sectors=True,
                include_sentiment=True,
                include_technical=True
            )
            
            if not analysis_result.get("success"):
                return {
                    "sentiment": "Neutral",
                    "trend": "Sideways",
                    "market_phase": "Consolidation",
                    "volatility": "Medium",
                    "total_market_cap": 0,
                    "total_volume_24h": 0,
                    "btc_dominance": 50,
                    "fear_greed_index": 50
                }
            
            analysis_data = analysis_result.get("analysis", {})
            
            return {
                "sentiment": analysis_data.get("market_sentiment", "Neutral"),
                "trend": analysis_data.get("trend_direction", "Sideways"),
                "market_phase": analysis_data.get("market_phase", "Consolidation"),
                "volatility": analysis_data.get("volatility_level", "Medium"),
                "total_market_cap": analysis_data.get("total_market_cap", 0) / 1e9,  # Convert to billions
                "total_volume_24h": analysis_data.get("total_volume_24h", 0) / 1e9,  # Convert to billions
                "btc_dominance": analysis_data.get("btc_dominance", 50),
                "fear_greed_index": analysis_data.get("fear_greed_index", 50),
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Comprehensive analysis failed", error=str(e))
            return {
                "sentiment": "Unknown",
                "error": str(e)
            }
    
    async def get_sector_analysis(self) -> Dict[str, Any]:
        """Get sector analysis for market overview."""
        try:
            # Mock sector data - in reality this would come from market data service
            sectors = [
                {"name": "Layer 1", "24h_change": 3.2, "market_cap": 450e9},
                {"name": "DeFi", "24h_change": -1.8, "market_cap": 89e9},
                {"name": "Gaming", "24h_change": 8.5, "market_cap": 15e9},
                {"name": "NFT", "24h_change": -5.2, "market_cap": 12e9},
                {"name": "Infrastructure", "24h_change": 2.1, "market_cap": 78e9},
                {"name": "Meme Coins", "24h_change": 12.8, "market_cap": 45e9}
            ]
            
            return {
                "sectors": sectors,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Sector analysis failed", error=str(e))
            return {"sectors": []}
    
    async def comprehensive_market_scan(self) -> Dict[str, Any]:
        """Comprehensive market scan for opportunities."""
        try:
            # This would integrate with multiple data sources
            return {
                "sentiment": "Bullish",
                "market_phase": "Growth",
                "volatility": "Medium",
                "top_gainers": ["SOL", "AVAX", "DOT"],
                "top_losers": ["ADA", "XRP", "DOGE"],
                "volume_leaders": ["BTC", "ETH", "SOL"],
                "breakout_candidates": ["MATIC", "LINK", "UNI"],
                "oversold_opportunities": ["ADA", "XRP"],
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Market scan failed", error=str(e))
            return {}
    
    async def get_market_risk_factors(self) -> Dict[str, Any]:
        """Get current market risk factors."""
        try:
            return {
                "market_volatility": "Medium",
                "correlation_trend": "Increasing",
                "liquidity_status": "Good",
                "regulatory_risk": "Medium",
                "macro_risk": "Low",
                "technical_risk": "Medium",
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Market risk factors failed", error=str(e))
            return {}
    
    async def emergency_risk_assessment(self, user_id: str, trigger: str) -> Dict[str, Any]:
        """Emergency risk assessment for urgent situations."""
        try:
            # Get current portfolio
            portfolio_summary = await self.get_portfolio_summary(user_id)
            
            # Get current market conditions
            market_conditions = await self.get_market_risk_factors()
            
            # Assess immediate risks
            risk_level = "HIGH" if portfolio_summary.get("daily_pnl", 0) < -portfolio_summary.get("total_value", 0) * 0.1 else "MEDIUM"
            
            return {
                "risk_level": risk_level,
                "total_value": portfolio_summary.get("total_value", 0),
                "unrealized_pnl": portfolio_summary.get("total_pnl", 0),
                "daily_pnl": portfolio_summary.get("daily_pnl", 0),
                "trigger": trigger,
                "market_conditions": market_conditions,
                "immediate_actions": [
                    "Review stop-loss levels",
                    "Consider partial liquidation",
                    "Monitor market volatility",
                    "Assess position concentration"
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Emergency risk assessment failed", error=str(e))
            return {
                "risk_level": "UNKNOWN",
                "error": str(e)
            }


# Global adapter instance
chat_adapters = ChatServiceAdapters()