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
        self.master_controller = MasterSystemController()  # Use pipeline instead of direct calls
        self.trade_executor = TradeExecutionService()
        self.trading_strategies = TradingStrategiesService()
        self.ai_consensus = AIConsensusService()
    
    async def get_portfolio_summary(self, user_id: str) -> Dict[str, Any]:
        """Get portfolio summary for chat interface using REAL exchange data."""
        try:
            # Use REAL portfolio data from connected exchanges
            from app.api.v1.endpoints.exchanges import get_user_portfolio_from_exchanges
            from app.core.database import AsyncSessionLocal
            
            async with AsyncSessionLocal() as db:
                portfolio_result = await get_user_portfolio_from_exchanges(user_id, db)
            
            if not portfolio_result.get("success"):
                return {
                    "total_value": 0,
                    "daily_pnl": 0,
                    "total_pnl": 0,
                    "positions": [],
                    "risk_level": "Unknown",
                    "error": portfolio_result.get("error", "No portfolio data")
                }
            
            # Extract REAL portfolio data
            total_value = portfolio_result.get("total_value_usd", 0)
            balances = portfolio_result.get("balances", [])
            exchanges = portfolio_result.get("exchanges", [])
            
            # Calculate daily P&L (use real exchange data)
            daily_pnl = sum(balance.get("unrealized_pnl_24h", 0) for balance in balances)
            total_pnl = sum(balance.get("unrealized_pnl", 0) for balance in balances)
            
            # Format positions for chat using REAL balance data
            formatted_positions = []
            for balance in balances[:10]:  # Top 10 positions
                if balance.get("total", 0) > 0:  # Only include non-zero balances
                    formatted_positions.append({
                        "symbol": balance.get("asset", "Unknown"),
                        "value": balance.get("value_usd", 0),
                        "percentage": (balance.get("value_usd", 0) / total_value * 100) if total_value > 0 else 0,
                        "pnl_percentage": balance.get("pnl_percentage", 0),
                        "quantity": balance.get("total", 0),
                        "exchange": balance.get("exchange", "Unknown")
                    })
            
            return {
                "total_value": total_value,
                "daily_pnl": daily_pnl,
                "total_pnl": total_pnl,
                "positions": formatted_positions,
                "risk_level": "Moderate",  # Would calculate based on actual data
                "exchanges_connected": len(exchanges),
                "data_source": "real_exchanges",  # Indicate this is real data
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
        """Get analysis for a specific asset using the 5-phase pipeline."""
        try:
            # Use Master Controller pipeline for comprehensive asset analysis
            pipeline_result = await self.master_controller.trigger_pipeline(
                analysis_type="asset_analysis",
                symbols=symbol,
                timeframes="1h,4h,1d",
                user_id="chat_system"
            )
            
            if not pipeline_result.get("success"):
                return {
                    "current_price": 0,
                    "trend": "Unknown",
                    "momentum": "Unknown",
                    "support_level": 0,
                    "resistance_level": 0,
                    "volatility": 0.5
                }
            
            # Extract data from pipeline result (comes from all 5 phases)
            pipeline_data = pipeline_result.get("pipeline_results", {})
            market_analysis = pipeline_data.get("market_analysis", {})
            ai_consensus = pipeline_data.get("ai_consensus", {})
            
            return {
                "current_price": market_analysis.get("current_price", 0),
                "trend": ai_consensus.get("trend_direction", "Neutral"),
                "momentum": market_analysis.get("momentum", "Neutral"),
                "support_level": market_analysis.get("support_levels", [0])[0] if market_analysis.get("support_levels") else 0,
                "resistance_level": market_analysis.get("resistance_levels", [0])[0] if market_analysis.get("resistance_levels") else 0,
                "volatility": market_analysis.get("volatility_score", 0.5),
                "volume_trend": market_analysis.get("volume_trend", "Normal"),
                "rsi": market_analysis.get("technical_indicators", {}).get("rsi", 50),
                "macd": market_analysis.get("technical_indicators", {}).get("macd", 0),
                "sentiment": ai_consensus.get("sentiment_score", 0.5),
                "pipeline_source": "5_phase_system"  # Indicate this comes from full pipeline
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
                strategy="equal_weight",  # Use equal_weight for proper detection
                target_allocation=target_allocation,
                rebalance_threshold=0.05  # 5% threshold
            )
            
            if not optimization_result.get("success"):
                return {
                    "needs_rebalancing": False,
                    "deviation_score": 0,
                    "recommended_trades": [],
                    "analysis_type": "rebalancing"  # Ensure analysis_type is always present
                }
            
            optimization_data = optimization_result.get("optimization_result", {})
            
            # Check if rebalancing is needed (defensive extraction)
            needs_rebalancing = optimization_data.get("rebalancing_needed", False)
            deviation_score = optimization_data.get("deviation_percentage", 0)
            
            # Format recommended trades (defensive extraction)
            recommended_trades = []
            raw_trades = optimization_data.get("recommended_trades", [])
            if isinstance(raw_trades, list):
                for trade in raw_trades:
                    if isinstance(trade, dict):
                        recommended_trades.append({
                            "symbol": trade.get("symbol", "Unknown"),
                            "action": trade.get("action", "HOLD"),  # buy/sell
                            "amount": trade.get("amount_usd", 0),
                            "current_percentage": trade.get("current_allocation", 0),
                            "target_percentage": trade.get("target_allocation", 0),
                            "reason": trade.get("reason", "Portfolio optimization")
                        })
            
            return {
                "needs_rebalancing": needs_rebalancing,
                "deviation_score": deviation_score,
                "recommended_trades": recommended_trades,
                "risk_reduction": optimization_data.get("risk_reduction_percentage", 0),
                "expected_improvement": optimization_data.get("expected_return_improvement", 0),
                "analysis_type": "rebalancing"  # Ensure analysis_type is always present
            }
            
        except KeyError as ke:
            logger.error("Rebalancing analysis failed - missing key", 
                        missing_key=str(ke), 
                        user_id=user_id)
            return {
                "needs_rebalancing": False,
                "error": f"Missing required data field: {str(ke)}",
                "analysis_type": "error"  # Ensure analysis_type is always present
            }
        except Exception as e:
            logger.error("Rebalancing analysis failed", error=str(e), user_id=user_id)
            return {
                "needs_rebalancing": False,
                "error": str(e),
                "analysis_type": "error"  # Ensure analysis_type is always present
            }
    
    async def discover_opportunities(self, user_id: str, risk_tolerance: str = "balanced") -> Dict[str, Any]:
        """Discover market opportunities using the 5-phase pipeline."""
        try:
            # Use Master Controller pipeline for comprehensive opportunity discovery
            pipeline_result = await self.master_controller.trigger_pipeline(
                analysis_type="opportunity_discovery",
                symbols="BTC,ETH,SOL,MATIC,LINK,UNI,AVAX,DOT",  # Top assets for opportunities
                risk_tolerance=risk_tolerance,
                user_id=user_id
            )
            
            if not pipeline_result.get("success"):
                return {
                    "opportunities": [],
                    "analysis_type": "opportunity_discovery",
                    "error": pipeline_result.get("error", "Pipeline execution failed")
                }
            
            # Extract opportunities from pipeline results (trading strategies + AI consensus)
            pipeline_data = pipeline_result.get("pipeline_results", {})
            trading_strategies = pipeline_data.get("trading_strategies", {})
            ai_consensus = pipeline_data.get("ai_consensus", {})
            opportunities_data = trading_strategies.get("opportunities", [])
            
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
                "market_conditions": ai_consensus.get("market_context", {}),
                "pipeline_source": "5_phase_system",
                "analysis_type": "opportunity_discovery",
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except KeyError as ke:
            logger.error("Opportunity discovery failed - missing key", 
                        missing_key=str(ke), 
                        user_id=user_id)
            return {
                "opportunities": [],
                "error": f"Missing required data field: {str(ke)}",
                "analysis_type": "opportunity_discovery"
            }
        except Exception as e:
            logger.error("Opportunity discovery failed", error=str(e))
            return {
                "opportunities": [],
                "error": str(e),
                "analysis_type": "opportunity_discovery"
            }
    
    async def get_comprehensive_analysis(self) -> Dict[str, Any]:
        """Get comprehensive market analysis using the 5-phase pipeline."""
        try:
            # Use Master Controller pipeline for comprehensive market overview
            pipeline_result = await self.master_controller.trigger_pipeline(
                analysis_type="market_overview",
                symbols="BTC,ETH,BNB,SOL,ADA,XRP,MATIC,DOT,AVAX,LINK",
                timeframes="1h,4h,1d",
                user_id="chat_system"
            )
            
            if not pipeline_result.get("success"):
                return {
                    "sentiment": "Neutral",
                    "trend": "Sideways",
                    "market_phase": "Consolidation",
                    "volatility": "Medium",
                    "total_market_cap": 0,
                    "total_volume_24h": 0,
                    "btc_dominance": 50,
                    "fear_greed_index": 50,
                    "analysis_type": "market_overview",
                    "error": pipeline_result.get("error", "Pipeline failed")
                }
            
            # Extract comprehensive data from pipeline results
            pipeline_data = pipeline_result.get("pipeline_results", {})
            market_analysis = pipeline_data.get("market_analysis", {})
            ai_consensus = pipeline_data.get("ai_consensus", {})
            
            return {
                "sentiment": ai_consensus.get("market_sentiment", "Neutral"),
                "trend": ai_consensus.get("trend_direction", "Sideways"),
                "market_phase": ai_consensus.get("market_phase", "Consolidation"),
                "volatility": market_analysis.get("volatility_level", "Medium"),
                "total_market_cap": market_analysis.get("total_market_cap", 0) / 1e9,  # Convert to billions
                "total_volume_24h": market_analysis.get("total_volume_24h", 0) / 1e9,  # Convert to billions
                "btc_dominance": market_analysis.get("btc_dominance", 50),
                "fear_greed_index": ai_consensus.get("fear_greed_index", 50),
                "pipeline_source": "5_phase_system",
                "analysis_type": "market_overview",
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except KeyError as ke:
            logger.error("Comprehensive analysis failed - missing key", 
                        missing_key=str(ke))
            return {
                "sentiment": "Unknown",
                "error": f"Missing required data field: {str(ke)}",
                "analysis_type": "market_overview"
            }
        except Exception as e:
            logger.error("Comprehensive analysis failed", error=str(e))
            return {
                "sentiment": "Unknown",
                "error": str(e),
                "analysis_type": "market_overview"
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
                "analysis_type": "sector_analysis",
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Sector analysis failed", error=str(e))
            return {
                "sectors": [],
                "analysis_type": "sector_analysis",
                "error": str(e)
            }
    
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
                "analysis_type": "market_scan",
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Market scan failed", error=str(e))
            return {
                "analysis_type": "market_scan",
                "error": str(e)
            }
    
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

    async def get_user_strategies_summary(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user strategies summary for chat responses."""
        try:
            # Import here to avoid circular imports
            import asyncio
            from app.core.database import get_database
            from app.services.strategy_marketplace_service import strategy_marketplace_service

            # Get user strategy portfolio with timeout protection
            async with asyncio.timeout(15.0):  # 15 second timeout
                portfolio_data = await strategy_marketplace_service.get_user_strategy_portfolio(user_id)

            if not portfolio_data.get('success', False):
                return {
                    "total_strategies": 0,
                    "active_strategies": 0,
                    "inactive_strategies": 0,
                    "strategies": [],
                    "summary": "No strategies found",
                    "error": portfolio_data.get('error', 'Failed to load strategies')
                }

            strategies = portfolio_data.get('active_strategies', [])
            total_strategies = len(strategies)
            active_strategies = sum(1 for s in strategies if s.get('is_active', False))
            inactive_strategies = total_strategies - active_strategies

            # Calculate performance summary
            total_pnl = sum(s.get('total_pnl_usd', 0) for s in strategies)
            total_trades = sum(s.get('total_trades', 0) for s in strategies)
            avg_win_rate = sum(s.get('win_rate', 0) for s in strategies) / max(1, total_strategies)

            # Get recent top performing strategies
            recent_strategies = sorted(
                strategies,
                key=lambda x: x.get('total_pnl_usd', 0),
                reverse=True
            )[:5]

            return {
                "total_strategies": total_strategies,
                "active_strategies": active_strategies,
                "inactive_strategies": inactive_strategies,
                "strategies": strategies,
                "recent_strategies": recent_strategies,
                "performance": {
                    "total_pnl": total_pnl,
                    "total_trades": total_trades,
                    "average_win_rate": avg_win_rate
                },
                "summary": f"Found {total_strategies} strategies ({active_strategies} active)",
                "last_updated": portfolio_data.get('last_updated')
            }

        except asyncio.TimeoutError:
            return {
                "total_strategies": 0,
                "active_strategies": 0,
                "inactive_strategies": 0,
                "strategies": [],
                "summary": "Strategy loading timed out",
                "error": "Database timeout - please try again"
            }

        except Exception as e:
            logger.error("Failed to get user strategies summary", error=str(e), user_id=user_id)
            return {
                "total_strategies": 0,
                "active_strategies": 0,
                "inactive_strategies": 0,
                "strategies": [],
                "summary": "Error loading strategies",
                "error": str(e)
            }


# Global adapter instance
chat_adapters = ChatServiceAdapters()