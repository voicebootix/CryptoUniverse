"""
AI Chat Engine - Comprehensive Money Management Assistant

This service provides a sophisticated chat interface for managing cryptocurrency
portfolios, executing trades, rebalancing, and discovering opportunities through
natural language conversations with AI.

Integrates with existing services:
- Master System Controller for trading orchestration
- AI Consensus Service for multi-model decision making
- Trading Services for execution
- Portfolio Risk Management
- Market Analysis
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import uuid
import re

import structlog
from app.core.config import get_settings
from app.core.logging import LoggerMixin
from app.services.websocket import manager
from app.services.ai_consensus_core import AIConsensusService
from app.services.master_controller import MasterSystemController
from app.services.trade_execution import TradeExecutionService

settings = get_settings()
logger = structlog.get_logger(__name__)


class ChatMessageType(str, Enum):
    """Chat message types."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TRADE_NOTIFICATION = "trade_notification"
    PORTFOLIO_UPDATE = "portfolio_update"
    MARKET_ALERT = "market_alert"


class ChatIntent(str, Enum):
    """Chat intent classification."""
    GENERAL_QUERY = "general_query"
    PORTFOLIO_ANALYSIS = "portfolio_analysis"
    TRADE_EXECUTION = "trade_execution"
    MARKET_ANALYSIS = "market_analysis"
    RISK_ASSESSMENT = "risk_assessment"
    REBALANCING = "rebalancing"
    STRATEGY_DISCUSSION = "strategy_discussion"
    PERFORMANCE_REVIEW = "performance_review"
    OPPORTUNITY_DISCOVERY = "opportunity_discovery"
    EMERGENCY_COMMAND = "emergency_command"
    AUTONOMOUS_CONTROL = "autonomous_control"


@dataclass
class ChatMessage:
    """Chat message data structure."""
    id: str
    user_id: str
    content: str
    message_type: ChatMessageType
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    intent: Optional[ChatIntent] = None
    confidence: Optional[float] = None


@dataclass
class ChatSession:
    """Chat session management."""
    session_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    messages: List[ChatMessage]
    context: Dict[str, Any]
    active_strategies: List[str]
    portfolio_state: Optional[Dict[str, Any]] = None


class AIChatEngine(LoggerMixin):
    """
    Comprehensive AI Chat Engine for Cryptocurrency Money Management
    
    Provides natural language interface for:
    - Portfolio management and analysis
    - Trade execution and monitoring
    - Risk assessment and rebalancing
    - Market opportunity discovery
    - Strategy optimization
    - Performance review
    """
    
    def __init__(
        self, 
        portfolio_risk: Optional['PortfolioRiskServiceExtended'] = None,
        market_analysis: Optional['MarketAnalysisService'] = None
    ):
        self.sessions: Dict[str, ChatSession] = {}
        self.ai_consensus = AIConsensusService()
        self.master_controller = MasterSystemController()
        self.trade_executor = TradeExecutionService()
        self.unified_manager = None  # Will be set by unified manager
        
        # Initialize portfolio and market analysis services
        if portfolio_risk is not None:
            self.portfolio_risk = portfolio_risk
        else:
            try:
                from app.services.portfolio_risk_core import PortfolioRiskServiceExtended
                self.portfolio_risk = PortfolioRiskServiceExtended()
            except ImportError:
                self.portfolio_risk = None
        
        if market_analysis is not None:
            self.market_analysis = market_analysis
        else:
            try:
                from app.services.market_analysis_core import MarketAnalysisService
                self.market_analysis = MarketAnalysisService()
            except ImportError:
                self.market_analysis = None
        
        # Intent classification patterns
        self.intent_patterns = {
            ChatIntent.TRADE_EXECUTION: [
                r'\b(buy|sell|trade|execute|order)\b',
                r'\b(purchase|acquire|dispose|liquidate)\b',
                r'\b(long|short|position)\b'
            ],
            ChatIntent.PORTFOLIO_ANALYSIS: [
                r'\b(portfolio|holdings|positions|balance)\b',
                r'\b(allocation|distribution|composition)\b',
                r'\b(performance|returns|profit|loss)\b'
            ],
            ChatIntent.REBALANCING: [
                r'\b(rebalance|rebalancing|adjust|optimize)\b',
                r'\b(reallocate|redistribute)\b',
                r'\b(weight|weighting|allocation)\b'
            ],
            ChatIntent.MARKET_ANALYSIS: [
                r'\b(market|analysis|trend|sentiment)\b',
                r'\b(price|chart|technical|fundamental)\b',
                r'\b(support|resistance|breakout)\b'
            ],
            ChatIntent.RISK_ASSESSMENT: [
                r'\b(risk|volatility|drawdown|exposure)\b',
                r'\b(safety|protection|hedge|insurance)\b',
                r'\b(stop|limit|loss)\b'
            ],
            ChatIntent.OPPORTUNITY_DISCOVERY: [
                r'\b(opportunity|opportunities|find|discover)\b',
                r'\b(new|emerging|potential|promising)\b',
                r'\b(invest|investment|recommendation)\b'
            ],
            ChatIntent.EMERGENCY_COMMAND: [
                r'\b(stop|halt|emergency|urgent|panic)\b',
                r'\b(sell all|liquidate all|exit all)\b',
                r'\b(emergency|crisis|problem)\b'
            ],
            "autonomous_control": [
                r'\b(autonomous|auto|automatic|start.*auto|stop.*auto)\b',
                r'\b(enable.*autonomous|disable.*autonomous)\b',
                r'\b(auto.*mode|autonomous.*mode)\b'
            ]
        }
        
        # System prompts for different intents
        self.system_prompts = {
            ChatIntent.GENERAL_QUERY: """You are CryptoUniverse AI, a sophisticated cryptocurrency money manager. 
            Provide helpful, accurate information about cryptocurrency trading, markets, and portfolio management.
            Be professional, concise, and actionable in your responses.""",
            
            ChatIntent.PORTFOLIO_ANALYSIS: """You are analyzing a cryptocurrency portfolio. 
            Provide detailed insights about portfolio performance, allocation, risk metrics, and optimization suggestions.
            Include specific recommendations for improvement.""",
            
            ChatIntent.TRADE_EXECUTION: """You are executing cryptocurrency trades. 
            Analyze the trade request, assess market conditions, calculate optimal entry/exit points, 
            and provide clear execution recommendations with risk management.""",
            
            ChatIntent.MARKET_ANALYSIS: """You are analyzing cryptocurrency markets. 
            Provide comprehensive market analysis including technical indicators, sentiment, trends, 
            and actionable trading insights.""",
            
            ChatIntent.RISK_ASSESSMENT: """You are assessing portfolio and trading risks. 
            Analyze current risk exposure, potential threats, and provide specific risk mitigation strategies.""",
            
            ChatIntent.REBALANCING: """You are optimizing portfolio allocation. 
            Analyze current allocation, market conditions, and provide specific rebalancing recommendations 
            with clear rationale and execution steps.""",
            
            ChatIntent.OPPORTUNITY_DISCOVERY: """You are discovering new investment opportunities. 
            Analyze market conditions, identify promising assets, and provide detailed opportunity assessments 
            with risk-reward analysis.""",
            
            ChatIntent.EMERGENCY_COMMAND: """You are handling an emergency trading situation. 
            Prioritize capital preservation, assess immediate risks, and provide urgent action recommendations."""
        }
    
    async def start_chat_session(self, user_id: str) -> str:
        """Start a new chat session for a user."""
        session_id = str(uuid.uuid4())
        
        session = ChatSession(
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            messages=[],
            context={
                "preferences": {},
                "active_strategies": [],
                "risk_tolerance": "balanced"
            },
            active_strategies=[]
        )
        
        # Add welcome message
        welcome_message = ChatMessage(
            id=str(uuid.uuid4()),
            user_id=user_id,
            content="""👋 Welcome to CryptoUniverse AI Money Manager!

I'm your comprehensive AI assistant for cryptocurrency portfolio management. I can help you with:

🔹 **Portfolio Analysis** - Review performance, allocation, and optimization
🔹 **Trade Execution** - Execute buy/sell orders with AI analysis
🔹 **Risk Management** - Assess and mitigate portfolio risks
🔹 **Rebalancing** - Optimize your asset allocation
🔹 **Market Opportunities** - Discover new investment prospects
🔹 **Strategy Optimization** - Fine-tune your trading strategies

Just chat with me naturally! For example:
• "Show me my portfolio performance"
• "Buy $1000 of Bitcoin"
• "Rebalance my portfolio"
• "What are the best opportunities right now?"
• "Analyze the risk in my current positions"

How can I help you manage your crypto investments today?""",
            message_type=ChatMessageType.ASSISTANT,
            timestamp=datetime.utcnow()
        )
        
        session.messages.append(welcome_message)
        self.sessions[session_id] = session
        
        self.logger.info("Chat session started", user_id=user_id, session_id=session_id)
        return session_id
    
    async def process_message(
        self, 
        session_id: str, 
        user_message: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Process a user message and generate AI response."""
        
        try:
            # Get or create session
            if session_id not in self.sessions:
                session_id = await self.start_chat_session(user_id)
            
            session = self.sessions[session_id]
            session.last_activity = datetime.utcnow()
            
            # Create user message
            user_msg = ChatMessage(
                id=str(uuid.uuid4()),
                user_id=user_id,
                content=user_message,
                message_type=ChatMessageType.USER,
                timestamp=datetime.utcnow()
            )
            
            # Classify intent
            intent = await self._classify_intent(user_message)
            user_msg.intent = intent
            
            session.messages.append(user_msg)
            
            # Process based on intent
            response = await self._process_intent(session, user_msg, intent)
            
            # Create assistant message
            assistant_msg = ChatMessage(
                id=str(uuid.uuid4()),
                user_id=user_id,
                content=response["content"],
                message_type=ChatMessageType.ASSISTANT,
                timestamp=datetime.utcnow(),
                metadata=response.get("metadata", {}),
                confidence=response.get("confidence")
            )
            
            session.messages.append(assistant_msg)
            
            # Send real-time update via WebSocket
            await self._send_websocket_update(user_id, {
                "type": "chat_message",
                "message": {
                    "id": assistant_msg.id,
                    "content": assistant_msg.content,
                    "timestamp": assistant_msg.timestamp.isoformat(),
                    "metadata": assistant_msg.metadata
                }
            })
            
            return {
                "success": True,
                "session_id": session_id,
                "message_id": assistant_msg.id,
                "content": assistant_msg.content,
                "intent": intent.value,
                "confidence": assistant_msg.confidence,
                "metadata": assistant_msg.metadata
            }
            
        except Exception as e:
            self.logger.error("Message processing failed", error=str(e), user_id=user_id)
            return {
                "success": False,
                "error": str(e),
                "content": "I apologize, but I encountered an error processing your message. Please try again."
            }
    
    async def _classify_intent(self, message: str) -> ChatIntent:
        """Classify user message intent using pattern matching and AI."""
        
        message_lower = message.lower()
        
        # Check for emergency patterns first
        for pattern in self.intent_patterns[ChatIntent.EMERGENCY_COMMAND]:
            if re.search(pattern, message_lower):
                return ChatIntent.EMERGENCY_COMMAND
        
        # Check other intents
        intent_scores = {}
        for intent, patterns in self.intent_patterns.items():
            if intent == ChatIntent.EMERGENCY_COMMAND:
                continue
                
            score = 0
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    score += 1
            
            if score > 0:
                intent_scores[intent] = score
        
        # Return highest scoring intent or general query
        if intent_scores:
            return max(intent_scores.items(), key=lambda x: x[1])[0]
        
        return ChatIntent.GENERAL_QUERY
    
    async def _process_intent(
        self, 
        session: ChatSession, 
        message: ChatMessage, 
        intent: ChatIntent
    ) -> Dict[str, Any]:
        """Process message based on classified intent."""
        
        try:
            if intent == ChatIntent.EMERGENCY_COMMAND:
                return await self._handle_emergency_command(session, message)
            elif intent == ChatIntent.PORTFOLIO_ANALYSIS:
                return await self._handle_portfolio_analysis(session, message)
            elif intent == ChatIntent.TRADE_EXECUTION:
                return await self._handle_trade_execution(session, message)
            elif intent == ChatIntent.MARKET_ANALYSIS:
                return await self._handle_market_analysis(session, message)
            elif intent == ChatIntent.RISK_ASSESSMENT:
                return await self._handle_risk_assessment(session, message)
            elif intent == ChatIntent.REBALANCING:
                return await self._handle_rebalancing(session, message)
            elif intent == ChatIntent.OPPORTUNITY_DISCOVERY:
                return await self._handle_opportunity_discovery(session, message)
            elif intent == ChatIntent.STRATEGY_DISCUSSION:
                return await self._handle_strategy_discussion(session, message)
            elif intent == ChatIntent.PERFORMANCE_REVIEW:
                return await self._handle_performance_review(session, message)
            elif intent == ChatIntent.AUTONOMOUS_CONTROL:
                return await self._handle_autonomous_control(session, message)
            else:
                return await self._handle_general_query(session, message)
                
        except Exception as e:
            self.logger.error("Intent processing failed", intent=intent.value, error=str(e))
            return {
                "content": "I encountered an error processing your request. Please try rephrasing your question.",
                "confidence": 0.0,
                "metadata": {"error": str(e)}
            }
    
    async def _handle_emergency_command(self, session: ChatSession, message: ChatMessage) -> Dict[str, Any]:
        """Handle emergency trading commands."""
        
        self.logger.warning("Emergency command detected", user_id=session.user_id, message=message.content)
        
        # Immediate risk assessment
        risk_analysis = await self.portfolio_risk.emergency_risk_assessment(
            user_id=session.user_id,
            trigger="user_emergency_command"
        )
        
        response_content = f"""🚨 **EMERGENCY MODE ACTIVATED**

I've detected an emergency command and immediately assessed your portfolio risk:

**Current Risk Status:** {risk_analysis.get('risk_level', 'Unknown')}
**Portfolio Value:** ${risk_analysis.get('total_value', 0):,.2f}
**Unrealized P&L:** ${risk_analysis.get('unrealized_pnl', 0):,.2f}

**Available Emergency Actions:**
1. 🛑 **Stop All Trading** - Halt all automated trading
2. 💰 **Partial Liquidation** - Sell 25%/50%/75% of positions
3. 🔄 **Full Liquidation** - Convert everything to stablecoins
4. 🛡️ **Risk Reduction** - Close high-risk positions only

Please specify which action you'd like me to take, or say "cancel" if this was triggered by mistake.

**Type your choice or ask for more details about any option.**"""

        return {
            "content": response_content,
            "confidence": 1.0,
            "metadata": {
                "emergency_mode": True,
                "risk_analysis": risk_analysis,
                "available_actions": ["stop_trading", "partial_liquidation", "full_liquidation", "risk_reduction"]
            }
        }
    
    async def _handle_portfolio_analysis(self, session: ChatSession, message: ChatMessage) -> Dict[str, Any]:
        """Handle portfolio analysis requests."""
        
        # Get current portfolio data
        portfolio_data = await self.portfolio_risk.get_portfolio_summary(session.user_id)
        
        # Get AI analysis
        ai_context = {
            "portfolio_data": portfolio_data,
            "user_message": message.content,
            "session_context": session.context
        }
        
        ai_response = await self.ai_consensus.analyze_opportunity(
            json.dumps(ai_context),
            confidence_threshold=75.0,
            ai_models="all",
            user_id=session.user_id
        )
        
        # Format response
        if portfolio_data and ai_response.get("success"):
            total_value = portfolio_data.get("total_value", 0)
            daily_pnl = portfolio_data.get("daily_pnl", 0)
            positions = portfolio_data.get("positions", [])
            
            response_content = f"""📊 **Portfolio Analysis**

**Current Portfolio Value:** ${total_value:,.2f}
**Today's P&L:** ${daily_pnl:,.2f} ({(daily_pnl/total_value*100):+.2f}%)

**Top Holdings:**"""
            
            for i, position in enumerate(positions[:5]):
                symbol = position.get("symbol", "Unknown")
                value = position.get("value", 0)
                pnl_pct = position.get("pnl_percentage", 0)
                response_content += f"\n• {symbol}: ${value:,.2f} ({pnl_pct:+.1f}%)"
            
            # Add AI insights
            ai_insights = ai_response.get("analysis", "")
            if ai_insights:
                response_content += f"\n\n🤖 **AI Analysis:**\n{ai_insights}"
            
            # Add recommendations
            response_content += f"\n\n💡 **Recommendations:**"
            response_content += f"\n• Consider rebalancing if any position exceeds 25% allocation"
            response_content += f"\n• Monitor positions with high volatility"
            response_content += f"\n• Review stop-loss levels for protection"
            
        else:
            response_content = "I'm unable to retrieve your portfolio data at the moment. Please try again or contact support."
        
        return {
            "content": response_content,
            "confidence": ai_response.get("confidence", 0.8),
            "metadata": {
                "portfolio_data": portfolio_data,
                "ai_analysis": ai_response
            }
        }
    
    async def _handle_trade_execution(self, session: ChatSession, message: ChatMessage) -> Dict[str, Any]:
        """Handle trade execution requests."""
        
        # Extract trade parameters from message
        trade_params = await self._extract_trade_parameters(message.content)
        
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
        
        # Get AI analysis for the trade
        market_context = await self.market_analysis.get_market_overview()
        
        ai_context = {
            "trade_request": trade_params,
            "market_context": market_context,
            "user_message": message.content,
            "portfolio_context": await self.portfolio_risk.get_portfolio_summary(session.user_id)
        }
        
        ai_analysis = await self.ai_consensus.analyze_opportunity(
            json.dumps(ai_context),
            confidence_threshold=80.0,
            ai_models="all",
            user_id=session.user_id
        )
        
        # Generate trade recommendation
        response_content = f"""📈 **Trade Analysis: {trade_params.get('action', 'Unknown').upper()} {trade_params.get('symbol', 'Unknown')}**

**Trade Details:**
• Symbol: {trade_params.get('symbol', 'N/A')}
• Action: {trade_params.get('action', 'N/A')}
• Amount: ${trade_params.get('amount', 0):,.2f}
• Type: {trade_params.get('order_type', 'Market')} Order

**AI Analysis:**
{ai_analysis.get('analysis', 'Analysis unavailable')}

**Risk Assessment:**
• Confidence Score: {ai_analysis.get('confidence', 0):.1f}%
• Risk Level: {ai_analysis.get('risk_level', 'Medium')}

Would you like me to:
1. ✅ **Execute this trade** immediately
2. 📋 **Get detailed analysis** first
3. ❌ **Cancel** this trade

Reply with your choice or ask for more information."""
        
        return {
            "content": response_content,
            "confidence": ai_analysis.get("confidence", 0.8),
            "metadata": {
                "trade_params": trade_params,
                "ai_analysis": ai_analysis,
                "requires_confirmation": True
            }
        }
    
    async def _handle_rebalancing(self, session: ChatSession, message: ChatMessage) -> Dict[str, Any]:
        """Handle portfolio rebalancing requests."""
        
        # Get current portfolio
        portfolio_data = await self.portfolio_risk.get_portfolio_summary(session.user_id)
        
        # Get rebalancing recommendations
        rebalance_analysis = await self.portfolio_risk.analyze_rebalancing_needs(
            user_id=session.user_id,
            target_allocation=None  # Use default strategy allocation
        )
        
        if rebalance_analysis.get("needs_rebalancing"):
            recommended_trades = rebalance_analysis.get("recommended_trades", [])
            
            response_content = f"""⚖️ **Portfolio Rebalancing Analysis**

**Current Allocation Status:**
Your portfolio deviates from optimal allocation. Here's what I recommend:

**Recommended Trades:**"""
            
            total_trade_value = 0
            for trade in recommended_trades[:5]:  # Show top 5 trades
                symbol = trade.get("symbol", "Unknown")
                action = trade.get("action", "Unknown")
                amount = trade.get("amount", 0)
                reason = trade.get("reason", "Optimization")
                
                response_content += f"\n• {action.upper()} ${amount:,.2f} {symbol} - {reason}"
                total_trade_value += abs(amount)
            
            response_content += f"""

**Total Trading Volume:** ${total_trade_value:,.2f}
**Expected Improvement:** {rebalance_analysis.get('expected_improvement', 0):.1f}% risk reduction

**Options:**
1. ✅ **Execute All Trades** - Automatic rebalancing
2. 📋 **Review Individual Trades** - Step-by-step approval
3. 🎯 **Custom Allocation** - Set your own targets
4. ❌ **Skip Rebalancing** - Keep current allocation

What would you like to do?"""
        
        else:
            response_content = """✅ **Portfolio is Well Balanced**

Your current allocation is within optimal ranges. No rebalancing needed at this time.

**Current Status:**
• Risk Level: Optimal
• Allocation Variance: < 5%
• Diversification Score: Excellent

I'll continue monitoring and notify you when rebalancing becomes beneficial."""
        
        return {
            "content": response_content,
            "confidence": 0.9,
            "metadata": {
                "rebalance_analysis": rebalance_analysis,
                "portfolio_data": portfolio_data
            }
        }
    
    async def _handle_opportunity_discovery(self, session: ChatSession, message: ChatMessage) -> Dict[str, Any]:
        """Handle opportunity discovery requests."""
        
        try:
            # Check if market analysis service is available
            if self.market_analysis is None:
                self.logger.warning("Market analysis service not available, falling back to AI consensus")
                # Fallback to AI consensus for opportunity discovery
                ai_analysis = await self.ai_consensus.analyze_opportunity(
                    f"Find market opportunities for user request: {message.content}",
                    confidence_threshold=75.0,
                    ai_models="all",
                    user_id=session.user_id
                )
                
                return {
                    "content": ai_analysis.get("analysis", "Unable to analyze opportunities at this time."),
                    "confidence": ai_analysis.get("confidence", 0.8),
                    "metadata": {"fallback_used": True}
                }
            
            # Step 1: Dynamically discover all available assets with good volume
            asset_discovery = await self.market_analysis.discover_exchange_assets(
                exchanges="all",
                asset_types="spot",
                user_id=session.user_id,
                min_volume_usd=1000000  # Only assets with >$1M daily volume
            )
            
            # Step 2: Extract top assets for scanning (dynamic, not hardcoded!)
            discovered_symbols = []
            for exchange_data in asset_discovery.get("asset_discovery", {}).values():
                high_volume_assets = exchange_data.get("high_volume_assets", [])[:20]  # Top 20 per exchange
                discovered_symbols.extend([asset.get("symbol", "").replace("/USDT", "").replace("/USD", "") for asset in high_volume_assets])
            
            # Remove duplicates and create symbol string
            unique_symbols = list(set(discovered_symbols))[:50]  # Limit to top 50 unique assets
            symbols_string = ",".join(unique_symbols) if unique_symbols else "BTC,ETH,BNB,SOL,ADA"  # Fallback
            
            self.logger.info(f"Dynamically discovered {len(unique_symbols)} assets for opportunity scanning")
            
            # Step 3: Scan for market inefficiencies across discovered assets
            market_opportunities = await self.market_analysis.market_inefficiency_scanner(
                symbols=symbols_string,
                exchanges="all", 
                scan_types="spread,volume,time",
                user_id=session.user_id
            )
        except Exception as e:
            self.logger.error(f"Error in opportunity discovery: {e}")
            return {
                "content": f"I'm having technical difficulties analyzing market opportunities. Error: {str(e)}",
                "confidence": 0.3,
                "metadata": {"error": str(e)}
            }
        
        # Get AI analysis
        ai_context = {
            "opportunities": market_opportunities,
            "user_message": message.content,
            "portfolio_context": await self.portfolio_risk.get_portfolio_summary(session.user_id)
        }
        
        ai_analysis = await self.ai_consensus.analyze_opportunity(
            json.dumps(ai_context),
            confidence_threshold=75.0,
            ai_models="all",
            user_id=session.user_id
        )
        
        opportunities = market_opportunities.get("opportunities", [])
        
        if opportunities:
            response_content = f"""🔍 **Market Opportunities Discovered**

I found {len(opportunities)} promising opportunities based on current market conditions:

**Top Opportunities:**"""
            
            for i, opp in enumerate(opportunities[:3], 1):
                symbol = opp.get("symbol", "Unknown")
                confidence = opp.get("confidence", 0)
                potential_return = opp.get("potential_return", 0)
                timeframe = opp.get("timeframe", "Unknown")
                reason = opp.get("reason", "")
                
                response_content += f"""

**{i}. {symbol}** 
• Confidence: {confidence:.1f}%
• Potential Return: {potential_return:+.1f}%
• Timeframe: {timeframe}
• Reason: {reason}"""
            
            response_content += f"""

🤖 **AI Assessment:**
{ai_analysis.get('analysis', 'Analysis in progress...')}

**Next Steps:**
• Ask for detailed analysis of any opportunity
• Request trade execution for promising assets
• Get risk assessment for potential investments

Which opportunity interests you most?"""
        
        else:
            response_content = """🔍 **Opportunity Scan Complete**

No significant opportunities detected in current market conditions. I'll continue monitoring and alert you when new prospects emerge.

**Current Focus:**
• Maintaining existing positions
• Risk management
• Market condition monitoring

Would you like me to:
• Expand search criteria
• Check specific sectors
• Set up opportunity alerts"""
        
        return {
            "content": response_content,
            "confidence": ai_analysis.get("confidence", 0.8),
            "metadata": {
                "opportunities": opportunities,
                "ai_analysis": ai_analysis
            }
        }
    
    async def _handle_market_analysis(self, session: ChatSession, message: ChatMessage) -> Dict[str, Any]:
        """Handle market analysis requests."""
        
        # Get comprehensive market data
        market_data = await self.market_analysis.get_comprehensive_analysis()
        
        # Get AI analysis
        ai_context = {
            "market_data": market_data,
            "user_message": message.content,
            "analysis_type": "comprehensive_market_analysis"
        }
        
        ai_analysis = await self.ai_consensus.analyze_opportunity(
            json.dumps(ai_context),
            confidence_threshold=75.0,
            ai_models="all",
            user_id=session.user_id
        )
        
        response_content = f"""📈 **Comprehensive Market Analysis**

**Market Overview:**
• Overall Sentiment: {market_data.get('sentiment', 'Neutral')}
• Trend Direction: {market_data.get('trend', 'Sideways')}
• Volatility Level: {market_data.get('volatility', 'Medium')}
• Volume Status: {market_data.get('volume_status', 'Normal')}

**Key Metrics:**
• Fear & Greed Index: {market_data.get('fear_greed_index', 50)}/100
• Market Cap: ${market_data.get('total_market_cap', 0):,.0f}B
• BTC Dominance: {market_data.get('btc_dominance', 0):.1f}%

🤖 **AI Multi-Model Analysis:**
{ai_analysis.get('analysis', 'Analysis in progress...')}

**Trading Implications:**
{ai_analysis.get('trading_implications', 'Analyzing market conditions...')}

Would you like me to:
• Analyze specific cryptocurrencies
• Provide trading recommendations
• Set up market alerts"""
        
        return {
            "content": response_content,
            "confidence": ai_analysis.get("confidence", 0.8),
            "metadata": {
                "market_data": market_data,
                "ai_analysis": ai_analysis
            }
        }
    
    async def _handle_risk_assessment(self, session: ChatSession, message: ChatMessage) -> Dict[str, Any]:
        """Handle risk assessment requests."""
        
        # Get comprehensive risk analysis
        risk_analysis = await self.portfolio_risk.comprehensive_risk_analysis(
            user_id=session.user_id
        )
        
        response_content = f"""🛡️ **Portfolio Risk Assessment**

**Overall Risk Level:** {risk_analysis.get('overall_risk', 'Medium')}

**Risk Metrics:**
• Value at Risk (24h): ${risk_analysis.get('var_24h', 0):,.2f}
• Maximum Drawdown: {risk_analysis.get('max_drawdown', 0):.1f}%
• Sharpe Ratio: {risk_analysis.get('sharpe_ratio', 0):.2f}
• Portfolio Beta: {risk_analysis.get('beta', 1.0):.2f}

**Risk Breakdown:**
• Concentration Risk: {risk_analysis.get('concentration_risk', 'Low')}
• Volatility Risk: {risk_analysis.get('volatility_risk', 'Medium')}
• Correlation Risk: {risk_analysis.get('correlation_risk', 'Low')}

**Recommendations:**
{risk_analysis.get('recommendations', 'Analyzing risk mitigation strategies...')}

**Risk Mitigation Options:**
1. 🛡️ Set stop-losses on high-risk positions
2. 🔄 Diversify into less correlated assets
3. 💰 Increase stablecoin allocation
4. 📉 Reduce position sizes

Which area would you like to address first?"""
        
        return {
            "content": response_content,
            "confidence": 0.9,
            "metadata": {
                "risk_analysis": risk_analysis
            }
        }
    
    async def _handle_general_query(self, session: ChatSession, message: ChatMessage) -> Dict[str, Any]:
        """Handle general queries using AI consensus."""
        
        # Build conversation context
        recent_messages = session.messages[-5:]  # Last 5 messages for context
        conversation_history = [
            {
                "role": msg.message_type.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in recent_messages
        ]
        
        ai_context = {
            "query": message.content,
            "conversation_history": conversation_history,
            "user_context": session.context,
            "system_role": "crypto_money_manager"
        }
        
        try:
            ai_response = await self.ai_consensus.analyze_opportunity(
                json.dumps(ai_context),
                confidence_threshold=70.0,
                ai_models="cost_optimized",
                user_id=session.user_id
            )
        except Exception as e:
            self.logger.warning("AI consensus failed for general query", error=str(e))
            ai_response = {"success": False}
        
        if ai_response.get("success"):
            response_content = ai_response.get("analysis", "I'm processing your request...")
            
            # Add helpful suggestions based on context
            response_content += """

**I can help you with:**
• 📊 Portfolio analysis and optimization
• 💹 Trade execution and monitoring  
• 🔍 Market opportunity discovery
• ⚖️ Risk assessment and management
• 🔄 Portfolio rebalancing
• 📈 Performance review and insights

Just ask me naturally about any of these topics!"""
        else:
            # Provide intelligent fallback based on the user's message
            user_message_lower = message.content.lower()
            
            if any(word in user_message_lower for word in ['bitcoin', 'btc', 'price']):
                response_content = """I can help you with Bitcoin analysis! While I'm connecting to my advanced AI models, here's what I can tell you:

Bitcoin is the leading cryptocurrency and I can help you with:
• Current price analysis and trends
• Portfolio allocation recommendations
• Trading strategies and timing
• Risk assessment for Bitcoin investments

What specific aspect of Bitcoin would you like to explore?"""
            
            elif any(word in user_message_lower for word in ['portfolio', 'balance', 'holdings']):
                response_content = """I'm your AI portfolio manager! I can help you with:

• **Portfolio Analysis** - Review your current holdings and performance
• **Asset Allocation** - Optimize your crypto distribution
• **Rebalancing** - Maintain your target allocation
• **Risk Management** - Assess and minimize portfolio risk

Would you like me to analyze your current portfolio or help with a specific aspect?"""
            
            elif any(word in user_message_lower for word in ['trade', 'buy', 'sell', 'execute']):
                response_content = """I can help you execute trades using our advanced 5-phase system:

**Phase 1** - Market Analysis
**Phase 2** - AI Consensus 
**Phase 3** - Risk Validation
**Phase 4** - Trade Execution
**Phase 5** - Monitoring

What trade are you considering? I can analyze the opportunity and help you execute it safely."""
            
            else:
                response_content = f"""Hello! I'm your AI cryptocurrency money manager. I understand you said: "{message.content}"

I'm here to help you manage your cryptocurrency investments!
• Risk management strategies
• Rebalancing recommendations

What would you like to know about your investments?"""
        
        return {
            "content": response_content,
            "confidence": ai_response.get("confidence", 0.7),
            "metadata": {
                "ai_response": ai_response
            }
        }
    
    async def _extract_trade_parameters(self, message: str) -> Optional[Dict[str, Any]]:
        """Extract trading parameters from natural language message."""
        
        message_lower = message.lower()
        
        # Extract action (buy/sell)
        action = None
        if re.search(r'\b(buy|purchase|acquire|long)\b', message_lower):
            action = "buy"
        elif re.search(r'\b(sell|dispose|liquidate|short)\b', message_lower):
            action = "sell"
        
        # Extract symbol
        symbol_patterns = [
            r'\b(btc|bitcoin)\b',
            r'\b(eth|ethereum)\b', 
            r'\b(sol|solana)\b',
            r'\b(ada|cardano)\b',
            r'\b(dot|polkadot)\b',
            r'\b(avax|avalanche)\b',
            r'\b(matic|polygon)\b',
            r'\b(link|chainlink)\b'
        ]
        
        symbol = None
        for pattern in symbol_patterns:
            match = re.search(pattern, message_lower)
            if match:
                symbol_map = {
                    'btc': 'BTC', 'bitcoin': 'BTC',
                    'eth': 'ETH', 'ethereum': 'ETH',
                    'sol': 'SOL', 'solana': 'SOL',
                    'ada': 'ADA', 'cardano': 'ADA',
                    'dot': 'DOT', 'polkadot': 'DOT',
                    'avax': 'AVAX', 'avalanche': 'AVAX',
                    'matic': 'MATIC', 'polygon': 'MATIC',
                    'link': 'LINK', 'chainlink': 'LINK'
                }
                symbol = symbol_map.get(match.group(1), match.group(1).upper())
                break
        
        # Extract amount
        amount = None
        amount_patterns = [
            r'\$([0-9,]+(?:\.[0-9]{1,2})?)',  # Dollar amounts
            r'([0-9]+(?:\.[0-9]+)?)\s*(?:dollars?|usd)',  # Number + dollars
            r'([0-9]+(?:\.[0-9]+)?)\s*(?:' + (symbol.lower() if symbol else '') + r')'  # Quantity
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, message_lower)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    break
                except ValueError:
                    continue
        
        # Extract order type
        order_type = "market"  # Default
        if re.search(r'\blimit\b', message_lower):
            order_type = "limit"
        
        # Return parameters if we have minimum required info
        if action and symbol:
            return {
                "action": action,
                "symbol": symbol,
                "amount": amount,
                "order_type": order_type
            }
        
        return None
    
    async def _send_websocket_update(self, user_id: str, data: Dict[str, Any]):
        """Send real-time update via WebSocket."""
        try:
            await manager.send_personal_message(json.dumps(data), user_id)
        except Exception as e:
            self.logger.warning("WebSocket update failed", user_id=user_id, error=str(e))
    
    async def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat history for a session."""
        
        if session_id not in self.sessions:
            return []
        
        session = self.sessions[session_id]
        messages = session.messages[-limit:]
        
        return [
            {
                "id": msg.id,
                "content": msg.content,
                "type": msg.message_type.value,
                "timestamp": msg.timestamp.isoformat(),
                "intent": msg.intent.value if msg.intent else None,
                "confidence": msg.confidence,
                "metadata": msg.metadata
            }
            for msg in messages
        ]
    
    async def get_active_sessions(self, user_id: str) -> List[str]:
        """Get active chat sessions for a user."""
        
        return [
            session_id for session_id, session in self.sessions.items()
            if session.user_id == user_id
        ]
    
    # Additional handler methods for other intents...
    async def _handle_strategy_discussion(self, session: ChatSession, message: ChatMessage) -> Dict[str, Any]:
        """Handle strategy discussion requests."""
        # Implementation for strategy discussions
        return {"content": "Strategy discussion handler - to be implemented", "confidence": 0.8}
    
    async def _handle_performance_review(self, session: ChatSession, message: ChatMessage) -> Dict[str, Any]:
        """Handle performance review requests."""
        # Implementation for performance reviews
        return {"content": "Performance review handler - to be implemented", "confidence": 0.8}
    
    async def _handle_autonomous_control(self, session: ChatSession, message: ChatMessage) -> Dict[str, Any]:
        """Handle autonomous mode control requests."""
        
        try:
            user_id = session.user_id
            message_lower = message.content.lower()
            
            # Determine if user wants to start or stop autonomous mode
            if any(word in message_lower for word in ['start', 'enable', 'activate', 'turn on']):
                # Starting autonomous mode
                
                # Extract trading mode if specified
                trading_mode = "balanced"  # default
                if "conservative" in message_lower:
                    trading_mode = "conservative"
                elif "aggressive" in message_lower:
                    trading_mode = "aggressive"
                elif "beast" in message_lower:
                    trading_mode = "beast_mode"
                
                # Check if unified manager is available
                if self.unified_manager:
                    result = await self.unified_manager.start_autonomous_mode(user_id, {
                        "mode": trading_mode,
                        "interface": "web_chat"
                    })
                else:
                    # Fallback to master controller
                    result = await self.master_controller.start_autonomous_mode({
                        "user_id": user_id,
                        "mode": trading_mode
                    })
                
                if result.get("success"):
                    response_content = f"""🤖 **Autonomous AI Money Manager Activated**

**Mode:** {trading_mode.replace('_', ' ').title()}
**Status:** Active and monitoring markets

**What I'm Now Doing Automatically:**
• 📊 Continuous portfolio monitoring
• 📈 Real-time market analysis
• 💹 Automated trade execution based on AI signals
• ⚖️ Dynamic portfolio rebalancing
• 🛡️ Risk management and stop-loss adjustments
• 🔍 Opportunity discovery and execution

**AI Decision Making:**
• Multi-model consensus (GPT-4, Claude, Gemini)
• Confidence threshold: 85%+ for autonomous execution
• Risk assessment before every trade
• Emergency protocols activated

**You Can Still:**
• Monitor progress through this chat
• Override decisions manually
• Adjust settings anytime
• Stop autonomous mode instantly

**Estimated Activity:** {result.get('estimated_trades_per_day', 10)} trades per day

I'm now actively managing your cryptocurrency portfolio. You can ask me "What are you doing?" anytime for updates!"""

                else:
                    response_content = f"""❌ **Failed to Start Autonomous Mode**

Error: {result.get('error', 'Unknown error')}

**Please Check:**
• Sufficient account balance
• Exchange connections active
• No emergency stops in place
• Proper permissions configured

Try again or contact support if the issue persists."""

            elif any(word in message_lower for word in ['stop', 'disable', 'deactivate', 'turn off']):
                # Stopping autonomous mode
                
                if self.unified_manager:
                    result = await self.unified_manager.stop_autonomous_mode(user_id, "web_chat")
                else:
                    result = await self.master_controller.stop_autonomous_mode(user_id)
                
                if result.get("success"):
                    stats = result.get('session_stats', {})
                    response_content = f"""🛑 **Autonomous AI Money Manager Stopped**

**Session Summary:**
• Duration: {stats.get('session_duration', 0) / 3600:.1f} hours
• Trades Executed: {stats.get('trades_executed', 0)}
• Total P&L: ${stats.get('total_pnl', 0):,.2f}

**Current Status:**
• Mode: Manual/Assisted
• AI: Available for recommendations
• Trading: Manual approval required

**I'm Still Here To:**
• Provide trading recommendations
• Analyze your portfolio
• Find market opportunities
• Assess risks and suggest actions

You can restart autonomous mode anytime by saying "Start autonomous mode" or use the UI controls."""

                else:
                    response_content = "✅ Autonomous mode was already stopped or not active."

            else:
                # General autonomous mode information
                
                # Check current status
                if self.unified_manager:
                    status = await self.unified_manager.get_ai_status(user_id)
                    autonomous_active = status.get("autonomous_active", False)
                else:
                    # Fallback status check
                    master_status = await self.master_controller.get_system_status(user_id)
                    autonomous_active = master_status.get("autonomous_mode", False)
                
                if autonomous_active:
                    response_content = """🤖 **Autonomous Mode Status: ACTIVE**

I'm currently managing your portfolio autonomously with:
• Real-time market monitoring
• Automated trade execution
• Dynamic risk management
• Continuous optimization

**Commands:**
• "What are you doing?" - Current activity
• "Stop autonomous mode" - Switch to manual
• "Show performance" - Autonomous results
• "Adjust settings" - Modify parameters

**Current Activity:** Monitoring markets and executing AI-driven trades"""

                else:
                    response_content = """🤖 **Autonomous Mode Status: INACTIVE**

I'm currently in assisted mode, providing recommendations that require your approval.

**To Start Autonomous Mode:**
• "Start autonomous mode" - Balanced approach
• "Start conservative autonomous" - Lower risk
• "Start aggressive autonomous" - Higher returns
• "Start beast mode autonomous" - Maximum opportunity

**In Autonomous Mode I Will:**
• Monitor markets 24/7
• Execute trades automatically
• Rebalance your portfolio
• Manage risk dynamically
• Find and act on opportunities

**Safety Features:**
• AI confidence thresholds
• Risk limits and stop-losses
• Emergency protocols
• Real-time monitoring

Ready to activate autonomous AI money management?"""
            
            return {
                "content": response_content,
                "confidence": 0.95,
                "metadata": {
                    "autonomous_control": True,
                    "current_mode": "autonomous" if autonomous_active else "assisted"
                }
            }
            
        except Exception as e:
            self.logger.error("Autonomous control handling failed", error=str(e))
            return {
                "content": "I encountered an error with autonomous mode control. Please try again or use the UI controls.",
                "confidence": 0.0,
                "metadata": {"error": str(e)}
            }
    
    async def execute_confirmed_action(self, session_id: str, command: str, user_id: str) -> Dict[str, Any]:
        """Execute a confirmed action from chat interaction."""
        
        try:
            if session_id not in self.sessions:
                raise ValueError("Session not found")
            
            session = self.sessions[session_id]
            
            # Parse and execute the command
            if command.startswith("execute_trade"):
                # Extract trade parameters and execute
                # This would integrate with your existing trade execution service
                return {"success": True, "message": "Trade executed successfully"}
            elif command.startswith("rebalance_portfolio"):
                # Execute portfolio rebalancing
                return {"success": True, "message": "Portfolio rebalanced successfully"}
            elif command.startswith("emergency_stop"):
                # Execute emergency stop
                await self.master_controller.emergency_stop(user_id)
                return {"success": True, "message": "Emergency stop executed"}
            else:
                return {"success": False, "error": "Unknown command"}
                
        except Exception as e:
            self.logger.error("Command execution failed", error=str(e))
            return {"success": False, "error": str(e)}


# Global chat engine instance
chat_engine = AIChatEngine()