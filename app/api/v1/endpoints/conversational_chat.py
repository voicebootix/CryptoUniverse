"""
Conversational AI Chat Endpoints

Provides streaming conversational AI interface to ALL platform features:
- Natural language financial conversations
- Real-time streaming responses  
- Paper trading and live trading integration
- Strategy marketplace and copy trading
- Autonomous trading control
- Portfolio management and analysis
- Market intelligence and opportunities
- Complete platform feature access
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.services.unified_ai_manager import unified_ai_manager
from app.services.conversational_ai_orchestrator import (
    get_conversational_ai_orchestrator,
    ConversationalAIOrchestrator,
    ConversationMode,
    ResponseType
)
from app.services.websocket import manager
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Conversational AI Chat"])


class ConversationalChatRequest(BaseModel):
    """Request model for conversational chat."""
    message: str = Field(..., description="User's natural language message")
    session_id: Optional[str] = Field(None, description="Chat session ID")
    conversation_mode: Optional[str] = Field("live_trading", description="Conversation mode: live_trading, paper_trading, strategy_exploration, learning, analysis")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")


class ConversationalChatResponse(BaseModel):
    """Response model for conversational chat."""
    success: bool
    session_id: str
    message_id: str
    response_chunks: List[Dict[str, Any]]
    conversation_mode: str
    personality: str
    requires_action: bool = False
    action_data: Optional[Dict[str, Any]] = None
    timestamp: datetime


class ActionConfirmationRequest(BaseModel):
    """Request model for action confirmation."""
    action_type: str = Field(..., description="Type of action to confirm")
    action_data: Dict[str, Any] = Field(..., description="Action data")
    confirmed: bool = Field(..., description="Whether action is confirmed")
    session_id: str = Field(..., description="Chat session ID")


@router.post("/conversational", response_model=ConversationalChatResponse)
async def conversational_chat(
    request: ConversationalChatRequest,
    current_user: User = Depends(get_current_user)
) -> ConversationalChatResponse:
    """
    Process conversational AI chat with complete platform integration.
    
    Handles ANY financial conversation naturally while providing access to:
    - Live trading and paper trading (simulation mode - no credits)
    - Strategy marketplace and copy trading
    - Autonomous trading control
    - Portfolio analysis and risk management
    - Market intelligence and opportunities
    - All platform features through natural language
    """
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Validate conversation mode
        try:
            conversation_mode = ConversationMode(request.conversation_mode)
        except ValueError:
            conversation_mode = ConversationMode.LIVE_TRADING
        
        logger.info(
            "Conversational chat request",
            user_id=str(current_user.id),
            session_id=session_id,
            mode=conversation_mode.value,
            message_length=len(request.message)
        )
        
        # Get conversational AI orchestrator
        try:
            orchestrator = await get_conversational_ai_orchestrator(unified_ai_manager)
        except Exception as e:
            logger.error("Failed to initialize conversational AI orchestrator", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Conversational AI service temporarily unavailable"
            )
        
        # Process conversation and collect streaming responses
        response_chunks = []
        personality = "Alex - Strategic Portfolio Manager"  # Default
        requires_action = False
        action_data = None
        
        async for chunk in orchestrator.process_conversation(
            user_message=request.message,
            session_id=session_id,
            user_id=str(current_user.id),
            conversation_mode=conversation_mode
        ):
            response_chunks.append(chunk)
            
            # Extract personality and action requirements
            if chunk.get("personality"):
                personality = chunk["personality"]
            
            if chunk.get("type") == ResponseType.ACTION_REQUIRED.value:
                requires_action = True
                action_data = {
                    "action": chunk.get("action"),
                    "content": chunk.get("content")
                }
        
        return ConversationalChatResponse(
            success=True,
            session_id=session_id,
            message_id=str(uuid.uuid4()),
            response_chunks=response_chunks,
            conversation_mode=conversation_mode.value,
            personality=personality,
            requires_action=requires_action,
            action_data=action_data,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(
            "Conversational chat failed",
            error=str(e),
            user_id=str(current_user.id),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while processing the request"
        )


@router.websocket("/stream/{session_id}")
async def conversational_chat_stream(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for real-time conversational AI chat.
    
    Provides streaming responses with <2 second latency for natural conversation.
    """
    user_id = None
    
    try:
        # Authenticate user via query params or cookies (secure method)
        token = None
        
        # Try to get token from query parameters
        query_params = getattr(websocket, 'scope', {}).get('query_string', b'').decode()
        if 'token=' in query_params:
            for param in query_params.split('&'):
                if param.startswith('token='):
                    token = param.split('=', 1)[1]
                    break
        
        # If no token in query params, try cookies
        if not token:
            cookies = getattr(websocket, 'scope', {}).get('headers', [])
            for name, value in cookies:
                if name == b'cookie':
                    cookie_str = value.decode()
                    for cookie in cookie_str.split(';'):
                        if 'access_token=' in cookie:
                            token = cookie.split('access_token=')[1].split(';')[0].strip()
                            break
        
        # Authenticate with token
        if token:
            try:
                from app.core.security import verify_access_token
                from jose import JWTError
                payload = verify_access_token(token)
                if payload and payload.get("sub"):
                    user_id = payload["sub"]
                    logger.info("Conversational WebSocket authenticated", user_id=user_id)
            except JWTError as e:
                logger.warning("WebSocket JWT authentication failed", error=str(e))
        
        # Require authentication
        if not user_id:
            logger.warning("Conversational WebSocket rejected: Authentication required")
            await websocket.close(code=1008, reason="Authentication required")
            return
        
        # Accept connection
        await websocket.accept()
        
        # Connect to WebSocket manager
        await manager.connect(websocket, user_id)
        
        logger.info("Conversational WebSocket connected", session_id=session_id, user_id=user_id)
        
        # Send connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Connected to CryptoUniverse Conversational AI",
            "features": [
                "Natural language financial conversations",
                "Real-time streaming responses",
                "Paper trading (simulation mode - no credits)",
                "Live trading with full validation",
                "Strategy marketplace integration",
                "Autonomous trading control",
                "Complete portfolio analysis",
                "Market intelligence and opportunities"
            ]
        }))
        
        # Get conversational AI orchestrator
        try:
            orchestrator = await get_conversational_ai_orchestrator(unified_ai_manager)
        except Exception as e:
            logger.error("Failed to initialize conversational AI orchestrator for WebSocket", error=str(e))
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Conversational AI service temporarily unavailable",
                "timestamp": datetime.utcnow().isoformat()
            }))
            await websocket.close(code=1011, reason="Service unavailable")
            return
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.utcnow().isoformat()
                }))
                continue
            
            if message_data.get("type") == "conversational_message":
                user_message = message_data.get("message", "")
                
                try:
                    conversation_mode = ConversationMode(
                        message_data.get("conversation_mode", "live_trading")
                    )
                except ValueError:
                    conversation_mode = ConversationMode.LIVE_TRADING
                
                if user_message.strip():
                    # Stream response in real-time
                    try:
                        async for response_chunk in orchestrator.process_conversation(
                            user_message=user_message,
                            session_id=session_id,
                            user_id=user_id,
                            conversation_mode=conversation_mode
                        ):
                            await websocket.send_text(json.dumps({
                                "type": "conversational_response",
                                "session_id": session_id,
                                "chunk": response_chunk,
                                "timestamp": datetime.utcnow().isoformat()
                            }))
                    except Exception as e:
                        logger.error("Conversation processing error", error=str(e))
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": f"Error processing conversation: {str(e)}",
                            "timestamp": datetime.utcnow().isoformat()
                        }))
            
            elif message_data.get("type") == "action_confirmation":
                # Handle action confirmations
                action_type = message_data.get("action_type")
                action_data = message_data.get("action_data", {})
                confirmed = message_data.get("confirmed", False)
                
                result = await orchestrator.handle_action_confirmation(
                    user_id=user_id,
                    action_type=action_type,
                    action_data=action_data,
                    confirmed=confirmed
                )
                
                await websocket.send_text(json.dumps({
                    "type": "action_result",
                    "session_id": session_id,
                    "action_type": action_type,
                    "result": result,
                    "timestamp": datetime.utcnow().isoformat()
                }))
            
            elif message_data.get("type") == "ping":
                # Handle ping for connection keep-alive
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                }))
            
            # Small delay to prevent overwhelming
            await asyncio.sleep(0.05)
            
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)
        logger.info("Conversational WebSocket disconnected", session_id=session_id, user_id=user_id)
    except asyncio.CancelledError:
        await manager.disconnect(websocket, user_id)
        raise
    except Exception as e:
        logger.exception("Conversational WebSocket error", session_id=session_id, user_id=user_id)
        await manager.disconnect(websocket, user_id)


@router.post("/action/confirm")
async def confirm_action(
    request: ActionConfirmationRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Confirm or cancel an action from conversational AI.
    
    Handles confirmations for:
    - Trade executions (live and paper trading)
    - Strategy purchases from marketplace
    - Autonomous trading mode changes
    - Portfolio rebalancing
    - Risk management actions
    """
    try:
        orchestrator = await get_conversational_ai_orchestrator(unified_ai_manager)
        
        result = await orchestrator.handle_action_confirmation(
            user_id=str(current_user.id),
            action_type=request.action_type,
            action_data=request.action_data,
            confirmed=request.confirmed
        )
        
        logger.info(
            "Action confirmation processed",
            user_id=str(current_user.id),
            action_type=request.action_type,
            confirmed=request.confirmed,
            success=result.get("success", False)
        )
        
        return {
            "success": True,
            "action_type": request.action_type,
            "confirmed": request.confirmed,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(
            "Action confirmation failed",
            error=str(e),
            user_id=str(current_user.id),
            action_type=request.action_type
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Action confirmation failed: {str(e)}"
        )


@router.get("/capabilities")
async def get_conversational_capabilities(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get comprehensive list of conversational AI capabilities.
    
    Shows all features accessible through natural language conversation.
    """
    try:
        orchestrator = await get_conversational_ai_orchestrator(unified_ai_manager)
        
        # Get user's current context to show personalized capabilities
        user_context = await orchestrator._build_complete_context(
            user_id=str(current_user.id),
            session_id=str(uuid.uuid4()),
            conversation_mode=ConversationMode.LIVE_TRADING
        )
        
        capabilities = {
            "trading_features": {
                "live_trading": {
                    "available": bool(user_context.portfolio_data.get("has_live_positions")),
                    "description": "Execute real trades with full validation and credit usage",
                    "examples": [
                        "Buy $1000 of Bitcoin",
                        "Sell half my Ethereum position",
                        "Set stop loss at 5% below current price"
                    ]
                },
                "paper_trading": {
                    "available": True,
                    "description": "Simulate trading with virtual money (NO CREDITS REQUIRED)",
                    "examples": [
                        "Let me practice trading with paper money",
                        "Simulate buying $5000 of crypto portfolio",
                        "Test my strategy in paper trading mode"
                    ]
                }
            },
            "portfolio_management": {
                "analysis": {
                    "available": True,
                    "description": "Comprehensive portfolio analysis and insights",
                    "examples": [
                        "How is my portfolio performing?",
                        "What's my biggest risk exposure?",
                        "Should I rebalance my allocation?"
                    ]
                },
                "risk_management": {
                    "available": True,
                    "description": "Advanced risk assessment and protection",
                    "examples": [
                        "Analyze my portfolio risk",
                        "Set up stop losses for my positions",
                        "How can I reduce volatility?"
                    ]
                }
            },
            "strategy_features": {
                "marketplace": {
                    "available": True,
                    "active_strategies": len(user_context.strategy_portfolio.get("active_strategies", [])),
                    "available_strategies": len(user_context.strategy_portfolio.get("available_strategies", [])),
                    "description": "Access to 25+ AI trading strategies",
                    "examples": [
                        "What strategies do I have?",
                        "Find me profitable arbitrage strategies",
                        "Show me the best performing strategies"
                    ]
                },
                "copy_trading": {
                    "available": True,
                    "description": "Follow successful traders and strategies",
                    "examples": [
                        "Find top performing traders to copy",
                        "Show me copy trading opportunities",
                        "How much can I earn from copy trading?"
                    ]
                }
            },
            "autonomous_trading": {
                "available": True,
                "currently_active": user_context.autonomous_status.get("is_active", False),
                "current_mode": user_context.autonomous_status.get("current_mode", "balanced"),
                "trading_modes": ["conservative", "balanced", "aggressive", "beast_mode"],
                "description": "Fully automated AI trading with personality modes",
                "examples": [
                    "Start autonomous trading in aggressive mode",
                    "How is my AI trader performing?",
                    "Switch to beast mode for maximum returns"
                ]
            },
            "market_intelligence": {
                "available": True,
                "description": "Real-time market analysis and opportunities",
                "examples": [
                    "What's happening in the crypto market?",
                    "Find me the best opportunities right now",
                    "Should I buy the dip or wait?"
                ]
            },
            "conversation_modes": {
                "live_trading": "Full trading with real money and credit usage",
                "paper_trading": "Risk-free simulation mode (no credits required)",
                "strategy_exploration": "Explore and learn about trading strategies",
                "learning": "Educational mode for understanding concepts",
                "analysis": "Focus on analysis and insights without trading"
            },
            "personalities": {
                user_context.trading_mode.value: {
                    "name": orchestrator.personalities[user_context.trading_mode]["name"],
                    "style": orchestrator.personalities[user_context.trading_mode]["style"],
                    "greeting": orchestrator.personalities[user_context.trading_mode]["greeting"]
                }
            },
            "user_status": {
                "trading_mode": user_context.trading_mode.value,
                "operation_mode": user_context.user_profile.get("operation_mode", "assisted"),
                "credits_available": user_context.credit_status.get("available_credits", 0),
                "has_paper_account": user_context.paper_trading_status.get("has_paper_account", False),
                "autonomous_active": user_context.autonomous_status.get("is_active", False)
            }
        }
        
        return {
            "success": True,
            "capabilities": capabilities,
            "platform_features_count": 50,  # Approximate count of all features
            "ai_models_available": ["GPT-4", "Claude", "Gemini"],
            "real_time_streaming": True,
            "paper_trading_no_credits": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get capabilities", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get capabilities: {str(e)}"
        )


@router.get("/personality/{trading_mode}")
async def get_personality_info(
    trading_mode: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get information about a specific AI personality/trading mode."""
    try:
        from app.services.master_controller import TradingMode
        
        # Validate trading mode
        try:
            mode = TradingMode(trading_mode.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid trading mode. Available: {[m.value for m in TradingMode]}"
            )
        
        orchestrator = await get_conversational_ai_orchestrator(unified_ai_manager)
        personality = orchestrator.personalities[mode]
        
        return {
            "success": True,
            "trading_mode": mode.value,
            "personality": personality,
            "mode_config": {
                "risk_tolerance": personality["risk_tolerance"],
                "decision_speed": personality["decision_speed"],
                "vocabulary": personality["vocabulary"]
            },
            "example_conversations": [
                f"User: 'How should I invest $1000?'",
                f"{personality['name']}: [Response in {personality['style']} style]"
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get personality info", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get personality info: {str(e)}"
        )