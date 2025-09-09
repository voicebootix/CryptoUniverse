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
from app.services.chat_memory import chat_memory

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
        # Initialize services
        self.ai_consensus = AIConsensusService()
        self.master_controller = MasterSystemController()
        self.trade_executor = TradeExecutionService()
        self.memory = chat_memory
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
            # Save user message
            user_message_id = await self.memory.save_message(
                session_id=session_id,
                user_id=user_id,
                content=user_message,
                message_type=ChatMessageType.USER.value,
                processing_time_ms=0,
                tokens_used=len(user_message.split())
            )
            
            # TEMPORARY: Bypass complex AI processing to test chat infrastructure
            context = {}  # Skip context retrieval temporarily
            intent = ChatIntent.GENERAL_QUERY  # Use simple intent
            
            # Simple test response instead of complex AI processing
            response = {
                "content": f"✅ Chat is working! You said: '{user_message}' - This is a test response while we fix the AI processing.",
                "confidence": 0.9,
                "metadata": {"test": True},
                "model_used": "test_system"
            }
            
            processing_time = (time.time() - processing_start) * 1000
            
            # Save assistant response
            assistant_message_id = await self.memory.save_message(
                session_id=session_id,
                user_id=user_id,
                content=response["content"],
                message_type=ChatMessageType.ASSISTANT.value,
                intent=intent.value,
                confidence=response.get("confidence", 0.8),
                metadata=response.get("metadata", {}),
                model_used=response.get("model_used", "ai_consensus"),
                processing_time_ms=processing_time,
                tokens_used=response.get("tokens_used", len(response["content"].split()))
            )
            
            # Update session context if needed
            if response.get("context_updates"):
                await self.memory.update_session_context(
                    session_id, response["context_updates"]
                )
            
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
            
            # Save error message
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
            
            return {
                "success": False,
                "error": str(e),
                "content": "I apologize, but I encountered an error processing your message. Please try again."
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
        """Execute Phase 1: Analysis"""
        # Analyze the request using AI consensus
        analysis = await self.ai_consensus.analyze_request(
            user_message, context, intent.value
        )
        
        return {
            "summary": analysis.get("summary", "Market analysis completed"),
            "risk_assessment": analysis.get("risk_level", "medium"),
            "market_conditions": analysis.get("market_conditions", {}),
            "recommendations": analysis.get("recommendations", [])
        }
    
    async def _execute_phase_consensus(
        self, user_message: str, analysis: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Phase 2: Consensus"""
        # Get consensus from multiple AI models
        consensus = await self.ai_consensus.get_consensus(
            user_message, analysis, context
        )
        
        return {
            "recommendation": consensus.get("final_recommendation", "No consensus reached"),
            "confidence": consensus.get("consensus_confidence", 0.7),
            "model_agreement": consensus.get("model_agreement", {}),
            "dissenting_views": consensus.get("dissenting_views", [])
        }
    
    async def _execute_phase_validation(
        self, consensus: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Phase 3: Validation"""
        # Validate against risk parameters and portfolio rules
        validation = await self.master_controller.validate_trading_decision(
            consensus, context
        )
        
        return {
            "approved": validation.get("approved", False),
            "reason": validation.get("validation_message", "Validation completed"),
            "risk_checks": validation.get("risk_checks", {}),
            "compliance_status": validation.get("compliance_status", "unknown")
        }
    
    async def _execute_phase_execution(
        self, validation: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Phase 4: Execution"""
        # Execute the trade through the master controller
        execution = await self.master_controller.execute_validated_trade(
            validation, context
        )
        
        return {
            "trade_id": execution.get("trade_id", str(uuid.uuid4())),
            "summary": execution.get("execution_summary", "Trade executed"),
            "status": execution.get("status", "completed"),
            "details": execution.get("execution_details", {})
        }
    
    async def _execute_phase_monitoring(
        self, execution: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Phase 5: Monitoring"""
        # Set up monitoring and alerts
        monitoring = await self.master_controller.setup_trade_monitoring(
            execution, context
        )
        
        return {
            "monitoring_id": monitoring.get("monitoring_id", str(uuid.uuid4())),
            "monitoring_summary": monitoring.get("setup_summary", "Monitoring active"),
            "alert_types": monitoring.get("alert_types", []),
            "monitoring_duration": monitoring.get("duration", "ongoing")
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
        """Process non-trading intents with conversation memory."""
        
        # Build context-aware prompt
        system_prompt = self.system_prompts.get(intent, self.system_prompts[ChatIntent.GENERAL_QUERY])
        
        # Add conversation context
        context_summary = self._build_context_summary(context)
        
        full_prompt = f"""
{system_prompt}

CONVERSATION CONTEXT:
{context_summary}

USER MESSAGE: {user_message}

Provide a helpful, context-aware response that builds on our conversation history.
"""
        
        # Get AI response
        ai_response = await self.ai_consensus.generate_response(
            full_prompt, context, intent.value
        )
        
        return {
            "content": ai_response.get("content", "I apologize, but I couldn't process that request."),
            "confidence": ai_response.get("confidence", 0.8),
            "metadata": {
                "intent": intent.value,
                "context_used": len(context.get("recent_messages", [])),
                "model_used": ai_response.get("model_used", "unknown")
            },
            "model_used": ai_response.get("model_used", "ai_consensus"),
            "tokens_used": ai_response.get("tokens_used", 0)
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
        return await self.memory.get_session_messages(session_id, limit)
    
    async def get_active_sessions(self, user_id: str) -> List[str]:
        """Get active chat sessions for a user."""
        sessions = await self.memory.get_user_sessions(user_id, limit=10)
        return [session["session_id"] for session in sessions]
    
    async def execute_confirmed_action(
        self, session_id: str, command: str, user_id: str
    ) -> Dict[str, Any]:
        """Execute a confirmed action from a previous conversation."""
        
        # Get conversation context
        context = await self.memory.get_conversation_context(session_id)
        
        # Process the command execution
        result = await self.master_controller.execute_confirmed_command(
            command, context, user_id
        )
        
        # Save the execution result
        await self.memory.save_message(
            session_id=session_id,
            user_id=user_id,
            content=f"Executed command: {command}. Result: {result.get('summary', 'Command executed')}",
            message_type=ChatMessageType.SYSTEM.value,
            intent="command_execution",
            metadata={"command": command, "result": result}
        )
        
        return result
    
    async def _send_websocket_update(self, user_id: str, data: Dict[str, Any]):
        """Send real-time update via WebSocket."""
        try:
            await manager.send_personal_message(json.dumps(data), user_id)
        except Exception as e:
            self.logger.debug("WebSocket update failed", error=str(e), user_id=user_id)


# Global instance with enhanced memory
enhanced_chat_engine = EnhancedAIChatEngine()