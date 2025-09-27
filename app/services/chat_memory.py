"""
Chat Memory Service - Persistent conversation memory management

This service manages the storage and retrieval of chat conversations,
enabling persistent memory across server restarts and advanced conversation
features like summarization and context management.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import uuid
from sqlalchemy import desc, asc, and_, or_, select, text, func
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
import structlog

from app.core.database import get_database
from app.models.chat import ChatSession, ChatMessage, ChatSessionSummary
from app.models.user import User


logger = structlog.get_logger(__name__)


class ChatMemoryService:
    """
    Persistent chat memory management service.
    
    Handles storage, retrieval, and optimization of chat conversations
    with features like automatic summarization and context preservation.
    """
    
    def __init__(self):
        self.max_messages_per_session = 1000  # Before triggering summarization
        self.context_window_size = 50  # Messages to keep in active context
        self.summarization_threshold = 200  # Messages to include in summary
        self.session_timeout_hours = 24  # Hours before session becomes inactive
    
    async def create_session(
        self,
        user_id: str,
        session_type: str = "general",
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> str:
        """
        Create a new chat session.
        
        Args:
            user_id: User identifier
            session_type: Type of session (general, trading, analysis)
            context: Initial session context
            session_id: Optional pre-generated session identifier
            
        Returns:
            Session ID string
        """
        try:
            provided_session_id: Optional[uuid.UUID] = None
            if session_id:
                if isinstance(session_id, uuid.UUID):
                    provided_session_id = session_id
                else:
                    try:
                        provided_session_id = uuid.UUID(str(session_id))
                    except ValueError as exc:
                        raise ValueError("session_id must be a valid UUID") from exc

            async for db in get_database():
                session = ChatSession(
                    session_id=provided_session_id,
                    user_id=user_id,
                    session_type=session_type,
                    context=context or {},
                    active_strategies=[],
                    is_active=True
                )
                
                db.add(session)
                await db.commit()
                await db.refresh(session)
                
                logger.info(
                    "Chat session created",
                    session_id=str(session.session_id),
                    user_id=user_id,
                    session_type=session_type
                )
                
                return str(session.session_id)
                
        except SQLAlchemyError as e:
            logger.error("Failed to create chat session", error=str(e), user_id=user_id)
            raise Exception(f"Failed to create chat session: {str(e)}")
    
    async def save_message(
        self,
        session_id: str,
        user_id: str,
        content: str,
        message_type: str,
        intent: Optional[str] = None,
        confidence: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        model_used: Optional[str] = None,
        processing_time_ms: Optional[float] = None,
        tokens_used: Optional[float] = None
    ) -> str:
        """
        Save a chat message to persistent storage.
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            content: Message content
            message_type: Type of message (user, assistant, system, etc.)
            intent: Classified intent
            confidence: AI confidence score
            metadata: Additional message metadata
            model_used: AI model that generated the response
            processing_time_ms: Processing time in milliseconds
            tokens_used: Number of tokens consumed
            
        Returns:
            Message ID string
        """
        try:
            async for db in get_database():
                message = ChatMessage(
                    session_id=session_id,
                    user_id=user_id,
                    content=content,
                    message_type=message_type,
                    intent=intent,
                    confidence=confidence,
                    message_metadata=metadata or {},
                    model_used=model_used,
                    processing_time_ms=processing_time_ms,
                    tokens_used=tokens_used,
                    processed=True
                )
                
                db.add(message)
                
                # Update session last activity
                await db.execute(
                    text("UPDATE chat_sessions SET last_activity = :now WHERE session_id = :session_id"),
                    {"now": datetime.utcnow(), "session_id": session_id}
                )
                
                await db.commit()
                await db.refresh(message)
                
                # Check if session needs summarization
                await self._check_and_summarize_session(db, session_id)
                
                return str(message.message_id)
                
        except SQLAlchemyError as e:
            logger.error("Failed to save chat message", error=str(e), session_id=session_id)
            raise Exception(f"Failed to save chat message: {str(e)}")
    
    async def get_session_messages(
        self,
        session_id: str,
        limit: int = 50,
        include_context: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get messages for a chat session.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of messages to return
            include_context: Whether to include session context
            
        Returns:
            List of message dictionaries
        """
        try:
            async for db in get_database():
                # Use async SQLAlchemy syntax
                stmt = select(ChatMessage).filter(
                    ChatMessage.session_id == session_id
                ).order_by(desc(ChatMessage.timestamp))
                
                if limit:
                    stmt = stmt.limit(limit)
                
                result = await db.execute(stmt)
                messages = result.scalars().all()
                
                # Convert to dict format
                result_messages = [msg.to_dict() for msg in reversed(messages)]
                
                # Add session context if requested
                if include_context:
                    session_stmt = select(ChatSession).filter(
                        ChatSession.session_id == session_id
                    )
                    session_result = await db.execute(session_stmt)
                    session = session_result.scalar_one_or_none()
                    
                    if session:
                        result_messages.insert(0, {
                            "type": "session_context",
                            "context": session.context,
                            "active_strategies": session.active_strategies,
                            "portfolio_state": session.portfolio_state,
                            "session_type": session.session_type
                        })
                
                return result_messages
                
        except SQLAlchemyError as e:
            logger.error("Failed to get session messages", error=str(e), session_id=session_id)
            return []
    
    async def get_user_sessions(
        self,
        user_id: str,
        limit: int = 10,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get chat sessions for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of sessions to return
            include_inactive: Whether to include inactive sessions
            
        Returns:
            List of session dictionaries
        """
        try:
            async for db in get_database():
                # Use async SQLAlchemy syntax
                stmt = select(ChatSession).filter(
                    ChatSession.user_id == user_id
                )
                
                if not include_inactive:
                    stmt = stmt.filter(ChatSession.is_active == True)
                
                stmt = stmt.order_by(desc(ChatSession.last_activity))
                
                if limit:
                    stmt = stmt.limit(limit)
                
                result = await db.execute(stmt)
                sessions = result.scalars().all()
                
                # Convert to dict manually to avoid lazy loading issues
                session_list = []
                for session in sessions:
                    # Get message count separately to avoid lazy loading
                    message_count_stmt = text(
                        "SELECT COUNT(*) FROM chat_messages WHERE session_id = :session_id"
                    )
                    count_result = await db.execute(
                        message_count_stmt, 
                        {"session_id": str(session.session_id)}
                    )
                    message_count = count_result.scalar() or 0
                    
                    session_dict = {
                        "session_id": str(session.session_id),
                        "user_id": str(session.user_id),
                        "created_at": session.created_at.isoformat() if session.created_at else None,
                        "last_activity": session.last_activity.isoformat() if session.last_activity else None,
                        "context": session.context or {},
                        "portfolio_state": session.portfolio_state,
                        "active_strategies": session.active_strategies or [],
                        "is_active": session.is_active,
                        "session_type": session.session_type,
                        "message_count": message_count
                    }
                    session_list.append(session_dict)
                
                return session_list
                
        except SQLAlchemyError as e:
            logger.error("Failed to get user sessions", error=str(e), user_id=user_id)
            return []
    
    async def update_session_context(
        self,
        session_id: str,
        context_updates: Dict[str, Any]
    ) -> bool:
        """
        Update session context with new information.
        
        Args:
            session_id: Session identifier
            context_updates: Context updates to apply
            
        Returns:
            Success boolean
        """
        try:
            async for db in get_database():
                # Use async SQLAlchemy syntax
                stmt = select(ChatSession).filter(
                    ChatSession.session_id == session_id
                )
                result = await db.execute(stmt)
                session = result.scalar_one_or_none()
                
                if not session:
                    return False
                
                # Merge context updates
                current_context = session.context or {}
                current_context.update(context_updates)
                session.context = current_context
                session.last_activity = datetime.utcnow()
                
                await db.commit()
                
                logger.info(
                    "Session context updated",
                    session_id=session_id,
                    updates=list(context_updates.keys())
                )
                
                return True
                
        except SQLAlchemyError as e:
            logger.error("Failed to update session context", error=str(e), session_id=session_id)
            return False
    
    async def get_conversation_context(
        self,
        session_id: str,
        context_window: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get conversation context for AI processing.
        
        Combines session context, recent messages, and summaries
        to provide comprehensive context for AI interactions.
        
        Args:
            session_id: Session identifier
            context_window: Number of recent messages to include
            
        Returns:
            Conversation context dictionary
        """
        try:
            async for db in get_database():
                # Get session information
                stmt = select(ChatSession).filter(
                    ChatSession.session_id == session_id
                )
                result = await db.execute(stmt)
                session = result.scalar_one_or_none()
                
                if not session:
                    return {}
                
                context_window = context_window or self.context_window_size
                
                # Get recent messages
                msg_stmt = select(ChatMessage).filter(
                    ChatMessage.session_id == session_id
                ).order_by(desc(ChatMessage.timestamp)).limit(context_window)
                msg_result = await db.execute(msg_stmt)
                recent_messages = msg_result.scalars().all()
                
                # Get session summaries
                sum_stmt = select(ChatSessionSummary).filter(
                    ChatSessionSummary.session_id == session_id
                ).order_by(desc(ChatSessionSummary.created_at)).limit(3)
                sum_result = await db.execute(sum_stmt)
                summaries = sum_result.scalars().all()
                
                return {
                    "session_id": str(session.session_id),
                    "session_context": session.context or {},
                    "active_strategies": session.active_strategies or [],
                    "portfolio_state": session.portfolio_state,
                    "session_type": session.session_type,
                    "recent_messages": [
                        {
                            "content": msg.content,
                            "type": msg.message_type,
                            "intent": msg.intent,
                            "timestamp": msg.timestamp.isoformat(),
                            "confidence": msg.confidence
                        }
                        for msg in reversed(recent_messages)
                    ],
                    "conversation_summaries": [
                        {
                            "summary": summary.summary_text,
                            "messages_count": summary.messages_summarized,
                            "key_decisions": summary.key_decisions or [],
                            "trade_actions": summary.trade_actions or []
                        }
                        for summary in summaries
                    ],
                    "total_messages": len(recent_messages)
                }
                
        except SQLAlchemyError as e:
            logger.error("Failed to get conversation context", error=str(e), session_id=session_id)
            return {}
    
    async def _check_and_summarize_session(self, db: Session, session_id: str) -> bool:
        """
        Check if session needs summarization and create summary if needed.
        
        Args:
            db: Database session
            session_id: Session to check
            
        Returns:
            Whether summarization was performed
        """
        try:
            # Count messages in session
            count_stmt = select(func.count(ChatMessage.message_id)).filter(
                ChatMessage.session_id == session_id
            )
            count_result = await db.execute(count_stmt)
            message_count = count_result.scalar()
            
            if message_count < self.max_messages_per_session:
                return False
            
            # Get last summary timestamp
            summary_stmt = select(ChatSessionSummary).filter(
                ChatSessionSummary.session_id == session_id
            ).order_by(desc(ChatSessionSummary.created_at))
            summary_result = await db.execute(summary_stmt)
            last_summary = summary_result.scalar_one_or_none()
            
            # Determine messages to summarize
            if last_summary:
                msgs_stmt = select(ChatMessage).filter(
                    and_(
                        ChatMessage.session_id == session_id,
                        ChatMessage.timestamp > last_summary.end_timestamp
                    )
                ).order_by(asc(ChatMessage.timestamp)).limit(self.summarization_threshold)
            else:
                msgs_stmt = select(ChatMessage).filter(
                    ChatMessage.session_id == session_id
                ).order_by(asc(ChatMessage.timestamp)).limit(self.summarization_threshold)
            
            msgs_result = await db.execute(msgs_stmt)
            messages_to_summarize = msgs_result.scalars().all()
            
            if len(messages_to_summarize) < 50:  # Not enough messages to summarize
                return False
            
            # Create summary
            await self._create_session_summary(db, session_id, messages_to_summarize)
            
            return True
            
        except Exception as e:
            logger.error("Failed to check/summarize session", error=str(e), session_id=session_id)
            return False
    
    async def _create_session_summary(
        self,
        db: Session,
        session_id: str,
        messages: List[ChatMessage]
    ) -> bool:
        """
        Create a summary of conversation messages.
        
        Args:
            db: Database session
            session_id: Session identifier
            messages: Messages to summarize
            
        Returns:
            Success boolean
        """
        try:
            if not messages:
                return False
            
            # Extract key information
            trade_actions = []
            key_decisions = []
            portfolio_changes = []
            
            conversation_text = []
            
            for msg in messages:
                conversation_text.append(f"{msg.message_type}: {msg.content[:200]}...")
                
                if msg.intent == "trade_execution" and msg.metadata:
                    trade_actions.append(msg.metadata)
                elif msg.intent in ["portfolio_analysis", "rebalancing"] and msg.metadata:
                    portfolio_changes.append(msg.metadata)
                
                if msg.confidence and msg.confidence > 0.8:
                    key_decisions.append({
                        "intent": msg.intent,
                        "content": msg.content[:100] + "...",
                        "timestamp": msg.timestamp.isoformat(),
                        "confidence": msg.confidence
                    })
            
            # Create summary text (simplified - in production, use AI summarization)
            summary_text = f"""
Conversation Summary ({len(messages)} messages):

Key Activities:
- {len(trade_actions)} trading actions discussed
- {len(portfolio_changes)} portfolio changes
- {len(key_decisions)} high-confidence decisions

Recent Topics: {', '.join([msg.intent for msg in messages[-5:] if msg.intent])}

This summary covers conversation from {messages[0].timestamp} to {messages[-1].timestamp}.
            """.strip()
            
            # Save summary
            summary = ChatSessionSummary(
                session_id=session_id,
                user_id=messages[0].user_id,
                summary_text=summary_text,
                messages_summarized=len(messages),
                summary_type="conversation",
                start_timestamp=messages[0].timestamp,
                end_timestamp=messages[-1].timestamp,
                key_decisions=key_decisions,
                trade_actions=trade_actions,
                portfolio_changes=portfolio_changes
            )
            
            db.add(summary)
            await db.commit()
            
            logger.info(
                "Session summary created",
                session_id=session_id,
                messages_summarized=len(messages),
                summary_id=str(summary.summary_id)
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to create session summary", error=str(e), session_id=session_id)
            return False
    
    async def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """
        Clean up old inactive chat sessions.
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            Number of sessions cleaned up
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            async for db in get_database():
                # Mark old sessions as inactive
                result = await db.execute(
                    text("""
                    UPDATE chat_sessions 
                    SET is_active = false 
                    WHERE last_activity < :cutoff_date 
                    AND is_active = true
                    """),
                    {"cutoff_date": cutoff_date}
                )
                
                cleaned_count = result.rowcount
                await db.commit()
                
                logger.info(
                    "Old chat sessions cleaned up",
                    sessions_cleaned=cleaned_count,
                    cutoff_date=cutoff_date
                )
                
                return cleaned_count
                
        except Exception as e:
            logger.error("Failed to cleanup old sessions", error=str(e))
            return 0


# Global instance
chat_memory = ChatMemoryService()