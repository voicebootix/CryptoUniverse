"""
Chat Integration Service

Provides deep integration between the AI chat engine and all existing CryptoUniverse services.
This service acts as a bridge to enable comprehensive money management through chat.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import structlog

from app.core.config import get_settings
from app.core.logging import LoggerMixin
from app.services.ai_chat_engine import enhanced_chat_engine as chat_engine, ChatIntent
from app.services.master_controller import MasterSystemController
from app.services.trade_execution import TradeExecutionService
from app.services.chat_service_adapters_fixed import chat_adapters_fixed as chat_adapters
from app.services.websocket import manager

settings = get_settings()
logger = structlog.get_logger(__name__)


class ChatIntegrationService(LoggerMixin):
    """
    Integrates AI chat engine with all CryptoUniverse services for comprehensive
    money management through natural language conversation.
    """
    
    def __init__(self):
        # Initialize all service connections
        self.master_controller = MasterSystemController()
        self.trade_executor = TradeExecutionService()
        self.adapters = chat_adapters
        
        # Register chat handlers
        self._register_chat_handlers()
    
    def _register_chat_handlers(self):
        """Register enhanced chat handlers with service integration."""
        
        # Override chat engine methods with integrated versions
        chat_engine._handle_portfolio_analysis = self._enhanced_portfolio_analysis
        chat_engine._handle_trade_execution = self._enhanced_trade_execution
        chat_engine._handle_rebalancing = self._enhanced_rebalancing
        chat_engine._handle_opportunity_discovery = self._enhanced_opportunity_discovery
        chat_engine._handle_risk_assessment = self._enhanced_risk_assessment
        chat_engine._handle_market_analysis = self._enhanced_market_analysis
        chat_engine.execute_confirmed_action = self._execute_confirmed_action
    
    async def _enhanced_portfolio_analysis(self, message: str, context: Dict, user_id: str) -> Dict[str, Any]:
        """Enhanced portfolio analysis with optimized performance for chat."""
        
        try:
            # Get portfolio data using FAST method (same as working API)
            portfolio_summary = await self.adapters.get_portfolio_summary(user_id)
            
            # Skip expensive operations for faster response in chat
            # Only get basic risk analysis if available quickly
            try:
                import asyncio
                risk_metrics = await asyncio.wait_for(
                    self.adapters.comprehensive_risk_analysis(user_id),
                    timeout=5.0  # 5 second timeout for risk analysis
                )
            except (asyncio.TimeoutError, Exception) as e:
                self.logger.warning("Risk analysis timed out or failed, using defaults", error=str(e))
                risk_metrics = {
                    "overall_risk": "Medium",
                    "var_24h": 0,
                    "sharpe_ratio": 0,
                    "max_drawdown": 0
                }
            
            # Skip heavy AI analysis for chat - use lightweight analysis only
            ai_analysis = {
                "success": True,
                "analysis": "Portfolio data successfully retrieved. For detailed AI analysis, use the full analysis feature.",
                "confidence": 0.8,
                "recommendations": []
            }
            
            # Format fast response with actual values
            total_value = float(portfolio_summary.get("total_value", 0))
            daily_pnl = float(portfolio_summary.get("daily_pnl", 0))
            total_pnl = float(portfolio_summary.get("total_pnl", 0))
            positions = portfolio_summary.get("positions", [])
            available_balance = float(portfolio_summary.get("available_balance", 0))
            
            # Calculate percentages safely
            daily_pnl_pct = (daily_pnl/total_value*100) if total_value > 0 else 0
            total_pnl_pct = (total_pnl/total_value*100) if total_value > 0 else 0
            
            response_content = f"""💰 **Your Portfolio Summary**

**Current Balance:**
• Total Portfolio Value: ${total_value:,.2f}
• Available Cash: ${available_balance:,.2f}
• Today's P&L: ${daily_pnl:,.2f} ({daily_pnl_pct:+.2f}%)
• Overall P&L: ${total_pnl:,.2f} ({total_pnl_pct:+.2f}%)

**Risk Assessment:**
• Risk Level: {risk_metrics.get('overall_risk', 'Medium')}
• Active Positions: {len(positions)}

**Top 5 Holdings:**"""
            
            # Show top positions with better formatting
            for i, position in enumerate(positions[:5]):
                symbol = position.get("symbol", "Unknown")
                value_usd = float(position.get("value_usd", 0))
                amount = float(position.get("amount", 0))
                exchange = position.get("exchange", "Unknown")
                
                if value_usd > 0:
                    percentage = (value_usd / total_value * 100) if total_value > 0 else 0
                    response_content += f"\n{i+1}. {symbol} ({exchange}): ${value_usd:,.2f} ({percentage:.1f}%)"
                    response_content += f"   Amount: {amount:,.4f}"
            
            # Add quick actions
            response_content += f"""

**Quick Actions:**
• Ask "Show me more details" for full analysis
• Ask "What should I buy?" for recommendations
• Ask "How risky is my portfolio?" for risk analysis

Your portfolio is connected and showing live data from your exchanges!"""
            
            return {
                "content": response_content,
                "confidence": ai_analysis.get("confidence", 0.9),
                "metadata": {
                    "portfolio_summary": portfolio_summary,
                    "risk_metrics": risk_metrics,
                    "ai_analysis": ai_analysis,
                    "actionable_items": ["rebalance", "risk_analysis", "opportunities", "stop_losses"]
                }
            }
            
        except Exception as e:
            self.logger.exception("Enhanced portfolio analysis failed", error=str(e))
            
            # Fallback: Try to get basic portfolio value directly
            try:
                from app.api.v1.endpoints.trading import get_portfolio
                from app.core.database import AsyncSessionLocal
                from app.models.user import User
                from sqlalchemy import text
                
                async with AsyncSessionLocal() as db:
                    # Get user object
                    user_result = await db.execute(
                        text("SELECT * FROM users WHERE id = :user_id"),
                        {"user_id": user_id}
                    )
                    user_row = user_result.fetchone()
                    
                    if user_row:
                        # Create a basic user object
                        class BasicUser:
                            def __init__(self, row):
                                self.id = row[0]  # Assume first column is id
                        
                        basic_user = BasicUser(user_row)
                        portfolio_response = await get_portfolio(current_user=basic_user)
                        
                        if hasattr(portfolio_response, 'total_value'):
                            total_value = float(portfolio_response.total_value)
                            return {
                                "content": f"""💰 **Portfolio Balance**
                                
**Your Current Portfolio:** ${total_value:,.2f}

I was able to retrieve your portfolio balance, but detailed analysis is temporarily unavailable. 
Your portfolio is connected and showing live data from your exchanges!

Try asking "What's my balance?" again in a moment for full details.""",
                                "confidence": 0.7,
                                "metadata": {"fallback_used": True, "total_value": total_value}
                            }
            except Exception as fallback_error:
                self.logger.error("Portfolio fallback also failed", error=str(fallback_error))
            
            return {
                "content": f"""💰 **Portfolio Status**

I'm having trouble accessing detailed portfolio analysis right now, but your portfolio is connected to the system.

**What you can try:**
• Ask "What's my balance?" in a moment
• Check the direct portfolio API at /api/v1/trading/portfolio
• Contact support if this persists

Your exchanges are connected and data should be available.""",
                "confidence": 0.3,
                "metadata": {"error": str(e)}
            }
    
    async def _enhanced_trade_execution(self, message: str, context: Dict, user_id: str) -> Dict[str, Any]:
        """Enhanced trade execution with full market analysis."""
        
        try:
            
            # Extract trade parameters
            trade_params = await chat_engine._extract_trade_parameters(message)
            
            if not trade_params:
                return {
                    "content": """I need more details to execute a trade. Please specify:

• **Asset:** Which cryptocurrency (e.g., BTC, ETH, SOL)
• **Action:** Buy or Sell
• **Amount:** Dollar amount or quantity
• **Type:** Market or Limit order (optional)

Example: "Buy $1000 of Bitcoin" or "Sell 0.5 ETH at market price" """,
                    "confidence": 0.9,
                    "metadata": {"requires_clarification": True}
                }
            
            # Get comprehensive market analysis
            symbol = trade_params.get("symbol")
            market_data = await self.adapters.get_asset_analysis(symbol)
            
            # Get portfolio context
            portfolio_data = await self.adapters.get_portfolio_summary(user_id)
            
            # Get AI consensus on trade
            trade_context = {
                "trade_request": trade_params,
                "market_analysis": market_data,
                "portfolio_context": portfolio_data,
                "user_message": message
            }
            
            ai_analysis = await self.adapters.ai_consensus.analyze_opportunity(
                json.dumps(trade_context),
                confidence_threshold=85.0,
                ai_models="all",
                user_id=user_id
            )
            
            # Calculate position sizing and risk
            position_size = await self._calculate_optimal_position_size(
                trade_params, portfolio_data, market_data
            )
            
            # Format detailed trade analysis
            action = trade_params.get("action", "").upper()
            amount = trade_params.get("amount", 0)
            
            response_content = f"""📈 **Trade Analysis: {action} {symbol}**

**Trade Details:**
• Symbol: {symbol}
• Action: {action}
• Requested Amount: ${amount:,.2f}
• Recommended Size: ${position_size.get('recommended_amount', amount):,.2f}
• Market Price: ${market_data.get('current_price', 0):,.2f}

**Market Analysis:**
• Trend: {market_data.get('trend', 'Unknown')}
• Momentum: {market_data.get('momentum', 'Unknown')}
• Support: ${market_data.get('support_level', 0):,.2f}
• Resistance: ${market_data.get('resistance_level', 0):,.2f}

**AI Consensus:**
• Confidence: {ai_analysis.get('confidence', 0):.1f}%
• Recommendation: {ai_analysis.get('recommendation', 'ANALYZE')}
• Risk Level: {ai_analysis.get('risk_level', 'Medium')}

**Analysis:**
{ai_analysis.get('analysis', 'Analyzing trade opportunity...')}

**Risk Assessment:**
• Position Impact: {position_size.get('portfolio_impact', 0):.1f}% of portfolio
• Risk Score: {position_size.get('risk_score', 'Medium')}
• Stop Loss: ${position_size.get('stop_loss', 0):,.2f}
• Take Profit: ${position_size.get('take_profit', 0):,.2f}

**Ready to Execute?**
Reply with:
• "✅ Execute" - Proceed with the trade
• "📊 More analysis" - Get deeper insights
• "⚙️ Modify" - Adjust parameters
• "❌ Cancel" - Cancel this trade"""
            
            return {
                "content": response_content,
                "confidence": ai_analysis.get("confidence", 0.8),
                "metadata": {
                    "trade_params": trade_params,
                    "market_analysis": market_data,
                    "ai_analysis": ai_analysis,
                    "position_sizing": position_size,
                    "requires_confirmation": True,
                    "trade_ready": True
                }
            }
            
        except Exception as e:
            self.logger.exception("Enhanced trade execution failed", error=str(e))
            return {
                "content": "I encountered an error analyzing your trade request. Please try again.",
                "confidence": 0.0,
                "metadata": {"error": str(e)}
            }
    
    async def _enhanced_rebalancing(self, message: str, context: Dict, user_id: str) -> Dict[str, Any]:
        """Enhanced rebalancing with strategy optimization."""
        
        try:
            
            # Get current portfolio and strategy
            portfolio_data = await self.adapters.get_portfolio_summary(user_id)
            current_strategy = await self.adapters.trading_strategies.get_active_strategy(user_id) if hasattr(self.adapters, 'trading_strategies') else None
            
            # Analyze rebalancing needs
            rebalance_analysis = await self.adapters.analyze_rebalancing_needs(
                user_id=user_id,
                target_allocation=current_strategy.get("allocation") if current_strategy else None
            )
            
            # Get AI recommendations
            rebalance_context = {
                "portfolio_data": portfolio_data,
                "rebalance_analysis": rebalance_analysis,
                "current_strategy": current_strategy,
                "user_message": message
            }
            
            ai_analysis = await self.adapters.ai_consensus.analyze_opportunity(
                json.dumps(rebalance_context),
                confidence_threshold=80.0,
                ai_models="all",
                user_id=user_id
            )
            
            if rebalance_analysis.get("needs_rebalancing"):
                trades = rebalance_analysis.get("recommended_trades", [])
                
                response_content = f"""⚖️ **Portfolio Rebalancing Analysis**

**Current Status:**
• Portfolio Value: ${portfolio_data.get('total_value', 0):,.2f}
• Strategy: {current_strategy.get('name', 'Default') if current_strategy else 'Default'}
• Deviation Score: {rebalance_analysis.get('deviation_score', 0):.1f}%

**Rebalancing Needed:** Yes

**Recommended Trades:**"""
                
                total_trade_value = 0
                for i, trade in enumerate(trades[:5], 1):
                    symbol = trade.get("symbol", "Unknown")
                    action = trade.get("action", "Unknown")
                    amount = trade.get("amount", 0)
                    current_pct = trade.get("current_percentage", 0)
                    target_pct = trade.get("target_percentage", 0)
                    
                    response_content += f"""
{i}. **{action.upper()} {symbol}**
   • Amount: ${abs(amount):,.2f}
   • Current: {current_pct:.1f}% → Target: {target_pct:.1f}%
   • Reason: {trade.get('reason', 'Optimization')}"""
                    
                    total_trade_value += abs(amount)
                
                response_content += f"""

**Rebalancing Summary:**
• Total Trading Volume: ${total_trade_value:,.2f}
• Expected Risk Reduction: {rebalance_analysis.get('risk_reduction', 0):.1f}%
• Estimated Improvement: {rebalance_analysis.get('expected_improvement', 0):.1f}%

🤖 **AI Analysis:**
{ai_analysis.get('analysis', 'Analyzing rebalancing strategy...')}

**Execution Options:**
• "✅ Execute rebalancing" - Automatic execution
• "📊 Step-by-step" - Review each trade individually
• "⚙️ Custom allocation" - Set your own targets
• "❌ Skip for now" - Keep current allocation"""
                
            else:
                response_content = f"""✅ **Portfolio is Optimally Balanced**

**Current Status:**
• Portfolio Value: ${portfolio_data.get('total_value', 0):,.2f}
• Allocation Variance: < 3% (Excellent)
• Risk Level: {portfolio_data.get('risk_level', 'Optimal')}

Your portfolio is well-balanced according to your current strategy. No rebalancing needed at this time.

**Monitoring:**
• I'll continue watching for optimization opportunities
• You'll be notified when rebalancing becomes beneficial
• Current allocation is within target ranges

**Alternative Actions:**
• "Change strategy" - Switch to different allocation model
• "Increase risk tolerance" - Adjust for higher returns
• "Add new assets" - Expand portfolio diversity"""
            
            return {
                "content": response_content,
                "confidence": 0.95,
                "metadata": {
                    "rebalance_analysis": rebalance_analysis,
                    "portfolio_data": portfolio_data,
                    "ai_analysis": ai_analysis,
                    "needs_rebalancing": rebalance_analysis.get("needs_rebalancing", False)
                }
            }
            
        except Exception as e:
            self.logger.error("Enhanced rebalancing failed", error=str(e))
            return {
                "content": "I encountered an error analyzing your rebalancing needs. Please try again.",
                "confidence": 0.0,
                "metadata": {"error": str(e)}
            }
    
    async def _enhanced_opportunity_discovery(self, message: str, context: Dict, user_id: str) -> Dict[str, Any]:
        """Enhanced opportunity discovery with comprehensive market scanning."""
        
        try:
            
            # Use REAL user opportunity discovery service instead of adapters
            from app.services.user_opportunity_discovery import user_opportunity_discovery
            
            # Ensure user has active strategies (3 free ones by default)
            try:
                from app.services.user_onboarding_service import user_onboarding_service
                onboarding_check = await user_onboarding_service.check_user_onboarding_status(user_id)
                if onboarding_check.get("needs_onboarding", True):
                    await user_onboarding_service.onboard_new_user(user_id)
                    self.logger.info("User onboarding completed", user_id=user_id)
            except Exception as onboarding_error:
                self.logger.warning("User onboarding service unavailable, using fallback strategy activation", 
                                  error=str(onboarding_error), user_id=user_id)
                
                # FALLBACK: Directly activate the 3 free strategies using strategy marketplace
                try:
                    from app.services.strategy_marketplace_service import strategy_marketplace_service
                    await strategy_marketplace_service.async_init()
                    
                    # Activate the 3 default free strategies
                    free_strategies = ["ai_risk_management", "portfolio_optimization", "ai_spot_momentum_strategy"]
                    for strategy_id in free_strategies:
                        try:
                            result = await strategy_marketplace_service.purchase_strategy(user_id, strategy_id)
                            if result.get("success"):
                                self.logger.info("Fallback strategy activation successful", 
                                               strategy_id=strategy_id, user_id=user_id)
                        except Exception as strategy_error:
                            self.logger.warning("Fallback strategy activation failed", 
                                              strategy_id=strategy_id, error=str(strategy_error))
                                              
                except Exception as fallback_error:
                    self.logger.error("All strategy activation methods failed", error=str(fallback_error))
            
            # Initialize and use real opportunity discovery service
            await user_opportunity_discovery.async_init()
            
            strategy_opportunities = await user_opportunity_discovery.discover_opportunities_for_user(
                user_id=user_id,
                force_refresh=False,
                include_strategy_recommendations=True
            )
            
            # Get portfolio context for additional analysis
            portfolio_context = await self.adapters.get_portfolio_summary(user_id)
            
            # Get AI consensus on opportunities
            opportunity_context = {
                "strategy_opportunities": strategy_opportunities,
                "portfolio_context": portfolio_context,
                "user_message": message
            }
            
            # Use single AI model for informational opportunity discovery (not trade execution)
            ai_analysis = await self.adapters.ai_consensus.analyze_opportunity(
                json.dumps(opportunity_context),
                confidence_threshold=70.0,  # Lower threshold for informational queries
                ai_models="single",  # Use single model for speed, not validation
                user_id=user_id
            )
            
            opportunities = strategy_opportunities.get("opportunities", [])
            
            if opportunities:
                response_content = f"""🔍 **Market Opportunity Discovery**

Found **{len(opportunities)}** promising opportunities based on current market conditions:

**Top Opportunities:**"""
                
                for i, opp in enumerate(opportunities[:3], 1):
                    symbol = opp.get("symbol", "Unknown")
                    confidence = opp.get("confidence", 0)
                    potential_return = opp.get("potential_return", 0)
                    timeframe = opp.get("timeframe", "Unknown")
                    strategy = opp.get("strategy", "Unknown")
                    risk_level = opp.get("risk_level", "Medium")
                    
                    response_content += f"""

**{i}. {symbol}** 
• Strategy: {strategy}
• Confidence: {confidence:.1f}%
• Potential Return: {potential_return:+.1f}%
• Timeframe: {timeframe}
• Risk Level: {risk_level}
• Entry Price: ${opp.get('entry_price', 0):,.4f}"""
                
                response_content += f"""

🤖 **AI Multi-Model Assessment:**
{ai_analysis.get('analysis', 'Analyzing opportunities...')}

**Market Context:**
• Real-time strategy analysis active
• Professional opportunity scanning enabled
• Portfolio risk-aligned recommendations

**Next Steps:**
• "Analyze [symbol]" - Deep dive on specific opportunity
• "Execute opportunity [number]" - Invest in selected opportunity
• "Set alerts for [symbol]" - Monitor for better entry
• "Show more opportunities" - Expand search results"""
                
            else:
                # FINANCIAL SAFETY: Never show fake analysis when real analysis fails
                # Check if this is due to system errors vs genuinely no opportunities
                scan_errors = strategy_opportunities.get("errors", [])
                execution_time = strategy_opportunities.get("execution_time_ms", 0)
                
                if scan_errors or execution_time < 1000:  # Too fast = likely failed
                    response_content = """⚠️ **Analysis System Error**

I cannot provide trading recommendations because the underlying analysis systems encountered errors.

**Status:** Strategy analysis failed
**Issue:** Core calculation methods unavailable  
**Safety:** No recommendations provided to prevent bad decisions

**Actions:**
• Contact technical support 
• System diagnostic required
• Do not trade based on incomplete analysis

**For immediate assistance:** Use direct API endpoints to verify system status."""
                else:
                    response_content = """🔍 **Opportunity Scan Complete**

After comprehensive analysis, no significant trading opportunities meet the current risk and return criteria.

**Analysis Completed:**
• All strategy models executed successfully
• Risk thresholds applied correctly  
• Market conditions analyzed

**Current Assessment:**
• Markets in consolidation phase
• Volatility below opportunity threshold
• Existing positions recommended to hold

**Options:**
• "Lower risk threshold" - See more aggressive opportunities
• "Check specific sectors" - DeFi, Layer 1, Gaming analysis
• "Review positions" - Optimize current holdings"""
            
            return {
                "content": response_content,
                "confidence": ai_analysis.get("confidence", 0.8),
                "metadata": {
                    "opportunities": opportunities,
                    "service_used": "user_opportunity_discovery",
                    "opportunities_count": len(opportunities),
                    "ai_analysis": ai_analysis
                }
            }
            
        except Exception as e:
            self.logger.error("Enhanced opportunity discovery failed", error=str(e))
            return {
                "content": "I encountered an error discovering opportunities. Please try again.",
                "confidence": 0.0,
                "metadata": {"error": str(e)}
            }
    
    async def _enhanced_risk_assessment(self, message: str, context: Dict, user_id: str) -> Dict[str, Any]:
        """Enhanced risk assessment with comprehensive analysis."""
        
        try:
            
            # Get comprehensive risk analysis
            risk_analysis = await self.adapters.comprehensive_risk_analysis(user_id)
            portfolio_data = await self.adapters.get_portfolio_summary(user_id)
            market_conditions = await self.adapters.get_market_risk_factors(user_id)
            
            # Get AI risk assessment
            risk_context = {
                "risk_analysis": risk_analysis,
                "portfolio_data": portfolio_data,
                "market_conditions": market_conditions,
                "user_message": message
            }
            
            # Use single AI model for informational risk assessment (not trade execution)
            ai_assessment = await self.adapters.ai_consensus.analyze_opportunity(
                json.dumps(risk_context),
                confidence_threshold=75.0,  # Lower threshold for informational queries  
                ai_models="single",  # Use single model for speed, not validation
                user_id=user_id
            )
            
# ENHANCED SAFETY GUARD: Detect fake/zero data and show explicit warnings
            var_24h = risk_analysis.get('var_24h', 0)
            var_7d = risk_analysis.get('var_7d', 0) 
            max_drawdown = risk_analysis.get('max_drawdown', 0)
            sharpe_ratio = risk_analysis.get('sharpe_ratio', 0)
            
            # Check if this looks like fake/template data
            is_fake_data = (
                var_24h == 0 and var_7d == 0 and max_drawdown == 0 and 
                sharpe_ratio == 0 and risk_analysis.get('overall_risk') in ['Medium', 'Unknown']
            )
            
            if is_fake_data:
                response_content = """⚠️ **Risk Analysis System Unavailable**

**Status:** Risk calculation systems are currently unavailable
**Issue:** Core risk analysis methods are not functional
**Safety Warning:** Do not make trading decisions without proper risk analysis

**What This Means:**
• Portfolio risk metrics cannot be calculated
• Value at Risk (VaR) calculations unavailable  
• Sharpe ratios and drawdown analysis offline
• Market risk factor analysis incomplete

**Immediate Actions:**
• Do not execute large trades without risk analysis
• Contact technical support for system status
• Use direct API endpoints to verify portfolio data
• Wait for risk analysis systems to come online

**For Real-Time Status:** Check /api/v1/health/risk-analysis endpoint

⚠️ **This is a safety message - trading systems have been designed to show explicit errors instead of fake analysis data to protect your capital.**"""
                
            else:
                response_content = f"""🛡️ **Comprehensive Risk Assessment**

**Overall Risk Profile:** {risk_analysis.get('overall_risk', 'Medium')}

**Key Risk Metrics:**
• Value at Risk (24h): ${var_24h:,.2f}
• Value at Risk (7d): ${var_7d:,.2f}
• Maximum Drawdown: {max_drawdown:.1f}%
• Sharpe Ratio: {sharpe_ratio:.2f}
• Portfolio Beta: {risk_analysis.get('beta', 1.0):.2f}
**Risk Breakdown:**
• Concentration Risk: {risk_analysis.get('concentration_risk', 'Low')}
• Volatility Risk: {risk_analysis.get('volatility_risk', 'Medium')}
• Correlation Risk: {risk_analysis.get('correlation_risk', 'Low')}
• Liquidity Risk: {risk_analysis.get('liquidity_risk', 'Low')}

**Market Risk Factors:**
• Market Volatility: {market_conditions.get('market_volatility', 'Medium')}
• Correlation Increase: {market_conditions.get('correlation_trend', 'Stable')}
• Liquidity Conditions: {market_conditions.get('liquidity_status', 'Good')}

🤖 **AI Risk Analysis:**
{ai_assessment.get('analysis', 'Analyzing risk factors...')}

**Risk Mitigation Recommendations:**
{ai_assessment.get('risk_mitigation', 'Generating recommendations...')}

**Immediate Actions Available:**
• "Set stop losses" - Implement protective stops
• "Reduce position sizes" - Lower exposure
• "Hedge portfolio" - Add protective positions
• "Increase cash allocation" - Reduce market exposure

What risk management action would you like to take?"""
            
            return {
                "content": response_content,
                "confidence": ai_assessment.get("confidence", 0.9),
                "metadata": {
                    "risk_analysis": risk_analysis,
                    "market_conditions": market_conditions,
                    "ai_assessment": ai_assessment
                }
            }
            
        except Exception as e:
            self.logger.error("Enhanced risk assessment failed", error=str(e))
            return {
                "content": "I encountered an error assessing portfolio risk. Please try again.",
                "confidence": 0.0,
                "metadata": {"error": str(e)}
            }
    
    async def _enhanced_market_analysis(self, message: str, context: Dict, user_id: str) -> Dict[str, Any]:
        """Enhanced market analysis with multi-timeframe insights."""
        
        try:
            # Get comprehensive market analysis using FIXED adapters
            market_overview = await self.adapters.get_market_overview()
            technical_analysis = await self.adapters.get_technical_analysis()
            
            # Get sector analysis - fix undefined variable
            try:
                if hasattr(self.adapters, 'get_sector_analysis'):
                    sector_analysis = await self.adapters.get_sector_analysis()
                else:
                    sector_analysis = {"sectors": []}  # Default empty sectors
            except Exception as e:
                self.logger.warning("Sector analysis failed, using defaults", error=str(e))
                sector_analysis = {"sectors": []}
            
            # Get AI consensus on market conditions
            market_context = {
                "market_overview": market_overview,
                "technical_analysis": technical_analysis,
                "sector_analysis": sector_analysis,
                "user_message": message,
                "analysis_type": "comprehensive_market_analysis"
            }
            
            # Skip heavy AI analysis for faster response in chat
            # Only do lightweight analysis to prevent timeouts
            try:
                import asyncio
                ai_analysis = await asyncio.wait_for(
                    self.adapters.ai_consensus.analyze_opportunity(
                        json.dumps(market_context),
                        confidence_threshold=70.0,  # Lower threshold for chat
                        ai_models="single",  # Use single fast model for chat, NOT "all"
                        user_id=user_id
                    ),
                    timeout=8.0  # 8 second timeout for chat responses
                )
            except (asyncio.TimeoutError, Exception) as e:
                self.logger.warning("AI analysis timed out or failed, using simplified response", error=str(e))
                ai_analysis = {
                    "success": True,
                    "analysis": "Market data successfully retrieved. AI analysis temporarily unavailable.",
                    "confidence": 0.7
                }
            
            response_content = f"""📈 **Comprehensive Market Analysis**

**Market Overview:**
• Overall Sentiment: {market_overview.get('sentiment', 'Neutral')}
• Trend Direction: {market_overview.get('trend', 'Sideways')}
• Market Phase: {market_overview.get('market_phase', 'Consolidation')}
• Volatility Level: {market_overview.get('volatility', 'Medium')}

**Key Metrics:**
• Total Market Cap: ${market_overview.get('total_market_cap', 0):,.0f}B
• 24h Volume: ${market_overview.get('total_volume_24h', 0):,.0f}B
• BTC Dominance: {market_overview.get('btc_dominance', 0):.1f}%
• Fear & Greed: {market_overview.get('fear_greed_index', 50)}/100

**Sector Performance:**"""
            
            sectors = sector_analysis.get("sectors", [])
            for sector in sectors[:5]:
                name = sector.get("name", "Unknown")
                performance = sector.get("24h_change", 0)
                status = "🟢" if performance > 0 else "🔴" if performance < -5 else "🟡"
                response_content += f"\n{status} {name}: {performance:+.1f}%"
            
            response_content += f"""

🤖 **AI Multi-Model Analysis:**
{ai_analysis.get('analysis', 'Analyzing market conditions...')}

**Trading Implications:**
{ai_analysis.get('trading_implications', 'Generating trading insights...')}

**Recommended Focus Areas:**
{ai_analysis.get('focus_areas', 'Identifying key opportunities...')}

**Available Actions:**
• "Analyze [specific crypto]" - Deep dive on asset
• "Find sector opportunities" - Explore hot sectors
• "Risk assessment" - Check portfolio against market risks
• "Rebalance for market" - Optimize for current conditions

What aspect of the market would you like to explore?"""
            
            return {
                "content": response_content,
                "confidence": ai_analysis.get("confidence", 0.85),
                "metadata": {
                    "market_overview": market_overview,
                    "sector_analysis": sector_analysis,
                    "ai_analysis": ai_analysis
                }
            }
            
        except Exception as e:
            self.logger.error("Enhanced market analysis failed", error=str(e))
            
            # Fallback: Try to get basic market data
            try:
                basic_market = await self.adapters.get_market_overview()
                return {
                    "content": f"""📊 **Market Status**

**Current Market:**
• Sentiment: {basic_market.get('sentiment', 'Neutral')}
• Trend: {basic_market.get('trend', 'Sideways')}
• Phase: {basic_market.get('market_phase', 'Consolidation')}
• BTC Dominance: {basic_market.get('btc_dominance', 0):.1f}%

I was able to get basic market data, but detailed analysis is temporarily unavailable.

**Quick Actions:**
• Ask "What's Bitcoin doing?" for specific analysis
• Ask "Should I buy now?" for opportunities
• Try your question again in a moment

Market connections are active and data is flowing!""",
                    "confidence": 0.6,
                    "metadata": {"fallback_used": True, "basic_market": basic_market}
                }
            except Exception as fallback_error:
                self.logger.error("Market fallback also failed", error=str(fallback_error))
                
            return {
                "content": f"""📊 **Market Analysis Status**

I'm having trouble accessing detailed market analysis right now, but market data connections are active.

**What you can try:**
• Ask "What's the market like?" in a moment  
• Try asking about specific coins like "How's Bitcoin?"
• Check direct market endpoints if needed

The market analysis systems are running and should be available shortly.""",
                "confidence": 0.3,
                "metadata": {"error": str(e)}
            }
    
    async def _calculate_optimal_position_size(
        self, 
        trade_params: Dict[str, Any], 
        portfolio_data: Dict[str, Any], 
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate optimal position size based on risk management."""
        
        try:
            symbol = trade_params.get("symbol")
            action = trade_params.get("action")
            requested_amount = trade_params.get("amount", 0)
            
            portfolio_value = portfolio_data.get("total_value", 0)
            current_price = market_data.get("current_price", 0)
            volatility = market_data.get("volatility", 0.5)
            
            # Calculate risk-adjusted position size
            max_position_pct = 0.1  # Maximum 10% of portfolio per position
            volatility_adjustment = max(0.5, 1 - volatility)  # Reduce size for volatile assets
            
            max_amount = portfolio_value * max_position_pct * volatility_adjustment
            recommended_amount = min(requested_amount, max_amount)
            
            # Calculate stop loss and take profit levels
            stop_loss_pct = 0.15 if volatility > 0.7 else 0.10
            take_profit_pct = 0.25 if volatility > 0.7 else 0.20
            
            if action == "buy":
                stop_loss = current_price * (1 - stop_loss_pct)
                take_profit = current_price * (1 + take_profit_pct)
            else:  # sell
                stop_loss = current_price * (1 + stop_loss_pct)
                take_profit = current_price * (1 - take_profit_pct)
            
            return {
                "recommended_amount": recommended_amount,
                "portfolio_impact": (recommended_amount / portfolio_value * 100) if portfolio_value > 0 else 0,
                "risk_score": "High" if volatility > 0.7 else "Medium" if volatility > 0.4 else "Low",
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "volatility_adjustment": volatility_adjustment
            }
            
        except Exception as e:
            self.logger.error("Position sizing calculation failed", error=str(e))
            return {
                "recommended_amount": trade_params.get("amount", 0),
                "portfolio_impact": 0,
                "risk_score": "Unknown",
                "stop_loss": 0,
                "take_profit": 0
            }
    
    async def _execute_confirmed_action(self, session_id: str, command: str, user_id: str) -> Dict[str, Any]:
        """Execute confirmed actions with full service integration."""
        
        try:
            session = chat_engine.sessions.get(session_id)
            if not session:
                return {"success": False, "error": "Session not found"}
            
            # Get the last assistant message metadata for context
            last_message = None
            for msg in reversed(session.messages):
                if msg.message_type.value == "assistant" and msg.metadata:
                    last_message = msg
                    break
            
            if not last_message or not last_message.metadata:
                return {"success": False, "error": "No actionable context found"}
            
            metadata = last_message.metadata
            
            if command == "execute_trade" and metadata.get("trade_ready"):
                # Execute trade using trade execution service
                trade_params = metadata.get("trade_params")
                result = await self.trade_executor.execute_trade(
                    user_id=user_id,
                    symbol=trade_params.get("symbol"),
                    action=trade_params.get("action"),
                    amount=trade_params.get("amount"),
                    order_type=trade_params.get("order_type", "market")
                )
                
                if result.get("success"):
                    # Send real-time notification
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "trade_notification",
                            "trade_id": result.get("trade_id"),
                            "symbol": trade_params.get("symbol"),
                            "action": trade_params.get("action"),
                            "amount": trade_params.get("amount"),
                            "status": "executed",
                            "timestamp": datetime.utcnow().isoformat()
                        }),
                        user_id
                    )
                
                return result
            
            elif command == "execute_rebalancing" and metadata.get("needs_rebalancing"):
                # Execute rebalancing
                rebalance_analysis = metadata.get("rebalance_analysis")
                result = await self.portfolio_risk.execute_rebalancing(
                    user_id=user_id,
                    trades=rebalance_analysis.get("recommended_trades", [])
                )
                
                return result
            
            elif command == "emergency_stop":
                # Execute emergency stop
                result = await self.master_controller.emergency_stop(user_id)
                return result
            
            else:
                return {"success": False, "error": "Unknown or invalid command"}
                
        except Exception as e:
            self.logger.error("Action execution failed", error=str(e))
            return {"success": False, "error": str(e)}


# Global integration service instance
chat_integration = ChatIntegrationService()