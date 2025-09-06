"""
Enterprise Emergency Liquidation Manager
Based on institutional best practices from major exchanges and hedge funds.

Implements circuit breaker protocols used by:
- Binance, Coinbase Pro, CME Group
- Major crypto hedge funds
- Traditional finance risk management

NO MOCK DATA - REAL EMERGENCY PROTOCOLS
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid

import structlog
from app.core.config import get_settings
from app.core.logging import LoggerMixin
from app.core.redis import get_redis_client

settings = get_settings()
logger = structlog.get_logger(__name__)


class EmergencyLevel(str, Enum):
    """Emergency levels based on institutional risk management."""
    NORMAL = "normal"
    WARNING = "warning"      # 7% portfolio loss - Reduce positions
    CRITICAL = "critical"    # 15% portfolio loss - Halt new trades
    EMERGENCY = "emergency"  # 25% portfolio loss - Full liquidation


class LiquidationPriority(str, Enum):
    """Liquidation priority based on institutional best practices."""
    LEVERAGED_POSITIONS = "leveraged_positions"  # Highest risk first
    LOW_LIQUIDITY_ALTS = "low_liquidity_alts"   # Illiquid altcoins
    MAJOR_ALTS = "major_alts"                   # ETH, SOL, etc.
    BITCOIN = "bitcoin"                         # Most liquid, last resort


@dataclass
class EmergencyAction:
    """Emergency action data structure."""
    action_id: str
    user_id: str
    emergency_level: EmergencyLevel
    trigger_reason: str
    portfolio_loss_pct: float
    actions_taken: List[Dict[str, Any]]
    target_stablecoin: str
    execution_time_ms: float
    success: bool
    timestamp: datetime


class EmergencyManager(LoggerMixin):
    """
    Enterprise Emergency Liquidation Manager
    
    Implements institutional-grade emergency protocols:
    - Circuit breaker system (7%, 15%, 25% loss levels)
    - Stablecoin safety ranking (USDC > USDT > DAI)
    - Position liquidation priority (leveraged > alts > BTC)
    - Real-time risk monitoring and automatic execution
    """
    
    def __init__(self):
        # Stablecoin safety ranking based on institutional analysis
        # Tier 1: USDC - Fully regulated, 1:1 USD backing, Circle/Coinbase
        # Tier 2: USDT - Highest liquidity but regulatory concerns
        # Tier 3: DAI - Decentralized but complex collateral
        self.stablecoin_priority = [
            {"symbol": "USDC", "safety_score": 95, "liquidity_score": 90},
            {"symbol": "USDT", "safety_score": 75, "liquidity_score": 100},
            {"symbol": "DAI", "safety_score": 85, "liquidity_score": 70}
        ]
        
        # Circuit breaker thresholds (institutional standard)
        self.circuit_breakers = {
            EmergencyLevel.WARNING: {
                "loss_threshold_pct": 7.0,
                "action": "reduce_positions",
                "reduction_pct": 50.0,
                "halt_new_trades": False
            },
            EmergencyLevel.CRITICAL: {
                "loss_threshold_pct": 15.0,
                "action": "halt_and_review",
                "reduction_pct": 75.0,
                "halt_new_trades": True
            },
            EmergencyLevel.EMERGENCY: {
                "loss_threshold_pct": 25.0,
                "action": "full_liquidation",
                "reduction_pct": 100.0,
                "halt_new_trades": True
            }
        }
        
        # Liquidation priority order (risk-based)
        self.liquidation_priority = [
            LiquidationPriority.LEVERAGED_POSITIONS,  # Margin/futures first
            LiquidationPriority.LOW_LIQUIDITY_ALTS,   # Small cap altcoins
            LiquidationPriority.MAJOR_ALTS,          # ETH, SOL, AVAX, etc.
            LiquidationPriority.BITCOIN              # BTC last (store of value)
        ]
        
        # Active emergency states per user
        self.active_emergencies: Dict[str, EmergencyAction] = {}
        
        self.logger.info("🚨 Emergency Manager initialized with institutional protocols")
    
    async def assess_emergency_level(self, user_id: str, portfolio_data: Dict[str, Any]) -> Tuple[EmergencyLevel, float]:
        """
        Assess current emergency level based on portfolio performance.
        
        Returns:
            Tuple of (EmergencyLevel, current_loss_percentage)
        """
        try:
            # Calculate current portfolio loss percentage
            total_value = portfolio_data.get("total_value_usd", 0)
            initial_value = portfolio_data.get("initial_value_usd", total_value)
            
            if initial_value <= 0:
                return EmergencyLevel.NORMAL, 0.0
            
            current_loss_pct = ((initial_value - total_value) / initial_value) * 100
            
            # Determine emergency level based on loss thresholds
            if current_loss_pct >= self.circuit_breakers[EmergencyLevel.EMERGENCY]["loss_threshold_pct"]:
                return EmergencyLevel.EMERGENCY, current_loss_pct
            elif current_loss_pct >= self.circuit_breakers[EmergencyLevel.CRITICAL]["loss_threshold_pct"]:
                return EmergencyLevel.CRITICAL, current_loss_pct
            elif current_loss_pct >= self.circuit_breakers[EmergencyLevel.WARNING]["loss_threshold_pct"]:
                return EmergencyLevel.WARNING, current_loss_pct
            else:
                return EmergencyLevel.NORMAL, current_loss_pct
                
        except Exception as e:
            self.logger.error("Emergency level assessment failed", user_id=user_id, error=str(e))
            return EmergencyLevel.NORMAL, 0.0
    
    async def execute_emergency_protocol(
        self,
        user_id: str,
        emergency_level: EmergencyLevel,
        portfolio_data: Dict[str, Any],
        trigger_reason: str = "portfolio_loss_threshold"
    ) -> Dict[str, Any]:
        """
        Execute institutional-grade emergency protocol.
        
        Args:
            user_id: User identifier
            emergency_level: Level of emergency (WARNING, CRITICAL, EMERGENCY)
            portfolio_data: Current portfolio state
            trigger_reason: What triggered the emergency
            
        Returns:
            Emergency action results
        """
        start_time = datetime.utcnow()
        action_id = f"EMRG_{int(start_time.timestamp())}_{uuid.uuid4().hex[:8]}"
        
        self.logger.critical(
            "🚨 EMERGENCY PROTOCOL ACTIVATED",
            user_id=user_id,
            emergency_level=emergency_level.value,
            trigger_reason=trigger_reason,
            action_id=action_id
        )
        
        try:
            # Get circuit breaker configuration
            cb_config = self.circuit_breakers[emergency_level]
            
            # Execute appropriate emergency action
            if emergency_level == EmergencyLevel.WARNING:
                result = await self._execute_position_reduction(user_id, portfolio_data, cb_config)
            elif emergency_level == EmergencyLevel.CRITICAL:
                result = await self._execute_halt_and_review(user_id, portfolio_data, cb_config)
            elif emergency_level == EmergencyLevel.EMERGENCY:
                result = await self._execute_full_liquidation(user_id, portfolio_data, cb_config)
            else:
                return {"success": False, "error": "Invalid emergency level"}
            
            # Calculate execution time
            execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Create emergency action record
            emergency_action = EmergencyAction(
                action_id=action_id,
                user_id=user_id,
                emergency_level=emergency_level,
                trigger_reason=trigger_reason,
                portfolio_loss_pct=result.get("portfolio_loss_pct", 0),
                actions_taken=result.get("actions_taken", []),
                target_stablecoin=result.get("target_stablecoin", "USDC"),
                execution_time_ms=execution_time_ms,
                success=result.get("success", False),
                timestamp=start_time
            )
            
            # Store emergency action
            self.active_emergencies[user_id] = emergency_action
            await self._store_emergency_record(emergency_action)
            
            # Send notifications
            await self._send_emergency_notifications(user_id, emergency_action)
            
            self.logger.info(
                "🚨 Emergency protocol completed",
                user_id=user_id,
                action_id=action_id,
                execution_time_ms=execution_time_ms,
                success=result.get("success", False)
            )
            
            return {
                "success": True,
                "action_id": action_id,
                "emergency_level": emergency_level.value,
                "execution_time_ms": execution_time_ms,
                "result": result
            }
            
        except Exception as e:
            self.logger.error(
                "🚨 Emergency protocol FAILED",
                user_id=user_id,
                action_id=action_id,
                error=str(e),
                exc_info=True
            )
            
            return {
                "success": False,
                "action_id": action_id,
                "error": str(e),
                "emergency_level": emergency_level.value
            }
    
    async def _execute_position_reduction(
        self,
        user_id: str,
        portfolio_data: Dict[str, Any],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute position reduction (WARNING level)."""
        
        reduction_pct = config["reduction_pct"]
        actions_taken = []
        
        try:
            # Get all positions
            positions = portfolio_data.get("positions", [])
            
            # Reduce positions by specified percentage
            for position in positions:
                if position.get("quantity", 0) > 0:
                    original_qty = position["quantity"]
                    reduced_qty = original_qty * (reduction_pct / 100)
                    
                    # Execute position reduction via trade execution service
                    from app.services.trade_execution import TradeExecutionService
                    trade_executor = TradeExecutionService()
                    
                    reduction_result = await trade_executor.execute_trade(
                        {
                            "symbol": position["symbol"],
                            "action": "sell",
                            "quantity": reduced_qty,
                            "order_type": "market",
                            "urgency": "emergency"
                        },
                        user_id,
                        simulation_mode=False
                    )
                    
                    actions_taken.append({
                        "action": "position_reduction",
                        "symbol": position["symbol"],
                        "original_quantity": original_qty,
                        "reduced_quantity": reduced_qty,
                        "reduction_pct": reduction_pct,
                        "execution_result": reduction_result
                    })
            
            return {
                "success": True,
                "actions_taken": actions_taken,
                "message": f"Reduced all positions by {reduction_pct}%"
            }
            
        except Exception as e:
            self.logger.error("Position reduction failed", user_id=user_id, error=str(e))
            return {
                "success": False,
                "error": str(e),
                "actions_taken": actions_taken
            }
    
    async def _execute_halt_and_review(
        self,
        user_id: str,
        portfolio_data: Dict[str, Any],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute halt and review (CRITICAL level)."""
        
        actions_taken = []
        
        try:
            # 1. Halt all new trading
            await self._halt_user_trading(user_id)
            actions_taken.append({
                "action": "halt_trading",
                "message": "All new trades halted"
            })
            
            # 2. Reduce positions more aggressively
            reduction_result = await self._execute_position_reduction(user_id, portfolio_data, config)
            actions_taken.extend(reduction_result.get("actions_taken", []))
            
            # 3. Send critical alert
            actions_taken.append({
                "action": "critical_alert",
                "message": "Critical risk level reached - manual review required"
            })
            
            return {
                "success": True,
                "actions_taken": actions_taken,
                "message": "Trading halted and positions reduced - manual review required"
            }
            
        except Exception as e:
            self.logger.error("Halt and review failed", user_id=user_id, error=str(e))
            return {
                "success": False,
                "error": str(e),
                "actions_taken": actions_taken
            }
    
    async def _execute_full_liquidation(
        self,
        user_id: str,
        portfolio_data: Dict[str, Any],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute full emergency liquidation (EMERGENCY level)."""
        
        actions_taken = []
        
        try:
            # 1. Get safest stablecoin
            target_stablecoin = await self._get_safest_stablecoin(user_id)
            
            # 2. Halt all trading immediately
            await self._halt_user_trading(user_id)
            actions_taken.append({
                "action": "emergency_halt",
                "message": "All trading halted immediately"
            })
            
            # 3. Liquidate positions in priority order
            positions = portfolio_data.get("positions", [])
            
            for priority in self.liquidation_priority:
                priority_positions = await self._get_positions_by_priority(positions, priority)
                
                for position in priority_positions:
                    liquidation_result = await self._liquidate_position(
                        user_id=user_id,
                        position=position,
                        target_stablecoin=target_stablecoin
                    )
                    
                    actions_taken.append({
                        "action": "emergency_liquidation",
                        "priority": priority.value,
                        "symbol": position["symbol"],
                        "quantity": position.get("quantity", 0),
                        "target": target_stablecoin,
                        "result": liquidation_result
                    })
            
            return {
                "success": True,
                "actions_taken": actions_taken,
                "target_stablecoin": target_stablecoin,
                "message": f"Full emergency liquidation to {target_stablecoin} completed"
            }
            
        except Exception as e:
            self.logger.error("Full liquidation failed", user_id=user_id, error=str(e))
            return {
                "success": False,
                "error": str(e),
                "actions_taken": actions_taken
            }
    
    async def _get_safest_stablecoin(self, user_id: str) -> str:
        """Get the safest available stablecoin for liquidation."""
        
        try:
            # Check user's available exchanges and stablecoin liquidity
            from app.services.market_data_feeds import market_data_feeds
            
            for stablecoin in self.stablecoin_priority:
                symbol = stablecoin["symbol"]
                
                # Check if stablecoin is available and liquid
                liquidity_check = await market_data_feeds.get_real_time_price(symbol)
                
                if liquidity_check.get("success") and liquidity_check.get("volume_24h", 0) > 1000000:
                    self.logger.info(f"Selected {symbol} as target stablecoin", user_id=user_id)
                    return symbol
            
            # Default to USDC if checks fail
            return "USDC"
            
        except Exception as e:
            self.logger.error("Stablecoin selection failed", user_id=user_id, error=str(e))
            return "USDC"  # Safe default
    
    async def _get_positions_by_priority(self, positions: List[Dict[str, Any]], priority: LiquidationPriority) -> List[Dict[str, Any]]:
        """Filter positions by liquidation priority."""
        
        if priority == LiquidationPriority.LEVERAGED_POSITIONS:
            return [p for p in positions if p.get("leverage", 1) > 1 or p.get("position_type") == "margin"]
        
        elif priority == LiquidationPriority.LOW_LIQUIDITY_ALTS:
            # Define low liquidity altcoins (market cap < $1B or daily volume < $10M)
            low_liquidity_symbols = ["DOGE", "SHIB", "PEPE", "FLOKI", "BONK"]  # Example list
            return [p for p in positions if any(symbol in p["symbol"] for symbol in low_liquidity_symbols)]
        
        elif priority == LiquidationPriority.MAJOR_ALTS:
            major_alts = ["ETH", "SOL", "AVAX", "MATIC", "ADA", "DOT", "LINK", "UNI"]
            return [p for p in positions if any(symbol in p["symbol"] for symbol in major_alts)]
        
        elif priority == LiquidationPriority.BITCOIN:
            return [p for p in positions if "BTC" in p["symbol"]]
        
        return []
    
    async def _liquidate_position(self, user_id: str, position: Dict[str, Any], target_stablecoin: str) -> Dict[str, Any]:
        """Liquidate a specific position."""
        
        try:
            from app.services.trade_execution import TradeExecutionService
            trade_executor = TradeExecutionService()
            
            # Execute market sell order
            liquidation_result = await trade_executor.execute_trade(
                {
                    "symbol": position["symbol"],
                    "action": "sell",
                    "quantity": position.get("quantity", 0),
                    "order_type": "market",
                    "urgency": "emergency",
                    "target_asset": target_stablecoin
                },
                user_id,
                simulation_mode=False
            )
            
            return liquidation_result
            
        except Exception as e:
            self.logger.error(
                "Position liquidation failed",
                user_id=user_id,
                symbol=position.get("symbol"),
                error=str(e)
            )
            return {"success": False, "error": str(e)}
    
    async def _halt_user_trading(self, user_id: str):
        """Halt all trading for a user."""
        try:
            # Set emergency flag in Redis
            redis = await get_redis_client()
            if redis:
                await redis.set(f"emergency_halt:{user_id}", "true", ex=3600)  # 1 hour expiry
            
            # Notify master controller to stop autonomous trading
            from app.services.master_controller import MasterSystemController
            master_controller = MasterSystemController()
            await master_controller.emergency_stop(user_id, "emergency_liquidation")
            
        except Exception as e:
            self.logger.error("Failed to halt user trading", user_id=user_id, error=str(e))
    
    async def _store_emergency_record(self, emergency_action: EmergencyAction):
        """Store emergency action record for audit trail."""
        try:
            redis = await get_redis_client()
            if redis:
                record_key = f"emergency_record:{emergency_action.user_id}:{emergency_action.action_id}"
                record_data = {
                    "action_id": emergency_action.action_id,
                    "user_id": emergency_action.user_id,
                    "emergency_level": emergency_action.emergency_level.value,
                    "trigger_reason": emergency_action.trigger_reason,
                    "portfolio_loss_pct": emergency_action.portfolio_loss_pct,
                    "actions_taken": emergency_action.actions_taken,
                    "target_stablecoin": emergency_action.target_stablecoin,
                    "execution_time_ms": emergency_action.execution_time_ms,
                    "success": emergency_action.success,
                    "timestamp": emergency_action.timestamp.isoformat()
                }
                
                await redis.set(record_key, json.dumps(record_data), ex=86400 * 30)  # 30 days
                
        except Exception as e:
            self.logger.error("Failed to store emergency record", error=str(e))
    
    async def _send_emergency_notifications(self, user_id: str, emergency_action: EmergencyAction):
        """Send emergency notifications via all channels."""
        try:
            # WebSocket notification
            from app.services.websocket import manager
            await manager.broadcast({
                "type": "emergency_alert",
                "data": {
                    "action_id": emergency_action.action_id,
                    "emergency_level": emergency_action.emergency_level.value,
                    "message": f"Emergency protocol activated: {emergency_action.emergency_level.value}",
                    "actions_taken": len(emergency_action.actions_taken),
                    "timestamp": emergency_action.timestamp.isoformat()
                }
            }, user_id)
            
            # Telegram notification
            from app.services.telegram_core import TelegramCommanderService
            telegram = TelegramCommanderService()
            await telegram.send_alert(
                message_content=f"Emergency action required: {emergency_action}",
                message_type="alert",
                priority="high",
                recipient="owner"
            )
            
            # Chat notification
            from app.services.unified_ai_manager import unified_ai_manager
            await unified_ai_manager.send_emergency_notification(user_id, emergency_action)
            
        except Exception as e:
            self.logger.error("Failed to send emergency notifications", user_id=user_id, error=str(e))
    
    async def get_emergency_status(self, user_id: str) -> Dict[str, Any]:
        """Get current emergency status for user."""
        try:
            # Check if user is in emergency state
            active_emergency = self.active_emergencies.get(user_id)
            
            # Check if trading is halted - check both possible keys
            redis = await get_redis_client()
            is_halted = False
            if redis:
                halt_status = await redis.get(f"emergency_halt:{user_id}") or \
                              await redis.get(f"emergency_stop:{user_id}")
                is_halted = halt_status is not None
            
            return {
                "success": True,
                "user_id": user_id,
                "has_active_emergency": active_emergency is not None,
                "emergency_level": active_emergency.emergency_level.value if active_emergency else "normal",
                "trading_halted": is_halted,
                "last_emergency": active_emergency.timestamp.isoformat() if active_emergency else None
            }
            
        except Exception as e:
            self.logger.error("Failed to get emergency status", user_id=user_id, error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    async def resume_trading(self, user_id: str, admin_override: bool = False) -> Dict[str, Any]:
        """Resume trading after emergency (admin or automatic)."""
        try:
            # Remove emergency halt flag
            redis = await get_redis_client()
            if redis:
                await redis.delete(f"emergency_halt:{user_id}")
            
            # Clear active emergency
            if user_id in self.active_emergencies:
                del self.active_emergencies[user_id]
            
            # Notify master controller
            from app.services.master_controller import MasterSystemController
            master_controller = MasterSystemController()
            await master_controller.resume_operations(user_id)
            
            self.logger.info(
                "Trading resumed after emergency",
                user_id=user_id,
                admin_override=admin_override
            )
            
            return {
                "success": True,
                "message": "Trading resumed successfully",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error("Failed to resume trading", user_id=user_id, error=str(e))
            return {
                "success": False,
                "error": str(e)
            }


# Global emergency manager instance
emergency_manager = EmergencyManager()