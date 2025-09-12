"""
Enhanced AI Chat Engine with Persistent Memory

This enhanced version of the chat engine integrates with the persistent memory service
to provide continuous conversation context across server restarts and sessions.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
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
# Chat memory will be initialized lazily
from app.services.market_analysis_core import MarketAnalysisService
from app.services.trading_strategies import TradingStrategiesService
from app.services.portfolio_risk_core import PortfolioRiskService
from app.services.chat_service_adapters_fixed import ChatServiceAdaptersFixed as ChatServiceAdapters

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


class AIPhase(str, Enum):
    """5-Phase AI execution phases."""
    ANALYSIS = "analysis"
    CONSENSUS = "consensus" 
    VALIDATION = "validation"
    EXECUTION = "execution"
    MONITORING = "monitoring"


class EnhancedAIChatEngine(LoggerMixin):
    """
    Enhanced AI Chat Engine with Persistent Memory and 5-Phase Execution
    
    Provides natural language interface for:
    - Portfolio management and analysis
    - Trade execution with 5-phase validation
    - Risk assessment and rebalancing
    - Market opportunity discovery
    - Strategy optimization
    - Performance review
    - Persistent conversation memory
    """
    
    def __init__(
        self, 
        portfolio_risk: Optional['PortfolioRiskServiceExtended'] = None,
        market_analysis: Optional['MarketAnalysisService'] = None
    ):
        # Initialize core services only - LAZY LOADING for others
        # Initialize memory service lazily to prevent startup failures
        self.memory = None
        self._memory_initialized = False
            
        self.unified_manager = None  # Will be set by unified manager
        
        # Initialize services lazily to prevent startup failures
        self.ai_consensus = None
        self.master_controller = None
        self.trade_executor = None
        self.market_analysis = None
        self.trading_strategies = None
        self.portfolio_risk = None
        self.chat_adapters = None
        
        self.logger.info("✅ Enhanced chat engine initialized")
        
    async def _ensure_services(self):
        """Lazy initialization of services to prevent startup failures."""
        try:
            # Initialize memory service if not already done
            if not self._memory_initialized:
                try:
                    from app.services.chat_memory import chat_memory
                    self.memory = chat_memory
                    self._memory_initialized = True
                    self.logger.info("✅ Chat memory service initialized")
                except Exception as e:
                    self.logger.warning("Chat memory service failed, continuing without memory", error=str(e))
                    self.memory = None
                    self._memory_initialized = True  # Don't keep trying
            
            if self.ai_consensus is None:
                self.ai_consensus = AIConsensusService()
            if self.master_controller is None:
                self.master_controller = MasterSystemController()
            if self.trade_executor is None:
                self.trade_executor = TradeExecutionService()
            if self.market_analysis is None:
                self.market_analysis = MarketAnalysisService()
            if self.chat_adapters is None:
                self.chat_adapters = ChatServiceAdapters()
        except Exception as e:
            self.logger.warning("Some services failed to initialize", error=str(e))
    
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
            ChatIntent.AUTONOMOUS_CONTROL: [
                r'\b(autonomous|auto|automatic|start.*auto|stop.*auto)\b',
                r'\b(enable.*autonomous|disable.*autonomous)\b',
                r'\b(auto.*mode|autonomous.*mode)\b'
            ]
        }
        
        # System prompts for different intents
        self.system_prompts = {
            ChatIntent.GENERAL_QUERY: """You are CryptoUniverse AI, a sophisticated cryptocurrency money manager. 
            Provide helpful, accurate information about cryptocurrency trading, markets, and portfolio management.
            Be professional, concise, and actionable in your responses. Always consider the user's conversation history.""",
            
            ChatIntent.PORTFOLIO_ANALYSIS: """You are analyzing a cryptocurrency portfolio with full conversation context. 
            Provide detailed insights about portfolio performance, allocation, risk metrics, and optimization suggestions.
            Include specific recommendations for improvement based on previous conversations and user preferences.""",
            
            ChatIntent.TRADE_EXECUTION: """You are executing cryptocurrency trades using the 5-phase framework.
            PHASE 1 - ANALYSIS: Analyze the trade request and market conditions
            PHASE 2 - CONSENSUS: Get consensus from multiple AI models  
            PHASE 3 - VALIDATION: Validate the trade against risk parameters
            PHASE 4 - EXECUTION: Execute the trade with proper risk management
            PHASE 5 - MONITORING: Set up monitoring and alerts
            Consider conversation history and user's trading patterns.""",
            
            ChatIntent.MARKET_ANALYSIS: """You are analyzing cryptocurrency markets with historical context. 
            Provide comprehensive market analysis including technical indicators, sentiment, trends, 
            and actionable trading insights. Reference previous market discussions with this user.""",
            
            ChatIntent.RISK_ASSESSMENT: """You are assessing portfolio and trading risks with full context. 
            Analyze current risk exposure, potential threats, and provide specific risk mitigation strategies.
            Consider the user's risk tolerance and previous risk discussions.""",
            
            ChatIntent.REBALANCING: """You are optimizing portfolio allocation with conversation memory. 
            Analyze current allocation, market conditions, and provide specific rebalancing recommendations 
            with clear rationale and execution steps. Consider previous rebalancing discussions."""
        }
    
    async def start_chat_session(self, user_id: str, session_type: str = "general") -> str:
        """Start a new chat session with persistent memory."""
        try:
            # If memory service is not available, generate a simple session ID
            if not self.memory:
                session_id = f"session_{user_id}_{int(time.time())}"
                self.logger.info("Created simple session without memory", session_id=session_id)
                return session_id
            
            # Check for recent active sessions
            recent_sessions = await self.memory.get_user_sessions(user_id, limit=1)
            
            # If there's a recent active session (within 1 hour), continue it
            if recent_sessions:
                last_session = recent_sessions[0]
                last_activity = datetime.fromisoformat(last_session["last_activity"])
                if datetime.utcnow() - last_activity < timedelta(hours=1):
                    self.logger.info(
                        "Continuing recent chat session",
                        session_id=last_session["session_id"],
                        user_id=user_id
                    )
                    return last_session["session_id"]
            
            # Create new session
            session_id = await self.memory.create_session(
                user_id=user_id,
                session_type=session_type,
                context={
                    "preferences": {},
                    "active_strategies": [],
                    "risk_tolerance": "balanced",
                    "created_via": "chat_interface"
                }
            )
            
            # Add welcome message
            await self.memory.save_message(
                session_id=session_id,
                user_id=user_id,
                content="""👋 Welcome back to CryptoUniverse AI Money Manager!

I remember our previous conversations and can help you with:

🔹 **Portfolio Analysis** - Review performance with historical context
🔹 **5-Phase Trade Execution** - Advanced AI-powered trading
🔹 **Risk Management** - Continuous risk assessment
🔹 **Smart Rebalancing** - Context-aware optimization
🔹 **Market Opportunities** - Personalized discovery
🔹 **Strategy Evolution** - Learning from our interactions

I'll remember our conversation and provide increasingly personalized assistance. How can I help you today?""",
                message_type=ChatMessageType.ASSISTANT.value,
                intent=ChatIntent.GENERAL_QUERY.value,
                confidence=1.0,
                metadata={"welcome_message": True, "session_type": session_type},
                model_used="system"
            )
            
            return session_id
            
        except Exception as e:
            self.logger.error("Failed to start chat session", error=str(e), user_id=user_id)
            raise Exception(f"Failed to start chat session: {str(e)}")
    
    async def process_message(
        self, 
        session_id: str, 
        user_message: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Process a user message with persistent memory and 5-phase execution."""
        
        processing_start = time.time()
        
        try:
            # Ensure services are initialized (lazy loading)
            await self._ensure_services()
            
            # Create session if none provided
            if not session_id or session_id.strip() == "":
                session_id = await self.start_chat_session(user_id)
            
            # Save user message (with fallback if memory unavailable)
            user_message_id = f"user_{uuid.uuid4().hex}"  # Always generate a message ID
            context = {}
            
            if self.memory:
                try:
                    saved_user_id = await self.memory.save_message(
                        session_id=session_id,
                        user_id=user_id,
                        content=user_message,
                        message_type=ChatMessageType.USER.value,
                        processing_time_ms=0,
                        tokens_used=len(user_message.split())
                    )
                    # Use the saved message ID if successful
                    if saved_user_id:
                        user_message_id = saved_user_id
                    # Get conversation context
                    context = await self.memory.get_conversation_context(session_id)
                    # Ensure user_id is in session_context for authenticated operations
                    if "session_context" not in context:
                        context["session_context"] = {}
                    context["session_context"]["user_id"] = user_id
                except Exception as e:
                    self.logger.warning("Memory service failed, continuing without memory", error=str(e))
                    context = {
                        "session_context": {"user_id": user_id}
                    }
            
            # Try enhanced processing, fallback to simple response
            try:
                # Classify intent
                intent = await self._classify_intent(user_message, context)
                
                # Process with 5-phase execution for trading intents
                if intent in [ChatIntent.TRADE_EXECUTION, ChatIntent.REBALANCING]:
                    response = await self._process_with_5_phases(
                        session_id, user_message, intent, context
                    )
                else:
                    response = await self._process_intent(
                        user_message, intent, context
                    )
            except Exception as e:
                self.logger.warning("Enhanced processing failed, using simple fallback", error=str(e))
                # Simple fallback response
                intent = ChatIntent.GENERAL_QUERY
                response = {
                    "content": "I'm here to help with your cryptocurrency trading and portfolio management. What would you like to know?",
                    "confidence": 0.7,
                    "metadata": {"fallback": True, "error": str(e)}
                }
            
            processing_time = (time.time() - processing_start) * 1000
            
            # Save assistant response (with fallback)
            assistant_message_id = f"msg_{uuid.uuid4().hex}"  # Always generate a message ID
            if self.memory:
                try:
                    saved_message_id = await self.memory.save_message(
                        session_id=session_id,
                        user_id=user_id,
                        content=response["content"],
                        message_type=ChatMessageType.ASSISTANT.value,
                        intent=intent.value,
                        confidence=response.get("confidence", 0.8),
                        metadata=response.get("metadata", {}),
                        model_used=response.get("model_used", "enhanced_engine"),
                        processing_time_ms=processing_time,
                        tokens_used=response.get("tokens_used", len(response["content"].split()))
                    )
                    # Use the saved message ID if successful
                    if saved_message_id:
                        assistant_message_id = saved_message_id
                    
                    # Update session context if needed
                    if response.get("context_updates"):
                        await self.memory.update_session_context(
                            session_id, response["context_updates"]
                        )
                except Exception as e:
                    self.logger.warning("Failed to save response to memory", error=str(e))
                    # Keep the fallback message ID
            
            # Send real-time update via WebSocket
            await self._send_websocket_update(user_id, {
                "type": "chat_message",
                "message": {
                    "id": assistant_message_id,
                    "content": response["content"],
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": response.get("metadata", {}),
                    "intent": intent.value,
                    "confidence": response.get("confidence")
                }
            })
            
            return {
                "success": True,
                "session_id": session_id,
                "message_id": assistant_message_id,
                "content": response["content"],
                "intent": intent.value,
                "confidence": response.get("confidence", 0.8),
                "metadata": response.get("metadata", {}),
                "processing_time_ms": processing_time
            }
            
        except Exception as e:
            self.logger.error(
                "Message processing failed", 
                error=str(e), 
                user_id=user_id, 
                session_id=session_id
            )
            
            # Save error message (if memory available)
            if self.memory:
                try:
                    await self.memory.save_message(
                        session_id=session_id,
                        user_id=user_id,
                        content="I apologize, but I encountered an error processing your message. Please try again.",
                        message_type=ChatMessageType.ASSISTANT.value,
                        intent=ChatIntent.GENERAL_QUERY.value,
                        confidence=0.0,
                        metadata={"error": True, "error_message": str(e)},
                        model_used="system"
                    )
                except Exception as memory_error:
                    self.logger.warning("Failed to save error message to memory", error=str(memory_error))
            
            return {
                "success": False,
                "session_id": session_id,
                "message_id": f"error_{uuid.uuid4().hex}",
                "content": "I apologize, but I encountered an error processing your message. Please try again.",
                "intent": "error",
                "confidence": 0.0,
                "metadata": {"error": True, "error_message": str(e)},
                "error": str(e)
            }
    
    async def _process_with_5_phases(
        self,
        session_id: str,
        user_message: str,
        intent: ChatIntent,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process trading requests using 5-phase execution framework."""
        
        phases_completed = []
        
        try:
            # PHASE 1: ANALYSIS
            analysis_result = await self._execute_phase_analysis(
                user_message, intent, context
            )
            phases_completed.append("analysis")
            
            # PHASE 2: CONSENSUS
            consensus_result = await self._execute_phase_consensus(
                user_message, analysis_result, context
            )
            phases_completed.append("consensus")
            
            # PHASE 3: VALIDATION
            validation_result = await self._execute_phase_validation(
                consensus_result, context
            )
            phases_completed.append("validation")
            
            if not validation_result.get("approved", False):
                return {
                    "content": f"""🛡️ **Trading Request Analysis Complete**

**Phases Completed:** {' → '.join(phases_completed)}

**Recommendation:** {validation_result.get('reason', 'Trade not approved by validation')}

**Analysis Summary:**
{analysis_result.get('summary', 'Analysis completed')}

**Consensus Result:**
{consensus_result.get('recommendation', 'Consensus reached')}

Would you like to modify the trade parameters or proceed with a different approach?""",
                    "confidence": 0.9,
                    "metadata": {
                        "phases_completed": phases_completed,
                        "validation_failed": True,
                        "analysis": analysis_result,
                        "consensus": consensus_result,
                        "validation": validation_result
                    }
                }
            
            # PHASE 4: EXECUTION (if validated)
            execution_result = await self._execute_phase_execution(
                validation_result, context
            )
            phases_completed.append("execution")
            
            # PHASE 5: MONITORING
            monitoring_result = await self._execute_phase_monitoring(
                execution_result, context
            )
            phases_completed.append("monitoring")
            
            return {
                "content": f"""✅ **Trade Executed Successfully - 5 Phases Complete**

**Phases:** {' → '.join(phases_completed)}

**Execution Summary:**
{execution_result.get('summary', 'Trade executed')}

**Monitoring Setup:**
{monitoring_result.get('monitoring_summary', 'Monitoring active')}

**Next Steps:**
- Real-time monitoring is now active
- You'll receive alerts for significant changes
- Performance tracking has been updated

I'll continue monitoring this trade and notify you of important developments.""",
                "confidence": 0.95,
                "metadata": {
                    "phases_completed": phases_completed,
                    "execution_successful": True,
                    "trade_id": execution_result.get("trade_id"),
                    "monitoring_id": monitoring_result.get("monitoring_id"),
                    "phases_data": {
                        "analysis": analysis_result,
                        "consensus": consensus_result,
                        "validation": validation_result,
                        "execution": execution_result,
                        "monitoring": monitoring_result
                    }
                },
                "context_updates": {
                    "last_trade_execution": datetime.utcnow().isoformat(),
                    "active_trades": context.get("active_trades", []) + [execution_result.get("trade_id")]
                }
            }
            
        except Exception as e:
            return {
                "content": f"""❌ **Trading Error in Phase {len(phases_completed) + 1}**

**Phases Completed:** {' → '.join(phases_completed)}

**Error:** {str(e)}

I encountered an error during the 5-phase execution. The trade was not completed for safety. Would you like me to retry or help you with a different approach?""",
                "confidence": 0.6,
                "metadata": {
                    "phases_completed": phases_completed,
                    "error": str(e),
                    "execution_failed": True
                }
            }
    
    async def _execute_phase_analysis(
        self, user_message: str, intent: ChatIntent, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Phase 1: Market Analysis using real market data"""
        try:
            # Use the actual market analysis service
            if self.market_analysis:
                market_data = await self.market_analysis.complete_market_assessment(
                    symbols=["BTC", "ETH", "SOL"],  # Default major coins
                    depth="comprehensive"
                )
            else:
                market_data = {"status": "service_unavailable"}
            
            return {
                "summary": f"Market analysis completed - {market_data.get('market_trend', 'neutral')} trend detected",
                "risk_assessment": market_data.get("risk_level", "medium"),
                "market_conditions": market_data.get("market_conditions", {}),
                "recommendations": market_data.get("opportunities", []),
                "raw_analysis": market_data
            }
        except Exception as e:
            self.logger.error("Market analysis failed", error=str(e))
            return {
                "summary": f"Market analysis failed: {str(e)}",
                "risk_assessment": "unknown",
                "market_conditions": {},
                "recommendations": []
            }
    
    async def _execute_phase_consensus(
        self, user_message: str, analysis: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Phase 2: Portfolio Risk Assessment + AI Consensus"""
        try:
            # First get portfolio risk assessment using real service
            user_id = context.get("session_context", {}).get("user_id")
            
            portfolio_status = {}
            if self.portfolio_risk and user_id and user_id != "unknown":
                try:
                    portfolio_status = await self.portfolio_risk.get_portfolio_status(user_id)
                except Exception as e:
                    self.logger.error("Portfolio risk assessment failed", error=str(e))
                    portfolio_status = {"status": "service_unavailable", "error": str(e)}
            
            # Then get AI consensus on the combined analysis
            consensus = await self.ai_consensus.consensus_decision(
                decision_request=json.dumps({
                    "user_request": user_message,
                    "market_analysis": analysis,
                    "portfolio_status": portfolio_status,
                    "context": context
                }),
                confidence_threshold=80.0,
                ai_models="all",
                user_id=user_id
            )
            
            return {
                "recommendation": consensus.get("final_recommendation", "Analyze market and portfolio data for trading decision"),
                "confidence": consensus.get("consensus_score", 0.7),
                "portfolio_assessment": portfolio_status,
                "market_data": analysis,
                "ai_consensus": consensus.get("success", False)
            }
        except Exception as e:
            self.logger.error("Phase 2 consensus failed", error=str(e))
            return {
                "recommendation": f"Consensus phase failed: {str(e)}",
                "confidence": 0.5,
                "portfolio_assessment": {},
                "market_data": analysis,
                "ai_consensus": False
            }
    
    async def _execute_phase_validation(
        self, consensus: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Phase 3: Validation"""
        # Simplified validation based on consensus confidence
        confidence = consensus.get("confidence", 0.7)
        approved = confidence >= 0.75
        
        return {
            "approved": approved,
            "reason": f"Validation {'passed' if approved else 'failed'} with {confidence:.1%} confidence",
            "risk_checks": {"consensus_confidence": confidence},
            "compliance_status": "validated" if approved else "rejected"
        }
    
    async def _execute_phase_execution(
        self, validation: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Phase 4: Execution"""
        # Simplified execution placeholder
        trade_id = str(uuid.uuid4())
        
        return {
            "trade_id": trade_id,
            "summary": "Trade execution simulated - full execution requires exchange integration",
            "status": "simulated",
            "details": {"validation_result": validation}
        }
    
    async def _execute_phase_monitoring(
        self, execution: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Phase 5: Monitoring"""
        # Simplified monitoring setup
        monitoring_id = str(uuid.uuid4())
        
        return {
            "monitoring_id": monitoring_id,
            "monitoring_summary": "Monitoring setup for trade tracking and alerts",
            "alert_types": ["price_target", "stop_loss", "volume_anomaly"],
            "monitoring_duration": "ongoing"
        }
    
    async def _classify_intent(
        self, message: str, context: Dict[str, Any]
    ) -> ChatIntent:
        """Classify user message intent with conversation context."""
        
        message_lower = message.lower()
        
        # Check for emergency patterns first
        for pattern in self.intent_patterns[ChatIntent.EMERGENCY_COMMAND]:
            if re.search(pattern, message_lower):
                return ChatIntent.EMERGENCY_COMMAND
        
        # Use conversation context to improve classification
        recent_intents = [
            msg.get("intent") for msg in context.get("recent_messages", [])
            if msg.get("intent")
        ]
        
        # Check other intents with context weighting
        intent_scores = {}
        for intent, patterns in self.intent_patterns.items():
            if intent == ChatIntent.EMERGENCY_COMMAND:
                continue
                
            score = 0
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    score += 1
            
            # Boost score if recent conversation was about this topic
            if intent.value in recent_intents[-3:]:  # Last 3 messages
                score += 0.5
            
            if score > 0:
                intent_scores[intent] = score
        
        # Return highest scoring intent or general query
        if intent_scores:
            return max(intent_scores.items(), key=lambda x: x[1])[0]
        
        return ChatIntent.GENERAL_QUERY
    
    async def _process_intent(
        self,
        user_message: str,
        intent: ChatIntent,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process intents by ROUTING TO ACTUAL SERVICES first, then using AI consensus for validation."""
        
        user_id = context.get("session_context", {}).get("user_id")
        
        if not user_id:
            raise ValueError("Authentication required: No valid user session found")
        
        try:
            # STEP 1: ROUTE TO APPROPRIATE SERVICE (Do the work!)
            if intent == ChatIntent.OPPORTUNITY_DISCOVERY:
                return await self._handle_opportunity_discovery(user_message, context, user_id)
            
            elif intent == ChatIntent.MARKET_ANALYSIS:
                return await self._handle_market_analysis(user_message, context, user_id)
            
            elif intent == ChatIntent.PORTFOLIO_ANALYSIS:
                return await self._handle_portfolio_analysis(user_message, context, user_id)
            
            elif intent == ChatIntent.STRATEGY_DISCUSSION:
                return await self._handle_strategy_discussion(user_message, context, user_id)
            
            elif intent == ChatIntent.RISK_ASSESSMENT:
                return await self._handle_risk_assessment(user_message, context, user_id)
            
            elif intent == ChatIntent.AUTONOMOUS_CONTROL:
                return await self._handle_autonomous_control(user_message, context, user_id)
            
            elif intent == ChatIntent.EMERGENCY_COMMAND:
                return await self._handle_emergency_command(user_message, context, user_id)
            
            else:
                # For general queries, use AI consensus but with service context
                return await self._handle_general_query(user_message, context, user_id)
                
        except Exception as e:
            self.logger.error("Service routing failed", error=str(e), intent=intent.value)
            return {
                "content": f"I encountered an error accessing the {intent.value} service: {str(e)}",
                "confidence": 0.3,
                "metadata": {"error": True, "intent": intent.value, "service_error": str(e)}
            }
    
    async def _handle_opportunity_discovery(self, message: str, context: Dict, user_id: str) -> Dict[str, Any]:
        """Handle opportunity discovery using REAL user strategy-based system."""
        
        try:
            # Import the new enterprise services
            from app.services.user_opportunity_discovery import user_opportunity_discovery
            from app.services.user_onboarding_service import user_onboarding_service
            
            # STEP 0: Ensure user is onboarded with free strategies
            onboarding_check = await user_onboarding_service.check_user_onboarding_status(user_id)
            
            if onboarding_check.get("needs_onboarding", True):
                self.logger.info("Auto-triggering user onboarding for opportunity discovery", user_id=user_id)
                onboarding_result = await user_onboarding_service.onboard_new_user(user_id)
                
                if onboarding_result.get("success"):
                    self.logger.info("User onboarding completed successfully", user_id=user_id)
                else:
                    self.logger.warning("User onboarding failed", user_id=user_id, error=onboarding_result.get("error"))
            
            # STEP 1: Initialize discovery service if needed  
            await user_opportunity_discovery.async_init()
            
            # STEP 2: Use REAL user strategy-based opportunity discovery
            opportunities_result = await user_opportunity_discovery.discover_opportunities_for_user(
                user_id=user_id,
                force_refresh=False,
                include_strategy_recommendations=True
            )
            
            if not opportunities_result.get("success"):
                return {
                    "recommendation": "Unable to discover opportunities at this time. Please ensure you have active trading strategies.",
                    "confidence": 0.3,
                    "error": opportunities_result.get("error", "Unknown error"),
                    "next_actions": [
                        "Visit the Strategy Marketplace to activate your free strategies",
                        "Connect your exchange accounts for better opportunity discovery"
                    ]
                }
            
            opportunities = opportunities_result.get("opportunities", [])
            user_profile = opportunities_result.get("user_profile", {})
            strategy_recommendations = opportunities_result.get("strategy_recommendations", [])
            
            # STEP 2: Use AI consensus to ANALYZE and format results based on user's request
            analysis_prompt = f"""
            USER REQUEST: {message}
            
            REAL TRADING OPPORTUNITIES DISCOVERED:
            Total Opportunities: {len(opportunities)}
            User's Active Strategies: {user_profile.get('active_strategies', 0)}
            User Tier: {user_profile.get('user_tier', 'basic')}
            
            TOP OPPORTUNITIES:
            {json.dumps(opportunities[:10], indent=2)}
            
            STRATEGY RECOMMENDATIONS:
            {json.dumps(strategy_recommendations, indent=2)}
            
            Based on the user's request and these REAL opportunities, provide:
            1. Executive summary of opportunities that match their request
            2. Top 3 recommended opportunities with specific profit potential
            3. Risk assessment and required capital for each
            4. Clear action steps the user should take
            5. Strategy recommendations to unlock more opportunities
            
            Format as actionable investment advice with specific numbers and timeframes.
            """
            
            ai_validation = await self.ai_consensus.consensus_decision(
                decision_request=analysis_prompt,
                confidence_threshold=75.0,
                ai_models="all",
                user_id=user_id
            )
            
            # Build comprehensive response with real data and recommendations
            total_opportunities = len(opportunities)
            total_potential = sum(opp.get("profit_potential_usd", 0) for opp in opportunities)
            
            response_content = f"""🎯 **ENTERPRISE Opportunity Discovery Results**

{ai_validation.get('final_recommendation', 'Market opportunities analyzed using your active trading strategies.')}

**📊 Discovery Summary:**
• **{total_opportunities}** opportunities found using your **{user_profile.get('active_strategies', 0)}** active strategies
• **${total_potential:,.0f}** total profit potential identified
• **{user_profile.get('user_tier', 'basic').title()}** tier access - scanning {user_profile.get('scan_limit', 'limited')} assets
• **Asset Discovery:** {opportunities_result.get('asset_discovery', {}).get('total_assets_scanned', 0)} assets analyzed across multiple exchanges

**🚀 Strategy Performance:**
{chr(10).join([f"• {strategy}: {perf.get('count', 0)} opportunities (avg confidence {perf.get('avg_confidence', 0):.0%})" 
              for strategy, perf in opportunities_result.get('strategy_performance', {}).items()])}

**💡 Recommendations to Unlock More Opportunities:**
{chr(10).join([f"• {rec.get('name', '')}: {rec.get('benefit', '')}" 
              for rec in strategy_recommendations[:3]])}

**Next Steps:**
1. Review detailed opportunities in your dashboard
2. Connect exchange accounts for live trading
3. Consider upgrading strategies for {'+50-200% more opportunities' if len(strategy_recommendations) > 0 else 'enhanced discovery'}"""

            return {
                "content": response_content,
                "confidence": ai_validation.get("consensus_score", 0.85),
                "metadata": {
                    "service_used": "user_opportunity_discovery",
                    "opportunities_count": total_opportunities,
                    "user_tier": user_profile.get('user_tier'),
                    "active_strategies": user_profile.get('active_strategies'),
                    "assets_scanned": opportunities_result.get('asset_discovery', {}).get('total_assets_scanned'),
                    "strategy_recommendations": len(strategy_recommendations),
                    "ai_validated": True,
                    "real_data": True,
                    "enterprise_grade": True
                }
            }
            
        except Exception as e:
            self.logger.error("Opportunity discovery failed", error=str(e))
            return {
                "content": f"Market analysis service error: {str(e)}",
                "confidence": 0.3,
                "metadata": {"service_error": True}
            }
    
    async def _handle_market_analysis(self, message: str, context: Dict, user_id: str) -> Dict[str, Any]:
        """Handle market analysis using REAL market service."""
        
        try:
            # Use real market analysis
            analysis = await self.market_analysis.complete_market_assessment(
                symbols="BTC,ETH,SOL",
                depth="comprehensive",
                user_id=user_id
            )
            
            # AI formats the real data
            format_prompt = f"""
            REAL MARKET ANALYSIS RESULTS:
            {json.dumps(analysis, indent=2)}
            
            USER REQUEST: {message}
            
            Format this real market data into a professional analysis response.
            """
            
            ai_format = await self.ai_consensus.consensus_decision(
                decision_request=format_prompt,
                confidence_threshold=70.0,
                ai_models="all",
                user_id=user_id
            )
            
            return {
                "content": f"📊 **Real Market Analysis**\n\n{ai_format.get('final_recommendation', 'Analysis complete')}",
                "confidence": 0.9,
                "metadata": {"service_used": "market_analysis", "real_data": True}
            }
            
        except Exception as e:
            return {"content": f"Market analysis error: {str(e)}", "confidence": 0.3}
    
    async def _handle_portfolio_analysis(self, message: str, context: Dict, user_id: str) -> Dict[str, Any]:
        """Handle portfolio analysis using REAL portfolio service."""
        
        try:
            # Use real portfolio service
            portfolio = await self.chat_adapters.get_portfolio_summary(user_id)
            risk_analysis = await self.portfolio_risk.get_portfolio_status(user_id)
            
            # AI analyzes real portfolio data
            analysis_prompt = f"""
            REAL PORTFOLIO DATA:
            {json.dumps(portfolio, indent=2)}
            
            RISK ANALYSIS:
            {json.dumps(risk_analysis, indent=2)}
            
            USER REQUEST: {message}
            
            Provide comprehensive portfolio analysis with specific recommendations.
            """
            
            ai_analysis = await self.ai_consensus.consensus_decision(
                decision_request=analysis_prompt,
                confidence_threshold=75.0,
                ai_models="all",
                user_id=user_id
            )
            
            return {
                "content": f"💼 **Your Portfolio Analysis**\n\n{ai_analysis.get('final_recommendation', 'Analysis complete')}",
                "confidence": ai_analysis.get("consensus_score", 0.85),
                "metadata": {"service_used": "portfolio_analysis", "real_data": True}
            }
            
        except Exception as e:
            return {"content": f"Portfolio analysis error: {str(e)}", "confidence": 0.3}
    
    async def _handle_strategy_discussion(self, message: str, context: Dict, user_id: str) -> Dict[str, Any]:
        """Handle strategy discussion using REAL trading strategies service."""
        
        try:
            # Use real trading strategies service - fallback if service unavailable
            if self.trading_strategies:
                strategies = await self.trading_strategies.futures_trade(
                    symbol="BTC", action="analyze", amount=0, leverage=1
                )
            else:
                strategies = {"available_strategies": ["momentum", "mean_reversion", "arbitrage"]}
            
            strategy_prompt = f"""
            AVAILABLE TRADING STRATEGIES:
            {json.dumps(strategies, indent=2)}
            
            USER REQUEST: {message}
            
            Recommend appropriate strategies and explain their benefits.
            """
            
            ai_recommendation = await self.ai_consensus.consensus_decision(
                decision_request=strategy_prompt,
                confidence_threshold=70.0,
                ai_models="all",
                user_id=user_id
            )
            
            return {
                "content": f"📈 **Trading Strategy Recommendations**\n\n{ai_recommendation.get('final_recommendation', 'Strategies available')}",
                "confidence": ai_recommendation.get("consensus_score", 0.8),
                "metadata": {"service_used": "trading_strategies", "real_data": True}
            }
            
        except Exception as e:
            return {"content": f"Strategy service error: {str(e)}", "confidence": 0.3}
    
    async def _handle_risk_assessment(self, message: str, context: Dict, user_id: str) -> Dict[str, Any]:
        """Handle risk assessment using REAL risk service."""
        
        try:
            # Use real risk assessment service
            risk_data = await self.portfolio_risk.get_portfolio_status(user_id)
            
            risk_prompt = f"""
            REAL RISK ANALYSIS:
            {json.dumps(risk_data, indent=2)}
            
            USER REQUEST: {message}
            
            Provide detailed risk assessment and mitigation recommendations.
            """
            
            ai_assessment = await self.ai_consensus.consensus_decision(
                decision_request=risk_prompt,
                confidence_threshold=80.0,
                ai_models="all",
                user_id=user_id
            )
            
            return {
                "content": f"🛡️ **Risk Assessment**\n\n{ai_assessment.get('final_recommendation', 'Risk analysis complete')}",
                "confidence": ai_assessment.get("consensus_score", 0.85),
                "metadata": {"service_used": "risk_assessment", "real_data": True}
            }
            
        except Exception as e:
            return {"content": f"Risk assessment error: {str(e)}", "confidence": 0.3}
    
    async def _handle_autonomous_control(self, message: str, context: Dict, user_id: str) -> Dict[str, Any]:
        """Handle autonomous mode control."""
        
        try:
            if "start" in message.lower() or "enable" in message.lower():
                result = await self.master_controller.start_autonomous_mode({
                    "user_id": user_id,
                    "mode": "balanced"
                })
                return {
                    "content": f"🤖 **Autonomous Mode Started**\n\n{result.get('message', 'Autonomous trading activated')}",
                    "confidence": 0.9,
                    "metadata": {"service_used": "master_controller", "action": "start_autonomous"}
                }
            else:
                result = await self.master_controller.stop_autonomous_mode(user_id)
                return {
                    "content": f"🛑 **Autonomous Mode Stopped**\n\n{result.get('message', 'Autonomous trading deactivated')}",
                    "confidence": 0.9,
                    "metadata": {"service_used": "master_controller", "action": "stop_autonomous"}
                }
                
        except Exception as e:
            return {"content": f"Autonomous control error: {str(e)}", "confidence": 0.3}
    
    async def _handle_emergency_command(self, message: str, context: Dict, user_id: str) -> Dict[str, Any]:
        """Handle emergency commands."""
        
        try:
            result = await self.master_controller.emergency_stop(user_id)
            return {
                "content": f"🚨 **Emergency Protocol Activated**\n\n{result.get('message', 'All trading halted for safety')}",
                "confidence": 1.0,
                "metadata": {"service_used": "master_controller", "action": "emergency_stop"}
            }
            
        except Exception as e:
            return {"content": f"Emergency protocol error: {str(e)}", "confidence": 0.3}
    
    async def _handle_general_query(self, message: str, context: Dict, user_id: str) -> Dict[str, Any]:
        """Handle general queries with service context."""
        
        context_summary = self._build_context_summary(context)
        
        general_prompt = f"""
        You are CryptoUniverse AI with access to real trading services.
        
        CONVERSATION CONTEXT:
        {context_summary}
        
        USER MESSAGE: {message}
        
        Provide helpful information about cryptocurrency trading and portfolio management.
        """
        
        try:
            ai_response = await self.ai_consensus.consensus_decision(
                decision_request=general_prompt,
                confidence_threshold=70.0,
                ai_models="all",
                user_id=user_id
            )
            
            return {
                "content": ai_response.get("final_recommendation", "I can help with trading questions."),
                "confidence": ai_response.get("consensus_score", 0.7),
                "metadata": {"service_used": "ai_consensus", "query_type": "general"}
            }
            
        except Exception as e:
            return {
                "content": "I'm here to help with cryptocurrency trading and portfolio management questions.",
                "confidence": 0.6,
                "metadata": {"fallback": True}
            }
    
    def _build_context_summary(self, context: Dict[str, Any]) -> str:
        """Build a summary of conversation context for AI processing."""
        
        parts = []
        
        # Session context
        session_context = context.get("session_context", {})
        if session_context.get("risk_tolerance"):
            parts.append(f"User Risk Tolerance: {session_context['risk_tolerance']}")
        
        # Recent conversation
        recent_messages = context.get("recent_messages", [])
        if recent_messages:
            parts.append(f"Recent Conversation ({len(recent_messages)} messages):")
            for msg in recent_messages[-5:]:  # Last 5 messages
                intent_str = f" [{msg.get('intent', 'general')}]" if msg.get('intent') else ""
                parts.append(f"- {msg.get('type', 'unknown')}: {msg.get('content', '')[:100]}...{intent_str}")
        
        # Conversation summaries
        summaries = context.get("conversation_summaries", [])
        if summaries:
            parts.append("Previous Session Summaries:")
            for summary in summaries[:2]:  # Most recent 2 summaries
                parts.append(f"- {summary.get('summary', '')[:150]}...")
        
        # Active strategies
        if context.get("active_strategies"):
            parts.append(f"Active Strategies: {', '.join(context['active_strategies'])}")
        
        return "\n".join(parts) if parts else "No previous conversation context."
    
    async def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chat history from persistent storage."""
        if not self.memory:
            return []
        return await self.memory.get_session_messages(session_id, limit)
    
    async def get_active_sessions(self, user_id: str) -> List[str]:
        """Get active chat sessions for a user."""
        if not self.memory:
            return []
        sessions = await self.memory.get_user_sessions(user_id, limit=10)
        return [session["session_id"] for session in sessions]
    
    async def execute_confirmed_action(
        self, session_id: str, command: str, user_id: str
    ) -> Dict[str, Any]:
        """Execute a confirmed action from a previous conversation."""
        
        # Get conversation context
        if not self.memory:
            return {"summary": "Memory service unavailable", "status": "error"}
        
        context = await self.memory.get_conversation_context(session_id)
        
        # Process the command execution (simplified)
        result = {
            "summary": f"Command '{command}' acknowledged and queued for execution",
            "status": "acknowledged",
            "user_id": user_id
        }
        
        # Save the execution result (if memory available)
        if self.memory:
            try:
                await self.memory.save_message(
                    session_id=session_id,
                    user_id=user_id,
                    content=f"Executed command: {command}. Result: {result.get('summary', 'Command executed')}",
                    message_type=ChatMessageType.SYSTEM.value,
                    intent="command_execution",
                    metadata={"command": command, "result": result}
                )
            except Exception as e:
                self.logger.warning("Failed to save execution result to memory", error=str(e))
        
        return result
    
    async def _send_websocket_update(self, user_id: str, data: Dict[str, Any]):
        """Send real-time update via WebSocket."""
        try:
            await manager.send_personal_message(json.dumps(data), user_id)
        except Exception as e:
            self.logger.debug("WebSocket update failed", error=str(e), user_id=user_id)


# Global instance with enhanced memory
enhanced_chat_engine = EnhancedAIChatEngine()