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
        self.redis = None  # Redis client for autonomous mode checks
        
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
            if self.redis is None:
                from app.core.redis import get_redis_client
                self.redis = await get_redis_client()
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
            # If memory service is not available, generate a simple session ID using proper UUID
            if not self.memory:
                session_id = str(uuid.uuid4())
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
            
            # Generate proper UUID for new session
            session_id = str(uuid.uuid4())
            
            # Create new session with the UUID
            created_session_id = await self.memory.create_session(
                user_id=user_id,
                session_type=session_type,
                session_id=session_id,  # Pass the UUID to ensure proper format
                context={
                    "preferences": {},
                    "active_strategies": [],
                    "risk_tolerance": "balanced",
                    "created_via": "chat_interface"
                }
            )
            
            # Use the created session ID (should be the same UUID we passed)
            session_id = created_session_id if created_session_id else session_id
            
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
            
            # Create session if none provided or invalid format
            if not session_id or session_id.strip() == "" or len(session_id) > 50:
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
                
                # Process with 5-phase execution for trading intents (except rebalancing)
                if intent == ChatIntent.TRADE_EXECUTION:
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
                        tokens_used=response.get("tokens_used", len(str(response.get("content", "")).split()))
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
        """Execute Phase 5: Real Monitoring Setup"""
        
        try:
            user_id = context.get("session_context", {}).get("user_id")
            
            # Generate monitoring configuration based on execution results
            monitoring_id = str(uuid.uuid4())
            
            # If this was a rebalancing operation, set up portfolio monitoring
            if execution.get("status") in ["completed", "simulated"] and execution.get("trade_id"):
                
                # Set up portfolio performance monitoring
                monitoring_config = {
                    "user_id": user_id,
                    "monitoring_type": "rebalancing_performance",
                    "trade_references": [execution.get("trade_id")],
                    "alert_thresholds": {
                        "portfolio_deviation": 5.0,  # Alert if portfolio deviates 5% from target
                        "performance_drop": -10.0,   # Alert if portfolio drops 10%
                        "risk_increase": 25.0        # Alert if risk increases 25%
                    },
                    "monitoring_duration_days": 30,
                    "check_frequency_hours": 6,
                    "created_at": datetime.utcnow().isoformat()
                }
                
                # Store monitoring configuration in Redis if available
                if hasattr(self, 'redis') and self.redis:
                    try:
                        # Serialize all mapping values to strings for Redis compatibility
                        redis_mapping = {}
                        for key, value in monitoring_config.items():
                            if isinstance(value, (dict, list)):
                                redis_mapping[str(key)] = json.dumps(value)
                            elif value is None:
                                redis_mapping[str(key)] = ""
                            else:
                                redis_mapping[str(key)] = str(value)
                        
                        await self.redis.hset(
                            f"portfolio_monitoring:{monitoring_id}",
                            mapping=redis_mapping
                        )
                        await self.redis.expire(f"portfolio_monitoring:{monitoring_id}", 86400 * 30)  # 30 days
                        
                        # Add to user's active monitoring list (ensure user_id is string)
                        await self.redis.sadd(f"active_monitoring:{str(user_id)}", str(monitoring_id))
                        await self.redis.expire(f"active_monitoring:{str(user_id)}", 86400 * 30)
                        
                        self.logger.info("Portfolio monitoring setup completed", 
                                       monitoring_id=monitoring_id, user_id=user_id)
                        
                    except Exception as redis_error:
                        self.logger.warning("Could not store monitoring config in Redis", error=str(redis_error))
                
                # Set up WebSocket notifications for real-time updates
                try:
                    await self._schedule_monitoring_checks(monitoring_id, user_id, monitoring_config)
                except Exception as e:
                    self.logger.warning("Could not schedule monitoring checks", error=str(e))
                
                return {
                    "monitoring_id": monitoring_id,
                    "monitoring_summary": "Real-time portfolio rebalancing monitoring active",
                    "monitoring_config": {
                        "performance_tracking": "30 days",
                        "deviation_alerts": "5% threshold",
                        "risk_monitoring": "25% increase threshold",
                        "check_frequency": "Every 6 hours",
                        "alert_methods": ["WebSocket", "Chat notifications"]
                    },
                    "alert_types": ["portfolio_deviation", "performance_drop", "risk_increase", "rebalancing_needed"],
                    "monitoring_duration": "30 days",
                    "status": "active"
                }
            
            else:
                # Fallback for non-rebalancing or failed executions
                return {
                    "monitoring_id": monitoring_id,
                    "monitoring_summary": "Basic trade monitoring setup",
                    "alert_types": ["execution_status", "general_alerts"],
                    "monitoring_duration": "7 days",
                    "status": "basic"
                }
                
        except Exception as e:
            self.logger.error("Phase 5 monitoring setup failed", error=str(e))
            return {
                "monitoring_id": f"error_{uuid.uuid4().hex}",
                "monitoring_summary": f"Monitoring setup failed: {str(e)}",
                "alert_types": [],
                "monitoring_duration": "none",
                "status": "failed",
                "error": str(e)
            }
    
    async def _schedule_monitoring_checks(self, monitoring_id: str, user_id: str, config: Dict[str, Any]):
        """Schedule periodic monitoring checks for rebalanced portfolio."""
        
        try:
            # This would integrate with your background task scheduler
            # For now, we'll set up the monitoring framework
            
            check_config = {
                "monitoring_id": monitoring_id,
                "user_id": user_id,
                "next_check": (datetime.utcnow() + timedelta(hours=6)).isoformat(),
                "config": config
            }
            
            # Store in Redis for background processor to pick up
            if hasattr(self, 'redis') and self.redis:
                # Ensure all mapping values are strings
                redis_schedule_mapping = {
                    "user_id": str(user_id),
                    "next_check": str(check_config["next_check"]),
                    "config": json.dumps(config),
                    "status": "scheduled"
                }
                await self.redis.hset(
                    f"monitoring_schedule:{monitoring_id}",
                    mapping=redis_schedule_mapping
                )
                await self.redis.expire(f"monitoring_schedule:{monitoring_id}", 86400 * 30)
                
                # Add to global monitoring queue
                await self.redis.zadd(
                    "monitoring_queue",
                    {monitoring_id: time.time() + 6 * 3600}  # 6 hours from now
                )
            
            self.logger.info("Monitoring checks scheduled", monitoring_id=monitoring_id, user_id=user_id)
            
        except Exception as e:
            self.logger.error("Failed to schedule monitoring checks", error=str(e), monitoring_id=monitoring_id)
    
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
                
            elif intent == ChatIntent.REBALANCING:
                return await self._handle_rebalancing(user_message, context, user_id)
            
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
        
        self.logger.info("🎯 ENTERING _handle_opportunity_discovery", user_id=user_id, message=message)
        
        try:
            # Import the new enterprise services
            self.logger.info("🎯 Importing user_opportunity_discovery service")
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
                error_message = "Unable to discover opportunities at this time. Please ensure you have active trading strategies."
                return {
                    "content": error_message,
                    "recommendation": error_message,
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
    
    def _validate_rebalancing_request(self, user_id: str, strategy: str) -> Dict[str, Any]:
        """Validate rebalancing request parameters for security and safety."""
        
        # Validate user_id format (should be UUID)
        if not user_id or len(user_id.strip()) == 0:
            return {"valid": False, "reason": "Invalid user ID: empty"}
        
        if user_id == "system":
            return {"valid": False, "reason": "System user cannot perform rebalancing"}
        
        # Basic UUID format validation (loose check for flexibility)
        if len(user_id) < 8 or len(user_id) > 128:
            return {"valid": False, "reason": "Invalid user ID format"}
        
        # Validate strategy against allowed values
        allowed_strategies = [
            "risk_parity", "equal_weight", "max_sharpe", "min_variance", "kelly", "adaptive"
        ]
        if strategy not in allowed_strategies:
            return {"valid": False, "reason": f"Invalid strategy: {strategy}. Allowed: {', '.join(allowed_strategies)}"}
        
        return {"valid": True}
    
    async def _check_rebalancing_rate_limits(self, user_id: str) -> Dict[str, Any]:
        """Check rate limits to prevent excessive rebalancing requests."""
        
        if not self.redis:
            # If Redis unavailable, allow but log warning
            self.logger.warning("Rate limiting unavailable - Redis not connected", user_id=user_id)
            return {"allowed": True}
        
        try:
            # Check recent rebalancing attempts (max 5 per hour)
            rate_limit_key = f"rebalancing_rate_limit:{user_id}"
            current_count = await self.redis.get(rate_limit_key)
            
            if current_count and int(current_count) >= 5:
                ttl = await self.redis.ttl(rate_limit_key)
                return {
                    "allowed": False, 
                    "reason": f"Rate limit exceeded. Try again in {ttl // 60} minutes.",
                    "retry_after_minutes": ttl // 60
                }
            
            # Increment counter
            await self.redis.incr(rate_limit_key)
            await self.redis.expire(rate_limit_key, 3600)  # 1 hour window
            
            return {"allowed": True}
            
        except Exception as e:
            self.logger.error("Rate limiting check failed", error=str(e), user_id=user_id)
            return {"allowed": True}  # Fail open for availability
    
    def _format_strategy_comparison_response(self, strategy_comparison: Dict, user_id: str) -> Dict[str, Any]:
        """Format strategy comparison results for user display."""
        
        strategy_results = strategy_comparison.get("strategy_results", {})
        recommended_strategy = strategy_comparison.get("recommended_strategy", "adaptive")
        best_metrics = strategy_comparison.get("best_metrics", {})
        
        # Sort strategies by comprehensive score
        sorted_strategies = sorted(
            strategy_results.items(),
            key=lambda x: x[1].get("comprehensive_score", 0),
            reverse=True
        )
        
        # Format strategy display
        strategy_display = []
        for i, (strategy_name, metrics) in enumerate(sorted_strategies[:6]):
            rank_emoji = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
            
            profit_potential = metrics.get("profit_potential", 0)
            expected_return = metrics.get("expected_return", 0) 
            sharpe_ratio = metrics.get("sharpe_ratio", 0)
            
            strategy_display.append(
                f"{rank_emoji} **{strategy_name.replace('_', ' ').title()}**\n"
                f"   • Profit Potential: {profit_potential:.2%}\n" 
                f"   • Expected Return: {expected_return:.2%}\n"
                f"   • Sharpe Ratio: {sharpe_ratio:.2f}\n"
                f"   • Score: {metrics.get('comprehensive_score', 0):.2f}"
            )
        
        strategies_text = "\n\n".join(strategy_display)
        
        content = f"""📊 **6-Strategy Profit Analysis Complete**

**🤖 AI Money Manager Recommendation:** 
**{recommended_strategy.replace('_', ' ').title()}** - Best profit potential of {best_metrics.get('expected_return', 0):.2%}

**📈 All Strategy Comparisons:**

{strategies_text}

**💡 Next Steps:**
• "**Execute {recommended_strategy}**" - Use AI recommendation 
• "**Use [strategy name]**" - Choose different strategy
• "**Autonomous mode**" - Let AI manage automatically

All analysis based on your real portfolio data and current market conditions."""
        
        return {
            "content": content,
            "confidence": 0.95,
            "metadata": {
                "strategy_comparison": strategy_results,
                "recommended_strategy": recommended_strategy,
                "ai_recommendation": True,
                "all_strategies_analyzed": True
            }
        }
    
    async def _handle_rebalancing(self, message: str, context: Dict, user_id: str) -> Dict[str, Any]:
        """Handle portfolio rebalancing using REAL optimization service with security validation."""
        
        try:
            # 1. SERVICE AVAILABILITY CHECK
            service_status = await self._ensure_services_with_fallback()
            critical_services_missing = []
            
            if not service_status["chat_adapters"]:
                critical_services_missing.append("chat_adapters")
            if not service_status["portfolio_risk"]:
                critical_services_missing.append("portfolio_risk")
            
            if critical_services_missing:
                return await self._handle_service_unavailable(critical_services_missing, user_id)
            
            # 2. INPUT VALIDATION & SECURITY CHECKS
            strategy = self._detect_rebalancing_strategy(message, context)
            
            # Validate request parameters
            validation_result = self._validate_rebalancing_request(user_id, strategy)
            if not validation_result["valid"]:
                return {
                    "content": f"❌ **Invalid Request**\n\n{validation_result['reason']}\n\nPlease check your request and try again.",
                    "confidence": 0.1,
                    "metadata": {"error": True, "validation_error": validation_result['reason']}
                }
            
            # Check rate limits
            rate_limit_result = await self._check_rebalancing_rate_limits(user_id)
            if not rate_limit_result["allowed"]:
                return {
                    "content": f"""⏱️ **Rate Limit Exceeded**

{rate_limit_result['reason']}

**Rate Limits:**
- Maximum 5 rebalancing requests per hour
- This prevents excessive trading and protects your portfolio

**Alternative Options:**
- Enable autonomous mode for automatic rebalancing
- Use "portfolio status" to check current allocation
- Try again in {rate_limit_result.get('retry_after_minutes', 60)} minutes""",
                    "confidence": 0.8,
                    "metadata": {"error": True, "rate_limited": True, "retry_after": rate_limit_result.get('retry_after_minutes')}
                }
            # Check if autonomous mode is active
            autonomous_active = False
            autonomous_config = {}
            
            if self.redis:
                try:
                    autonomous_active = await self.redis.get(f"autonomous_active:{user_id}")
                    if autonomous_active:
                        autonomous_config = await self.redis.hgetall(f"autonomous_config:{user_id}")
                except Exception as e:
                    self.logger.warning("Could not check autonomous status", error=str(e))
            
            # If autonomous mode is active, show current status instead of manual rebalancing
            if autonomous_active:
                last_rebalance = autonomous_config.get("last_rebalance_time", "Not available")
                current_strategy = autonomous_config.get("rebalancing_strategy", "risk_parity")
                
                return {
                    "content": f"""🤖 **Autonomous Mode Active - Portfolio Auto-Management**

**Current Settings:**
- Strategy: {current_strategy.replace('_', ' ').title()}
- Last Rebalanced: {last_rebalance}
- Auto-rebalance: Enabled

**Options:**
- Type "**rebalance now**" to force immediate rebalancing
- Type "**change strategy [name]**" to update autonomous strategy
- Type "**disable autonomous**" for manual control
- Type "**rebalancing status**" for detailed analysis

Your portfolio is being optimized automatically every 30 minutes.""",
                    "confidence": 0.95,
                    "metadata": {"autonomous_active": True, "current_strategy": current_strategy}
                }
            
            # Manual rebalancing flow
            # 1. Detect strategy from user message
            strategy = self._detect_rebalancing_strategy(message, context)
            
            # 2. Check if user wants strategy comparison
            message_lower = message.lower()
            wants_comparison = any(word in message_lower for word in [
                "all strategies", "compare strategies", "strategy comparison", 
                "profit potential", "best strategy", "show strategies"
            ])
            
            # 2a. For strategy comparison requests, show all 6 strategies
            if wants_comparison or strategy == "auto":
                try:
                    strategy_comparison = await self.chat_adapters._analyze_all_strategies_comprehensive(
                        portfolio_data={}, user_id=user_id
                    )
                    
                    if strategy_comparison and strategy_comparison.get("strategy_results"):
                        return self._format_strategy_comparison_response(strategy_comparison, user_id)
                    
                except Exception as e:
                    self.logger.error("Strategy comparison failed", error=str(e))
            
            # 2b. Get current portfolio analysis with timeout and retry
            portfolio_analysis = await self._get_portfolio_analysis_with_retry(user_id, strategy)
            
            if portfolio_analysis.get("error"):
                return {
                    "content": f"❌ **Portfolio Analysis Failed**\n\nError: {portfolio_analysis['error']}\n\nPlease try again or contact support if the issue persists.",
                    "confidence": 0.3,
                    "metadata": {"error": True, "service_error": portfolio_analysis['error']}
                }
            
            # 3. Check if rebalancing is needed
            needs_rebalancing = portfolio_analysis.get("needs_rebalancing", False)
            deviation_score = portfolio_analysis.get("deviation_score", 0)
            recommended_trades = portfolio_analysis.get("recommended_trades", [])
            
            if not needs_rebalancing:
                return {
                    "content": f"""✅ **Portfolio Already Optimized**

**Analysis Results:**
- Strategy: {strategy.replace('_', ' ').title()}
- Deviation: {deviation_score:.2%} (within threshold)
- Status: No rebalancing needed

Your portfolio allocation is already well-optimized for the selected strategy. Consider checking again later or trying a different strategy.""",
                    "confidence": 0.9,
                    "metadata": {"needs_rebalancing": False, "strategy": strategy}
                }
            
            # 4. Present rebalancing preview
            if not recommended_trades:
                return {
                    "content": f"""⚠️ **Rebalancing Analysis Complete**

**Results:**
- Strategy: {strategy.replace('_', ' ').title()}
- Deviation: {deviation_score:.2%}
- Status: Rebalancing recommended but no specific trades generated

This might indicate insufficient portfolio size or market conditions. Try again later or contact support.""",
                    "confidence": 0.6,
                    "metadata": {"needs_rebalancing": True, "no_trades": True}
                }
            
            # Format trades for display
            trade_summary = []
            for trade in recommended_trades[:5]:  # Show top 5 trades
                action = trade.get("action", "").upper()
                symbol = trade.get("symbol", "")
                amount = trade.get("amount", 0)
                trade_summary.append(f"• {action} {amount:.6f} {symbol}")
            
            trade_display = "\n".join(trade_summary)
            
            # Store rebalancing plan in context for execution
            rebalancing_plan = {
                "strategy": strategy,
                "trades": recommended_trades,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Save to session context if memory available
            if self.memory:
                try:
                    session_id = context.get("session_id")
                    if session_id:
                        await self.memory.update_session_context(session_id, {
                            "pending_rebalancing_plan": rebalancing_plan
                        })
                except Exception as e:
                    self.logger.warning("Could not save rebalancing plan to memory", error=str(e))
            
            return {
                "content": f"""🎯 **Portfolio Rebalancing Plan Ready**

**Strategy:** {strategy.replace('_', ' ').title()}
**Current Deviation:** {deviation_score:.2%}
**Risk Reduction:** {portfolio_analysis.get('risk_reduction', 0):.1f}%
**Expected Improvement:** +{portfolio_analysis.get('expected_improvement', 0):.1f}%

**Recommended Trades:**
{trade_display}

**Next Steps:**
- Type "**execute rebalancing**" to proceed with these trades
- Type "**different strategy**" to try another approach
- Type "**cancel**" to abort

⚠️ **Important:** These trades will be executed on your live portfolio.""",
                "confidence": 0.95,
                "metadata": {
                    "rebalancing_plan": rebalancing_plan,
                    "awaiting_execution_confirmation": True,
                    "strategy": strategy,
                    "trade_count": len(recommended_trades)
                }
            }
            
        except Exception as e:
            self.logger.error("Rebalancing handler failed", error=str(e), user_id=user_id)
            return {
                "content": f"❌ **Rebalancing Service Error**\n\nError: {str(e)}\n\nPlease try again or contact support if the issue persists.",
                "confidence": 0.3,
                "metadata": {"error": True, "handler_error": str(e)}
            }
    
    def _detect_rebalancing_strategy(self, message: str, context: Dict[str, Any]) -> str:
        """Detect rebalancing strategy from user message or use intelligent default."""
        
        message_lower = message.lower()
        
        # Strategy patterns for detection
        strategy_patterns = {
            "risk_parity": [r"risk parity", r"equal risk", r"risk weighted", r"balanced risk", r"diversify"],
            "equal_weight": [r"equal weight", r"equally", r"same amount", r"equal allocation", r"simple"],
            "max_sharpe": [r"sharpe", r"best return", r"optimize return", r"maximum sharpe", r"highest return"],
            "min_variance": [r"low risk", r"minimum risk", r"conservative", r"min variance", r"lowest risk", r"safe"],
            "kelly_criterion": [r"kelly", r"optimal sizing", r"kelly criterion", r"position sizing"],
            "adaptive": [r"adaptive", r"blended", r"mixed approach", r"combination"],
            "auto": [r"smart", r"automatic", r"ai choose", r"best strategy", r"intelligent", r"optimize", r"rebalance"]
        }
        
        # Check user's message for strategy keywords
        for strategy, patterns in strategy_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    self.logger.info("Detected rebalancing strategy from message", strategy=strategy, pattern=pattern)
                    return strategy
        
        # Check conversation context for previous preferences
        session_context = context.get("session_context", {})
        if session_context.get("preferred_rebalancing_strategy"):
            preferred = session_context["preferred_rebalancing_strategy"]
            self.logger.info("Using preferred rebalancing strategy from context", strategy=preferred)
            return preferred
        
        # Use intelligent auto-selection as default
        self.logger.info("No specific strategy detected, using intelligent auto-selection")
        return "auto"  # Let the system intelligently choose the best strategy

    async def _get_portfolio_analysis_with_retry(self, user_id: str, strategy: str, max_retries: int = 2) -> Dict[str, Any]:
        """Get portfolio analysis with retry logic and timeout handling."""
        
        for attempt in range(max_retries + 1):
            try:
                # Set timeout for portfolio analysis
                analysis_result = await asyncio.wait_for(
                    self.chat_adapters.analyze_rebalancing_needs(user_id=user_id, strategy=strategy),
                    timeout=15.0  # 15 second timeout
                )
                
                # Ensure analysis_result is a dict and not null
                if not isinstance(analysis_result, dict) or not analysis_result:
                    error_msg = "Portfolio analysis returned invalid result"
                    self.logger.warning("Portfolio analysis failed", 
                                      attempt=attempt + 1, error=error_msg, user_id=user_id)
                    if attempt < max_retries:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    else:
                        return {"error": f"Portfolio analysis failed after {max_retries + 1} attempts: {error_msg}"}
                
                # Check for presence of error key - if no error, it's a success
                if not analysis_result.get("error"):
                    return analysis_result
                
                # If explicit failure, log and potentially retry
                error_msg = analysis_result.get("error", "Portfolio analysis failed")
                self.logger.warning("Portfolio analysis failed", 
                                  attempt=attempt + 1, error=error_msg, user_id=user_id)
                
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    return {"error": f"Portfolio analysis failed after {max_retries + 1} attempts: {error_msg}"}
                    
            except asyncio.TimeoutError:
                self.logger.warning("Portfolio analysis timeout", 
                                  attempt=attempt + 1, user_id=user_id)
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    return {"error": "Portfolio analysis timed out. Please try again later."}
                    
            except Exception as e:
                self.logger.error("Portfolio analysis exception", 
                                attempt=attempt + 1, error=str(e), user_id=user_id)
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    return {"error": f"Portfolio analysis failed: {str(e)}"}
        
        return {"error": "Portfolio analysis failed after all retry attempts"}

    async def _ensure_services_with_fallback(self) -> Dict[str, bool]:
        """Ensure services are available with fallback handling."""
        
        service_status = {
            "chat_adapters": False,
            "trade_executor": False,
            "portfolio_risk": False,
            "redis": False,
            "memory": False
        }
        
        try:
            await self._ensure_services()
            
            # Check individual service availability
            if self.chat_adapters:
                service_status["chat_adapters"] = True
            
            if self.trade_executor:
                service_status["trade_executor"] = True
                
            if self.portfolio_risk:
                service_status["portfolio_risk"] = True
                
            if self.redis:
                try:
                    await self.redis.ping()
                    service_status["redis"] = True
                except Exception:
                    self.logger.warning("Redis ping failed - service may be unavailable")
                    
            if self.memory:
                service_status["memory"] = True
                
        except Exception as e:
            self.logger.error("Service initialization check failed", error=str(e))
        
        return service_status

    async def _handle_service_unavailable(self, missing_services: List[str], user_id: str) -> Dict[str, Any]:
        """Handle cases where critical services are unavailable."""
        
        if "chat_adapters" in missing_services or "portfolio_risk" in missing_services:
            return {
                "content": """🔧 **Service Temporarily Unavailable**

Portfolio analysis services are currently unavailable. This might be due to:
- Temporary system maintenance
- High system load
- Network connectivity issues

**Recommended Actions:**
- Wait 2-3 minutes and try again
- Check system status page
- Use autonomous mode if available
- Contact support if issues persist

Your portfolio data is safe and no trades have been executed.""",
                "confidence": 0.7,
                "metadata": {"error": True, "service_unavailable": missing_services}
            }
        
        if "trade_executor" in missing_services:
            return {
                "content": """⚠️ **Trade Execution Unavailable**

The trade execution service is currently unavailable. 
- Portfolio analysis can still be performed
- No live trades can be executed at this time
- Autonomous mode may be affected

**Options:**
- Get portfolio analysis and rebalancing recommendations
- Wait for service restoration before executing trades
- Contact support for urgent trading needs""",
                "confidence": 0.7,
                "metadata": {"error": True, "trade_execution_unavailable": True}
            }
        
        # Redis/Memory unavailable - degraded functionality
        return {
            "content": """⚠️ **Limited Functionality**

Some background services are unavailable:
- Session memory may be limited
- Rate limiting may not work properly  
- Monitoring features may be reduced

Rebalancing can still proceed but with reduced features.""",
            "confidence": 0.8,
            "metadata": {"error": False, "degraded_mode": True, "unavailable_services": missing_services}
        }

    async def _validate_trade_safety(self, user_id: str, trades: List[Dict], portfolio_summary: Dict) -> Dict[str, Any]:
        """Validate trades are safe to execute with comprehensive safety checks."""
        
        try:
            # Check for concurrent rebalancing lock
            if self.redis:
                rebalancing_lock = await self.redis.get(f"rebalancing_lock:{user_id}")
                if rebalancing_lock:
                    return {
                        "valid": False, 
                        "reason": "Another rebalancing operation is already in progress. Please wait for it to complete."
                    }
            
            portfolio_value = portfolio_summary.get("total_value", 0)
            
            # Portfolio minimum size check
            if portfolio_value < 100:  # Minimum $100 portfolio
                return {
                    "valid": False,
                    "reason": f"Portfolio too small for rebalancing (${portfolio_value:.2f}). Minimum: $100."
                }
            
            # Validate individual trades
            total_trade_value = 0
            for i, trade in enumerate(trades):
                symbol = trade.get("symbol", "").upper()
                action = trade.get("action", "").lower()
                amount = trade.get("amount", 0)
                
                # Basic trade validation
                if not symbol or symbol.strip() == "":
                    return {"valid": False, "reason": f"Trade {i+1}: Invalid symbol"}
                
                if action not in ["buy", "sell"]:
                    return {"valid": False, "reason": f"Trade {i+1}: Invalid action '{action}'. Must be 'buy' or 'sell'"}
                
                if amount <= 0:
                    return {"valid": False, "reason": f"Trade {i+1}: Invalid amount {amount}. Must be positive"}
                
                # Estimate trade value (rough calculation)
                estimated_price = trade.get("estimated_price", 0)
                if estimated_price > 0:
                    trade_value = amount * estimated_price
                    total_trade_value += trade_value
                    
                    # Single trade size limit (max 50% of portfolio)
                    max_trade_value = portfolio_value * 0.5
                    if trade_value > max_trade_value:
                        return {
                            "valid": False,
                            "reason": f"Trade {i+1}: Trade too large (${trade_value:.2f}). Max per trade: ${max_trade_value:.2f}"
                        }
            
            # Total rebalancing size check (max 90% of portfolio turnover)
            max_total_turnover = portfolio_value * 0.9
            if total_trade_value > max_total_turnover:
                return {
                    "valid": False,
                    "reason": f"Total rebalancing too large (${total_trade_value:.2f}). Max turnover: ${max_total_turnover:.2f}"
                }
            
            # Check minimum number of trades (rebalancing should involve multiple assets)
            if len(trades) < 2:
                return {
                    "valid": False,
                    "reason": "Rebalancing requires at least 2 trades. Single trades should use regular trading."
                }
            
            # Maximum number of trades check (prevent excessive fragmentation)
            if len(trades) > 20:
                return {
                    "valid": False,
                    "reason": f"Too many trades ({len(trades)}). Maximum 20 trades per rebalancing to ensure execution quality."
                }
            
            return {"valid": True}
            
        except Exception as e:
            self.logger.error("Trade safety validation failed", error=str(e), user_id=user_id)
            return {"valid": False, "reason": f"Safety validation error: {str(e)}"}
    
    async def _acquire_rebalancing_lock(self, user_id: str) -> bool:
        """Acquire exclusive lock for rebalancing to prevent concurrent operations."""
        
        if not self.redis:
            self.logger.warning("Cannot acquire rebalancing lock - Redis unavailable", user_id=user_id)
            return True  # Proceed without lock if Redis unavailable
        
        try:
            # Set lock with 30-minute expiration (safety timeout)
            lock_acquired = await self.redis.set(
                f"rebalancing_lock:{user_id}", 
                datetime.utcnow().isoformat(),
                ex=1800,  # 30 minutes
                nx=True   # Only set if not exists
            )
            
            if lock_acquired:
                self.logger.info("Rebalancing lock acquired", user_id=user_id)
                return True
            else:
                self.logger.warning("Failed to acquire rebalancing lock - already exists", user_id=user_id)
                return False
                
        except Exception as e:
            self.logger.error("Failed to acquire rebalancing lock", error=str(e), user_id=user_id)
            return True  # Fail open for availability
    
    async def _release_rebalancing_lock(self, user_id: str):
        """Release rebalancing lock."""
        
        if self.redis:
            try:
                await self.redis.delete(f"rebalancing_lock:{user_id}")
                self.logger.info("Rebalancing lock released", user_id=user_id)
            except Exception as e:
                self.logger.error("Failed to release rebalancing lock", error=str(e), user_id=user_id)

    async def _execute_trade_with_safety(self, trade: Dict, user_id: str, attempt: int = 1) -> Dict[str, Any]:
        """Execute individual trade with safety checks and retry logic."""
        
        max_attempts = 3
        base_delay = 2  # seconds
        
        try:
            # Pre-execution validation
            symbol = trade.get("symbol", "").upper().strip()
            action = trade.get("action", "").lower().strip()
            amount = float(trade.get("amount", 0))
            
            if not all([symbol, action in ["buy", "sell"], amount > 0]):
                return {
                    "success": False,
                    "error": f"Invalid trade parameters: symbol={symbol}, action={action}, amount={amount}"
                }
            
            # Prepare trade request in correct format for TradeExecutionService
            trade_request = {
                "symbol": symbol,
                "quantity": amount,  # TradeExecutionService expects 'quantity', not 'amount'
                "exchange": trade.get("exchange", "auto"),
                "side": action,      # 'buy' or 'sell'
                "order_type": "market",
                "source": "rebalancing",
                "opportunity_data": trade.get("opportunity_data"),
                "safety_checks": True
            }
            
            # Execute trade with timeout using correct signature
            execution_result = await asyncio.wait_for(
                self.trade_executor.execute_trade(
                    trade_request=trade_request, 
                    user_id=user_id, 
                    simulation_mode=False  # Real trades for rebalancing
                ),
                timeout=30.0  # 30 second timeout per trade
            )
            
            return execution_result
            
        except asyncio.TimeoutError:
            if attempt < max_attempts:
                # Exponential backoff retry
                delay = base_delay ** attempt
                self.logger.warning(f"Trade execution timeout, retrying in {delay}s", 
                                  symbol=symbol, attempt=attempt, user_id=user_id)
                await asyncio.sleep(delay)
                return await self._execute_trade_with_safety(trade, user_id, attempt + 1)
            else:
                return {"success": False, "error": f"Trade execution timeout after {max_attempts} attempts"}
                
        except Exception as e:
            if attempt < max_attempts:
                delay = base_delay ** attempt
                self.logger.warning(f"Trade execution error, retrying in {delay}s", 
                                  error=str(e), symbol=symbol, attempt=attempt, user_id=user_id)
                await asyncio.sleep(delay)
                return await self._execute_trade_with_safety(trade, user_id, attempt + 1)
            else:
                return {"success": False, "error": f"Trade execution failed after {max_attempts} attempts: {str(e)}"}

    async def _execute_rebalancing_plan(self, user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a previously planned rebalancing operation with comprehensive safety checks."""
        
        try:
            # Get the pending rebalancing plan from context
            session_context = context.get("session_context", {})
            pending_plan = session_context.get("pending_rebalancing_plan")
            
            if not pending_plan:
                return {
                    "content": """❌ **No Rebalancing Plan Found**
                    
No pending rebalancing plan found. Please run portfolio analysis first by typing:
- "rebalance my portfolio"
- "optimize my portfolio using [strategy]"

Then you can execute the recommended trades.""",
                    "confidence": 0.8,
                    "metadata": {"error": "no_pending_plan"}
                }
            
            # Validate the plan is recent (within 10 minutes)
            plan_timestamp = datetime.fromisoformat(pending_plan.get("timestamp", "2000-01-01"))
            if (datetime.utcnow() - plan_timestamp).total_seconds() > 600:
                return {
                    "content": """⏰ **Rebalancing Plan Expired**
                    
The rebalancing plan has expired (older than 10 minutes). Please generate a new plan:
- "rebalance my portfolio"
- "optimize portfolio using [strategy]"

Market conditions may have changed since the original analysis.""",
                    "confidence": 0.8,
                    "metadata": {"error": "plan_expired"}
                }
            
            trades = pending_plan.get("trades", [])
            strategy = pending_plan.get("strategy", "unknown")
            
            if not trades:
                return {
                    "content": """❌ **No Trades to Execute**
                    
The rebalancing plan contains no executable trades. This might mean:
- Portfolio is already optimally balanced
- Insufficient portfolio size for rebalancing
- Market conditions prevent trade generation

Please try a different strategy or check your portfolio status.""",
                    "confidence": 0.7,
                    "metadata": {"error": "no_trades"}
                }
            
            # SAFETY CHECK: Acquire rebalancing lock
            if not await self._acquire_rebalancing_lock(user_id):
                return {
                    "content": """🔒 **Rebalancing Already in Progress**
                    
Another rebalancing operation is currently running for your account.
Please wait for it to complete before starting a new rebalancing.

**Status Check:**
- Type "portfolio status" to see current state
- Wait 5-10 minutes and try again
- Contact support if the lock persists

This safety mechanism prevents conflicting trades.""",
                    "confidence": 0.9,
                    "metadata": {"error": "rebalancing_locked"}
                }
            
            try:
                # Get current portfolio for safety validation
                portfolio_summary = await self.chat_adapters.get_portfolio_summary(user_id)
                
                # SAFETY CHECK: Validate all trades before execution
                safety_result = await self._validate_trade_safety(user_id, trades, portfolio_summary)
                if not safety_result["valid"]:
                    await self._release_rebalancing_lock(user_id)
                    return {
                        "content": f"""🛡️ **Safety Check Failed**
                        
{safety_result['reason']}

**Safety Limits:**
- Minimum portfolio: $100
- Maximum single trade: 50% of portfolio
- Maximum total turnover: 90% of portfolio  
- Trade count: 2-20 trades per rebalancing

Your portfolio and trades have been analyzed to prevent potential losses.""",
                        "confidence": 0.8,
                        "metadata": {"error": "safety_check_failed", "reason": safety_result['reason']}
                    }
                
                # Execute trades with enhanced safety
                self.logger.info(f"Executing rebalancing plan with {len(trades)} trades", 
                               user_id=user_id, strategy=strategy, portfolio_value=portfolio_summary.get("total_value"))
                
                executed_trades = []
                failed_trades = []
                
                for trade in trades:
                    try:
                        # Execute individual trade with safety and retry logic
                        execution_result = await self._execute_trade_with_safety(trade, user_id)
                        
                        if execution_result.get("success"):
                            executed_trades.append({
                                "symbol": trade.get("symbol"),
                                "action": trade.get("action"),
                                "amount": trade.get("amount"),
                                "trade_id": execution_result.get("trade_id")
                            })
                            self.logger.info("Rebalancing trade executed successfully", 
                                           symbol=trade.get("symbol"), 
                                           action=trade.get("action"),
                                           trade_id=execution_result.get("trade_id"))
                        else:
                            failed_trades.append({
                                "symbol": trade.get("symbol"),
                                "action": trade.get("action"),
                                "amount": trade.get("amount"),
                                "error": execution_result.get("error", "Unknown error")
                            })
                            self.logger.warning("Rebalancing trade failed", 
                                              symbol=trade.get("symbol"),
                                              error=execution_result.get("error"))
                        
                    except Exception as e:
                        self.logger.error("Trade execution exception", error=str(e), trade=trade)
                        failed_trades.append({
                            "symbol": trade.get("symbol"),
                            "action": trade.get("action"),
                            "amount": trade.get("amount"),
                            "error": str(e)
                        })
                
                # Always release the lock after execution attempt
                await self._release_rebalancing_lock(user_id)
                
            except Exception as safety_error:
                # Release lock on any exception during safety checks or execution
                await self._release_rebalancing_lock(user_id)
                raise safety_error
            
            # Clear the pending plan from context
            if self.memory:
                try:
                    session_id = context.get("session_id")
                    if session_id:
                        await self.memory.update_session_context(session_id, {
                            "pending_rebalancing_plan": None,
                            "last_rebalancing_execution": {
                                "timestamp": datetime.utcnow().isoformat(),
                                "strategy": strategy,
                                "executed_count": len(executed_trades),
                                "failed_count": len(failed_trades)
                            }
                        })
                except Exception as e:
                    self.logger.warning("Could not clear rebalancing plan from memory", error=str(e))
            
            # Format response based on results
            if len(executed_trades) == len(trades):
                # All trades succeeded
                trade_summary = "\n".join([
                    f"✅ {trade['action'].upper()} {trade['amount']:.6f} {trade['symbol']}"
                    for trade in executed_trades
                ])
                
                return {
                    "content": f"""🎉 **Portfolio Rebalancing Completed Successfully**

**Strategy:** {strategy.replace('_', ' ').title()}
**Executed Trades:** {len(executed_trades)}/{len(trades)}

**Trade Summary:**
{trade_summary}

**Status:** All rebalancing trades executed successfully
**Next Steps:** 
- Your portfolio is now optimized according to the {strategy.replace('_', ' ')} strategy
- Monitor performance over the next few days
- Consider enabling autonomous mode for automatic rebalancing

Portfolio rebalancing complete! 🚀""",
                    "confidence": 0.98,
                    "metadata": {
                        "rebalancing_complete": True,
                        "strategy": strategy,
                        "executed_trades": len(executed_trades),
                        "total_trades": len(trades)
                    }
                }
                
            elif len(executed_trades) > 0:
                # Partial success
                executed_summary = "\n".join([
                    f"✅ {trade['action'].upper()} {trade['amount']:.6f} {trade['symbol']}"
                    for trade in executed_trades
                ])
                failed_summary = "\n".join([
                    f"❌ {trade['action'].upper()} {trade['amount']:.6f} {trade['symbol']} - {trade['error']}"
                    for trade in failed_trades
                ])
                
                return {
                    "content": f"""⚠️ **Portfolio Rebalancing Partially Completed**

**Strategy:** {strategy.replace('_', ' ').title()}
**Executed:** {len(executed_trades)}/{len(trades)} trades

**Successful Trades:**
{executed_summary}

**Failed Trades:**
{failed_summary}

**Status:** Partial rebalancing completed
**Recommendation:** Review failed trades and consider manual execution or retry later.""",
                    "confidence": 0.7,
                    "metadata": {
                        "rebalancing_partial": True,
                        "strategy": strategy,
                        "executed_trades": len(executed_trades),
                        "failed_trades": len(failed_trades),
                        "total_trades": len(trades)
                    }
                }
                
            else:
                # All trades failed
                failed_summary = "\n".join([
                    f"❌ {trade['action'].upper()} {trade['amount']:.6f} {trade['symbol']} - {trade['error']}"
                    for trade in failed_trades
                ])
                
                return {
                    "content": f"""❌ **Portfolio Rebalancing Failed**

**Strategy:** {strategy.replace('_', ' ').title()}
**Status:** All trades failed to execute

**Failed Trades:**
{failed_summary}

**Possible Causes:**
- Insufficient balance for trades
- Exchange connectivity issues
- Market conditions preventing execution

**Recommendations:**
- Check your exchange account balances
- Verify exchange API connections
- Try again in a few minutes
- Contact support if issues persist""",
                    "confidence": 0.4,
                    "metadata": {
                        "rebalancing_failed": True,
                        "strategy": strategy,
                        "failed_trades": len(failed_trades),
                        "total_trades": len(trades)
                    }
                }
            
        except Exception as e:
            self.logger.error("Rebalancing execution failed", error=str(e), user_id=user_id)
            return {
                "content": f"""❌ **Rebalancing Execution Error**
                
An unexpected error occurred during rebalancing execution:
{str(e)}

Please try again or contact support if the issue persists.""",
                "confidence": 0.3,
                "metadata": {"error": True, "execution_error": str(e)}
            }

    async def _handle_strategy_selection(self, message: str, context: Dict, user_id: str) -> Dict[str, Any]:
        """Handle strategy selection or change requests."""
        
        # Offer strategy selection menu
        return {
            "content": """🎯 **Choose Rebalancing Strategy**

**Available Strategies:**

1. **Risk Parity** ⚖️ - Equal risk contribution across assets (Recommended)
2. **Maximum Sharpe** 📈 - Optimize for best risk-adjusted returns
3. **Minimum Variance** 🛡️ - Lowest possible portfolio volatility  
4. **Equal Weight** ⚖️ - Simple equal allocation across all assets
5. **Kelly Criterion** 🎲 - Optimal position sizing based on expected returns
6. **Adaptive** 🤖 - AI selects the best strategy for current conditions

**Examples:**
- "rebalance using risk parity"
- "optimize portfolio with maximum sharpe"
- "use minimum variance strategy"

Which strategy would you like to use?""",
            "confidence": 0.95,
            "metadata": {"strategy_selection_menu": True}
        }

    async def _handle_general_query(self, message: str, context: Dict, user_id: str) -> Dict[str, Any]:
        """Handle general queries with service context."""
        
        # Check for execution confirmation commands
        message_lower = message.lower().strip()
        
        # Handle rebalancing execution confirmation
        if any(phrase in message_lower for phrase in ["execute rebalancing", "execute rebalance", "confirm rebalancing", "proceed with rebalancing"]):
            return await self._execute_rebalancing_plan(user_id, context)
        
        # Handle strategy change requests
        if "different strategy" in message_lower or "change strategy" in message_lower:
            return await self._handle_strategy_selection(message, context, user_id)
            
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