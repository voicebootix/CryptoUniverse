"""
Chat API Endpoints

Provides REST and WebSocket endpoints for the AI chat engine functionality.
Enables comprehensive cryptocurrency money management through natural language chat.
"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.api.v1.endpoints.auth import get_current_user
from app.core.database import get_database
from app.models.user import User
from app.services.ai_chat_engine import chat_engine, ChatMessageType
from app.services.chat_integration import chat_integration
from app.services.websocket import manager
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["AI Chat"])


# Pydantic models for request/response
class ChatMessageRequest(BaseModel):
    """Request model for sending chat messages."""
    message: str = Field(..., description="The user's message content")
    session_id: Optional[str] = Field(None, description="Optional session ID to continue existing conversation")


class ChatMessageResponse(BaseModel):
    """Response model for chat messages."""
    success: bool
    session_id: str
    message_id: str
    content: str
    intent: str
    confidence: float
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime


class ChatHistoryResponse(BaseModel):
    """Response model for chat history."""
    success: bool
    session_id: str
    messages: List[Dict[str, Any]]
    total_messages: int


class ChatSessionResponse(BaseModel):
    """Response model for chat sessions."""
    success: bool
    sessions: List[str]


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user)
) -> ChatMessageResponse:
    """
    Send a message to the AI chat engine.
    
    The AI will analyze the message and provide appropriate responses for:
    - Portfolio management
    - Trade execution
    - Market analysis
    - Risk assessment
    - Rebalancing recommendations
    - Opportunity discovery
    """
    try:
        # Process message through chat engine
        response = await chat_engine.process_message(
            session_id=request.session_id or "",
            user_message=request.message,
            user_id=str(current_user.id)
        )
        
        if not response.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.get("error", "Failed to process message")
            )
        
        return ChatMessageResponse(
            success=True,
            session_id=response["session_id"],
            message_id=response["message_id"],
            content=response["content"],
            intent=response["intent"],
            confidence=response["confidence"] or 0.0,
            metadata=response.get("metadata"),
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error("Chat message processing failed", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat message"
        )


@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
) -> ChatHistoryResponse:
    """
    Get chat history for a specific session.
    """
    try:
        messages = await chat_engine.get_chat_history(session_id, limit)
        
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


@router.get("/sessions", response_model=ChatSessionResponse)
async def get_user_sessions(
    current_user: User = Depends(get_current_user)
) -> ChatSessionResponse:
    """
    Get all active chat sessions for the current user.
    """
    try:
        sessions = await chat_engine.get_active_sessions(str(current_user.id))
        
        return ChatSessionResponse(
            success=True,
            sessions=sessions
        )
        
    except Exception as e:
        logger.error("Failed to get user sessions", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat sessions"
        )


@router.post("/session/new")
async def create_new_session(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Create a new chat session with comprehensive error handling.
    """
    try:
        # Ensure chat engine is available
        if not hasattr(chat_engine, 'start_chat_session'):
            logger.error("Chat engine not properly initialized")
            return {
                "success": False,
                "session_id": None,
                "message": "Chat engine not available",
                "error": "Service initialization issue"
            }
        
        session_id = await chat_engine.start_chat_session(str(current_user.id))
        
        if not session_id:
            logger.error("Chat engine returned empty session ID")
            return {
                "success": False,
                "session_id": None,
                "message": "Failed to generate session ID",
                "error": "Session creation failed"
            }
        
        logger.info("Chat session created successfully", session_id=session_id, user_id=current_user.id)
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "New chat session created successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to create chat session", error=str(e), user_id=current_user.id, exc_info=True)
        
        # ALWAYS return valid JSON, never raise HTTPException for frontend stability
        return {
            "success": False,
            "session_id": None,
            "message": "Chat session creation failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.websocket("/ws/{session_id}")
async def chat_websocket(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for real-time chat communication.
    
    Enables real-time bidirectional communication for:
    - Instant message delivery
    - Real-time portfolio updates
    - Live trading notifications
    - Market alerts and opportunities
    """
    try:
        # Implement WebSocket bearer subprotocol authentication 
        # Use unique per-connection ID to prevent message bleed between unauthenticated clients
        user_id = f"guest:{uuid.uuid4()}"  # Unique fallback for each connection
        selected_subprotocol = None  # Initialize to None, only set if safe subprotocol offered
        token = None
        
        # Read subprotocols from Sec-WebSocket-Protocol header
        subprotocols = getattr(websocket, 'scope', {}).get('subprotocols', [])
        
        # Scan client-offered subprotocols for bearer token format
        safe_subprotocols = {"json", "jwt"}  # Safe subprotocols we can echo back
        
        if subprotocols:
            # Look for bearer authentication pattern: ["bearer", <token>, "json"]
            bearer_index = None
            for i, subprotocol in enumerate(subprotocols):
                # Check if this is a safe subprotocol we can echo back
                if subprotocol.lower() in safe_subprotocols:
                    selected_subprotocol = subprotocol.lower()
                
                # Check for bearer indicator
                if subprotocol.lower() == "bearer":
                    bearer_index = i
                    break
            
            # If bearer found, look for JWT token in next subprotocol entry
            if bearer_index is not None and bearer_index + 1 < len(subprotocols):
                token = subprotocols[bearer_index + 1]
            
            # Try to authenticate with extracted bearer token
            if token:
                try:
                    from app.core.security import verify_access_token
                    from jose import JWTError  # Import specific JWT exception
                    payload = verify_access_token(token)
                    if payload and payload.get("sub"):
                        user_id = payload["sub"]
                        logger.info("Chat WebSocket user authenticated via bearer subprotocol", user_id=user_id)
                except JWTError as e:
                    # Handle JWT-specific errors only, let other exceptions propagate
                    logger.debug("Chat WebSocket JWT authentication failed, using guest ID", 
                               guest_id=user_id, 
                               error=str(e))
                    # Don't log token details
        
        # Accept WebSocket connection - only pass subprotocol if safe one was offered by client
        if selected_subprotocol:
            await websocket.accept(subprotocol=selected_subprotocol)
        else:
            await websocket.accept()
        
        # Connect to WebSocket manager
        await manager.connect(websocket, user_id)
        
        logger.info("Chat WebSocket connected", session_id=session_id, user_id=user_id)
        
        # Send connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Connected to CryptoUniverse AI Chat"
        }))
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "chat_message":
                # Process chat message
                user_message = message_data.get("message", "")
                
                if user_message.strip():
                    # Process through chat engine
                    response = await chat_engine.process_message(
                        session_id=session_id,
                        user_message=user_message,
                        user_id=user_id
                    )
                    
                    # Send response back through WebSocket
                    await websocket.send_text(json.dumps({
                        "type": "chat_response",
                        "session_id": session_id,
                        "message_id": response.get("message_id"),
                        "content": response.get("content"),
                        "intent": response.get("intent"),
                        "confidence": response.get("confidence"),
                        "metadata": response.get("metadata"),
                        "timestamp": datetime.utcnow().isoformat()
                    }))
            
            elif message_data.get("type") == "ping":
                # Handle ping for connection keep-alive
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                }))
            
            # Add small delay to prevent overwhelming
            await asyncio.sleep(0.1)
            
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)
        logger.info("Chat WebSocket disconnected", session_id=session_id, user_id=user_id)
    except asyncio.CancelledError:
        await manager.disconnect(websocket, user_id)
        raise  # Re-raise CancelledError so cancellation isn't swallowed
    except Exception as e:
        logger.exception("Chat WebSocket error", session_id=session_id, user_id=user_id)
        await manager.disconnect(websocket, user_id)


@router.post("/command/execute")
async def execute_chat_command(
    command: str,
    session_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Execute a specific chat command (for confirmed actions).
    
    Used when the user confirms an action from a previous chat interaction,
    such as executing a trade or performing a rebalancing operation.
    """
    try:
        # Get session
        sessions = await chat_engine.get_active_sessions(str(current_user.id))
        if session_id not in sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        # Process command execution
        result = await chat_engine.execute_confirmed_action(
            session_id=session_id,
            command=command,
            user_id=str(current_user.id)
        )
        
        return {
            "success": True,
            "result": result,
            "message": "Command executed successfully"
        }
        
    except Exception as e:
        logger.error("Command execution failed", error=str(e), command=command)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute command"
        )


@router.get("/status")
async def get_chat_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the current status of the AI chat engine and related services.
    """
    try:
        # Get service status
        ai_status = await chat_engine.ai_consensus.get_service_status()
        master_status = await chat_engine.master_controller.get_system_status(str(current_user.id))
        
        return {
            "success": True,
            "chat_engine_status": "operational",
            "ai_consensus_status": ai_status.get("status", "unknown"),
            "master_controller_status": master_status.get("status", "unknown"),
            "active_sessions": len(await chat_engine.get_active_sessions(str(current_user.id))),
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get chat status", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "chat_engine_status": "error"
        }


# Additional endpoints for specific chat functionalities
@router.post("/portfolio/quick-analysis")
async def quick_portfolio_analysis(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get a quick AI-powered portfolio analysis without starting a full chat session.
    """
    try:
        # Create temporary session for analysis
        session_id = await chat_engine.start_chat_session(str(current_user.id))
        
        # Process portfolio analysis request
        response = await chat_engine.process_message(
            session_id=session_id,
            user_message="Give me a comprehensive analysis of my current portfolio performance and recommendations",
            user_id=str(current_user.id)
        )
        
        return {
            "success": True,
            "analysis": response.get("content"),
            "confidence": response.get("confidence"),
            "metadata": response.get("metadata")
        }
        
    except Exception as e:
        logger.error("Quick portfolio analysis failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform portfolio analysis"
        )


@router.post("/market/opportunities")
async def discover_opportunities(
    risk_tolerance: str = "balanced",
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Discover market opportunities through AI analysis.
    """
    try:
        # Create temporary session for analysis
        session_id = await chat_engine.start_chat_session(str(current_user.id))
        
        # Process opportunity discovery request
        response = await chat_engine.process_message(
            session_id=session_id,
            user_message=f"Find me the best investment opportunities with {risk_tolerance} risk tolerance",
            user_id=str(current_user.id)
        )
        
        return {
            "success": True,
            "opportunities": response.get("content"),
            "confidence": response.get("confidence"),
            "metadata": response.get("metadata")
        }
        
    except Exception as e:
        logger.error("Opportunity discovery failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to discover opportunities"
        )