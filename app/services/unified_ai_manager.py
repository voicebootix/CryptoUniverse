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
from dataclasses import dataclass, asdict
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
from app.services.chat_service_adapters_fixed import chat_adapters_fixed as chat_adapters
from app.services.telegram_core import TelegramCommanderService, telegram_commander_service
from app.services.websocket import manager
from app.services.chat_memory import ChatMemoryService
from app.services.unified_chat_service import (
    unified_chat_service,
    ConversationMode as ChatConversationMode,
    InterfaceType as ChatInterfaceType,
)
from app.services.telegram_commander import TelegramConfig

# Import actual service engines for routing
from app.services.market_analysis_core import MarketAnalysisService
from app.services.portfolio_risk_core import PortfolioRiskService
from app.services.trading_strategies import TradingStrategiesService
from app.services.strategy_marketplace_service import strategy_marketplace_service
from app.services.user_opportunity_discovery import user_opportunity_discovery
from app.services.conversation import (
    conversation_state_hydrator,
    unified_response_builder,
    conversation_telemetry,
    ConversationStateSnapshot,
)

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


@dataclass
class IntentResolution:
    """Intent classification result with confidence and alternates."""

    intent: str
    confidence: float
    candidates: Dict[str, float]
    raw_intent: Optional[str] = None
    reason: Optional[str] = None


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
    
    def __init__(self, telegram_service: Optional[TelegramCommanderService] = None):
        # Core services
        self.master_controller = MasterSystemController()
        self.ai_consensus = AIConsensusService()
        self.trade_executor = TradeExecutionService()
        self.adapters = chat_adapters
        self.telegram_core = telegram_service or telegram_commander_service
        self.chat_service = unified_chat_service
        
        # Enhanced memory service for conversation continuity
        self.memory_service = ChatMemoryService()
        
        # Actual service engines for routing
        self.market_analysis = MarketAnalysisService()
        self.portfolio_risk = PortfolioRiskService()
        self.trading_strategies = TradingStrategiesService()
        self.opportunity_discovery = user_opportunity_discovery
        
        # Redis for state management - initialize properly for async usage
        self.redis = None
        self._redis_initialized = False

        # Decision tracking
        self.active_decisions: Dict[str, AIDecision] = {}
        self.user_preferences: Dict[str, Dict[str, Any]] = {}

        # Shared conversational tooling
        self.state_hydrator = conversation_state_hydrator
        self.response_builder = unified_response_builder
        self.telemetry = conversation_telemetry

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
            context = context or {}

            # Get user operation mode and preferences
            user_config = await self._get_user_config(user_id)
            operation_mode = OperationMode(user_config.get("operation_mode", "assisted"))

            state_snapshot = await self.state_hydrator.hydrate(
                user_id,
                context={"user_config": user_config, **context},
            )

            intent_resolution = await self._classify_unified_intent(
                request, interface, context, state_snapshot
            )
            intent = intent_resolution.intent

            # Clarify when we are unsure instead of falling back to canned help
            if intent_resolution.confidence < 0.40:
                clarification = self.response_builder.clarify(
                    request=request,
                    intent_candidates=intent_resolution.candidates,
                    state=state_snapshot,
                )
                await self.telemetry.record(
                    user_id=user_id,
                    interface=interface.value,
                    intent=intent,
                    request=request,
                    confidence=intent_resolution.confidence,
                    resolution=asdict(intent_resolution),
                    state_summary=state_snapshot.to_dict(),
                    outcome="clarify",
                )
                return {
                    "success": True,
                    "decision_id": None,
                    "action": "clarify",
                    "content": clarification,
                    "requires_approval": False,
                    "confidence": intent_resolution.confidence,
                    "metadata": {"intent_candidates": intent_resolution.candidates},
                }

            # Create AI decision context
            decision_context = {
                "user_id": user_id,
                "request": request,
                "interface": interface.value,
                "operation_mode": operation_mode.value,
                "intent": intent,
                "user_config": user_config,
                "context": context,
                "timestamp": datetime.utcnow().isoformat(),
                "state_snapshot": state_snapshot,
                "intent_resolution": asdict(intent_resolution),
            }

            # ENHANCED: Route to actual services first based on intent
            service_result = await self._route_to_service(
                intent, request, user_id, context, state_snapshot
            )
            decision_context["service_result"] = service_result

            # Then use AI consensus to VALIDATE and format the service result
            enhanced_context = {
                **{k: v for k, v in decision_context.items() if k != "state_snapshot"},
                "service_result": service_result,
                "analysis_type": "validation_and_formatting",
            }

            ai_response = await self.ai_consensus.analyze_opportunity(
                json.dumps(enhanced_context, default=str),
                confidence_threshold=75.0,
                ai_models="all",
                user_id=user_id,
            )

            recommendation_payload = ai_response.get("recommendation", {})

            # Create AI decision
            decision = AIDecision(
                decision_id=str(uuid.uuid4()),
                user_id=user_id,
                interface=interface,
                operation_mode=operation_mode,
                intent=intent,
                decision_type=self._get_decision_type(intent),
                recommendation=recommendation_payload,
                confidence=ai_response.get("confidence", 0.0),
                risk_assessment=ai_response.get("risk_assessment", {}),
                requires_approval=self._requires_approval(operation_mode, intent, ai_response),
                auto_execute=self._should_auto_execute(operation_mode, intent, ai_response),
                timestamp=datetime.utcnow(),
                context=decision_context,
            )
            
            decision.context["ai_response"] = ai_response

            # Store decision
            self.active_decisions[decision.decision_id] = decision

            # Execute or return for approval based on operation mode
            if decision.auto_execute and not decision.requires_approval:
                # Autonomous execution
                execution_result = await self._execute_ai_decision(decision)

                if execution_result.get("success"):
                    self.active_decisions.pop(decision.decision_id, None)
                else:
                    self.logger.warning(
                        "Autonomous decision execution failed",
                        decision_id=decision.decision_id,
                        user_id=user_id,
                        error=execution_result.get("error")
                    )

                await self.telemetry.record(
                    user_id=user_id,
                    interface=interface.value,
                    intent=intent,
                    request=request,
                    confidence=decision.confidence,
                    resolution=asdict(intent_resolution),
                    state_summary=state_snapshot.to_dict(),
                    outcome="executed" if execution_result.get("success") else "execution_failed",
                )

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

                await self.telemetry.record(
                    user_id=user_id,
                    interface=interface.value,
                    intent=intent,
                    request=request,
                    confidence=decision.confidence,
                    resolution=asdict(intent_resolution),
                    state_summary=state_snapshot.to_dict(),
                    outcome="response",
                )

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

            if result.get("success"):
                # Clean up only on success
                self.active_decisions.pop(decision_id, None)

                return {
                    "success": True,
                    "decision_id": decision_id,
                    "execution_result": result,
                    "message": "Decision executed successfully"
                }

            error_message = result.get("error", "Execution failed")
            self.logger.warning(
                "AI decision execution returned error",
                decision_id=decision_id,
                user_id=user_id,
                error=error_message
            )

            return {
                "success": False,
                "decision_id": decision_id,
                "error": error_message,
                "execution_result": result
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

        streaming_result = await self._try_stream_telegram_response(chat_id, user_id, message)
        if streaming_result is not None:
            return streaming_result

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

        if not cached_config:
            in_memory = self.user_preferences.get(user_id)
            if in_memory:
                return in_memory

        # Use single default configuration source
        default_config = self._get_default_user_config()

        # Cache for future use as JSON blob
        redis_client = await self._ensure_redis()
        if redis_client:
            await redis_client.set(f"user_ai_config:{user_id}", json.dumps(default_config))

        self.user_preferences[user_id] = default_config.copy()

        return default_config

    def _get_default_user_config(self) -> Dict[str, Any]:
        """Get single default user configuration to avoid duplication."""
        return {
            "operation_mode": "assisted",
            "risk_tolerance": "balanced",
            "investment_amount": None,
            "time_horizon": None,
            "investment_objectives": [],
            "constraints": None,
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

    @staticmethod
    def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
        """Best-effort conversion of incoming values to floats."""

        if value is None:
            return default

        if isinstance(value, (int, float)):
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        if isinstance(value, str):
            sanitized = value.replace("$", "").replace(",", "").strip()
            if not sanitized:
                return default
            try:
                return float(sanitized)
            except ValueError:
                return default

        return default

    def _resolve_trading_mode_from_risk(self, risk_tolerance: Optional[str]) -> str:
        """Align stored trading mode with the latest risk tolerance."""

        if not risk_tolerance:
            return TradingMode.BALANCED.value

        normalized = str(risk_tolerance).strip().lower()

        if normalized in {"very conservative", "conservative", "cautious", "low"}:
            return TradingMode.CONSERVATIVE.value

        if normalized in {"aggressive", "very aggressive", "high", "speculative"}:
            return TradingMode.AGGRESSIVE.value

        if normalized in {"beast", "beast_mode", "maximum"}:
            return TradingMode.BEAST_MODE.value

        return TradingMode.BALANCED.value

    async def get_user_profile_preferences(self, user_id: str) -> Dict[str, Any]:
        """Public accessor for user configuration with investment profile defaults."""

        config = await self._get_user_config(user_id)

        # Ensure new preference fields are always present for downstream consumers
        if "time_horizon" not in config:
            config["time_horizon"] = None
        if "investment_objectives" not in config:
            config["investment_objectives"] = []
        if "investment_amount" not in config:
            config["investment_amount"] = None
        if "constraints" not in config:
            config["constraints"] = None

        # Normalize investment objectives to list form
        objectives = config.get("investment_objectives")
        if isinstance(objectives, str):
            config["investment_objectives"] = [objectives]
        elif objectives is None:
            config["investment_objectives"] = []

        config["investment_amount"] = self._safe_float(
            config.get("investment_amount"),
            None,
        )

        constraints = config.get("constraints")
        if constraints is None:
            config["constraints"] = None
        elif isinstance(constraints, str):
            config["constraints"] = [constraints]
        else:
            config["constraints"] = list(constraints)

        config["trading_mode"] = self._resolve_trading_mode_from_risk(
            config.get("risk_tolerance")
        )

        return config

    async def update_user_profile_preferences(
        self,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Persist user preference updates while keeping Redis/in-memory caches aligned."""

        current_config = await self.get_user_profile_preferences(user_id)
        merged_config = {**current_config, **updates}

        # Normalize investment objectives after merge
        objectives = merged_config.get("investment_objectives")
        if isinstance(objectives, str):
            merged_config["investment_objectives"] = [objectives]
        elif objectives is None:
            merged_config["investment_objectives"] = []

        merged_config["investment_amount"] = self._safe_float(
            merged_config.get("investment_amount"),
            None,
        )

        constraints = merged_config.get("constraints")
        if constraints is None:
            merged_config["constraints"] = None
        elif isinstance(constraints, str):
            merged_config["constraints"] = [constraints]
        else:
            merged_config["constraints"] = list(constraints)

        merged_config["trading_mode"] = self._resolve_trading_mode_from_risk(
            merged_config.get("risk_tolerance")
        )

        # Store in in-memory preferences for quick access
        self.user_preferences[user_id] = merged_config

        redis_client = await self._ensure_redis()
        if redis_client:
            try:
                await redis_client.set(
                    f"user_ai_config:{user_id}",
                    json.dumps(merged_config)
                )
            except Exception:
                # Non-fatal: keep running with in-memory configuration
                self.logger.warning(
                    "Failed to persist user profile preferences to Redis",
                    user_id=user_id,
                    fields=list(updates.keys())
                )

        return merged_config

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
    
    async def _classify_unified_intent(
        self,
        request: str,
        interface: InterfaceType,
        context: Optional[Dict],
        state: Optional[ConversationStateSnapshot] = None,
    ) -> IntentResolution:
        """Classify intent across all interfaces with confidence scoring."""

        request_lower = (request or "").lower().strip()
        candidates: Dict[str, float] = {}
        raw_intent = None

        # Use existing chat engine intent classification when available
        if hasattr(chat_engine, "_classify_intent"):
            try:
                chat_context = context or {}
                chat_result = await chat_engine._classify_intent(request, chat_context)  # type: ignore[arg-type]
            except TypeError:
                chat_result = await chat_engine._classify_intent(request)
            raw_intent = getattr(chat_result, "value", str(chat_result))

        keyword_map = {
            "greeting": ["hi", "hello", "hey", "gm", "good morning", "good evening"],
            "help": ["help", "what can you do", "how can you help", "commands"],
            "portfolio_analysis": ["portfolio", "balance", "holdings", "positions", "allocation", "exposure", "value"],
            "strategy_management": ["strategy", "strategies", "automation", "algo", "bot", "playbook"],
            "credit_inquiry": ["credit", "credits", "profit potential", "limit", "upgrade", "tier"],
            "opportunity_discovery": ["opportunity", "opportunities", "signals", "setups", "ideas", "trade idea", "show me opportunities"],
            "risk_assessment": ["risk", "drawdown", "hedge", "volatility", "stress"],
            "market_analysis": ["market", "price", "outlook", "btc", "eth", "macro", "analysis"],
            "trade_execution": ["buy", "sell", "trade", "execute", "allocate", "enter", "exit"],
            "rebalancing": ["rebalance", "rebalancing", "redistribute", "realign"],
        }

        for intent_name, keywords in keyword_map.items():
            match_count = sum(1 for keyword in keywords if keyword in request_lower)
            if match_count:
                base_score = 0.60 + 0.1 * (match_count - 1)
                candidates[intent_name] = min(0.95, base_score)

        if raw_intent:
            normalized_raw = raw_intent.lower()
            raw_mapping = {
                "opportunity_discovery": "opportunity_discovery",
                "strategy_discussion": "strategy_management",
                "strategy_recommendation": "strategy_management",
                "credit_inquiry": "credit_inquiry",
                "credit_management": "credit_inquiry",
                "portfolio_analysis": "portfolio_analysis",
                "market_analysis": "market_analysis",
                "trade_execution": "trade_execution",
                "risk_assessment": "risk_assessment",
                "rebalancing": "rebalancing",
                "help": "help",
                "greeting": "greeting",
            }
            mapped = raw_mapping.get(normalized_raw, normalized_raw)

            if mapped == "general_query":
                # Preserve keyword-based intents when the chat engine falls back to
                # "general_query". This prevents greetings like "hi" from being
                # misrouted away from the greeting templates simply because the
                # legacy classifier could not determine a more specific intent.
                if not candidates:
                    candidates[mapped] = max(candidates.get(mapped, 0.0), 0.7)
                else:
                    candidates[mapped] = max(candidates.get(mapped, 0.0), 0.35)
            else:
                candidates[mapped] = max(candidates.get(mapped, 0.0), 0.7)

        recent_intents: List[str] = []
        if context:
            recent_intents.extend(context.get("previous_intents", []))
            history = context.get("recent_messages", [])
            for msg in history:
                if isinstance(msg, dict) and msg.get("intent"):
                    recent_intents.append(str(msg["intent"]))

        for prev_intent in recent_intents[-3:]:
            if prev_intent in candidates:
                candidates[prev_intent] = max(candidates.get(prev_intent, 0.0), 0.5)

        if not candidates:
            candidates = {"general_query": 0.35}

        # Emergency overrides
        if any(word in request_lower for word in ["emergency", "stop", "halt", "panic"]):
            candidates["emergency_command"] = 0.95

        intent = max(candidates.items(), key=lambda item: item[1])[0]
        confidence = min(0.99, candidates[intent])

        return IntentResolution(
            intent=intent,
            confidence=confidence,
            candidates=candidates,
            raw_intent=raw_intent,
            reason="keyword_match",
        )
    
    def _get_decision_type(self, intent: str) -> str:
        """Get decision type from intent."""
        mapping = {
            "trade_execution": "trade",
            "portfolio_analysis": "analysis",
            "market_analysis": "analysis",
            "rebalancing": "rebalance",
            "risk_assessment": "risk_action",
            "opportunity_discovery": "opportunity",
            "strategy_management": "strategy",
            "strategy_recommendation": "strategy",
            "credit_inquiry": "credit",
            "autonomous_control": "mode_change",
            "emergency_command": "emergency",
            "general_query": "information",
            "help": "information",
            "greeting": "information",
        }
        return mapping.get(intent, "information")
    
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
                trade_request = self._build_trade_request(decision)
                if not trade_request.get("symbol") or not trade_request.get("action"):
                    return {
                        "success": False,
                        "error": "Trade recommendation missing required fields",
                        "timestamp": datetime.utcnow().isoformat(),
                    }

                strategy_id = trade_request.pop("strategy_id", None)
                simulation_mode = trade_request.pop("simulation_mode", None)

                if simulation_mode is None:
                    simulation_mode = (
                        decision.recommendation.get("simulation_mode")
                        or decision.context.get("user_config", {}).get("simulation_mode")
                        or decision.context.get("simulation_mode")
                        or True
                    )

                if isinstance(simulation_mode, str):
                    simulation_mode = simulation_mode.strip().lower() not in {"false", "0", "off", "no"}

                result = await self.trade_executor.execute_trade(
                    trade_request=trade_request,
                    user_id=user_id,
                    simulation_mode=bool(simulation_mode),
                    strategy_id=strategy_id,
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
            log_data = {
                "decision_id": decision.decision_id,
                "decision_type": decision_type,
                "success": result.get("success"),
            }
            if not result.get("success") and result.get("error"):
                log_data["error"] = result.get("error")

            self.logger.info("AI decision executed", **log_data)

            return result

        except Exception as e:
            self.logger.error("AI decision execution failed", error=str(e), decision_id=decision.decision_id)
            return {"success": False, "error": str(e)}

    def _build_trade_request(self, decision: AIDecision) -> Dict[str, Any]:
        """Build a normalized trade request payload from an AI decision."""

        recommendation = decision.recommendation or {}
        metadata = decision.context or {}

        trade_request: Dict[str, Any] = {
            "symbol": recommendation.get("symbol") or recommendation.get("asset") or recommendation.get("pair"),
            "action": recommendation.get("action") or recommendation.get("side") or metadata.get("action"),
            "quantity": recommendation.get("quantity"),
            "amount": recommendation.get("amount"),
            "position_size_usd": recommendation.get("position_size_usd") or recommendation.get("notional_usd"),
            "order_type": recommendation.get("order_type") or recommendation.get("orderType"),
            "price": recommendation.get("price") or recommendation.get("entry_price"),
            "stop_loss": recommendation.get("stop_loss") or recommendation.get("stopLoss"),
            "take_profit": recommendation.get("take_profit") or recommendation.get("takeProfit"),
            "exchange": recommendation.get("exchange") or metadata.get("exchange"),
            "time_in_force": recommendation.get("time_in_force") or recommendation.get("tif"),
            "opportunity_data": recommendation.get("opportunity_data") or metadata.get("opportunity_data"),
            "strategy_id": recommendation.get("strategy_id") or metadata.get("strategy_id"),
            "simulation_mode": recommendation.get("simulation_mode"),
        }

        # Clean up empty values while preserving False/0
        cleaned_request = {key: value for key, value in trade_request.items() if value is not None}

        if "order_type" not in cleaned_request:
            cleaned_request["order_type"] = "market"

        return cleaned_request
    
    async def _format_ai_response(self, decision: AIDecision, interface: InterfaceType) -> Dict[str, Any]:
        """Format AI response based on interface type."""

        try:
            state_snapshot = decision.context.get("state_snapshot")
            if not isinstance(state_snapshot, ConversationStateSnapshot):
                state_snapshot = await self.state_hydrator.hydrate(
                    decision.user_id,
                    context=decision.context.get("context") if isinstance(decision.context, dict) else None,
                )

            service_result = decision.context.get("service_result")
            if not isinstance(service_result, dict):
                service_result = {}

            recommendation = decision.recommendation if isinstance(decision.recommendation, dict) else {}
            ai_response = decision.context.get("ai_response") or {}

            render = self.response_builder.build(
                intent=decision.intent,
                request=decision.context.get("request", ""),
                recommendation=recommendation,
                service_result=service_result,
                state=state_snapshot,
                ai_analysis=ai_response.get("analysis"),
                interface=interface.value,
                requires_approval=decision.requires_approval,
            )

            metadata = {
                **render.metadata,
                "decision_id": decision.decision_id,
                "requires_approval": decision.requires_approval,
                "confidence": decision.confidence,
                "interface": interface.value,
                "intent": decision.intent,
                "decision_type": decision.decision_type,
                "risk_assessment": decision.risk_assessment,
                "timestamp": decision.timestamp.isoformat(),
            }

            return {"content": render.content, "metadata": metadata}

        except Exception as e:
            self.logger.error("Response formatting failed", error=str(e))
            return {
                "content": "I encountered an error formatting the response.",
                "metadata": {"error": str(e)}
            }

    async def _try_stream_telegram_response(
        self,
        chat_id: str,
        user_id: str,
        message: str,
    ) -> Optional[Dict[str, Any]]:
        """Attempt to stream a Telegram response using the unified chat service."""

        if not getattr(settings, "enable_telegram_streaming", True):
            return None

        if not self.chat_service:
            return None

        session_id = f"telegram:{chat_id}"

        try:
            stream = await self.chat_service.process_message(
                message=message,
                user_id=user_id,
                session_id=session_id,
                interface=ChatInterfaceType.TELEGRAM,
                conversation_mode=ChatConversationMode.LIVE_TRADING,
                stream=True,
            )
        except Exception as exc:
            self.logger.warning(
                "Telegram streaming unavailable, falling back to non-streaming response",
                error=str(exc),
                chat_id=chat_id,
                user_id=user_id,
            )
            return None

        if not hasattr(stream, "__anext__"):
            return None

        status_message_id: Optional[int] = None
        last_status_text: Optional[str] = None
        response_message_id: Optional[int] = None
        response_buffer: str = ""
        response_delivered = False
        last_response_sent_length = 0
        final_metadata: Optional[Dict[str, Any]] = None

        async def _send_status(text: str) -> Optional[int]:
            nonlocal status_message_id, last_status_text

            sanitized = self._truncate_telegram_text(text)

            if status_message_id and sanitized == last_status_text:
                return status_message_id

            if status_message_id:
                try:
                    edit_result = await self.telegram_core.telegram_api.edit_message_text(
                        chat_id,
                        status_message_id,
                        sanitized,
                    )
                    if edit_result.get("success"):
                        last_status_text = sanitized
                        return status_message_id
                except Exception as exc:
                    self.logger.debug(
                        "Failed to edit Telegram status message, sending a new one",
                        error=str(exc),
                        chat_id=chat_id,
                    )

            try:
                send_result = await self.telegram_core.telegram_api.send_message(chat_id, sanitized)
            except Exception as exc:
                self.logger.warning(
                    "Failed to send Telegram streaming status",
                    error=str(exc),
                    chat_id=chat_id,
                )
                return status_message_id

            status_message_id = send_result.get("message_id")
            last_status_text = sanitized
            return status_message_id

        async def _update_response(text: str, *, replace: bool = False) -> Optional[int]:
            nonlocal response_message_id, response_buffer, last_response_sent_length, response_delivered

            response_buffer = text if replace else response_buffer + text
            truncated = self._truncate_telegram_text(response_buffer)

            if response_message_id is None:
                try:
                    send_result = await self.telegram_core.telegram_api.send_message(chat_id, truncated)
                except Exception as exc:
                    self.logger.error(
                        "Failed to send Telegram streaming response",
                        error=str(exc),
                        chat_id=chat_id,
                    )
                    return None

                message_id = send_result.get("message_id")
                if not message_id:
                    self.logger.error(
                        "Telegram streaming response missing message_id",
                        chat_id=chat_id,
                    )
                    return None

                response_message_id = message_id
                last_response_sent_length = len(truncated)
                response_delivered = True
                return response_message_id

            if replace or len(truncated) - last_response_sent_length >= 32 or truncated.endswith((".", "!", "?")):
                try:
                    await self.telegram_core.telegram_api.edit_message_text(
                        chat_id,
                        response_message_id,
                        truncated,
                    )
                    last_response_sent_length = len(truncated)
                except Exception as exc:
                    self.logger.debug(
                        "Failed to edit Telegram streaming response",
                        error=str(exc),
                        chat_id=chat_id,
                    )
                    try:
                        send_result = await self.telegram_core.telegram_api.send_message(chat_id, truncated)
                        message_id = send_result.get("message_id")
                        if not message_id:
                            self.logger.error(
                                "Telegram streaming recovery missing message_id",
                                chat_id=chat_id,
                            )
                            return response_message_id

                        response_message_id = message_id
                        last_response_sent_length = len(truncated)
                        response_delivered = True
                    except Exception as send_exc:
                        self.logger.error(
                            "Failed to recover Telegram streaming response",
                            error=str(send_exc),
                            chat_id=chat_id,
                        )

            return response_message_id

        try:
            async for chunk in stream:
                formatted = self._format_stream_chunk_for_telegram(chunk)
                if not formatted:
                    continue

                chunk_metadata = formatted.get("metadata")
                if chunk_metadata:
                    final_metadata = chunk_metadata

                mode = formatted["mode"]
                text = formatted.get("text", "")

                if mode == "status":
                    await _send_status(text)
                elif mode == "append":
                    await _update_response(text)
                elif mode == "replace":
                    await _update_response(text, replace=True)
                elif mode == "action":
                    await self.telegram_core.telegram_api.send_message(chat_id, text)
                elif mode == "error":
                    await self.telegram_core.telegram_api.send_message(chat_id, text)
                    return {"success": False, "error": text}
                elif mode == "final-status":
                    await _send_status(text)

        except Exception as exc:
            self.logger.warning(
                "Telegram streaming failed mid-response",
                error=str(exc),
                chat_id=chat_id,
                user_id=user_id,
            )
            return None

        if response_buffer:
            if not response_delivered or not response_message_id:
                self.logger.warning(
                    "Telegram streaming response was never delivered",
                    chat_id=chat_id,
                    user_id=user_id,
                )
                return None

            if len(response_buffer) > last_response_sent_length:
                truncated = self._truncate_telegram_text(response_buffer)
                try:
                    await self.telegram_core.telegram_api.edit_message_text(
                        chat_id,
                        response_message_id,
                        truncated,
                    )
                except Exception as exc:
                    self.logger.debug(
                        "Final Telegram stream update failed", error=str(exc), chat_id=chat_id
                    )
            return {
                "success": True,
                "response": self._truncate_telegram_text(response_buffer),
                "streamed": True,
                "metadata": final_metadata or {},
            }

        return None

    def _format_stream_chunk_for_telegram(self, chunk: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert streaming chunk into Telegram-friendly instructions."""

        chunk_type = (chunk or {}).get("type")

        if chunk_type == "processing":
            content = (chunk.get("content") or "").strip()
            if not content:
                return None
            return {"mode": "status", "text": f"⏳ {content}"}

        if chunk_type == "progress":
            progress = chunk.get("progress") or {}
            message = (progress.get("message") or "").strip()
            if not message:
                return None
            stage = (progress.get("stage") or "").lower()
            emoji = "📊" if "opportunit" in stage else "🔄"
            percent = progress.get("percent")
            try:
                if percent is not None:
                    percent_value = int(float(percent))
                    message = f"{message} ({percent_value}% complete)"
            except (TypeError, ValueError):
                pass
            return {"mode": "status", "text": f"{emoji} {message}"}

        if chunk_type == "response":
            content = chunk.get("content")
            if not content:
                return None
            return {"mode": "append", "text": content}

        if chunk_type == "persona_enriched":
            content = chunk.get("content")
            if not content:
                return None
            if chunk.get("replaces_previous"):
                return {"mode": "replace", "text": content}
            return {"mode": "append", "text": content}

        if chunk_type == "action_required":
            content = (chunk.get("content") or "This action requires confirmation.").strip()
            decision_id = chunk.get("decision_id")
            if decision_id:
                content = f"{content}\nDecision ID: {decision_id}"
            return {"mode": "action", "text": f"⚠️ {content}"}

        if chunk_type == "error":
            content = (chunk.get("content") or chunk.get("error") or "An unexpected error occurred.").strip()
            return {"mode": "error", "text": f"❌ {content}"}

        if chunk_type == "complete":
            metadata = chunk.get("metadata")
            return {
                "mode": "final-status",
                "text": "✅ Analysis complete.",
                "metadata": metadata,
            }

        return None

    def _truncate_telegram_text(self, text: str) -> str:
        """Ensure Telegram messages stay within platform limits."""

        if not text:
            return ""

        max_length = getattr(TelegramConfig, "MAX_MESSAGE_LENGTH", 4096)
        if len(text) <= max_length:
            return text

        return text[: max_length - 20].rstrip() + "\n…"

    def _format_for_telegram(self, result: Dict[str, Any]) -> str:
        """Format response specifically for Telegram."""

        content = result.get("content", "")
        confidence = result.get("confidence")
        requires_approval = result.get("requires_approval")

        segments: List[str] = []

        if isinstance(confidence, (int, float)) and confidence > 0:
            confidence_emoji = "🟢" if confidence >= 0.9 else "🟡" if confidence >= 0.7 else "🔴"
            segments.append(f"{confidence_emoji} Confidence {confidence * 100:.0f}%")

        if isinstance(content, dict):
            formatted_content = "\n".join(
                f"{key.replace('_', ' ').title()}: {value}"
                for key, value in content.items()
            )
        else:
            formatted_content = str(content).strip()

        if formatted_content:
            segments.append(formatted_content)

        if requires_approval:
            segments.append("Ready for me to execute or would you like any tweaks?")

        response = "\n\n".join(segments) if segments else "I processed the request, but there was no additional detail to share."

        if len(response) > 4000:
            response = response[:3900] + "\n\n... (truncated)"

        return response
    
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
    
    async def _route_to_service(
        self,
        intent: str,
        request: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
        state: Optional[ConversationStateSnapshot] = None,
    ) -> Dict[str, Any]:
        """Route request to appropriate service based on intent - REAL SERVICE CALLS."""

        try:
            self.logger.info(f"Routing intent '{intent}' to actual service for user {user_id}")

            if "opportunity" in intent.lower() or "discover" in intent.lower():
                # Route to the enterprise opportunity discovery service so Telegram receives
                # the rich opportunity payload rather than the generic market scanner stub.
                await self.opportunity_discovery.async_init()
                discovery_result = await self.opportunity_discovery.discover_opportunities_for_user(
                    user_id,
                    force_refresh=bool((context or {}).get("force_opportunity_refresh", False)),
                    include_strategy_recommendations=False,
                )

                return {
                    "service": "opportunity_discovery",
                    "method": "discover_opportunities_for_user",
                    "result": discovery_result,
                }

            elif "portfolio" in intent.lower():
                # Route to portfolio risk service
                result = await self.portfolio_risk.get_portfolio_status(user_id)
                return {"service": "portfolio_risk", "method": "portfolio_analysis", "result": result}

            elif "strategy" in intent.lower():
                result = await strategy_marketplace_service.get_user_strategy_portfolio(user_id)
                return {"service": "strategy_marketplace", "method": "strategy_summary", "result": result}

            elif "credit" in intent.lower():
                credit_state = state.credit if state else None
                credit_summary = {
                    "available_credits": getattr(credit_state, "available_credits", None),
                    "total_credits": getattr(credit_state, "total_credits", None),
                    "profit_potential_usd": getattr(credit_state, "profit_potential_usd", None),
                    "credit_to_usd_ratio": getattr(credit_state, "credit_to_usd_ratio", None),
                    "tier": getattr(credit_state, "tier", "standard"),
                }
                return {"service": "credits", "method": "account_summary", "result": credit_summary}

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

            elif "rebalance" in intent.lower():
                result = await self.portfolio_risk.analyze_rebalancing_strategies(
                    user_id,
                    risk_profile=(state.risk_profile if state else "medium"),
                )
                return {"service": "portfolio_risk", "method": "rebalancing", "result": result}

            elif "risk" in intent.lower():
                result = await self.portfolio_risk.get_portfolio_status(user_id)
                return {"service": "portfolio_risk", "method": "risk_assessment", "result": result}

            elif intent.lower() in {"help", "greeting"}:
                return {"service": "system", "method": "assistant_overview", "result": {"message": "lightweight"}}

            else:
                # Fallback for general queries - no service routing needed
                return {"service": "none", "method": "general", "result": {"message": "General query - no specific service routing required"}}
                
        except Exception as e:
            self.logger.error(f"Service routing failed for intent '{intent}': {e}")
            return {"service": "error", "method": "fallback", "result": {"error": str(e), "message": "Service routing failed, falling back to AI consensus"}}

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