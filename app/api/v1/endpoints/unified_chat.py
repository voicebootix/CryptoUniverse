"""
Unified AI Chat Endpoints - Enterprise Grade

Provides unified AI chat experience across all interfaces (Web, Telegram, Mobile).
All chat interactions go through the unified AI manager for consistent experience.

Features:
- Cross-platform conversation continuity
- Unified AI decision-making
- Context-aware responses
- Session synchronization across interfaces
- Real-time WebSocket support
"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user, get_websocket_user
from app.core.database import get_database
from app.core.config import get_settings
from app.models.user import User
from app.services.unified_ai_manager import unified_ai_manager, InterfaceType, OperationMode
from app.services.websocket import manager
from app.services.rate_limit import rate_limiter
import structlog

settings = get_settings()
logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Unified AI Chat"])


class ChatInterfaceType(str, Enum):
    """Chat interface types for frontend."""
    TRADING = "trading"          # ConversationalTradingInterface
    QUICK = "quick"              # ChatWidget
    ANALYSIS = "analysis"        # Portfolio analysis mode
    SUPPORT = "support"          # Help and support mode


class UnifiedChatRequest(BaseModel):
    """Request model for unified chat messages."""
    message: str = Field(..., min_length=1, max_length=4000, description="The user's message content")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    interface_type: ChatInterfaceType = Field(ChatInterfaceType.TRADING, description="Interface type for context-aware responses")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context information")
    
    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()


class UnifiedChatResponse(BaseModel):
    """Response model for unified chat messages."""
    success: bool
    session_id: str
    message_id: str
    content: str
    interface_type: ChatInterfaceType
    intent: str
    confidence: float
    requires_approval: bool = False
    decision_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime
    ai_analysis: Optional[str] = None


class ChatSessionRequest(BaseModel):
    """Request model for creating chat sessions."""
    interface_type: ChatInterfaceType = Field(ChatInterfaceType.TRADING, description="Interface type for session")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Initial session context")


class ChatSessionResponse(BaseModel):
    """Response model for chat session creation."""
    success: bool
    session_id: str
    interface_type: ChatInterfaceType
    welcome_message: str
    timestamp: datetime


class ChatHistoryResponse(BaseModel):
    """Response model for chat history."""
    success: bool
    session_id: str
    messages: List[Dict[str, Any]]
    total_messages: int
    interface_type: ChatInterfaceType


class DecisionApprovalRequest(BaseModel):
    """Request model for approving AI decisions."""
    decision_id: str = Field(..., description="Decision ID to approve")
    approved: bool = Field(..., description="Whether the decision is approved")
    modifications: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Any modifications to the decision")


class DecisionApprovalResponse(BaseModel):
    """Response model for decision approval."""
    success: bool
    decision_id: str
    execution_result: Optional[Dict[str, Any]] = None
    message: str


# Global session storage for cross-interface continuity
session_interface_mapping: Dict[str, ChatInterfaceType] = {}
session_context_cache: Dict[str, Dict[str, Any]] = {}


@router.post("/session/new", response_model=ChatSessionResponse)
async def create_unified_chat_session(
    request: ChatSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database)
) -> ChatSessionResponse:
    """
    Create a new unified chat session.
    
    Sessions are shared across all interfaces for conversation continuity.
    """
    try:
        await rate_limiter.check_rate_limit(
            key="unified_chat:session_create",
            limit=10,
            window=60,
            user_id=str(current_user.id)
        )
        
        # Generate session ID
        session_id = f"unified_{uuid.uuid4().hex}"
        
        # Store interface mapping for cross-platform continuity
        session_interface_mapping[session_id] = request.interface_type
        session_context_cache[session_id] = {
            "user_id": str(current_user.id),
            "created_at": datetime.utcnow().isoformat(),
            "interface_type": request.interface_type.value,
            "initial_context": request.context,
            "message_count": 0
        }
        
        # Generate welcome message based on interface type
        welcome_messages = {
            ChatInterfaceType.TRADING: f"""🧠 **Welcome to CryptoUniverse AI Money Manager!**

I'm your unified AI assistant, powered by the same brain across all platforms. Whether you're here, on Telegram, or using our mobile app, I'll remember our entire conversation.

**What I can help you with:**
• 📊 **Market Analysis** - Real-time insights and opportunities
• 💰 **Portfolio Management** - Optimization and rebalancing
• 🤖 **Autonomous Trading** - AI-powered automated strategies  
• 🛡️ **Risk Assessment** - Comprehensive risk analysis
• 📈 **Trade Execution** - Smart order placement

**Quick Start:**
• "I have $5000 to invest"
• "Show me the best opportunities"
• "Start autonomous trading"
• "Analyze my portfolio risk"

*Your conversation continues seamlessly across all devices and platforms.*""",

            ChatInterfaceType.QUICK: f"""👋 **Hi {current_user.email.split('@')[0]}!**

I'm your AI money manager. I remember our conversations across all platforms - web, Telegram, and mobile.

**Quick Help:**
• Portfolio status
• Market opportunities  
• Trading questions
• Risk analysis

What can I help you with?""",

            ChatInterfaceType.ANALYSIS: f"""📊 **Portfolio Analysis Mode**

Ready to dive deep into your portfolio performance, risk metrics, and optimization opportunities.

**Analysis Options:**
• Performance review
• Risk assessment
• Rebalancing recommendations
• Correlation analysis
• Stress testing

What would you like to analyze?""",

            ChatInterfaceType.SUPPORT: f"""🛟 **Support & Help**

I'm here to help with platform features, account questions, and technical support.

**I can help with:**
• Platform navigation
• Feature explanations
• Account settings
• Trading tutorials
• Technical issues

What do you need help with?"""
        }
        
        logger.info("Unified chat session created", 
                   session_id=session_id, 
                   user_id=str(current_user.id),
                   interface_type=request.interface_type.value)
        
        return ChatSessionResponse(
            success=True,
            session_id=session_id,
            interface_type=request.interface_type,
            welcome_message=welcome_messages[request.interface_type],
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error("Failed to create unified chat session", 
                    error=str(e), 
                    user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chat session"
        )


@router.post("/message", response_model=UnifiedChatResponse)
async def send_unified_message(
    request: UnifiedChatRequest,
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_database)
) -> UnifiedChatResponse:
    """
    Send a message through the unified AI manager.
    
    All messages are processed by the same AI brain for consistent experience
    across web, Telegram, and mobile interfaces.
    """
    try:
        await rate_limiter.check_rate_limit(
            key="unified_chat:message",
            limit=30,
            window=60,
            user_id=str(current_user.id)
        )
        
        # Ensure session exists
        session_id = request.session_id
        if not session_id or session_id not in session_context_cache:
            # Create new session if none provided
            session_response = await create_unified_chat_session(
                ChatSessionRequest(interface_type=request.interface_type),
                current_user,
                db
            )
            session_id = session_response.session_id
        
        # Update session context
        session_context = session_context_cache.get(session_id, {})
        session_context["message_count"] = session_context.get("message_count", 0) + 1
        session_context["last_activity"] = datetime.utcnow().isoformat()
        session_context["current_interface"] = request.interface_type.value
        
        # Map interface type to unified AI manager interface
        interface_mapping = {
            ChatInterfaceType.TRADING: InterfaceType.WEB_CHAT,
            ChatInterfaceType.QUICK: InterfaceType.WEB_CHAT,
            ChatInterfaceType.ANALYSIS: InterfaceType.WEB_UI,
            ChatInterfaceType.SUPPORT: InterfaceType.WEB_CHAT
        }
        
        unified_interface = interface_mapping[request.interface_type]
        
        # Build comprehensive context for unified AI manager
        unified_context = {
            "session_id": session_id,
            "interface_type": request.interface_type.value,
            "unified_interface": unified_interface.value,
            "session_context": session_context,
            "user_context": request.context,
            "platform": "web",
            "message_count": session_context.get("message_count", 1),
            "conversation_continuity": True,
            "cross_platform_session": True
        }
        
        # Process through unified AI manager
        logger.info("Processing unified chat message", 
                   session_id=session_id,
                   user_id=str(current_user.id),
                   interface_type=request.interface_type.value,
                   message_length=len(request.message))
        
        ai_result = await unified_ai_manager.process_user_request(
            user_id=str(current_user.id),
            request=request.message,
            interface=unified_interface,
            context=unified_context
        )
        
        if not ai_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ai_result.get("error", "AI processing failed")
            )
        
        # Generate message ID
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        
        # Update session cache
        session_context_cache[session_id] = session_context
        
        # Prepare response
        response = UnifiedChatResponse(
            success=True,
            session_id=session_id,
            message_id=message_id,
            content=ai_result.get("content", ""),
            interface_type=request.interface_type,
            intent=ai_result.get("intent", "general"),
            confidence=ai_result.get("confidence", 0.0),
            requires_approval=ai_result.get("requires_approval", False),
            decision_id=ai_result.get("decision_id"),
            metadata=ai_result.get("metadata", {}),
            timestamp=datetime.utcnow(),
            ai_analysis=ai_result.get("ai_analysis")
        )
        
        # Background task: Notify other interfaces about conversation update
        background_tasks.add_task(
            notify_cross_platform_update,
            str(current_user.id),
            session_id,
            {
                "type": "message_processed",
                "interface": request.interface_type.value,
                "message_id": message_id,
                "requires_approval": response.requires_approval
            }
        )
        
        logger.info("Unified chat message processed successfully",
                   session_id=session_id,
                   user_id=str(current_user.id),
                   confidence=response.confidence,
                   requires_approval=response.requires_approval)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unified chat message processing failed", 
                    error=str(e), 
                    user_id=str(current_user.id),
                    session_id=request.session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message"
        )


@router.post("/decision/approve", response_model=DecisionApprovalResponse)
async def approve_ai_decision(
    request: DecisionApprovalRequest,
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks
) -> DecisionApprovalResponse:
    """
    Approve or reject an AI decision that requires user approval.
    
    This enables the unified AI to execute trades and other actions
    after user confirmation.
    """
    try:
        await rate_limiter.check_rate_limit(
            key="unified_chat:decision_approval",
            limit=20,
            window=60,
            user_id=str(current_user.id)
        )
        
        if request.approved:
            # Execute the approved decision
            result = await unified_ai_manager.execute_approved_decision(
                decision_id=request.decision_id,
                user_id=str(current_user.id)
            )
            
            if result.get("success"):
                # Background task: Notify all interfaces about execution
                background_tasks.add_task(
                    notify_cross_platform_update,
                    str(current_user.id),
                    None,  # All sessions
                    {
                        "type": "decision_executed",
                        "decision_id": request.decision_id,
                        "execution_result": result.get("execution_result")
                    }
                )
                
                return DecisionApprovalResponse(
                    success=True,
                    decision_id=request.decision_id,
                    execution_result=result.get("execution_result"),
                    message="Decision executed successfully"
                )
            else:
                return DecisionApprovalResponse(
                    success=False,
                    decision_id=request.decision_id,
                    message=result.get("error", "Execution failed")
                )
        else:
            # Decision rejected
            logger.info("AI decision rejected by user",
                       decision_id=request.decision_id,
                       user_id=str(current_user.id))
            
            return DecisionApprovalResponse(
                success=True,
                decision_id=request.decision_id,
                message="Decision rejected"
            )
            
    except Exception as e:
        logger.error("Decision approval failed", 
                    error=str(e),
                    decision_id=request.decision_id,
                    user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process decision approval"
        )


@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
async def get_unified_chat_history(
    session_id: str,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
) -> ChatHistoryResponse:
    """
    Get chat history for a unified session.
    
    History is shared across all interfaces for conversation continuity.
    """
    try:
        # Get session context
        session_context = session_context_cache.get(session_id, {})
        
        if not session_context or session_context.get("user_id") != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or access denied"
            )
        
        # Get messages from unified AI manager
        # For now, return session context as history
        # In production, this would query a proper message store
        messages = [
            {
                "id": "session_info",
                "type": "system",
                "content": f"Session created on {session_context.get('created_at')}",
                "timestamp": session_context.get('created_at'),
                "interface_type": session_context.get('interface_type')
            }
        ]
        
        interface_type = ChatInterfaceType(session_context.get('interface_type', 'trading'))
        
        return ChatHistoryResponse(
            success=True,
            session_id=session_id,
            messages=messages,
            total_messages=len(messages),
            interface_type=interface_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get unified chat history", 
                    error=str(e),
                    session_id=session_id,
                    user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history"
        )


@router.websocket("/ws/{session_id}")
async def unified_chat_websocket(
    websocket: WebSocket,
    session_id: str,
    current_user: User = Depends(get_websocket_user)
):
    """
    WebSocket endpoint for real-time unified chat.
    
    Enables real-time communication and cross-platform notifications.
    """
    await manager.connect(websocket, str(current_user.id))
    
    try:
        # Verify session access
        session_context = session_context_cache.get(session_id, {})
        if not session_context or session_context.get("user_id") != str(current_user.id):
            await websocket.close(code=4003, reason="Session access denied")
            return
        
        logger.info("Unified chat WebSocket connected",
                   session_id=session_id,
                   user_id=str(current_user.id))
        
        while True:
            # Receive message from WebSocket
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "chat_message":
                # Process chat message
                request = UnifiedChatRequest(
                    message=message_data.get("message", ""),
                    session_id=session_id,
                    interface_type=ChatInterfaceType(message_data.get("interface_type", "trading")),
                    context=message_data.get("context", {})
                )
                
                # Process through unified system
                response = await send_unified_message(request, current_user, BackgroundTasks())
                
                # Send response back through WebSocket
                await websocket.send_text(json.dumps({
                    "type": "chat_response",
                    "data": response.dict()
                }))
            
            elif message_data.get("type") == "ping":
                # Heartbeat
                await websocket.send_text(json.dumps({"type": "pong"}))
                
    except WebSocketDisconnect:
        logger.info("Unified chat WebSocket disconnected",
                   session_id=session_id,
                   user_id=str(current_user.id))
    except Exception as e:
        logger.error("Unified chat WebSocket error",
                    error=str(e),
                    session_id=session_id,
                    user_id=str(current_user.id))
    finally:
        manager.disconnect(websocket, str(current_user.id))


async def notify_cross_platform_update(
    user_id: str,
    session_id: Optional[str],
    update_data: Dict[str, Any]
):
    """
    Notify all connected interfaces about conversation updates.
    
    This enables real-time synchronization across web, Telegram, and mobile.
    """
    try:
        # Send WebSocket notification to web interfaces
        await manager.send_personal_message(
            json.dumps({
                "type": "cross_platform_update",
                "session_id": session_id,
                "data": update_data,
                "timestamp": datetime.utcnow().isoformat()
            }),
            user_id
        )
        
        # TODO: Send notification to Telegram if user has Telegram connected
        # TODO: Send push notification to mobile app if installed
        
        logger.debug("Cross-platform update sent",
                    user_id=user_id,
                    session_id=session_id,
                    update_type=update_data.get("type"))
        
    except Exception as e:
        logger.error("Failed to send cross-platform update",
                    error=str(e),
                    user_id=user_id,
                    session_id=session_id)


# Health check endpoint
@router.get("/health")
async def unified_chat_health():
    """Health check for unified chat system."""
    try:
        # Check unified AI manager status
        health_status = await unified_ai_manager.get_system_status()
        
        return {
            "status": "healthy",
            "unified_ai_manager": health_status.get("status", "unknown"),
            "active_sessions": len(session_context_cache),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }