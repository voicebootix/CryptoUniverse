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

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from urllib.parse import parse_qs
import time
from collections import defaultdict

from app.api.v1.endpoints.auth import get_current_user, auth_service
from app.api.dependencies.sse_auth import get_current_user_sse
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
    requires_action: bool = False
    decision_id: Optional[str] = None
    action_data: Optional[Dict[str, Any]] = None
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
        
        intent_value = result.get("intent")
        if hasattr(intent_value, "value"):
            intent_value = intent_value.value

        if result["success"]:
            return UnifiedChatResponse(
                success=True,
                session_id=result["session_id"],
                message_id=result["message_id"],
                content=result["content"],
                intent=intent_value or "",
                confidence=result["confidence"],
                requires_approval=result.get("requires_approval", False),
                requires_action=result.get("requires_action", False),
                decision_id=result.get("decision_id"),
                action_data=result.get("action_data"),
                metadata=result.get("metadata", {}),
                timestamp=result["timestamp"]
            )
        else:
            if result.get("requires_action"):
                metadata = result.get("metadata") or {}
                action_data = result.get("action_data")
                if action_data:
                    metadata = {**metadata, "action_data": action_data}

                confidence = result.get("confidence")
                if confidence is None:
                    confidence = 0.0

                return UnifiedChatResponse(
                    success=False,
                    session_id=result.get("session_id", result.get("session", "")),
                    message_id=result.get("message_id", str(uuid.uuid4())),
                    content=result.get("content", ""),
                    intent=intent_value or "",
                    confidence=confidence,
                    requires_approval=result.get("requires_approval", False),
                    requires_action=True,
                    decision_id=result.get("decision_id"),
                    action_data=action_data,
                    metadata=metadata,
                    timestamp=result.get("timestamp", datetime.utcnow())
                )

            # Check if this is a requirements failure (credit/access) rather than a system error
            error_detail = result.get("error", "Chat processing failed")
            content_detail = result.get("content", "")

            # Credit/access failures should return 402/403, not 500
            if "insufficient credits" in content_detail.lower() or "credits" in content_detail.lower():
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=content_detail
                )
            elif "access" in content_detail.lower() or "permission" in content_detail.lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=content_detail
                )
            else:
                # True system errors remain 500
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_detail
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
@router.get("/stream")
async def stream_message(
    message: str = Query(..., description="The user's message"),
    session_id: Optional[str] = Query(None, description="Session ID for conversation continuity"),
    conversation_mode: str = Query("live_trading", description="Conversation mode"),
    current_user: User = Depends(get_current_user_sse)
):
    """
    Stream a chat response for real-time conversation experience.
    
    Returns Server-Sent Events (SSE) for streaming responses.
    Provides natural conversation flow with <100ms latency between chunks.
    """
    try:
        # Validate conversation mode
        try:
            validated_mode = ConversationMode(conversation_mode.lower())
        except ValueError:
            validated_mode = ConversationMode.LIVE_TRADING
        
        async def generate():
            """Generate SSE stream."""
            try:
                # Generate session ID if not provided
                actual_session_id = session_id or str(uuid.uuid4())
                
                # Await process_message to get the async generator
                generator = await unified_chat_service.process_message(
                    message=message,
                    user_id=str(current_user.id),
                    session_id=actual_session_id,
                    interface=InterfaceType.WEB_CHAT,
                    conversation_mode=validated_mode,
                    stream=True
                )
                
                # Now iterate over the async generator
                async for chunk in generator:
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
        
        # Log session creation for the user
        logger.info(
            "New chat session created",
            session_id=session_id,
            user_id=str(current_user.id)
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "New chat session created",
            "user_id": str(current_user.id),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to create chat session", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session"
        ) from e


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
        service_status = await unified_chat_service.get_service_status()
        
        return {
            "success": True,
            "service_status": service_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get chat status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": str(e),
                "service_status": "error",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


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
    
    # Simple rate limiting for failed auth attempts
    client_host = websocket.client.host if hasattr(websocket, 'client') else "unknown"
    
    try:
        # Authenticate via token (from query params or headers)
        if not token:
            # Try query params with proper URL decoding
            scope = getattr(websocket, 'scope', {})
            query_string = scope.get('query_string', b'')
            if query_string:
                params = parse_qs(query_string.decode('utf-8'))
                token = params.get('token', [None])[0]
        
        # Authenticate
        if token:
            try:
                from app.core.security import verify_access_token
                from jose import JWTError
                payload = verify_access_token(token)
                if payload and payload.get("sub"):
                    user_id = payload["sub"]
                    logger.info("WebSocket authenticated", user_id=user_id, client=client_host)
            except JWTError as e:
                logger.warning("WebSocket authentication failed", error=str(e), client=client_host)
            except Exception as e:
                logger.error("WebSocket auth error", error=str(e), client=client_host)
        
        # Require authentication
        if not user_id:
            logger.warning("WebSocket rejected: Authentication required", client=client_host)
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
        
        # Rate limiting setup
        MAX_MESSAGE_LENGTH = 4096
        RATE_LIMIT_MESSAGES = 30  # messages per minute
        RATE_LIMIT_WINDOW = 60    # seconds
        
        message_timestamps = []
        
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            # Validate message size
            if len(data) > MAX_MESSAGE_LENGTH * 2:  # Allow some overhead for JSON
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": f"Message too long. Maximum {MAX_MESSAGE_LENGTH} characters allowed.",
                    "code": "MESSAGE_TOO_LONG",
                    "timestamp": datetime.utcnow().isoformat()
                }))
                continue
            
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
                
                # Check message length
                if len(user_message) > MAX_MESSAGE_LENGTH:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "error": f"Message too long. Maximum {MAX_MESSAGE_LENGTH} characters allowed.",
                        "code": "MESSAGE_TOO_LONG",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                    continue
                
                # Rate limiting check
                current_time = time.time()
                message_timestamps = [t for t in message_timestamps if current_time - t < RATE_LIMIT_WINDOW]
                
                if len(message_timestamps) >= RATE_LIMIT_MESSAGES:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "error": f"Rate limit exceeded. Maximum {RATE_LIMIT_MESSAGES} messages per minute.",
                        "code": "RATE_LIMIT_EXCEEDED",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                    continue
                
                message_timestamps.append(current_time)
                
                conversation_mode = ConversationMode(
                    message_data.get("conversation_mode", "live_trading").lower()
                )
                
                if user_message.strip():
                    try:
                        # Stream response - await to get the async generator first
                        generator = await unified_chat_service.process_message(
                            message=user_message,
                            user_id=user_id,
                            session_id=session_id,
                            interface=InterfaceType.WEB_CHAT,
                            conversation_mode=conversation_mode,
                            stream=True
                        )
                        
                        # Now iterate over the async generator
                        async for chunk in generator:
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