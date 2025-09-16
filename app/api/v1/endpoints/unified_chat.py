"""
Unified Chat API Endpoints

SINGLE endpoint file for ALL chat operations.
Consolidates functionality from chat.py and conversational_chat.py.
NO DUPLICATES - One source of truth.
"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.services.unified_chat_service import (
    unified_chat_service,
    InterfaceType,
    ConversationMode,
    TradingMode
)
from app.services.websocket import manager as websocket_manager
import structlog

logger = structlog.get_logger(__name__)

# Create single router for all chat endpoints
router = APIRouter(tags=["Unified Chat"])


# Request/Response Models - Consolidated
class UnifiedChatRequest(BaseModel):
    """Unified chat request model for all chat operations."""
    message: str = Field(..., description="User's message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    conversation_mode: Optional[str] = Field("live_trading", description="Mode: live_trading, paper_trading, learning, analysis")
    stream: Optional[bool] = Field(False, description="Enable streaming response")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")


class UnifiedChatResponse(BaseModel):
    """Unified chat response model."""
    success: bool
    session_id: str
    message_id: str
    content: str
    intent: str
    confidence: float
    requires_approval: bool = False
    decision_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime


class ChatHistoryResponse(BaseModel):
    """Response model for chat history."""
    success: bool
    session_id: str
    messages: List[Dict[str, Any]]
    total_messages: int


class ChatSessionsResponse(BaseModel):
    """Response model for chat sessions."""
    success: bool
    sessions: List[str]
    active_count: int


class ChatCapabilitiesResponse(BaseModel):
    """Response model for platform capabilities."""
    success: bool
    capabilities: Dict[str, Any]
    platform_features: List[str]
    ai_models: List[str]
    timestamp: datetime


class ActionConfirmationRequest(BaseModel):
    """Request model for action confirmation."""
    decision_id: str = Field(..., description="Decision ID to confirm")
    approved: bool = Field(..., description="Whether action is approved")
    modifications: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional modifications")


class ActionConfirmationResponse(BaseModel):
    """Response model for action confirmation."""
    success: bool
    decision_id: str
    execution_result: Optional[Dict[str, Any]] = None
    message: str
    timestamp: datetime


# Main Chat Endpoint - Unified for all operations
@router.post("/message", response_model=UnifiedChatResponse)
async def send_message(
    request: UnifiedChatRequest,
    current_user: User = Depends(get_current_user)
) -> UnifiedChatResponse:
    """
    Send a message to the unified AI chat system.
    
    This single endpoint handles ALL chat operations:
    - Portfolio analysis with real exchange data
    - Trade execution with 5-phase validation
    - Market analysis and opportunities
    - Risk assessment and rebalancing
    - Strategy recommendations
    - Paper trading (NO CREDITS required)
    - All other chat features
    
    The AI will use the appropriate personality based on your trading mode.
    """
    try:
        # Validate conversation mode
        try:
            conversation_mode = ConversationMode(request.conversation_mode.lower())
        except ValueError:
            conversation_mode = ConversationMode.LIVE_TRADING
        
        # Process message through unified service
        result = await unified_chat_service.process_message(
            message=request.message,
            user_id=str(current_user.id),
            session_id=request.session_id,
            interface=InterfaceType.WEB_CHAT,
            conversation_mode=conversation_mode,
            stream=False  # Regular endpoint doesn't stream
        )
        
        if result["success"]:
            return UnifiedChatResponse(
                success=True,
                session_id=result["session_id"],
                message_id=result["message_id"],
                content=result["content"],
                intent=result["intent"],
                confidence=result["confidence"],
                requires_approval=result.get("requires_approval", False),
                decision_id=result.get("decision_id"),
                metadata=result.get("metadata", {}),
                timestamp=result["timestamp"]
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Chat processing failed")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Chat message processing failed", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred processing your message: {str(e)}"
        )


# Streaming Chat Endpoint
@router.post("/stream")
async def stream_message(
    request: UnifiedChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Stream a chat response for real-time conversation experience.
    
    Returns Server-Sent Events (SSE) for streaming responses.
    Provides natural conversation flow with <100ms latency between chunks.
    """
    try:
        # Validate conversation mode
        try:
            conversation_mode = ConversationMode(request.conversation_mode.lower())
        except ValueError:
            conversation_mode = ConversationMode.LIVE_TRADING
        
        async def generate():
            """Generate SSE stream."""
            try:
                async for chunk in unified_chat_service.process_message(
                    message=request.message,
                    user_id=str(current_user.id),
                    session_id=request.session_id,
                    interface=InterfaceType.WEB_CHAT,
                    conversation_mode=conversation_mode,
                    stream=True
                ):
                    # Format as SSE
                    data = json.dumps(chunk)
                    yield f"data: {data}\n\n"
                
                # Send completion event
                yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                
            except Exception as e:
                error_data = json.dumps({
                    "type": "error",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
                yield f"data: {error_data}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable Nginx buffering
            }
        )
        
    except Exception as e:
        logger.exception("Streaming chat failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Chat History
@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
) -> ChatHistoryResponse:
    """
    Get chat history for a specific session.
    
    Returns up to 'limit' messages from the session.
    Messages include both user and AI responses with metadata.
    """
    try:
        messages = await unified_chat_service.get_chat_history(
            session_id=session_id,
            user_id=str(current_user.id),
            limit=limit
        )
        
        return ChatHistoryResponse(
            success=True,
            session_id=session_id,
            messages=messages,
            total_messages=len(messages)
        )
        
    except Exception as e:
        logger.error("Failed to get chat history", error=str(e), session_id=session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history"
        )


# User Sessions
@router.get("/sessions", response_model=ChatSessionsResponse)
async def get_user_sessions(
    current_user: User = Depends(get_current_user)
) -> ChatSessionsResponse:
    """
    Get all active chat sessions for the current user.
    
    Sessions are considered active if used within the last 24 hours.
    """
    try:
        sessions = await unified_chat_service.get_active_sessions(str(current_user.id))
        
        return ChatSessionsResponse(
            success=True,
            sessions=sessions,
            active_count=len(sessions)
        )
        
    except Exception as e:
        logger.error("Failed to get user sessions", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat sessions"
        )


# Create New Session
@router.post("/session/new")
async def create_new_session(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Create a new chat session.
    
    Returns a new session ID for starting a fresh conversation.
    """
    try:
        session_id = str(uuid.uuid4())
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "New chat session created",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to create chat session", error=str(e))
        return {
            "success": False,
            "session_id": None,
            "message": "Failed to create session",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# Platform Capabilities
@router.get("/capabilities", response_model=ChatCapabilitiesResponse)
async def get_capabilities(
    current_user: User = Depends(get_current_user)
) -> ChatCapabilitiesResponse:
    """
    Get comprehensive list of platform capabilities accessible through chat.
    
    Shows all features available including:
    - Trading capabilities (live and paper)
    - Strategy marketplace access
    - Portfolio management features
    - Risk analysis tools
    - And much more
    """
    try:
        # Get user-specific capabilities
        capabilities = {
            "trading": {
                "live_trading": {
                    "enabled": True,
                    "requires_credits": True,
                    "features": ["spot", "futures", "options"],
                    "exchanges": ["binance", "kucoin", "coinbase"]
                },
                "paper_trading": {
                    "enabled": True,
                    "requires_credits": False,
                    "description": "Full simulation mode with NO CREDIT requirement"
                }
            },
            "portfolio": {
                "analysis": True,
                "rebalancing": True,
                "risk_assessment": True,
                "performance_tracking": True
            },
            "strategies": {
                "marketplace_access": True,
                "total_strategies": 25,
                "copy_trading": True,
                "backtesting": True
            },
            "autonomous": {
                "enabled": True,
                "modes": ["conservative", "balanced", "aggressive", "beast_mode"],
                "current_mode": "balanced"
            },
            "market": {
                "real_time_data": True,
                "technical_analysis": True,
                "opportunity_discovery": True,
                "sentiment_analysis": True
            },
            "ai_features": {
                "natural_language": True,
                "multi_model_validation": True,
                "personalities": ["Warren", "Alex", "Hunter", "Apex"],
                "streaming_responses": True
            }
        }
        
        platform_features = [
            "5-phase trade validation",
            "Real exchange integration",
            "Credit-based operations",
            "Paper trading (no credits)",
            "Strategy marketplace",
            "Copy trading",
            "Autonomous trading",
            "Risk management",
            "Portfolio optimization",
            "Multi-exchange support",
            "Telegram integration",
            "WebSocket streaming",
            "API access",
            "Mobile support"
        ]
        
        return ChatCapabilitiesResponse(
            success=True,
            capabilities=capabilities,
            platform_features=platform_features,
            ai_models=["GPT-4", "Claude", "Gemini"],
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.exception("Failed to get capabilities", user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve capabilities"
        )


# Action Confirmation
@router.post("/action/confirm", response_model=ActionConfirmationResponse)
async def confirm_action(
    request: ActionConfirmationRequest,
    current_user: User = Depends(get_current_user)
) -> ActionConfirmationResponse:
    """
    Confirm or reject an action proposed by the AI.
    
    Used for:
    - Trade execution confirmations
    - Rebalancing approvals
    - Strategy purchases
    - Any high-impact operations
    """
    try:
        result = await unified_chat_service.execute_decision(
            decision_id=request.decision_id,
            user_id=str(current_user.id),
            approved=request.approved,
            modifications=request.modifications
        )
        
        return ActionConfirmationResponse(
            success=result.get("success", False),
            decision_id=request.decision_id,
            execution_result=result.get("execution_details"),
            message=result.get("message", "Action processed"),
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.exception("Action confirmation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process action: {str(e)}"
        )


# Service Status
@router.get("/status")
async def get_chat_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the current status of the unified chat service.
    
    Shows health of all integrated services and features.
    """
    try:
        status = await unified_chat_service.get_service_status()
        
        return {
            "success": True,
            "service_status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get chat status", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "service_status": "error",
            "timestamp": datetime.utcnow().isoformat()
        }


# WebSocket Endpoint - Unified streaming chat
@router.websocket("/ws/{session_id}")
async def chat_websocket(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for real-time chat communication.
    
    Features:
    - Real-time streaming responses
    - Bidirectional communication
    - < 100ms latency
    - Personality-driven conversations
    - Full platform feature access
    """
    user_id = None
    
    try:
        # Authenticate via token (from query params or headers)
        if not token:
            # Try query params
            query_params = getattr(websocket, 'scope', {}).get('query_string', b'').decode()
            if 'token=' in query_params:
                for param in query_params.split('&'):
                    if param.startswith('token='):
                        token = param.split('=', 1)[1]
                        break
        
        # Authenticate
        if token:
            try:
                from app.core.security import verify_access_token
                from jose import JWTError
                payload = verify_access_token(token)
                if payload and payload.get("sub"):
                    user_id = payload["sub"]
                    logger.info("WebSocket authenticated", user_id=user_id)
            except JWTError as e:
                logger.warning("WebSocket authentication failed", error=str(e))
        
        # Require authentication
        if not user_id:
            logger.warning("WebSocket rejected: Authentication required")
            await websocket.close(code=1008, reason="Authentication required")
            return
        
        # Accept connection
        await websocket.accept()
        
        # Connect to WebSocket manager
        await websocket_manager.connect(websocket, user_id)
        
        logger.info("Chat WebSocket connected", session_id=session_id, user_id=user_id)
        
        # Send connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Connected to CryptoUniverse Unified Chat",
            "features": [
                "Natural language conversations",
                "Real-time streaming",
                "5-phase trade validation",
                "Paper trading (no credits)",
                "Live trading with credits",
                "Strategy marketplace",
                "Portfolio analysis",
                "Risk management"
            ]
        }))
        
        while True:
            # Receive message
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
            
            if message_data.get("type") == "chat_message":
                user_message = message_data.get("message", "")
                conversation_mode = ConversationMode(
                    message_data.get("conversation_mode", "live_trading").lower()
                )
                
                if user_message.strip():
                    try:
                        # Stream response
                        async for chunk in unified_chat_service.process_message(
                            message=user_message,
                            user_id=user_id,
                            session_id=session_id,
                            interface=InterfaceType.WEB_CHAT,
                            conversation_mode=conversation_mode,
                            stream=True
                        ):
                            await websocket.send_text(json.dumps({
                                "type": "chat_response",
                                "session_id": session_id,
                                "chunk": chunk,
                                "timestamp": datetime.utcnow().isoformat()
                            }))
                    except Exception as e:
                        logger.exception("WebSocket message processing error", exc_info=True)
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "Error processing message",
                            "timestamp": datetime.utcnow().isoformat()
                        }))
            
            elif message_data.get("type") == "action_confirmation":
                # Handle action confirmations
                decision_id = message_data.get("decision_id")
                approved = message_data.get("approved", False)
                
                result = await unified_chat_service.execute_decision(
                    decision_id=decision_id,
                    user_id=user_id,
                    approved=approved
                )
                
                await websocket.send_text(json.dumps({
                    "type": "action_result",
                    "session_id": session_id,
                    "decision_id": decision_id,
                    "result": result,
                    "timestamp": datetime.utcnow().isoformat()
                }))
            
            elif message_data.get("type") == "ping":
                # Keep-alive
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                }))
            
            # Small delay to prevent overwhelming
            await asyncio.sleep(0.05)
            
    except WebSocketDisconnect:
        if user_id:
            await websocket_manager.disconnect(websocket, user_id)
        logger.info("WebSocket disconnected", session_id=session_id)
    except asyncio.CancelledError:
        if user_id:
            await websocket_manager.disconnect(websocket, user_id)
        raise
    except Exception as e:
        logger.exception("WebSocket error", session_id=session_id, error=str(e))
        if user_id:
            await websocket_manager.disconnect(websocket, user_id)


# Quick Analysis Endpoints (preserved functionality)
@router.post("/quick/portfolio")
async def quick_portfolio_analysis(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get a quick AI-powered portfolio analysis.
    
    Provides instant insights without full conversation.
    """
    try:
        result = await unified_chat_service.process_message(
            message="Give me a comprehensive analysis of my current portfolio",
            user_id=str(current_user.id),
            interface=InterfaceType.WEB_CHAT,
            conversation_mode=ConversationMode.ANALYSIS,
            stream=False
        )
        
        return {
            "success": True,
            "analysis": result.get("content"),
            "confidence": result.get("confidence"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Quick portfolio analysis failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform portfolio analysis"
        )


@router.post("/quick/opportunities")
async def discover_opportunities(
    risk_level: str = "balanced",
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Discover market opportunities through AI analysis.
    """
    try:
        result = await unified_chat_service.process_message(
            message=f"Find me the best trading opportunities with {risk_level} risk",
            user_id=str(current_user.id),
            interface=InterfaceType.WEB_CHAT,
            conversation_mode=ConversationMode.ANALYSIS,
            stream=False
        )
        
        return {
            "success": True,
            "opportunities": result.get("content"),
            "confidence": result.get("confidence"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Opportunity discovery failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to discover opportunities"
        )