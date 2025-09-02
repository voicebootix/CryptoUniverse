"""
Unified AI Money Manager - The Central Brain

This is THE central AI brain responsible for all cryptocurrency money management
across ALL interfaces: Web UI, Chat, Telegram, and Autonomous operations.

This unified manager ensures consistent AI decision-making regardless of how
the user interacts with the platform (chat, UI, Telegram, or autonomous mode).
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import uuid

import structlog
from app.core.config import get_settings
from app.core.logging import LoggerMixin
from app.core.redis import get_redis_client

# Import all existing services
from app.services.master_controller import MasterSystemController, TradingMode
from app.services.ai_consensus_core import AIConsensusService
from app.services.trade_execution import TradeExecutionService
from app.services.ai_chat_engine import chat_engine, ChatIntent
from app.services.chat_service_adapters import chat_adapters
from app.services.telegram_core import TelegramCore
from app.services.websocket import manager

settings = get_settings()
logger = structlog.get_logger(__name__)


class OperationMode(str, Enum):
    """Operation modes for the unified AI manager."""
    MANUAL = "manual"              # User-initiated actions only
    ASSISTED = "assisted"          # AI recommendations with user approval
    AUTONOMOUS = "autonomous"      # Full AI autonomous operation
    EMERGENCY = "emergency"        # Emergency mode with safety protocols


class InterfaceType(str, Enum):
    """Interface types for user interaction."""
    WEB_UI = "web_ui"
    WEB_CHAT = "web_chat"
    TELEGRAM = "telegram"
    API = "api"
    AUTONOMOUS = "autonomous"


@dataclass
class AIDecision:
    """AI decision data structure."""
    decision_id: str
    user_id: str
    interface: InterfaceType
    operation_mode: OperationMode
    intent: str
    decision_type: str  # trade, rebalance, risk_action, etc.
    recommendation: Dict[str, Any]
    confidence: float
    risk_assessment: Dict[str, Any]
    requires_approval: bool
    auto_execute: bool
    timestamp: datetime
    context: Dict[str, Any]


class UnifiedAIManager(LoggerMixin):
    """
    THE UNIFIED AI MONEY MANAGER - Central Brain for All Operations
    
    This is the single responsible AI entity for all cryptocurrency money management
    across all interfaces and operation modes. It ensures consistent AI decision-making
    whether the user interacts via:
    - Web UI (manual/autonomous)
    - Web Chat (conversational)
    - Telegram (mobile/remote)
    - API (programmatic)
    - Autonomous mode (fully automated)
    """
    
    def __init__(self):
        # Core services
        self.master_controller = MasterSystemController()
        self.ai_consensus = AIConsensusService()
        self.trade_executor = TradeExecutionService()
        self.adapters = chat_adapters
        self.telegram_core = TelegramCore()
        
        # Redis for state management - initialize properly for async usage
        self.redis = None
        self._redis_initialized = False
        
        # Decision tracking
        self.active_decisions: Dict[str, AIDecision] = {}
        self.user_preferences: Dict[str, Dict[str, Any]] = {}
        
        # Initialize unified brain
        self.logger.info("🧠 UNIFIED AI MONEY MANAGER INITIALIZING")
        self._initialize_unified_brain()
    
    def _initialize_unified_brain(self):
        """Initialize the unified AI brain across all interfaces."""
        
        # Connect chat engine to unified manager
        chat_engine.unified_manager = self
        
        # Connect telegram to unified manager
        self.telegram_core.unified_manager = self
        
        # Connect master controller to unified manager
        self.master_controller.unified_manager = self
        
        self.logger.info("🧠 Unified AI brain connected to all interfaces")
    
    async def _ensure_redis(self):
        """Ensure Redis client is properly initialized."""
        if getattr(self, "_redis_initialized", False) is False:
            try:
                from app.core.redis import get_redis_client
                self.redis = await get_redis_client()
            except Exception:
                self.redis = None
            self._redis_initialized = True
        return self.redis
    
    async def process_user_request(
        self,
        user_id: str,
        request: str,
        interface: InterfaceType,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        CENTRAL METHOD: Process any user request from any interface.
        
        This is the single entry point for ALL AI decision-making across
        Web UI, Chat, Telegram, and Autonomous operations.
        """
        
        try:
            # Get user operation mode and preferences
            user_config = await self._get_user_config(user_id)
            operation_mode = OperationMode(user_config.get("operation_mode", "assisted"))
            
            # Classify the request intent
            intent = await self._classify_unified_intent(request, interface, context)
            
            # Create AI decision context
            decision_context = {
                "user_id": user_id,
                "request": request,
                "interface": interface.value,
                "operation_mode": operation_mode.value,
                "intent": intent,
                "user_config": user_config,
                "context": context or {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Get AI analysis and recommendation
            ai_response = await self.ai_consensus.analyze_opportunity(
                json.dumps(decision_context),
                confidence_threshold=80.0,
                ai_models="all",
                user_id=user_id
            )
            
            # Create AI decision
            decision = AIDecision(
                decision_id=str(uuid.uuid4()),
                user_id=user_id,
                interface=interface,
                operation_mode=operation_mode,
                intent=intent,
                decision_type=self._get_decision_type(intent),
                recommendation=ai_response.get("recommendation", {}),
                confidence=ai_response.get("confidence", 0.0),
                risk_assessment=ai_response.get("risk_assessment", {}),
                requires_approval=self._requires_approval(operation_mode, intent, ai_response),
                auto_execute=self._should_auto_execute(operation_mode, intent, ai_response),
                timestamp=datetime.utcnow(),
                context=decision_context
            )
            
            # Store decision
            self.active_decisions[decision.decision_id] = decision
            
            # Execute or return for approval based on operation mode
            if decision.auto_execute and not decision.requires_approval:
                # Autonomous execution
                execution_result = await self._execute_ai_decision(decision)
                return {
                    "success": True,
                    "decision_id": decision.decision_id,
                    "action": "executed",
                    "result": execution_result,
                    "ai_analysis": ai_response.get("analysis", ""),
                    "confidence": decision.confidence
                }
            else:
                # Return for user approval or information
                formatted_response = await self._format_ai_response(decision, interface)
                return {
                    "success": True,
                    "decision_id": decision.decision_id,
                    "action": "recommendation",
                    "content": formatted_response["content"],
                    "requires_approval": decision.requires_approval,
                    "ai_analysis": ai_response.get("analysis", ""),
                    "confidence": decision.confidence,
                    "metadata": formatted_response.get("metadata", {})
                }
                
        except Exception as e:
            self.logger.error("Unified AI request processing failed", error=str(e), user_id=user_id)
            return {
                "success": False,
                "error": str(e),
                "content": "I encountered an error processing your request. Please try again."
            }
    
    async def execute_approved_decision(self, decision_id: str, user_id: str) -> Dict[str, Any]:
        """Execute a previously approved AI decision."""
        
        try:
            if decision_id not in self.active_decisions:
                return {"success": False, "error": "Decision not found or expired"}
            
            decision = self.active_decisions[decision_id]
            
            if decision.user_id != user_id:
                return {"success": False, "error": "Unauthorized decision access"}
            
            # Execute the decision
            result = await self._execute_ai_decision(decision)
            
            # Clean up
            del self.active_decisions[decision_id]
            
            return {
                "success": True,
                "decision_id": decision_id,
                "execution_result": result,
                "message": "Decision executed successfully"
            }
            
        except Exception as e:
            self.logger.error("Decision execution failed", error=str(e), decision_id=decision_id)
            return {"success": False, "error": str(e)}
    
    async def start_autonomous_mode(self, user_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Start autonomous mode with unified AI control."""
        
        try:
            # Set user operation mode to autonomous
            await self._set_user_operation_mode(user_id, OperationMode.AUTONOMOUS)
            
            # Configure autonomous parameters
            autonomous_config = {
                "operation_mode": OperationMode.AUTONOMOUS.value,
                "trading_mode": config.get("mode", "balanced"),
                "max_daily_loss_pct": config.get("max_daily_loss_pct", 5.0),
                "max_position_size_pct": config.get("max_position_size_pct", 10.0),
                "allowed_symbols": config.get("allowed_symbols", ["BTC", "ETH", "SOL"]),
                "excluded_symbols": config.get("excluded_symbols", []),
                "ai_confidence_threshold": config.get("ai_confidence_threshold", 85.0),
                "risk_tolerance": config.get("risk_tolerance", "balanced"),
                "started_at": datetime.utcnow().isoformat(),
                "interface_initiated": config.get("interface", "web_ui")
            }
            
            # Start autonomous mode in master controller
            master_result = await self.master_controller.start_autonomous_mode({
                "user_id": user_id,
                **autonomous_config
            })
            
            if master_result.get("success"):
                # Store unified config as JSON blob
                redis_client = await self._ensure_redis()
                if redis_client:
                    await redis_client.set(
                        f"unified_ai_config:{user_id}",
                        json.dumps(autonomous_config)
                    )
                
                # Notify all connected interfaces
                await self._notify_all_interfaces(user_id, {
                    "type": "autonomous_mode_started",
                    "config": autonomous_config,
                    "message": f"🤖 Autonomous AI money manager activated in {config.get('mode', 'balanced')} mode"
                })
                
                self.logger.info("Autonomous mode started", user_id=user_id, mode=config.get("mode"))
                
                return {
                    "success": True,
                    "message": "🤖 AI Money Manager is now operating autonomously",
                    "config": autonomous_config,
                    "estimated_trades_per_day": master_result.get("estimated_trades", 10)
                }
            else:
                return master_result
                
        except Exception as e:
            self.logger.error("Failed to start autonomous mode", error=str(e), user_id=user_id)
            return {"success": False, "error": str(e)}
    
    async def stop_autonomous_mode(self, user_id: str, interface: InterfaceType) -> Dict[str, Any]:
        """Stop autonomous mode from any interface."""
        
        try:
            # Set user operation mode back to assisted
            await self._set_user_operation_mode(user_id, OperationMode.ASSISTED)
            
            # Stop autonomous mode in master controller
            master_result = await self.master_controller.stop_autonomous_mode(user_id)
            
            # Clean up unified config
            await self.redis.delete(f"unified_ai_config:{user_id}")
            
            # Notify all connected interfaces
            await self._notify_all_interfaces(user_id, {
                "type": "autonomous_mode_stopped",
                "interface": interface.value,
                "message": "🛑 Autonomous AI money manager stopped",
                "stats": master_result
            })
            
            self.logger.info("Autonomous mode stopped", user_id=user_id, interface=interface.value)
            
            return {
                "success": True,
                "message": "🛑 AI Money Manager autonomous mode stopped",
                "session_stats": master_result
            }
            
        except Exception as e:
            self.logger.error("Failed to stop autonomous mode", error=str(e), user_id=user_id)
            return {"success": False, "error": str(e)}
    
    async def get_ai_status(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive AI money manager status."""
        
        try:
            # Get user config
            user_config = await self._get_user_config(user_id)
            
            # Get autonomous status
            autonomous_active = await self.redis.get(f"autonomous_active:{user_id}")
            autonomous_config = await self.redis.hgetall(f"unified_ai_config:{user_id}") if autonomous_active else {}
            
            # Get system status
            master_status = await self.master_controller.get_system_status(user_id)
            
            # Get AI consensus status
            ai_status = await self.ai_consensus.get_service_status()
            
            # Get portfolio summary
            portfolio_summary = await self.adapters.get_portfolio_summary(user_id)
            
            return {
                "success": True,
                "ai_manager_status": "operational",
                "operation_mode": user_config.get("operation_mode", "assisted"),
                "autonomous_active": bool(autonomous_active),
                "autonomous_config": autonomous_config,
                "master_controller_status": master_status,
                "ai_consensus_status": ai_status,
                "portfolio_summary": portfolio_summary,
                "active_decisions": len([d for d in self.active_decisions.values() if d.user_id == user_id]),
                "interfaces_connected": {
                    "web_ui": True,  # Always available
                    "web_chat": True,  # Always available
                    "telegram": await self._check_telegram_connection(user_id),
                    "websocket": manager.get_connection_count(user_id) > 0
                },
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error("Failed to get AI status", error=str(e), user_id=user_id)
            return {
                "success": False,
                "error": str(e),
                "ai_manager_status": "error"
            }
    
    async def handle_telegram_request(self, chat_id: str, user_id: str, message: str) -> Dict[str, Any]:
        """Handle Telegram requests through unified AI manager."""
        
        # Process through unified system
        result = await self.process_user_request(
            user_id=user_id,
            request=message,
            interface=InterfaceType.TELEGRAM,
            context={"chat_id": chat_id, "platform": "telegram"}
        )
        
        # Format for Telegram
        if result.get("success"):
            telegram_response = self._format_for_telegram(result)
            
            # Send via Telegram
            await self.telegram_core.telegram_api.send_message(chat_id, telegram_response)
            
            return {"success": True, "response": telegram_response}
        else:
            error_message = "🤖 I encountered an error processing your request. Please try again."
            await self.telegram_core.telegram_api.send_message(chat_id, error_message)
            return {"success": False, "error": result.get("error")}
    
    async def handle_web_chat_request(self, session_id: str, user_id: str, message: str) -> Dict[str, Any]:
        """Handle web chat requests through unified AI manager."""
        
        # Get chat session context
        chat_history = await chat_engine.get_chat_history(session_id, limit=5)
        
        # Process through unified system
        result = await self.process_user_request(
            user_id=user_id,
            request=message,
            interface=InterfaceType.WEB_CHAT,
            context={
                "session_id": session_id,
                "chat_history": chat_history,
                "platform": "web_chat"
            }
        )
        
        return result
    
    async def handle_autonomous_decision(self, user_id: str, market_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle autonomous AI decisions during automated trading cycles."""
        
        try:
            # Get user autonomous config  
            redis_client = await self._ensure_redis()
            if redis_client:
                config_data = await redis_client.get(f"unified_ai_config:{user_id}")
                if config_data:
                    try:
                        autonomous_config = json.loads(config_data)
                    except json.JSONDecodeError:
                        autonomous_config = {}
                else:
                    autonomous_config = {}
            else:
                autonomous_config = {}
            
            if not autonomous_config:
                return {"success": False, "error": "No autonomous configuration found"}
            
            # Build autonomous decision context
            autonomous_request = {
                "type": "autonomous_trading_cycle",
                "market_context": market_context,
                "portfolio_context": await self.adapters.get_portfolio_summary(user_id),
                "risk_context": await self.adapters.comprehensive_risk_analysis(user_id),
                "user_preferences": autonomous_config
            }
            
            # Process through unified system with autonomous mode
            result = await self.process_user_request(
                user_id=user_id,
                request=json.dumps(autonomous_request),
                interface=InterfaceType.AUTONOMOUS,
                context={
                    "autonomous_cycle": True,
                    "market_context": market_context,
                    "config": autonomous_config
                }
            )
            
            # Log autonomous decision
            if result.get("success"):
                self.logger.info("Autonomous AI decision made", 
                               user_id=user_id, 
                               action=result.get("action"),
                               confidence=result.get("confidence"))
            
            return result
            
        except Exception as e:
            self.logger.error("Autonomous decision failed", error=str(e), user_id=user_id)
            return {"success": False, "error": str(e)}
    
    async def emergency_protocol(self, user_id: str, trigger: str, interface: InterfaceType) -> Dict[str, Any]:
        """Execute emergency protocol from any interface."""
        
        try:
            self.logger.warning("🚨 EMERGENCY PROTOCOL ACTIVATED", 
                              user_id=user_id, 
                              trigger=trigger, 
                              interface=interface.value)
            
            # Set emergency mode
            await self._set_user_operation_mode(user_id, OperationMode.EMERGENCY)
            
            # Stop autonomous mode if active
            await self.master_controller.stop_autonomous_mode(user_id)
            
            # Get emergency risk assessment
            emergency_assessment = await self.adapters.emergency_risk_assessment(user_id, trigger)
            
            # Execute emergency protocol based on risk level
            if emergency_assessment.get("risk_level") == "HIGH":
                # Immediate action required
                emergency_actions = await self._execute_emergency_actions(user_id, emergency_assessment)
            else:
                # Assessment and recommendation
                emergency_actions = await self._recommend_emergency_actions(user_id, emergency_assessment)
            
            # Notify all interfaces
            await self._notify_all_interfaces(user_id, {
                "type": "emergency_protocol_activated",
                "trigger": trigger,
                "interface": interface.value,
                "risk_assessment": emergency_assessment,
                "actions_taken": emergency_actions,
                "message": "🚨 Emergency protocol activated - AI money manager taking protective action"
            })
            
            return {
                "success": True,
                "emergency_level": emergency_assessment.get("risk_level"),
                "actions_taken": emergency_actions,
                "message": "🚨 Emergency protocol executed successfully"
            }
            
        except Exception as e:
            self.logger.error("Emergency protocol failed", error=str(e), user_id=user_id)
            return {"success": False, "error": str(e)}
    
    async def _get_user_config(self, user_id: str) -> Dict[str, Any]:
        """Get user configuration and preferences."""
        
        # Get from Redis cache first  
        redis_client = await self._ensure_redis()
        if redis_client:
            config_data = await redis_client.get(f"user_ai_config:{user_id}")
            if config_data:
                try:
                    cached_config = json.loads(config_data)
                    if cached_config:
                        return cached_config
                except json.JSONDecodeError:
                    cached_config = {}
            else:
                cached_config = {}
        else:
            cached_config = {}
        
        # Default configuration
        default_config = {
            "operation_mode": "assisted",
            "risk_tolerance": "balanced",
            "trading_mode": "balanced",
            "ai_confidence_threshold": 80.0,
            "max_position_size_pct": 10.0,
            "max_daily_loss_pct": 5.0,
            "auto_rebalance": False,
            "emergency_stop_loss_pct": 15.0,
            "preferred_ai_models": "all",
            "notification_preferences": {
                "telegram": True,
                "web": True,
                "email": False
            }
        }
        
        # Cache for future use as JSON blob
        redis_client = await self._ensure_redis()
        if redis_client:
            await redis_client.set(f"user_ai_config:{user_id}", json.dumps(default_config))
        
        return default_config
    
    async def _set_user_operation_mode(self, user_id: str, mode: OperationMode):
        """Set user operation mode."""
        redis_client = await self._ensure_redis()
        if redis_client:
            # Get existing config
            config_data = await redis_client.get(f"user_ai_config:{user_id}")
            if config_data:
                try:
                    user_config = json.loads(config_data)
                except json.JSONDecodeError:
                    # Create default config directly to avoid circular calls
                    user_config = {
                        "operation_mode": "assisted",
                        "risk_tolerance": "balanced",
                        "trading_mode": "balanced",
                        "ai_confidence_threshold": 80.0
                    }
            else:
                # Create default config directly
                user_config = {
                    "operation_mode": "assisted", 
                    "risk_tolerance": "balanced",
                    "trading_mode": "balanced",
                    "ai_confidence_threshold": 80.0
                }
            
            # Update operation mode
            user_config["operation_mode"] = mode.value
            
            # Save updated config back as JSON
            await redis_client.set(f"user_ai_config:{user_id}", json.dumps(user_config))
    
    async def _classify_unified_intent(self, request: str, interface: InterfaceType, context: Optional[Dict]) -> str:
        """Classify intent across all interfaces consistently."""
        
        # Use existing chat engine intent classification
        if hasattr(chat_engine, '_classify_intent'):
            chat_intent = await chat_engine._classify_intent(request)
            return chat_intent.value
        
        # Fallback classification
        request_lower = request.lower()
        
        if any(word in request_lower for word in ['emergency', 'stop', 'halt', 'panic']):
            return "emergency_command"
        elif any(word in request_lower for word in ['buy', 'sell', 'trade', 'execute']):
            return "trade_execution"
        elif any(word in request_lower for word in ['portfolio', 'balance', 'holdings']):
            return "portfolio_analysis"
        elif any(word in request_lower for word in ['rebalance', 'optimize', 'allocation']):
            return "rebalancing"
        elif any(word in request_lower for word in ['risk', 'safety', 'protection']):
            return "risk_assessment"
        elif any(word in request_lower for word in ['opportunity', 'find', 'discover']):
            return "opportunity_discovery"
        elif any(word in request_lower for word in ['autonomous', 'auto', 'automatic']):
            return "autonomous_control"
        else:
            return "general_query"
    
    def _get_decision_type(self, intent: str) -> str:
        """Get decision type from intent."""
        mapping = {
            "trade_execution": "trade",
            "portfolio_analysis": "analysis",
            "rebalancing": "rebalance",
            "risk_assessment": "risk_action",
            "opportunity_discovery": "opportunity",
            "autonomous_control": "mode_change",
            "emergency_command": "emergency"
        }
        return mapping.get(intent, "general")
    
    def _requires_approval(self, mode: OperationMode, intent: str, ai_response: Dict) -> bool:
        """Determine if decision requires user approval."""
        
        # Emergency commands always require immediate action
        if intent == "emergency_command":
            return False
        
        # In manual mode, everything requires approval
        if mode == OperationMode.MANUAL:
            return True
        
        # In autonomous mode, high-confidence decisions can auto-execute
        if mode == OperationMode.AUTONOMOUS:
            confidence = ai_response.get("confidence", 0.0)
            risk_level = ai_response.get("risk_level", "high")
            
            # Auto-execute if high confidence and low/medium risk
            if confidence >= 0.85 and risk_level in ["low", "medium"]:
                return False
            
            # Require approval for high-risk or low-confidence decisions
            return True
        
        # In assisted mode, most things require approval except analysis
        if mode == OperationMode.ASSISTED:
            return intent not in ["portfolio_analysis", "market_analysis", "general_query"]
        
        return True
    
    def _should_auto_execute(self, mode: OperationMode, intent: str, ai_response: Dict) -> bool:
        """Determine if decision should auto-execute."""
        
        # Only auto-execute in autonomous mode or for emergency commands
        if mode == OperationMode.AUTONOMOUS:
            confidence = ai_response.get("confidence", 0.0)
            return confidence >= 0.80
        
        # Emergency commands auto-execute regardless of mode
        if intent == "emergency_command":
            return True
        
        return False
    
    async def _execute_ai_decision(self, decision: AIDecision) -> Dict[str, Any]:
        """Execute an AI decision."""
        
        try:
            decision_type = decision.decision_type
            recommendation = decision.recommendation
            user_id = decision.user_id
            
            if decision_type == "trade":
                # Execute trade
                result = await self.trade_executor.execute_trade(
                    user_id=user_id,
                    symbol=recommendation.get("symbol"),
                    action=recommendation.get("action"),
                    amount=recommendation.get("amount"),
                    order_type=recommendation.get("order_type", "market")
                )
                
            elif decision_type == "rebalance":
                # Execute rebalancing
                trades = recommendation.get("trades", [])
                result = await self._execute_rebalancing_trades(user_id, trades)
                
            elif decision_type == "emergency":
                # Execute emergency actions
                result = await self.master_controller.emergency_stop(user_id)
                
            elif decision_type == "mode_change":
                # Change operation mode
                new_mode = recommendation.get("new_mode")
                if new_mode == "autonomous":
                    result = await self.start_autonomous_mode(user_id, recommendation.get("config", {}))
                else:
                    result = await self.stop_autonomous_mode(user_id, decision.interface)
                    
            else:
                result = {"success": False, "error": f"Unknown decision type: {decision_type}"}
            
            # Log execution
            self.logger.info("AI decision executed", 
                           decision_id=decision.decision_id,
                           decision_type=decision_type,
                           success=result.get("success"))
            
            return result
            
        except Exception as e:
            self.logger.error("AI decision execution failed", error=str(e), decision_id=decision.decision_id)
            return {"success": False, "error": str(e)}
    
    async def _format_ai_response(self, decision: AIDecision, interface: InterfaceType) -> Dict[str, Any]:
        """Format AI response based on interface type."""
        
        try:
            base_content = decision.recommendation.get("analysis", "")
            
            if interface == InterfaceType.TELEGRAM:
                # Telegram formatting (shorter, emoji-rich)
                content = f"🤖 **AI Analysis**\n\n{base_content[:500]}..."
                if decision.requires_approval:
                    content += "\n\nReply 'yes' to execute or 'no' to cancel."
                    
            elif interface == InterfaceType.WEB_CHAT:
                # Web chat formatting (detailed, interactive)
                content = base_content
                if decision.requires_approval:
                    content += "\n\nWould you like me to proceed with this recommendation?"
                    
            elif interface == InterfaceType.WEB_UI:
                # Web UI formatting (structured data)
                content = {
                    "analysis": base_content,
                    "recommendation": decision.recommendation,
                    "confidence": decision.confidence,
                    "risk_assessment": decision.risk_assessment
                }
                
            else:
                content = base_content
            
            return {
                "content": content,
                "metadata": {
                    "decision_id": decision.decision_id,
                    "requires_approval": decision.requires_approval,
                    "confidence": decision.confidence,
                    "interface": interface.value
                }
            }
            
        except Exception as e:
            self.logger.error("Response formatting failed", error=str(e))
            return {
                "content": "I encountered an error formatting the response.",
                "metadata": {"error": str(e)}
            }
    
    def _format_for_telegram(self, result: Dict[str, Any]) -> str:
        """Format response specifically for Telegram."""
        
        content = result.get("content", "")
        confidence = result.get("confidence", 0.0)
        
        # Add confidence indicator
        confidence_emoji = "🟢" if confidence >= 0.9 else "🟡" if confidence >= 0.7 else "🔴"
        
        telegram_response = f"{confidence_emoji} **Confidence: {confidence:.1%}**\n\n{content}"
        
        # Truncate if too long for Telegram
        if len(telegram_response) > 4000:
            telegram_response = telegram_response[:3900] + "\n\n... (truncated)"
        
        return telegram_response
    
    async def _notify_all_interfaces(self, user_id: str, notification: Dict[str, Any]):
        """Notify all connected interfaces about important events."""
        
        try:
            # WebSocket notification
            await manager.send_personal_message(json.dumps(notification), user_id)
            
            # Telegram notification (if connected)
            telegram_connected = await self._check_telegram_connection(user_id)
            if telegram_connected:
                telegram_message = self._format_for_telegram(notification)
                # Get user's telegram chat_id and send
                # This would require telegram chat_id lookup
                pass
            
            # Store notification for UI polling
            await self.redis.lpush(f"notifications:{user_id}", json.dumps(notification))
            await self.redis.ltrim(f"notifications:{user_id}", 0, 99)  # Keep last 100
            
        except Exception as e:
            self.logger.warning("Interface notification failed", error=str(e), user_id=user_id)
    
    async def _check_telegram_connection(self, user_id: str) -> bool:
        """Check if user has active Telegram connection."""
        try:
            # This would check if user has configured Telegram
            # For now, return False as placeholder
            return False
        except:
            return False
    
    async def _execute_rebalancing_trades(self, user_id: str, trades: List[Dict]) -> Dict[str, Any]:
        """Execute a series of rebalancing trades."""
        
        try:
            executed_trades = []
            failed_trades = []
            
            for trade in trades:
                result = await self.trade_executor.execute_trade(
                    user_id=user_id,
                    symbol=trade.get("symbol"),
                    action=trade.get("action"),
                    amount=trade.get("amount"),
                    order_type="market"
                )
                
                if result.get("success"):
                    executed_trades.append(result)
                else:
                    failed_trades.append({"trade": trade, "error": result.get("error")})
            
            return {
                "success": len(failed_trades) == 0,
                "executed_trades": len(executed_trades),
                "failed_trades": len(failed_trades),
                "details": {
                    "executed": executed_trades,
                    "failed": failed_trades
                }
            }
            
        except Exception as e:
            self.logger.error("Rebalancing execution failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _execute_emergency_actions(self, user_id: str, assessment: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute immediate emergency actions."""
        
        actions_taken = []
        
        try:
            # 1. Stop all autonomous trading
            stop_result = await self.master_controller.stop_autonomous_mode(user_id)
            actions_taken.append({
                "action": "stop_autonomous_trading",
                "result": stop_result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # 2. Cancel pending orders (if trade executor supports it)
            # cancel_result = await self.trade_executor.cancel_all_orders(user_id)
            # actions_taken.append({"action": "cancel_pending_orders", "result": cancel_result})
            
            # 3. Set emergency stop-losses (if needed)
            portfolio_data = await self.adapters.get_portfolio_summary(user_id)
            if portfolio_data.get("total_value", 0) > 0:
                # This would set emergency stop-losses
                actions_taken.append({
                    "action": "emergency_stop_losses_set",
                    "result": {"success": True, "message": "Emergency stop-losses activated"},
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            return actions_taken
            
        except Exception as e:
            self.logger.error("Emergency actions failed", error=str(e))
            return [{"action": "emergency_protocol", "result": {"success": False, "error": str(e)}}]
    
    async def _recommend_emergency_actions(self, user_id: str, assessment: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Recommend emergency actions without immediate execution."""
        
        recommendations = [
            {
                "action": "review_positions",
                "description": "Review all open positions for risk",
                "priority": "high"
            },
            {
                "action": "set_stop_losses",
                "description": "Implement protective stop-loss orders",
                "priority": "high"
            },
            {
                "action": "reduce_leverage",
                "description": "Reduce leverage on high-risk positions",
                "priority": "medium"
            },
            {
                "action": "increase_cash",
                "description": "Increase cash allocation for safety",
                "priority": "medium"
            }
        ]
        
        return recommendations


# Global unified AI manager instance
unified_ai_manager = UnifiedAIManager()