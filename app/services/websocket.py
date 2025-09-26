from fastapi import WebSocket
from typing import Dict, List, Any
from datetime import datetime
import asyncio
import structlog

from app.core.database import get_database_session

logger = structlog.get_logger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.market_subscribers: Dict[str, List[WebSocket]] = {}
        self.ai_consensus_subscribers: Dict[str, List[WebSocket]] = {}
        self.cost_dashboard_subscribers: List[WebSocket] = []  # Admin only
        self.is_market_streaming = False
        self._market_stream_task = None

    async def connect(self, websocket: WebSocket, user_id: str):
        """ENTERPRISE: Add WebSocket to connection pool (websocket should already be accepted)."""
        try:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            
            if websocket not in self.active_connections[user_id]:
                self.active_connections[user_id].append(websocket)
                
            logger.info(f"WebSocket connected for user {user_id}")
        except Exception as e:
            logger.error(f"Error connecting WebSocket for user {user_id}", error=str(e))

    async def disconnect(self, websocket: WebSocket, user_id: str):
        """Disconnect WebSocket and clean up subscriptions."""
        try:
            # Remove from active connections
            if user_id in self.active_connections and websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
                
            # Clean up empty user entries
            if user_id in self.active_connections and not self.active_connections[user_id]:
                del self.active_connections[user_id]
            
            # Remove from market subscribers
            for symbol, connections in self.market_subscribers.items():
                if websocket in connections:
                    connections.remove(websocket)
            
            # Remove from AI consensus subscribers
            if user_id in self.ai_consensus_subscribers and websocket in self.ai_consensus_subscribers[user_id]:
                self.ai_consensus_subscribers[user_id].remove(websocket)
                if not self.ai_consensus_subscribers[user_id]:
                    del self.ai_consensus_subscribers[user_id]
            
            # Remove from cost dashboard subscribers
            if websocket in self.cost_dashboard_subscribers:
                self.cost_dashboard_subscribers.remove(websocket)
            
            logger.info(f"WebSocket disconnected for user {user_id}")
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket for user {user_id}", error=str(e))

    async def subscribe_to_market_data(self, websocket: WebSocket, symbols: List[str]):
        """Subscribe WebSocket to market data updates for specific symbols."""
        for symbol in symbols:
            if symbol not in self.market_subscribers:
                self.market_subscribers[symbol] = []
            if websocket not in self.market_subscribers[symbol]:
                self.market_subscribers[symbol].append(websocket)
        
        # Start market streaming if not already running (prevent race condition)
        if not self.is_market_streaming:
            self.is_market_streaming = True
            self._market_stream_task = asyncio.create_task(self._start_market_streaming())

    async def unsubscribe_from_market_data(self, websocket: WebSocket, symbols: List[str]):
        """Unsubscribe WebSocket from market data updates for specific symbols."""
        for symbol in symbols:
            if symbol in self.market_subscribers and websocket in self.market_subscribers[symbol]:
                self.market_subscribers[symbol].remove(websocket)
                
                # Clean up empty symbol entries
                if not self.market_subscribers[symbol]:
                    del self.market_subscribers[symbol]
        
        # Stop market streaming if no subscribers remain
        if not self.market_subscribers and self.is_market_streaming and self._market_stream_task:
            try:
                self._market_stream_task.cancel()
                try:
                    await self._market_stream_task
                except asyncio.CancelledError:
                    pass
            except Exception as e:
                logger.error("Error cancelling market stream task", error=str(e))
            finally:
                self.is_market_streaming = False
                self._market_stream_task = None

    async def broadcast(self, message: dict, user_id: str):
        """Broadcast a JSON message to all connections for a user."""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}", error=str(e))

    async def broadcast_to_all(self, message: dict):
        """Broadcast a JSON message to all active connections."""
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}", error=str(e))

    async def subscribe_to_ai_consensus(self, websocket: WebSocket, user_id: str):
        """Subscribe WebSocket to real-time AI consensus updates."""
        try:
            if user_id not in self.ai_consensus_subscribers:
                self.ai_consensus_subscribers[user_id] = []
            
            if websocket not in self.ai_consensus_subscribers[user_id]:
                self.ai_consensus_subscribers[user_id].append(websocket)
                logger.info(f"User {user_id} subscribed to AI consensus updates")
        except Exception as e:
            logger.error(f"Failed to subscribe to AI consensus", user_id=user_id, error=str(e))
    
    async def unsubscribe_from_ai_consensus(self, websocket: WebSocket, user_id: str):
        """Unsubscribe WebSocket from AI consensus updates."""
        try:
            if user_id in self.ai_consensus_subscribers and websocket in self.ai_consensus_subscribers[user_id]:
                self.ai_consensus_subscribers[user_id].remove(websocket)
                
                # Clean up empty user entries
                if not self.ai_consensus_subscribers[user_id]:
                    del self.ai_consensus_subscribers[user_id]
                
                logger.info(f"User {user_id} unsubscribed from AI consensus updates")
        except Exception as e:
            logger.error(f"Failed to unsubscribe from AI consensus", user_id=user_id, error=str(e))
    
    async def _is_admin_user(self, user_id: str) -> bool:
        """Check if a user has admin privileges."""
        try:
            from app.models.user import User, UserRole
            from sqlalchemy import select

            async with get_database_session() as db:
                result = await db.execute(
                    select(User).filter(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    logger.warning(f"User {user_id} not found for admin check")
                    return False
                    
                return user.role == UserRole.ADMIN
                
        except Exception as e:
            logger.error(f"Failed to check admin role for user {user_id}", error=str(e))
            return False
    
    async def subscribe_to_cost_dashboard(self, websocket: WebSocket, user_id: str):
        """Subscribe WebSocket to cost dashboard updates (admin only)."""
        try:
            # Check if user has admin privileges
            if not await self._is_admin_user(user_id):
                logger.warning(f"User {user_id} attempted to access cost dashboard without admin privileges")
                raise PermissionError(f"User {user_id} does not have admin privileges for cost dashboard access")
            
            if websocket not in self.cost_dashboard_subscribers:
                self.cost_dashboard_subscribers.append(websocket)
                logger.info(f"Admin {user_id} subscribed to cost dashboard updates")
        except PermissionError:
            raise
        except Exception as e:
            logger.error(f"Failed to subscribe to cost dashboard", user_id=user_id, error=str(e))
    
    async def broadcast_ai_consensus_update(self, user_id: str, consensus_data: Dict[str, Any]):
        """Broadcast real-time AI consensus updates to subscribed users."""
        
        if user_id not in self.ai_consensus_subscribers:
            return
        
        message = {
            "type": "ai_consensus_update",
            "data": {
                "consensus_score": consensus_data.get("consensus_score", 0),
                "recommendation": consensus_data.get("recommendation", "HOLD"),
                "model_responses": consensus_data.get("model_responses", []),
                "explanation": consensus_data.get("explanation", ""),
                "cost_summary": consensus_data.get("cost_summary", {}),
                "confidence_threshold_met": consensus_data.get("confidence_threshold_met", False),
                "function": consensus_data.get("function", "unknown"),
                "timestamp": consensus_data.get("timestamp", datetime.utcnow().isoformat())
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Iterate over a snapshot to avoid skipping items when removing failed connections
        failed_websockets = []
        for websocket in list(self.ai_consensus_subscribers[user_id]):
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error("AI consensus WebSocket broadcast failed", 
                           user_id=user_id, 
                           error=str(e), 
                           exc_info=True)
                failed_websockets.append(websocket)
        
        # Clean up failed connections after iteration
        for websocket in failed_websockets:
            try:
                if user_id in self.ai_consensus_subscribers and websocket in self.ai_consensus_subscribers[user_id]:
                    self.ai_consensus_subscribers[user_id].remove(websocket)
                    logger.debug("Removed failed websocket from AI consensus subscribers", user_id=user_id)
            except (ValueError, KeyError):
                # Handle cases where the entry was already removed or user_id doesn't exist
                pass
        
        # Clean up empty user entries
        if user_id in self.ai_consensus_subscribers and not self.ai_consensus_subscribers[user_id]:
            del self.ai_consensus_subscribers[user_id]
            logger.debug("Cleaned up empty AI consensus subscriber list", user_id=user_id)
    
    async def broadcast_cost_update(self, cost_data: Dict[str, Any]):
        """Broadcast real-time cost updates to admin dashboard subscribers."""
        
        message = {
            "type": "api_cost_update",
            "data": cost_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        failed_connections = []
        for websocket in self.cost_dashboard_subscribers:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error("Cost dashboard WebSocket broadcast failed", error=str(e))
                failed_connections.append(websocket)
        
        # Remove failed connections
        for websocket in failed_connections:
            try:
                self.cost_dashboard_subscribers.remove(websocket)
            except ValueError:
                pass
    
    async def send_personal_message(self, message: str, user_id: str):
        """Send personal message to specific user (for chat integration)."""
        if user_id in self.active_connections:
            message_data = {
                "type": "personal_message",
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message_data)
                except Exception as e:
                    logger.error(f"Personal message failed for user {user_id}", error=str(e))
    
    async def broadcast_emergency_alert(self, user_id: str, emergency_data: Dict[str, Any]):
        """Broadcast emergency alerts to specific user."""
        
        message = {
            "type": "emergency_alert",
            "data": emergency_data,
            "timestamp": datetime.utcnow().isoformat(),
            "priority": "critical"
        }
        
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Emergency alert failed for user {user_id}", error=str(e))
    
    def get_connection_count(self, user_id: str) -> int:
        """Get number of active connections for user."""
        return len(self.active_connections.get(user_id, []))
    
    def get_ai_consensus_subscriber_count(self, user_id: str) -> int:
        """Get number of AI consensus subscribers for user."""
        return len(self.ai_consensus_subscribers.get(user_id, []))
    
    def get_cost_dashboard_subscriber_count(self) -> int:
        """Get number of cost dashboard subscribers."""
        return len(self.cost_dashboard_subscribers)
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get comprehensive connection statistics."""
        from datetime import datetime
        
        total_connections = sum(len(connections) for connections in self.active_connections.values())
        total_ai_subscribers = sum(len(connections) for connections in self.ai_consensus_subscribers.values())
        
        return {
            "total_connections": total_connections,
            "unique_users": len(self.active_connections),
            "market_subscribers": len(self.market_subscribers),
            "ai_consensus_subscribers": total_ai_subscribers,
            "cost_dashboard_subscribers": len(self.cost_dashboard_subscribers),
            "is_market_streaming": self.is_market_streaming,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _start_market_streaming(self):
        """Start streaming market data to subscribers (placeholder)."""
        # This would contain the actual market data streaming logic
        # For now, it's a placeholder to prevent the syntax error
        pass

manager = ConnectionManager()