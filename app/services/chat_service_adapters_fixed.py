"""
Chat Service Adapters - FIXED VERSION

Properly connects chat system to real exchange data and services.
All function calls have been verified to match actual service implementations.
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
from app.services.portfolio_risk_core import PortfolioRiskServiceExtended
from app.services.ai_consensus_core import AIConsensusService
from app.services.master_controller import MasterSystemController

settings = get_settings()
logger = structlog.get_logger(__name__)


class ChatServiceAdaptersFixed:
    """FIXED adapter methods for chat integration with REAL service calls."""
    
    def __init__(self):
        # Use the extended portfolio risk service that has real data methods
        self.portfolio_risk = PortfolioRiskServiceExtended()
        self.market_analysis = MarketAnalysisService()
        self.trade_executor = TradeExecutionService()
        self.trading_strategies = TradingStrategiesService()
        self.ai_consensus = AIConsensusService()
    
    async def get_portfolio_summary(self, user_id: str) -> Dict[str, Any]:
        """Get portfolio summary using THE SAME METHOD AS THE UI."""
        try:
            logger.info("Getting portfolio summary using UI method", user_id=user_id)
            
            # Use the EXACT SAME approach as the UI
            from app.api.v1.endpoints.exchanges import list_exchange_connections, get_exchange_balances
            from app.core.database import AsyncSessionLocal
            from app.models.user import User
            
            total_value = 0
            all_positions = []
            connected_exchanges = []
            
            # Create a mock user object for the function calls
            mock_user = User()
            mock_user.id = user_id
            
            async with AsyncSessionLocal() as db:
                # Step 1: Get exchange list (same as UI /exchanges/list)
                exchanges_response = await list_exchange_connections(current_user=mock_user, db=db)
                
                if exchanges_response.get("connections"):
                    # Step 2: Get balances for each exchange (same as UI /exchanges/{exchange}/balances)
                    for exchange_conn in exchanges_response["connections"]:
                        if exchange_conn.get("is_active"):
                            exchange_name = exchange_conn.get("exchange")
                            try:
                                # Get balances using the same endpoint as UI
                                balances_response = await get_exchange_balances(
                                    exchange=exchange_name,
                                    current_user=mock_user,
                                    db=db
                                )
                                
                                if balances_response and len(balances_response) > 0:
                                    exchange_total = 0
                                    for balance in balances_response:
                                        if balance.get("total_balance", 0) > 0:
                                            value_usd = balance.get("usd_value", 0)
                                            exchange_total += value_usd
                                            
                                            all_positions.append({
                                                "symbol": balance.get("symbol", "Unknown"),
                                                "amount": balance.get("total_balance", 0),
                                                "value_usd": value_usd,
                                                "exchange": exchange_name,
                                                "change_24h": 0  # TODO: Calculate from price data
                                            })
                                    
                                    total_value += exchange_total
                                    connected_exchanges.append({
                                        "name": exchange_name,
                                        "value_usd": exchange_total
                                    })
                                    
                                    logger.info(f"Exchange {exchange_name} balance: ${exchange_total:,.2f}")
                                
                            except Exception as e:
                                logger.warning(f"Failed to get {exchange_name} balances", error=str(e))
                                continue
                
                # Calculate percentages for positions
                for position in all_positions:
                    if total_value > 0:
                        position["percentage"] = (position["value_usd"] / total_value) * 100
                    else:
                        position["percentage"] = 0
                
                # Sort positions by value
                all_positions.sort(key=lambda x: x["value_usd"], reverse=True)
                
                logger.info(f"Portfolio summary: ${total_value:,.2f} across {len(connected_exchanges)} exchanges")
                
                return {
                    "total_value": total_value,
                    "daily_pnl": 0,  # TODO: Calculate from historical data
                    "daily_pnl_pct": 0,
                    "total_pnl": 0,  # TODO: Calculate from cost basis
                    "total_pnl_pct": 0,
                    "positions": all_positions[:10],  # Top 10 positions
                    "risk_level": "Medium",  # TODO: Calculate based on positions
                    "exchanges_connected": len(connected_exchanges),
                    "exchanges": connected_exchanges,
                    "data_source": "real_exchanges_ui_method",
                    "last_updated": datetime.utcnow().isoformat()
                }
            
        except Exception as e:
            logger.error("Portfolio summary failed", error=str(e), user_id=user_id, exc_info=True)
            return {
                "total_value": 0,
                "daily_pnl": 0,
                "total_pnl": 0,
                "positions": [],
                "risk_level": "Unknown",
                "error": str(e)
            }
    
    async def comprehensive_risk_analysis(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive risk analysis using CORRECT method calls."""
        try:
            logger.info("Getting risk analysis", user_id=user_id)
            
            # Use the CORRECT method signature that actually exists
            risk_result = await self.portfolio_risk.risk_analysis(
                user_id=user_id,
                assessment_type="comprehensive",  # Correct parameter name
                include_stress_tests=True  # Correct parameter name
            )
            
            if not risk_result.get("success"):
                logger.warning("Risk analysis failed", error=risk_result.get("error"))
                return {
                    "overall_risk": "Unknown",
                    "var_24h": 0,
                    "max_drawdown": 0,
                    "sharpe_ratio": 0,
                    "beta": 1.0,
                    "error": risk_result.get("error")
                }
            
            # Extract risk data using correct field names
            risk_data = risk_result.get("assessment", {})
            risk_metrics = risk_data.get("risk_metrics", {})
            
            return {
                "overall_risk": risk_metrics.get("overall_risk_level", "Medium"),
                "var_24h": risk_metrics.get("value_at_risk_24h", 0),
                "max_drawdown": risk_metrics.get("max_drawdown_percentage", 0),
                "sharpe_ratio": risk_metrics.get("sharpe_ratio", 0),
                "beta": risk_metrics.get("portfolio_beta", 1.0),
                "volatility": risk_metrics.get("portfolio_volatility", 0),
                "concentration_risk": risk_data.get("concentration_risk", "Medium"),
                "correlation_risk": risk_data.get("correlation_risk", "Medium"),
                "recommendations": risk_data.get("recommendations", [])
            }
            
        except Exception as e:
            logger.error("Risk analysis failed", error=str(e), user_id=user_id, exc_info=True)
            return {
                "overall_risk": "Unknown",
                "error": str(e)
            }
    
    async def get_market_overview(self) -> Dict[str, Any]:
        """Get market overview using CORRECT method call."""
        try:
            logger.info("Getting market overview")
            
            # Use the CORRECT method that actually exists (no parameters)
            market_result = await self.market_analysis.get_market_overview()
            
            if not market_result.get("success"):
                logger.warning("Market overview failed", error=market_result.get("error"))
                return {
                    "sentiment": "Unknown",
                    "trend": "Sideways",
                    "volatility": "Medium",
                    "error": market_result.get("error")
                }
            
            # Extract market data using correct field names
            market_data = market_result.get("market_overview", {})
            
            return {
                "sentiment": market_data.get("overall_sentiment", "Neutral"),
                "trend": market_data.get("trend_direction", "Sideways"),
                "market_phase": market_data.get("market_phase", "Consolidation"),
                "volatility": market_data.get("volatility_level", "Medium"),
                "fear_greed_index": market_data.get("fear_greed_index", 50),
                "btc_dominance": market_data.get("btc_dominance", 50),
                "total_market_cap": market_data.get("total_market_cap_billions", 0),
                "arbitrage_opportunities": market_data.get("arbitrage_opportunities", 0),
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Market overview failed", error=str(e), exc_info=True)
            return {
                "sentiment": "Unknown",
                "error": str(e)
            }
    
    async def get_technical_analysis(self, symbols: str = "BTC,ETH,SOL") -> Dict[str, Any]:
        """Get technical analysis using CORRECT method call."""
        try:
            logger.info("Getting technical analysis", symbols=symbols)
            
            # Use the CORRECT method that actually exists
            tech_result = await self.market_analysis.technical_analysis(
                symbols=symbols,
                timeframes="1h,4h,1d"  # Correct parameter format
            )
            
            if not tech_result.get("success"):
                logger.warning("Technical analysis failed", error=tech_result.get("error"))
                return {
                    "analysis": {},
                    "error": tech_result.get("error")
                }
            
            return {
                "analysis": tech_result.get("technical_analysis", {}),
                "symbols_analyzed": tech_result.get("symbols_analyzed", []),
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Technical analysis failed", error=str(e), exc_info=True)
            return {
                "analysis": {},
                "error": str(e)
            }
    
    async def get_market_sentiment(self, symbols: str = "BTC,ETH,SOL") -> Dict[str, Any]:
        """Get market sentiment using CORRECT method call."""
        try:
            logger.info("Getting market sentiment", symbols=symbols)
            
            # Use the CORRECT method that actually exists
            sentiment_result = await self.market_analysis.market_sentiment(
                symbols=symbols,
                timeframes="1h,4h,1d"  # Correct parameter format
            )
            
            if not sentiment_result.get("success"):
                logger.warning("Market sentiment failed", error=sentiment_result.get("error"))
                return {
                    "sentiment": {},
                    "error": sentiment_result.get("error")
                }
            
            return {
                "sentiment": sentiment_result.get("sentiment_analysis", {}),
                "overall_sentiment": sentiment_result.get("overall_sentiment", "Neutral"),
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Market sentiment failed", error=str(e), exc_info=True)
            return {
                "sentiment": {},
                "error": str(e)
            }
    
    async def discover_opportunities(self, user_id: str, risk_tolerance: str = "balanced") -> Dict[str, Any]:
        """Discover opportunities using REAL market analysis."""
        try:
            logger.info("Discovering opportunities", user_id=user_id, risk_tolerance=risk_tolerance)
            
            # Get market overview first
            market_overview = await self.get_market_overview()
            
            # Get technical analysis for major coins
            tech_analysis = await self.get_technical_analysis("BTC,ETH,SOL,ADA,DOT,AVAX")
            
            # Get market sentiment
            sentiment_analysis = await self.get_market_sentiment("BTC,ETH,SOL,ADA,DOT,AVAX")
            
            # Combine data to create opportunities
            opportunities = []
            
            # Extract opportunities from technical analysis
            tech_data = tech_analysis.get("analysis", {})
            for symbol, analysis in tech_data.items():
                if isinstance(analysis, dict):
                    # Create opportunity based on technical signals
                    signals = analysis.get("signals", {})
                    if signals.get("overall_signal") == "BUY":
                        opportunities.append({
                            "symbol": symbol,
                            "confidence": signals.get("confidence", 70),
                            "potential_return": signals.get("target_return", 10),
                            "timeframe": "Medium-term",
                            "strategy": "Technical Analysis",
                            "risk_level": self._map_risk_tolerance(risk_tolerance),
                            "entry_price": analysis.get("current_price", 0),
                            "reason": f"Technical signals: {signals.get('primary_signal', 'Bullish trend')}"
                        })
            
            # Limit to top opportunities
            opportunities = sorted(opportunities, key=lambda x: x["confidence"], reverse=True)[:5]
            
            return {
                "opportunities": opportunities,
                "market_conditions": {
                    "sentiment": market_overview.get("sentiment", "Neutral"),
                    "trend": market_overview.get("trend", "Sideways"),
                    "volatility": market_overview.get("volatility", "Medium")
                },
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Opportunity discovery failed", error=str(e), exc_info=True)
            return {
                "opportunities": [],
                "error": str(e)
            }
    
    async def analyze_rebalancing_needs(self, user_id: str, target_allocation: Optional[Dict] = None) -> Dict[str, Any]:
        """Analyze rebalancing needs using CORRECT method call."""
        try:
            logger.info("Analyzing rebalancing needs", user_id=user_id)
            
            # Use the CORRECT method that actually exists
            optimization_result = await self.portfolio_risk.optimize_allocation(
                user_id=user_id,
                strategy="balanced",  # Correct parameter
                target_allocation=target_allocation or {},
                rebalance_threshold=0.05
            )
            
            if not optimization_result.get("success"):
                logger.warning("Optimization failed", error=optimization_result.get("error"))
                return {
                    "needs_rebalancing": False,
                    "deviation_score": 0,
                    "recommended_trades": [],
                    "error": optimization_result.get("error")
                }
            
            # Extract optimization data
            optimization_data = optimization_result.get("optimization", {})
            
            return {
                "needs_rebalancing": optimization_data.get("rebalancing_recommended", False),
                "deviation_score": optimization_data.get("deviation_percentage", 0),
                "recommended_trades": optimization_data.get("recommended_trades", []),
                "risk_reduction": optimization_data.get("risk_reduction_percentage", 0),
                "expected_improvement": optimization_data.get("expected_return_improvement", 0)
            }
            
        except Exception as e:
            logger.error("Rebalancing analysis failed", error=str(e), user_id=user_id, exc_info=True)
            return {
                "needs_rebalancing": False,
                "error": str(e)
            }
    
    def _map_risk_tolerance(self, risk_tolerance: str) -> str:
        """Map risk tolerance to risk level."""
        mapping = {
            "conservative": "Low",
            "balanced": "Medium", 
            "aggressive": "High"
        }
        return mapping.get(risk_tolerance.lower(), "Medium")


# Create global instance with FIXED adapters
chat_adapters_fixed = ChatServiceAdaptersFixed()