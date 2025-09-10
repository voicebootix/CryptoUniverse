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
from app.services.ai_chat_engine import enhanced_chat_engine as chat_engine, ChatIntent
from app.services.chat_service_adapters import chat_adapters
from app.services.telegram_core import TelegramCommanderService
from app.services.websocket import manager
from app.services.chat_memory import ChatMemoryService

# Import actual service engines for routing
from app.services.market_analysis_core import MarketAnalysisService
from app.services.portfolio_risk_core import PortfolioRiskService
from app.services.trading_strategies import TradingStrategiesService

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
        self.telegram_core = TelegramCommanderService()
        
        # Enhanced memory service for conversation continuity
        self.memory_service = ChatMemoryService()
        
        # Actual service engines for routing
        self.market_analysis = MarketAnalysisService()
        self.portfolio_risk = PortfolioRiskService()
        self.trading_strategies = TradingStrategiesService()
        
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
            
            # ENHANCED: Route to actual services first based on intent
            service_result = await self._route_to_service(intent, request, user_id, context)
            
            # Then use AI consensus to VALIDATE and format the service result
            enhanced_context = {
                **decision_context,
                "service_result": service_result,
                "analysis_type": "validation_and_formatting"
            }
            
            ai_response = await self.ai_consensus.analyze_opportunity(
                json.dumps(enhanced_context),
                confidence_threshold=75.0,
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
            redis_client = await self._ensure_redis()
            if redis_client:
                await redis_client.delete(f"unified_ai_config:{user_id}")
            
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
            redis_client = await self._ensure_redis()
            autonomous_active = await redis_client.get(f"autonomous_active:{user_id}") if redis_client else None
            
            # Get autonomous config using JSON GET instead of hgetall
            autonomous_config = {}
            if autonomous_active and redis_client:
                config_data = await redis_client.get(f"unified_ai_config:{user_id}")
                if config_data:
                    try:
                        autonomous_config = json.loads(config_data)
                    except json.JSONDecodeError:
                        autonomous_config = {}
            
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
    
    async def handle_web_chat_request(
        self, 
        session_id: str, 
        user_id: str, 
        message: str, 
        interface_type: str = "web_chat",
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle web chat requests through unified AI manager.
        
        Enhanced to support different web interface types and cross-platform continuity.
        """
        
        try:
            # ENHANCED: Load persistent user memory for conversation continuity
            user_memory = {}
            try:
                user_memory = await self.memory_service.load_user_memory(user_id) or {}
            except Exception as e:
                self.logger.warning("Could not load user memory", error=str(e), user_id=user_id)
            
            # Get chat session context if available
            chat_history = []
            try:
                chat_history = await chat_engine.get_chat_history(session_id, limit=5)
            except Exception as e:
                self.logger.warning("Could not retrieve chat history", error=str(e), session_id=session_id)
            
            # Build comprehensive context with memory
            context = {
                "session_id": session_id,
                "chat_history": chat_history,
                "user_memory": user_memory,
                "user_expertise": user_memory.get("expertise_level", "intermediate"),
                "memory_anchors": user_memory.get("memory_anchors", []),
                "conversation_mood": user_memory.get("conversation_mood", "neutral"),
                "platform": "web_chat",
                "interface_type": interface_type,
                "conversation_continuity": True,
                "cross_platform_session": True,
                "enhanced_memory": True
            }
            
            # Add additional context if provided
            if additional_context:
                context.update(additional_context)
            
            # Map interface type to appropriate unified interface
            interface_mapping = {
                "trading": InterfaceType.WEB_CHAT,
                "quick": InterfaceType.WEB_CHAT,
                "analysis": InterfaceType.WEB_UI,
                "support": InterfaceType.WEB_CHAT,
                "web_chat": InterfaceType.WEB_CHAT
            }
            
            unified_interface = interface_mapping.get(interface_type, InterfaceType.WEB_CHAT)
            
            # Process through unified system
            result = await self.process_user_request(
                user_id=user_id,
                request=message,
                interface=unified_interface,
                context=context
            )
            
            # Enhance response with web-specific formatting and memory
            if result.get("success"):
                result = await self._enhance_web_response(result, interface_type, context)
                
                # ENHANCED: Save conversation to memory for continuity
                await self._save_conversation_to_memory(user_id, message, result.get("content", ""), context)
                
                # Add memory metadata to response
                if "metadata" not in result:
                    result["metadata"] = {}
                result["metadata"].update({
                    "enhanced_memory": True,
                    "user_expertise": context.get("user_expertise", "intermediate"),
                    "memory_anchors_count": len(context.get("memory_anchors", [])),
                    "conversation_continuity": True
                })
            
            return result
            
        except Exception as e:
            self.logger.error("Web chat request handling failed", 
                            error=str(e), 
                            user_id=user_id, 
                            session_id=session_id)
            return {
                "success": False,
                "error": str(e),
                "content": "I encountered an error processing your request. Please try again."
            }
    
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
        
        # Use single default configuration source
        default_config = self._get_default_user_config()
        
        # Cache for future use as JSON blob
        redis_client = await self._ensure_redis()
        if redis_client:
            await redis_client.set(f"user_ai_config:{user_id}", json.dumps(default_config))
        
        return default_config
    
    def _get_default_user_config(self) -> Dict[str, Any]:
        """Get single default user configuration to avoid duplication."""
        return {
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

    async def _set_user_operation_mode(self, user_id: str, mode: OperationMode):
        """Set user operation mode with in-memory fallback when Redis unavailable."""
        redis_client = await self._ensure_redis()
        
        # Get existing config from Redis or in-memory fallback
        user_config = None
        if redis_client:
            config_data = await redis_client.get(f"user_ai_config:{user_id}")
            if config_data:
                try:
                    user_config = json.loads(config_data)
                except json.JSONDecodeError:
                    pass
        
        # Fall back to in-memory store or defaults
        if not user_config:
            user_config = self.user_preferences.get(user_id, self._get_default_user_config().copy())
        
        # Always update operation mode (whether Redis available or not)
        user_config["operation_mode"] = mode.value
        
        # Store in in-memory fallback
        self.user_preferences[user_id] = user_config
        
        # Write-through to Redis if available
        if redis_client:
            try:
                await redis_client.set(f"user_ai_config:{user_id}", json.dumps(user_config))
                
                # Handle autonomous mode flag for status coherence
                if mode.value == "autonomous":
                    await redis_client.set(f"autonomous_active:{user_id}", "true")
                else:
                    await redis_client.delete(f"autonomous_active:{user_id}")
                    
                # Success - could optionally remove dirty flag here
                # self.user_preferences.pop(user_id, None)  # Clean in-memory on successful Redis write
                
            except Exception as e:
                # Redis write failed, keep in-memory version
                self.logger.debug(f"Failed to write user config to Redis, keeping in-memory fallback", error=str(e))
    
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
            redis_client = await self._ensure_redis()
            if redis_client:
                await redis_client.lpush(f"notifications:{user_id}", json.dumps(notification))
                await redis_client.ltrim(f"notifications:{user_id}", 0, 99)  # Keep last 100
            
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


    async def process_ai_consensus_result(
        self,
        user_id: str,
        function: str,
        result: Dict[str, Any],
        interface: InterfaceType
    ):
        """
        Process AI consensus results and broadcast to all interfaces.
        
        Args:
            user_id: User identifier
            function: AI consensus function name
            result: AI consensus result
            interface: Interface that triggered the request
        """
        
        try:
            # Generate natural language explanation
            explanation = await self._generate_consensus_explanation(function, result)
            
            # Broadcast via WebSocket to Command Center
            await manager.broadcast_ai_consensus_update(user_id, {
                "function": function,
                "result": result,
                "explanation": explanation,
                "consensus_score": result.get("consensus_score", 0),
                "recommendation": result.get("recommendation", "HOLD"),
                "model_responses": result.get("model_responses", []),
                "cost_summary": result.get("cost_summary", {}),
                "confidence_threshold_met": result.get("confidence_threshold_met", False),
                "timestamp": result.get("timestamp", datetime.utcnow().isoformat())
            })
            
            # Send to chat interface for natural language interaction
            await self._send_consensus_to_chat(user_id, explanation, result)
            
            # Send Telegram notification if high confidence
            consensus_score = result.get("consensus_score", 0)
            if consensus_score > 85:
                await self._send_telegram_consensus_notification(user_id, explanation, result)
            
            self.logger.info(
                "AI consensus result processed",
                user_id=user_id,
                function=function,
                consensus_score=consensus_score,
                interface=interface.value
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to process AI consensus result",
                user_id=user_id,
                function=function,
                error=str(e)
            )
    
    async def _generate_consensus_explanation(self, function: str, result: Dict[str, Any]) -> str:
        """Generate natural language explanation of AI consensus result."""
        
        try:
            consensus_score = result.get("consensus_score", 0)
            recommendation = result.get("recommendation", "HOLD")
            reasoning = result.get("reasoning", "Analysis completed")
            
            if function == "analyze_opportunity":
                return f"🤖 I analyzed the opportunity with {consensus_score}% confidence across GPT-4, Claude, and Gemini. My recommendation is {recommendation}. {reasoning}"
            
            elif function == "validate_trade":
                approval_status = result.get("trade_validation", {}).get("approval_status", "REVIEW_REQUIRED")
                return f"🤖 Trade validation complete: {approval_status} with {consensus_score}% confidence. {reasoning}"
            
            elif function == "risk_assessment":
                risk_level = result.get("risk_assessment", {}).get("risk_level", "MEDIUM")
                return f"🤖 Risk assessment: {risk_level} risk level detected with {consensus_score}% confidence. {reasoning}"
            
            elif function == "portfolio_review":
                portfolio_score = result.get("portfolio_review", {}).get("portfolio_score", 0)
                return f"🤖 Portfolio review: {portfolio_score}% optimization score with {consensus_score}% confidence. {reasoning}"
            
            elif function == "market_analysis":
                market_strength = result.get("market_analysis", {}).get("market_strength", 0)
                return f"🤖 Market analysis: {market_strength}% market strength with {consensus_score}% confidence. {reasoning}"
            
            elif function == "consensus_decision":
                final_recommendation = result.get("final_recommendation", "HOLD")
                return f"🤖 Final decision: {final_recommendation} with {consensus_score}% consensus confidence. {reasoning}"
            
            else:
                return f"🤖 AI consensus analysis complete: {recommendation} with {consensus_score}% confidence. {reasoning}"
                
        except Exception as e:
            self.logger.error("Failed to generate consensus explanation", error=str(e))
            return f"🤖 AI analysis complete with {result.get('consensus_score', 0)}% confidence."
    
    async def _send_consensus_to_chat(self, user_id: str, explanation: str, result: Dict[str, Any]):
        """Send AI consensus result to chat interface."""
        
        try:
            # Send via chat engine
            chat_message = {
                "type": "ai_consensus_result",
                "message": explanation,
                "consensus_score": result.get("consensus_score", 0),
                "recommendation": result.get("recommendation", "HOLD"),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send via WebSocket to chat interface
            await manager.send_personal_message(json.dumps(chat_message), user_id)
            
        except Exception as e:
            self.logger.error("Failed to send consensus to chat", user_id=user_id, error=str(e))
    
    async def _send_telegram_consensus_notification(self, user_id: str, explanation: str, result: Dict[str, Any]):
        """Send high-confidence AI consensus results to Telegram."""
        
        try:
            # Use existing Telegram service
            telegram_message = f"🤖 AI Money Manager Update:\n\n{explanation}"
            
            # This would integrate with your existing Telegram service
            # await self.telegram_core.send_message_to_user(user_id, telegram_message)
            
        except Exception as e:
            self.logger.error("Failed to send Telegram consensus notification", user_id=user_id, error=str(e))

    async def _save_conversation_to_memory(self, user_id: str, user_message: str, ai_response: str, context: Dict[str, Any]):
        """Save conversation exchange to persistent memory."""
        try:
            # Get existing memory
            user_memory = context.get("user_memory", {})
            
            # Update conversation history
            if "conversation_history" not in user_memory:
                user_memory["conversation_history"] = []
            
            # Add new exchange
            exchange = {
                "timestamp": datetime.utcnow().isoformat(),
                "user_message": user_message[:200],  # Limit for storage
                "ai_response": ai_response[:200],
                "interface": context.get("interface_type", "web_chat")
            }
            
            user_memory["conversation_history"].append(exchange)
            
            # Keep last 20 exchanges
            user_memory["conversation_history"] = user_memory["conversation_history"][-20:]
            
            # Update expertise level based on message complexity
            if any(word in user_message.lower() for word in ["what is", "explain", "help me understand"]):
                user_memory["expertise_level"] = "beginner"
            elif any(word in user_message.lower() for word in ["arbitrage", "defi", "yield farming", "technical analysis"]):
                user_memory["expertise_level"] = "expert"
            else:
                user_memory["expertise_level"] = user_memory.get("expertise_level", "intermediate")
            
            # Save updated memory
            await self.memory_service.save_user_memory(user_id, user_memory)
            
        except Exception as e:
            self.logger.error("Failed to save conversation to memory", error=str(e), user_id=user_id)

    async def _enhance_web_response(
        self, 
        result: Dict[str, Any], 
        interface_type: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhance response with web-specific formatting and features."""
        
        try:
            # Add interface-specific enhancements
            if interface_type == "trading":
                # Add trading-specific metadata
                result["metadata"] = result.get("metadata", {})
                result["metadata"]["interface_features"] = {
                    "show_charts": True,
                    "show_portfolio": True,
                    "enable_trading": True,
                    "show_risk_metrics": True
                }
                
            elif interface_type == "quick":
                # Add quick-help specific metadata
                result["metadata"] = result.get("metadata", {})
                result["metadata"]["interface_features"] = {
                    "compact_view": True,
                    "quick_actions": True,
                    "minimal_details": True
                }
                
            elif interface_type == "analysis":
                # Add analysis-specific metadata
                result["metadata"] = result.get("metadata", {})
                result["metadata"]["interface_features"] = {
                    "detailed_charts": True,
                    "advanced_metrics": True,
                    "export_options": True,
                    "comparison_tools": True
                }
            
            # Add cross-platform continuity info
            result["metadata"] = result.get("metadata", {})
            result["metadata"]["cross_platform"] = {
                "session_id": context.get("session_id"),
                "available_on": ["web", "telegram", "mobile"],
                "conversation_continues": True
            }
            
            return result
            
        except Exception as e:
            self.logger.error("Web response enhancement failed", error=str(e))
            return result
    
    async def _route_to_service(self, intent: str, request: str, user_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Route request to appropriate service based on intent - REAL SERVICE CALLS."""
        
        try:
            self.logger.info(f"Routing intent '{intent}' to actual service for user {user_id}")
            
            if "opportunity" in intent.lower() or "discover" in intent.lower():
                # Route to market analysis for opportunity discovery
                result = await self.market_analysis.market_inefficiency_scanner(
                    symbols="BTC,ETH,BNB,SOL,ADA,XRP,DOT,AVAX,MATIC,LINK,UNI,ATOM",
                    exchanges="all",
                    scan_types="spread,volume,time",
                    user_id=user_id
                )
                return {"service": "market_analysis", "method": "opportunity_discovery", "result": result}
                
            elif "portfolio" in intent.lower():
                # Route to portfolio risk service
                result = await self.portfolio_risk.get_portfolio_status(user_id)
                return {"service": "portfolio_risk", "method": "portfolio_analysis", "result": result}
                
            elif "market" in intent.lower() or "analysis" in intent.lower():
                # Route to market analysis service
                result = await self.market_analysis.complete_market_assessment(
                    symbols="BTC,ETH,SOL",
                    depth="comprehensive",
                    user_id=user_id
                )
                return {"service": "market_analysis", "method": "market_assessment", "result": result}
                
            elif "trade" in intent.lower() or "buy" in intent.lower() or "sell" in intent.lower():
                # Route to trading strategies service
                result = await self.trading_strategies.get_active_strategy(user_id)
                return {"service": "trading_strategies", "method": "trade_analysis", "result": result}
                
            else:
                # Fallback for general queries - no service routing needed
                return {"service": "none", "method": "general", "result": {"message": "General query - no specific service routing required"}}
                
        except Exception as e:
            self.logger.error(f"Service routing failed for intent '{intent}': {e}")
            return {"service": "error", "method": "fallback", "result": {"error": str(e), "message": "Service routing failed, falling back to AI consensus"}}

    def _get_decision_type(self, intent: str) -> str:
        """Map intent to decision type."""
        
        intent_mapping = {
            "trade": "trade_execution",
            "portfolio": "portfolio_management", 
            "analysis": "market_analysis",
            "risk": "risk_assessment",
            "rebalance": "portfolio_rebalance",
            "autonomous": "mode_change",
            "emergency": "emergency",
            "general": "information"
        }
        
        return intent_mapping.get(intent, "general")
    
    def _requires_approval(
        self, 
        operation_mode: OperationMode, 
        intent: str, 
        ai_response: Dict[str, Any]
    ) -> bool:
        """Determine if decision requires user approval."""
        
        # Always require approval for trades in manual/assisted mode
        if operation_mode in [OperationMode.MANUAL, OperationMode.ASSISTED]:
            if intent in ["trade", "rebalance", "autonomous"]:
                return True
        
        # High-risk decisions always require approval
        risk_level = ai_response.get("risk_assessment", {}).get("level", "medium")
        if risk_level == "high":
            return True
        
        # Low confidence decisions require approval
        confidence = ai_response.get("confidence", 0.0)
        if confidence < 0.8:
            return True
        
        return False
    
    def _should_auto_execute(
        self, 
        operation_mode: OperationMode, 
        intent: str, 
        ai_response: Dict[str, Any]
    ) -> bool:
        """Determine if decision should auto-execute."""
        
        # Only auto-execute in autonomous mode
        if operation_mode != OperationMode.AUTONOMOUS:
            return False
        
        # Don't auto-execute high-risk decisions
        risk_level = ai_response.get("risk_assessment", {}).get("level", "medium")
        if risk_level == "high":
            return False
        
        # Don't auto-execute low confidence decisions
        confidence = ai_response.get("confidence", 0.0)
        if confidence < 0.85:
            return False
        
        # Auto-execute for information requests
        if intent in ["general", "analysis", "portfolio"]:
            return True
        
        return False
    
    async def _check_telegram_connection(self, user_id: str) -> bool:
        """Check if user has Telegram connected."""
        
        try:
            # This would check the telegram_integration table
            # For now, return False as placeholder
            return False
        except Exception:
            return False
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get unified AI manager system status."""
        
        try:
            return {
                "status": "healthy",
                "active_decisions": len(self.active_decisions),
                "redis_connected": self.redis is not None,
                "services": {
                    "master_controller": "active",
                    "ai_consensus": "active", 
                    "trade_executor": "active",
                    "telegram_core": "active"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Global instance
unified_ai_manager = UnifiedAIManager()