"""
Conversational AI Orchestrator - Complete Financial AI Money Manager

This is the conversational layer that provides natural language interface to ALL
existing sophisticated platform features without breaking or duplicating anything.

Features:
- Natural language understanding for ANY financial conversation
- Streaming responses with real-time data
- Personality-driven responses based on trading modes
- Complete integration with all existing services
- Paper trading mode support (no credits required)
- Copy trading, strategy marketplace, autonomous trading integration
- Telegram integration preservation
- Multi-tenant support
- Advanced security and validation
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, AsyncGenerator, Tuple
from dataclasses import dataclass
from enum import Enum

import structlog
from app.core.config import get_settings
from app.core.logging import LoggerMixin
from app.core.redis import get_redis_client

# Import ALL existing services (no changes to existing code)
from app.services.unified_ai_manager import UnifiedAIManager, OperationMode, InterfaceType
from app.services.master_controller import MasterSystemController
from app.services.master_controller import TradingMode
from app.services.strategy_marketplace_service import strategy_marketplace_service
from app.services.paper_trading_engine import paper_trading_engine
from app.services.trading_strategies import trading_strategies_service
from app.services.portfolio_risk_core import portfolio_risk_service
from app.services.market_analysis_core import MarketAnalysisService
from app.services.ai_consensus_core import AIConsensusService
from app.services.telegram_core import TelegramCommanderService
from app.services.chat_memory import ChatMemoryService
from app.services.user_opportunity_discovery import user_opportunity_discovery
from app.services.user_onboarding_service import user_onboarding_service
# Profit sharing service will be imported dynamically when needed
from app.services.websocket import manager as websocket_manager

# Models
from app.models.user import User, UserRole
from app.models.trading import TradingStrategy, Trade, Position
from app.models.credit import CreditAccount
from app.models.copy_trading import StrategyPublisher, StrategyFollower

settings = get_settings()
logger = structlog.get_logger(__name__)


class ConversationMode(str, Enum):
    """Conversation modes for different user contexts."""
    LIVE_TRADING = "live_trading"
    PAPER_TRADING = "paper_trading"
    STRATEGY_EXPLORATION = "strategy_exploration"
    LEARNING = "learning"
    ANALYSIS = "analysis"


class ResponseType(str, Enum):
    """Response chunk types for streaming."""
    THINKING = "thinking"
    ANALYZING = "analyzing"
    GATHERING_DATA = "gathering_data"
    PROCESSING = "processing"
    RESPONSE = "response"
    ACTION_REQUIRED = "action_required"
    TRADE_VALIDATION = "trade_validation"
    ERROR = "error"
    COMPLETE = "complete"


@dataclass
class ConversationContext:
    """Complete conversation context with all platform data."""
    user_id: str
    session_id: str
    trading_mode: TradingMode
    conversation_mode: ConversationMode
    user_profile: Dict[str, Any]
    portfolio_data: Dict[str, Any]
    credit_status: Dict[str, Any]
    strategy_portfolio: Dict[str, Any]
    paper_trading_status: Dict[str, Any]
    autonomous_status: Dict[str, Any]
    recent_conversations: List[Dict[str, Any]]
    user_preferences: Dict[str, Any]


@dataclass
class ConversationAnalysis:
    """Analysis of user's conversational intent and needs."""
    primary_intent: str
    secondary_intents: List[str]
    entities_mentioned: List[str]
    data_requirements: List[str]
    action_requirements: List[str]
    emotional_context: str
    complexity_level: str
    requires_paper_trading: bool
    requires_live_trading: bool
    requires_strategy_data: bool
    requires_market_data: bool
    requires_portfolio_data: bool
    confidence_score: float


class ConversationalAIOrchestrator(LoggerMixin):
    """
    CONVERSATIONAL AI ORCHESTRATOR - Complete Financial AI Money Manager
    
    Provides natural language interface to ALL platform features:
    - Live Trading & Paper Trading (simulation mode)
    - Strategy Marketplace & Copy Trading
    - Autonomous Trading with personality modes
    - Portfolio Management & Risk Analysis
    - Market Analysis & Opportunity Discovery
    - Credit Management & Profit Sharing
    - Telegram Integration & Multi-channel support
    """
    
    def __init__(self, unified_ai_manager: UnifiedAIManager):
        # Connect to ALL existing services (zero changes to existing code)
        self.unified_manager = unified_ai_manager
        self.master_controller = unified_ai_manager.master_controller
        self.strategy_marketplace = strategy_marketplace_service
        self.paper_trading = paper_trading_engine
        self.trading_strategies = trading_strategies_service
        self.portfolio_risk = portfolio_risk_service
        self.market_analysis = MarketAnalysisService()
        self.ai_consensus = AIConsensusService()
        self.telegram_core = TelegramCommanderService()
        self.memory_service = ChatMemoryService()
        self.opportunity_discovery = user_opportunity_discovery
        self.onboarding_service = user_onboarding_service
        self.profit_sharing = None  # Will be imported dynamically when needed
        
        # Conversational AI components
        self.redis = None
        self._redis_initialized = False
        
        # Personality engine for different trading modes
        self.personalities = self._initialize_personalities()
        
        # Conversation analysis engine (implemented inline)
        # No separate analyzer needed - analysis is done inline
        
        self.logger.info("🧠 Conversational AI Orchestrator initialized with ALL platform features")
    
    async def _ensure_redis(self):
        """Ensure Redis connection for caching."""
        if not self._redis_initialized:
            try:
                self.redis = await get_redis_client()
            except Exception:
                self.redis = None
            self._redis_initialized = True
        return self.redis
    
    async def _get_profit_sharing_service(self):
        """Get profit sharing service dynamically."""
        if self.profit_sharing is None:
            try:
                from app.services.profit_sharing_service import profit_sharing_service
                self.profit_sharing = profit_sharing_service
            except ImportError:
                self.logger.warning("Profit sharing service not available")
                self.profit_sharing = None
        return self.profit_sharing
    
    def _normalize_trading_mode(self, mode_str: str) -> TradingMode:
        """Safely normalize trading mode string to TradingMode enum."""
        try:
            # Normalize the string (uppercase, handle common variations)
            normalized = mode_str.upper().strip()
            
            # Handle common variations
            mode_mapping = {
                "CONSERVATIVE": TradingMode.CONSERVATIVE,
                "BALANCED": TradingMode.BALANCED,
                "AGGRESSIVE": TradingMode.AGGRESSIVE,
                "BEAST_MODE": TradingMode.BEAST_MODE,
                "BEAST": TradingMode.BEAST_MODE,
            }
            
            if normalized in mode_mapping:
                return mode_mapping[normalized]
            
            # Try direct enum conversion
            return TradingMode(normalized.lower())
            
        except (ValueError, AttributeError):
            self.logger.warning(f"Invalid trading mode '{mode_str}', defaulting to BALANCED")
            return TradingMode.BALANCED
    
    def _initialize_personalities(self) -> Dict[TradingMode, Dict[str, Any]]:
        """Initialize AI personalities based on existing trading modes."""
        return {
            TradingMode.CONSERVATIVE: {
                "name": "Warren - Conservative Financial Advisor",
                "style": "cautious, analytical, risk-averse, thorough",
                "greeting": "I'm Warren, your conservative financial advisor. I prioritize capital preservation and steady, sustainable growth.",
                "approach": "detailed analysis, multiple confirmations, risk-first mindset",
                "vocabulary": ["carefully", "prudent", "conservative", "steady", "secure", "protected"],
                "risk_tolerance": "low",
                "decision_speed": "deliberate"
            },
            TradingMode.BALANCED: {
                "name": "Alex - Strategic Portfolio Manager",
                "style": "balanced, strategic, measured, professional",
                "greeting": "I'm Alex, your balanced portfolio strategist. I optimize for growth while managing risk intelligently.",
                "approach": "balanced analysis, calculated risks, strategic thinking",
                "vocabulary": ["strategic", "balanced", "optimized", "measured", "calculated", "intelligent"],
                "risk_tolerance": "medium",
                "decision_speed": "measured"
            },
            TradingMode.AGGRESSIVE: {
                "name": "Hunter - Aggressive Growth Manager",
                "style": "opportunistic, fast-moving, growth-focused, dynamic",
                "greeting": "I'm Hunter, your aggressive growth specialist. I hunt for high-potential opportunities and maximize returns.",
                "approach": "opportunity-focused, quick decisions, growth-oriented",
                "vocabulary": ["aggressive", "opportunity", "maximize", "dynamic", "capitalize", "accelerate"],
                "risk_tolerance": "high",
                "decision_speed": "fast"
            },
            TradingMode.BEAST_MODE: {
                "name": "Apex - Ultimate Performance Manager",
                "style": "ultra-aggressive, maximum opportunity seeker, performance-driven",
                "greeting": "I'm Apex, your beast mode money manager. Maximum risk, maximum reward, maximum performance.",
                "approach": "maximum opportunity, rapid execution, performance-first",
                "vocabulary": ["beast", "maximum", "ultimate", "dominate", "unleash", "explosive"],
                "risk_tolerance": "maximum",
                "decision_speed": "instant"
            }
        }
    
    async def process_conversation(
        self,
        user_message: str,
        session_id: str,
        user_id: str,
        conversation_mode: ConversationMode = ConversationMode.LIVE_TRADING
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process complete financial conversation with streaming responses.
        
        Handles ANY financial conversation naturally while leveraging ALL platform features.
        """
        try:
            # Yield immediate thinking response
            yield {
                "type": ResponseType.THINKING.value,
                "content": "Let me analyze your request and gather the necessary information...",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Build complete conversation context
            yield {
                "type": ResponseType.ANALYZING.value,
                "content": "Analyzing your portfolio, strategies, and current market conditions...",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            context = await self._build_complete_context(user_id, session_id, conversation_mode)
            
            # Analyze conversation for intent and requirements
            yield {
                "type": ResponseType.GATHERING_DATA.value,
                "content": "Understanding your request and gathering relevant data...",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            analysis = await self._analyze_conversation(user_message, context)
            
            # Gather all required data based on analysis
            yield {
                "type": ResponseType.PROCESSING.value,
                "content": "Processing your request through our AI systems...",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            required_data = await self._gather_all_required_data(analysis, context)
            
            # Generate streaming conversational response
            async for response_chunk in self._generate_streaming_response(
                user_message, analysis, context, required_data
            ):
                yield response_chunk
            
            # Save conversation to memory
            await self._save_conversation_memory(session_id, user_id, user_message, analysis)
            
            yield {
                "type": ResponseType.COMPLETE.value,
                "content": "",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.exception("Conversation processing failed", user_id=user_id, exc_info=True)
            yield {
                "type": ResponseType.ERROR.value,
                "content": "I encountered an error processing your request. Please try again.",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _build_complete_context(
        self,
        user_id: str,
        session_id: str,
        conversation_mode: ConversationMode
    ) -> ConversationContext:
        """Build complete conversation context with ALL platform data."""
        
        # Execute all data gathering in parallel for speed
        context_data = await asyncio.gather(
            self._get_user_profile(user_id),
            self._get_portfolio_data(user_id),
            self._get_credit_status(user_id),
            self._get_strategy_portfolio(user_id),
            self._get_paper_trading_status(user_id),
            self._get_autonomous_status(user_id),
            self._get_recent_conversations(session_id),
            self._get_user_preferences(user_id),
            return_exceptions=True
        )
        
        # Extract results with error handling
        (user_profile, portfolio_data, credit_status, strategy_portfolio,
         paper_trading_status, autonomous_status, recent_conversations,
         user_preferences) = [
            data if not isinstance(data, Exception) else {} for data in context_data
        ]
        
        # Determine trading mode from user profile or default to balanced
        trading_mode = self._normalize_trading_mode(user_profile.get("trading_mode", "balanced"))
        
        return ConversationContext(
            user_id=user_id,
            session_id=session_id,
            trading_mode=trading_mode,
            conversation_mode=conversation_mode,
            user_profile=user_profile,
            portfolio_data=portfolio_data,
            credit_status=credit_status,
            strategy_portfolio=strategy_portfolio,
            paper_trading_status=paper_trading_status,
            autonomous_status=autonomous_status,
            recent_conversations=recent_conversations,
            user_preferences=user_preferences
        )
    
    async def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get complete user profile including role, subscription, etc."""
        try:
            # Get user configuration from unified manager
            user_config = await self.unified_manager._get_user_config(user_id)
            
            # Add additional profile data
            profile = {
                "trading_mode": user_config.get("trading_mode", "balanced"),
                "operation_mode": user_config.get("operation_mode", "assisted"),
                "risk_tolerance": user_config.get("risk_tolerance", "medium"),
                "experience_level": user_config.get("experience_level", "intermediate"),
                "preferred_assets": user_config.get("preferred_assets", []),
                "notification_preferences": user_config.get("notifications", {}),
                "timezone": user_config.get("timezone", "UTC")
            }
            
            return profile
            
        except Exception as e:
            self.logger.warning("Failed to get user profile", error=str(e))
            return {"trading_mode": "balanced", "operation_mode": "assisted"}
    
    async def _get_portfolio_data(self, user_id: str) -> Dict[str, Any]:
        """Get complete portfolio data including live and paper trading."""
        try:
            # Get live portfolio data
            live_portfolio = await self.unified_manager.adapters.get_portfolio_summary(user_id)
            
            # Get paper trading portfolio if exists
            paper_portfolio = await self.paper_trading.get_paper_trading_performance(user_id)
            
            return {
                "live_portfolio": live_portfolio,
                "paper_portfolio": paper_portfolio,
                "has_live_positions": bool(live_portfolio.get("positions")),
                "has_paper_positions": paper_portfolio.get("success", False)
            }
            
        except Exception as e:
            self.logger.warning("Failed to get portfolio data", error=str(e))
            return {"live_portfolio": {}, "paper_portfolio": {}}
    
    async def _get_credit_status(self, user_id: str) -> Dict[str, Any]:
        """Get user's credit account status and transaction history."""
        try:
            # FIXED: Use same credit lookup logic as unified_chat_service
            from app.core.database import get_database
            from app.models.credit import CreditAccount
            from sqlalchemy import select
            import uuid

            async with get_database() as db:
                # Try multiple lookup methods to find existing account
                credit_account = None

                # First try: search by string user_id (as passed in)
                stmt = select(CreditAccount).where(CreditAccount.user_id == user_id)
                result = await db.execute(stmt)
                credit_account = result.scalar_one_or_none()

                # Second try: if user_id looks like UUID, try UUID conversion
                if not credit_account and len(user_id) == 36:  # UUID length
                    try:
                        user_uuid = uuid.UUID(user_id)
                        stmt = select(CreditAccount).where(CreditAccount.user_id == user_uuid)
                        result = await db.execute(stmt)
                        credit_account = result.scalar_one_or_none()
                    except ValueError:
                        pass

                if credit_account:
                    return {
                        "available_credits": float(credit_account.available_credits),
                        "total_earned": float(credit_account.total_credits),
                        "monthly_usage": 0,  # Could be calculated if needed
                        "credit_tier": "premium" if credit_account.available_credits > 100 else "basic"
                    }
                else:
                    # No account found - return 0 but don't create one
                    return {
                        "available_credits": 0,
                        "total_earned": 0,
                        "monthly_usage": 0,
                        "credit_tier": "basic"
                    }

        except Exception as e:
            self.logger.warning("Failed to get credit status", error=str(e))
            return {"available_credits": 0}
    
    async def _get_strategy_portfolio(self, user_id: str) -> Dict[str, Any]:
        """Get user's strategy portfolio from marketplace."""
        try:
            portfolio_result = await self.strategy_marketplace.get_user_strategy_portfolio(user_id)
            marketplace_strategies = await self.strategy_marketplace.get_marketplace_strategies(user_id)
            
            return {
                "active_strategies": portfolio_result.get("active_strategies", []),
                "available_strategies": marketplace_strategies.get("strategies", []),
                "strategy_performance": portfolio_result.get("performance", {}),
                "total_strategies": len(portfolio_result.get("active_strategies", []))
            }
            
        except Exception as e:
            self.logger.warning("Failed to get strategy portfolio", error=str(e))
            return {"active_strategies": [], "available_strategies": []}
    
    async def _get_paper_trading_status(self, user_id: str) -> Dict[str, Any]:
        """Get paper trading account status and performance."""
        try:
            paper_status = await self.paper_trading.get_paper_trading_performance(user_id)
            
            if paper_status.get("success"):
                return {
                    "has_paper_account": True,
                    "performance": paper_status.get("paper_portfolio", {}).get("performance_metrics", {}),
                    "virtual_balance": paper_status.get("paper_portfolio", {}).get("total_value", 0),
                    "trades_count": paper_status.get("paper_portfolio", {}).get("performance_metrics", {}).get("total_trades", 0)
                }
            else:
                return {"has_paper_account": False, "needs_setup": True}
                
        except Exception as e:
            self.logger.warning("Failed to get paper trading status", error=str(e))
            return {"has_paper_account": False}
    
    async def _get_autonomous_status(self, user_id: str) -> Dict[str, Any]:
        """Get autonomous trading status and configuration."""
        try:
            status = await self.master_controller.get_autonomous_status(user_id)
            return {
                "is_active": status.get("active", False),
                "current_mode": status.get("mode", "balanced"),
                "performance": status.get("performance", {}),
                "last_activity": status.get("last_activity")
            }
            
        except Exception as e:
            self.logger.warning("Failed to get autonomous status", error=str(e))
            return {"is_active": False}
    
    async def _get_recent_conversations(self, session_id: str) -> List[Dict[str, Any]]:
        """Get recent conversation history for context."""
        try:
            if self.memory_service:
                messages = await self.memory_service.get_session_messages(session_id, limit=10)
                return messages
            return []
            
        except Exception as e:
            self.logger.warning("Failed to get conversation history", error=str(e))
            return []
    
    async def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences and customization settings."""
        try:
            # Get from unified manager or default
            return {
                "communication_style": "professional",
                "detail_level": "comprehensive",
                "notification_frequency": "normal",
                "preferred_analysis_depth": "detailed"
            }
            
        except Exception as e:
            self.logger.warning("Failed to get user preferences", error=str(e))
            return {}
    
    async def _analyze_conversation(
        self,
        user_message: str,
        context: ConversationContext
    ) -> ConversationAnalysis:
        """Analyze user's message for intent and requirements using AI."""
        
        analysis_prompt = f"""
        Analyze this financial conversation message for a cryptocurrency trading platform user.
        
        User Message: "{user_message}"
        
        User Context:
        - Trading Mode: {context.trading_mode.value}
        - Has Live Portfolio: {bool(context.portfolio_data.get('has_live_positions'))}
        - Has Paper Trading: {context.paper_trading_status.get('has_paper_account', False)}
        - Active Strategies: {len(context.strategy_portfolio.get('active_strategies', []))}
        - Autonomous Trading: {context.autonomous_status.get('is_active', False)}
        - Credits Available: {context.credit_status.get('available_credits', 0)}
        
        Analyze and return JSON with:
        1. primary_intent (portfolio, trading, strategies, market, risk, autonomous, paper_trading, etc.)
        2. secondary_intents (list of additional intents)
        3. entities_mentioned (coins, exchanges, strategies, etc.)
        4. data_requirements (what data is needed to respond)
        5. action_requirements (what actions might be needed)
        6. emotional_context (excited, worried, curious, etc.)
        7. complexity_level (simple, moderate, complex)
        8. requires_paper_trading (boolean)
        9. requires_live_trading (boolean)
        10. requires_strategy_data (boolean)
        11. requires_market_data (boolean)
        12. requires_portfolio_data (boolean)
        13. confidence_score (0.0-1.0)
        """
        
        try:
            # Use single AI model for conversation analysis (not consensus)
            analysis_result = await self._call_conversation_ai(analysis_prompt)
            
            # Parse the analysis result
            if isinstance(analysis_result, str):
                analysis_data = json.loads(analysis_result)
            else:
                analysis_data = analysis_result
            
            return ConversationAnalysis(
                primary_intent=analysis_data.get("primary_intent", "general"),
                secondary_intents=analysis_data.get("secondary_intents", []),
                entities_mentioned=analysis_data.get("entities_mentioned", []),
                data_requirements=analysis_data.get("data_requirements", []),
                action_requirements=analysis_data.get("action_requirements", []),
                emotional_context=analysis_data.get("emotional_context", "neutral"),
                complexity_level=analysis_data.get("complexity_level", "moderate"),
                requires_paper_trading=analysis_data.get("requires_paper_trading", False),
                requires_live_trading=analysis_data.get("requires_live_trading", False),
                requires_strategy_data=analysis_data.get("requires_strategy_data", False),
                requires_market_data=analysis_data.get("requires_market_data", False),
                requires_portfolio_data=analysis_data.get("requires_portfolio_data", False),
                confidence_score=analysis_data.get("confidence_score", 0.8)
            )
            
        except Exception as e:
            self.logger.warning("Conversation analysis failed, using fallback", error=str(e))
            # Fallback analysis
            return ConversationAnalysis(
                primary_intent="general",
                secondary_intents=[],
                entities_mentioned=[],
                data_requirements=["portfolio", "market"],
                action_requirements=[],
                emotional_context="neutral",
                complexity_level="moderate",
                requires_paper_trading=False,
                requires_live_trading=False,
                requires_strategy_data=True,
                requires_market_data=True,
                requires_portfolio_data=True,
                confidence_score=0.7
            )
    
    async def _gather_all_required_data(
        self,
        analysis: ConversationAnalysis,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Gather all required data based on conversation analysis."""
        
        data_tasks = []
        
        # Market data
        if analysis.requires_market_data or "market" in analysis.data_requirements:
            data_tasks.append(("market_data", self._get_market_data()))
        
        # Portfolio data (if not already in context)
        if analysis.requires_portfolio_data or "portfolio" in analysis.data_requirements:
            data_tasks.append(("portfolio_analysis", self._get_detailed_portfolio_analysis(context.user_id)))
        
        # Strategy data
        if analysis.requires_strategy_data or "strategies" in analysis.data_requirements:
            data_tasks.append(("strategy_analysis", self._get_strategy_analysis(context.user_id)))
        
        # Paper trading data
        if analysis.requires_paper_trading or "paper_trading" in analysis.data_requirements:
            data_tasks.append(("paper_trading_data", self._get_paper_trading_data(context.user_id)))
        
        # Opportunity data
        if "opportunities" in analysis.data_requirements:
            data_tasks.append(("opportunities", self._get_opportunities_data(context.user_id)))
        
        # Risk data
        if "risk" in analysis.data_requirements:
            data_tasks.append(("risk_analysis", self._get_risk_analysis(context.user_id)))
        
        # Execute all data gathering in parallel
        if data_tasks:
            task_names, tasks = zip(*data_tasks)
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results
            gathered_data = {}
            for name, result in zip(task_names, results):
                if not isinstance(result, Exception):
                    gathered_data[name] = result
                else:
                    self.logger.warning(f"Failed to gather {name}", error=str(result))
                    gathered_data[name] = {}
        else:
            gathered_data = {}
        
        return gathered_data
    
    async def _get_market_data(self) -> Dict[str, Any]:
        """Get current market data and analysis."""
        try:
            market_overview = await self.market_analysis.get_market_overview()
            return market_overview
        except Exception as e:
            self.logger.warning("Failed to get market data", error=str(e))
            return {}
    
    async def _get_detailed_portfolio_analysis(self, user_id: str) -> Dict[str, Any]:
        """Get detailed portfolio analysis."""
        try:
            analysis = await self.portfolio_risk.risk_analysis(user_id)
            return analysis
        except Exception as e:
            self.logger.warning("Failed to get portfolio analysis", error=str(e))
            return {}
    
    async def _get_strategy_analysis(self, user_id: str) -> Dict[str, Any]:
        """Get strategy performance and recommendations."""
        try:
            active_strategy = await self.trading_strategies.get_active_strategy(user_id)
            return active_strategy
        except Exception as e:
            self.logger.warning("Failed to get strategy analysis", error=str(e))
            return {}
    
    async def _get_paper_trading_data(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive paper trading data."""
        try:
            paper_performance = await self.paper_trading.get_paper_trading_performance(user_id)
            return paper_performance
        except Exception as e:
            self.logger.warning("Failed to get paper trading data", error=str(e))
            return {}
    
    async def _get_opportunities_data(self, user_id: str) -> Dict[str, Any]:
        """Get opportunity discovery data."""
        try:
            opportunities = await self.opportunity_discovery.discover_opportunities_for_user(user_id)
            return opportunities
        except Exception as e:
            self.logger.warning("Failed to get opportunities data", error=str(e))
            return {}
    
    async def _get_risk_analysis(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive risk analysis."""
        try:
            risk_analysis = await self.portfolio_risk.risk_analysis(user_id)
            return risk_analysis
        except Exception as e:
            self.logger.warning("Failed to get risk analysis", error=str(e))
            return {}
    
    async def _generate_streaming_response(
        self,
        user_message: str,
        analysis: ConversationAnalysis,
        context: ConversationContext,
        required_data: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate streaming conversational response with personality."""
        
        personality = self.personalities[context.trading_mode]
        
        # Build comprehensive response prompt
        response_prompt = self._build_response_prompt(
            user_message, analysis, context, required_data, personality
        )
        
        # Stream response from conversation AI
        async for chunk in self._stream_ai_response(response_prompt):
            yield {
                "type": ResponseType.RESPONSE.value,
                "content": chunk,
                "timestamp": datetime.utcnow().isoformat(),
                "personality": personality["name"]
            }
        
        # Handle action requirements
        if analysis.action_requirements:
            for action in analysis.action_requirements:
                if action == "trade_execution":
                    yield {
                        "type": ResponseType.ACTION_REQUIRED.value,
                        "content": "Trade execution requires your confirmation. Would you like me to proceed?",
                        "action": "confirm_trade",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                elif action == "strategy_purchase":
                    yield {
                        "type": ResponseType.ACTION_REQUIRED.value,
                        "content": "Strategy purchase requires credit confirmation. Shall I proceed?",
                        "action": "confirm_purchase",
                        "timestamp": datetime.utcnow().isoformat()
                    }
    
    def _build_response_prompt(
        self,
        user_message: str,
        analysis: ConversationAnalysis,
        context: ConversationContext,
        required_data: Dict[str, Any],
        personality: Dict[str, Any]
    ) -> str:
        """Build comprehensive response prompt for AI."""
        
        return f"""
        You are {personality['name']}, a {personality['style']} AI financial advisor for a sophisticated cryptocurrency trading platform.
        
        PERSONALITY: {personality['greeting']}
        APPROACH: {personality['approach']}
        COMMUNICATION STYLE: Use vocabulary like {', '.join(personality['vocabulary'])}
        
        USER MESSAGE: "{user_message}"
        
        USER CONTEXT:
        - Trading Mode: {context.trading_mode.value}
        - Operation Mode: {context.user_profile.get('operation_mode', 'assisted')}
        - Has Live Portfolio: ${context.portfolio_data.get('live_portfolio', {}).get('total_value', 0):,.2f}
        - Paper Trading: {context.paper_trading_status.get('has_paper_account', False)}
        - Active Strategies: {len(context.strategy_portfolio.get('active_strategies', []))}
        - Autonomous Trading: {'Active' if context.autonomous_status.get('is_active') else 'Inactive'}
        - Credits: {context.credit_status.get('available_credits', 0)}
        
        CONVERSATION ANALYSIS:
        - Primary Intent: {analysis.primary_intent}
        - Emotional Context: {analysis.emotional_context}
        - Complexity: {analysis.complexity_level}
        
        AVAILABLE DATA:
        {json.dumps(required_data, indent=2)}
        
        INSTRUCTIONS:
        1. Respond in character as {personality['name']} with {personality['style']} approach
        2. Address the user's {analysis.primary_intent} request comprehensively
        3. Use the available data to provide specific, actionable insights
        4. If paper trading is mentioned, emphasize it uses NO CREDITS (simulation mode)
        5. If live trading is discussed, mention credit requirements and risks
        6. Reference their actual portfolio data, strategies, and performance
        7. Provide specific next steps and actionable recommendations
        8. Maintain conversational, helpful tone while being professional
        9. If data is missing, acknowledge what you'd need to provide better advice
        10. Always prioritize user education and risk awareness
        
        Generate a comprehensive, helpful response that addresses their needs while maintaining your personality.
        """
    
    async def _call_conversation_ai(self, prompt: str) -> str:
        """Call single AI model for conversation (not consensus)."""
        try:
            # Use existing AI consensus service but with single model for conversation
            response = await self.ai_consensus.consensus_decision(
                decision_request=prompt,
                confidence_threshold=70.0,
                ai_models="gpt4",  # Single model for conversation
                user_id="system"
            )
            
            return response.get("final_recommendation", "I'm here to help with your financial questions.")
            
        except Exception as e:
            self.logger.warning("Conversation AI call failed", error=str(e))
            return "I'm here to help with your cryptocurrency trading and portfolio management."
    
    async def _stream_ai_response(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream AI response in chunks for real-time experience."""
        try:
            # For now, simulate streaming by chunking the response
            response = await self._call_conversation_ai(prompt)
            
            # Split response into chunks for streaming effect
            words = response.split()
            chunk_size = 5  # 5 words per chunk
            
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size])
                if i + chunk_size < len(words):
                    chunk += " "
                
                yield chunk
                # Small delay for streaming effect
                await asyncio.sleep(0.1)
                
        except Exception as e:
            self.logger.error("AI response streaming failed", error=str(e))
            yield "I encountered an error generating my response. Please try again."
    
    async def _save_conversation_memory(
        self,
        session_id: str,
        user_id: str,
        user_message: str,
        analysis: ConversationAnalysis
    ):
        """Save conversation to memory for future context."""
        try:
            if self.memory_service:
                await self.memory_service.save_message(
                    session_id=session_id,
                    user_id=user_id,
                    content=user_message,
                    message_type="user",
                    intent=analysis.primary_intent,
                    confidence=analysis.confidence_score,
                    metadata={
                        "entities": analysis.entities_mentioned,
                        "emotional_context": analysis.emotional_context,
                        "complexity": analysis.complexity_level
                    }
                )
        except Exception as e:
            self.logger.warning("Failed to save conversation memory", error=str(e))
    
    async def handle_action_confirmation(
        self,
        user_id: str,
        action_type: str,
        action_data: Dict[str, Any],
        confirmed: bool
    ) -> Dict[str, Any]:
        """Handle user confirmation of actions (trades, purchases, etc.)."""
        
        if not confirmed:
            return {
                "success": True,
                "message": "Action cancelled as requested.",
                "action_type": action_type
            }
        
        try:
            if action_type == "confirm_trade":
                # Execute trade through existing systems
                if action_data.get("is_paper_trading", False):
                    # Paper trading - no credits required
                    result = await self.paper_trading.execute_paper_trade(
                        user_id=user_id,
                        symbol=action_data.get("symbol"),
                        side=action_data.get("side"),
                        quantity=action_data.get("quantity"),
                        strategy_used=action_data.get("strategy", "manual")
                    )
                else:
                    # Live trading - through existing trade execution
                    result = await self.unified_manager.process_user_request(
                        user_id=user_id,
                        request=f"Execute trade: {action_data}",
                        interface=InterfaceType.WEB_CHAT
                    )
                
                return result
            
            elif action_type == "confirm_purchase":
                # Strategy purchase through marketplace
                result = await self.strategy_marketplace.purchase_strategy_access(
                    user_id=user_id,
                    strategy_id=action_data.get("strategy_id"),
                    subscription_type=action_data.get("subscription_type", "monthly")
                )
                
                return result
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown action type: {action_type}"
                }
                
        except Exception as e:
            self.logger.error("Action confirmation failed", error=str(e), action_type=action_type)
            return {
                "success": False,
                "error": f"Failed to execute {action_type}: {str(e)}"
            }


# Helper classes removed - functionality implemented inline in main orchestrator


# Global service instance
conversational_ai_orchestrator = None


async def get_conversational_ai_orchestrator(
    unified_ai_manager: UnifiedAIManager
) -> ConversationalAIOrchestrator:
    """Get or create conversational AI orchestrator instance."""
    global conversational_ai_orchestrator
    
    try:
        if conversational_ai_orchestrator is None:
            conversational_ai_orchestrator = ConversationalAIOrchestrator(unified_ai_manager)
            await conversational_ai_orchestrator._ensure_redis()
        
        return conversational_ai_orchestrator
    except Exception as e:
        logger.error("Failed to initialize conversational AI orchestrator", error=str(e))
        # Create a new instance if the global one fails
        orchestrator = ConversationalAIOrchestrator(unified_ai_manager)
        await orchestrator._ensure_redis()
        return orchestrator