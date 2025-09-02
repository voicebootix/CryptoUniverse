"""
DYNAMIC RISK MANAGEMENT - THE PROFIT PROTECTION SYSTEM

Advanced dynamic profit take and stop loss system that:
- Adapts to market volatility in real-time
- Uses trailing stops for profit maximization
- Implements volatility-based position sizing
- Dynamic stop loss adjustment based on market conditions
- Smart profit taking with market timing

This protects profits while maximizing upside potential!
"""

import asyncio
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import structlog

from app.core.logging import LoggerMixin
from app.core.redis import get_redis_client

logger = structlog.get_logger(__name__)


@dataclass
class DynamicRiskParameters:
    """Dynamic risk management parameters."""
    symbol: str
    current_price: float
    volatility_adjusted_stop: float
    volatility_adjusted_target: float
    trailing_stop_distance: float
    profit_scaling_levels: List[Dict[str, float]]
    max_risk_per_trade: float
    position_size_multiplier: float


class DynamicRiskManagement(LoggerMixin):
    """
    DYNAMIC RISK MANAGEMENT - ADAPTIVE PROFIT PROTECTION
    
    Automatically adjusts stop losses and profit targets based on:
    - Real-time volatility
    - Market sentiment
    - Position performance
    - Time decay factors
    """
    
    def __init__(self):
        self.redis = None
        self.base_risk_params = {
            "conservative": {
                "max_risk_per_trade": 0.02,  # 2%
                "profit_target_multiplier": 1.5,
                "stop_loss_multiplier": 1.0,
                "trailing_stop_trigger": 0.01  # 1%
            },
            "balanced": {
                "max_risk_per_trade": 0.03,  # 3%
                "profit_target_multiplier": 2.0,
                "stop_loss_multiplier": 1.0,
                "trailing_stop_trigger": 0.015  # 1.5%
            },
            "aggressive": {
                "max_risk_per_trade": 0.05,  # 5%
                "profit_target_multiplier": 2.5,
                "stop_loss_multiplier": 0.8,
                "trailing_stop_trigger": 0.02  # 2%
            },
            "beast_mode": {
                "max_risk_per_trade": 0.08,  # 8%
                "profit_target_multiplier": 3.0,
                "stop_loss_multiplier": 0.6,
                "trailing_stop_trigger": 0.025  # 2.5%
            }
        }
    
    async def async_init(self):
        """Initialize async components."""
        self.redis = await get_redis_client()
    
    async def calculate_dynamic_risk_parameters(
        self,
        symbol: str,
        entry_price: float,
        position_side: str,
        risk_mode: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        CALCULATE DYNAMIC RISK PARAMETERS BASED ON REAL-TIME CONDITIONS
        
        This adapts risk management to current market volatility and conditions!
        """
        try:
            self.logger.info(f"🛡️ Calculating dynamic risk parameters for {symbol}")
            
            # Get current market volatility
            market_volatility = await self._get_current_volatility(symbol)
            
            # Get base risk parameters for mode
            base_params = self.base_risk_params.get(risk_mode, self.base_risk_params["balanced"])
            
            # Calculate volatility-adjusted parameters
            volatility_multiplier = self._calculate_volatility_multiplier(market_volatility)
            
            # Dynamic stop loss (tighter in high volatility, looser in low volatility)
            base_stop_distance = base_params["max_risk_per_trade"] * base_params["stop_loss_multiplier"]
            volatility_adjusted_stop_distance = base_stop_distance * volatility_multiplier
            
            if position_side.lower() == "buy":
                stop_loss_price = entry_price * (1 - volatility_adjusted_stop_distance)
            else:  # short position
                stop_loss_price = entry_price * (1 + volatility_adjusted_stop_distance)
            
            # Dynamic profit target (larger in high volatility)
            profit_multiplier = base_params["profit_target_multiplier"] * (1 + market_volatility / 100)
            profit_target_distance = volatility_adjusted_stop_distance * profit_multiplier
            
            if position_side.lower() == "buy":
                profit_target_price = entry_price * (1 + profit_target_distance)
            else:  # short position
                profit_target_price = entry_price * (1 - profit_target_distance)
            
            # Trailing stop configuration
            trailing_stop_distance = base_params["trailing_stop_trigger"] * volatility_multiplier
            
            # Create profit scaling levels for partial profit taking
            profit_scaling_levels = self._create_profit_scaling_levels(
                entry_price, profit_target_price, position_side, market_volatility
            )
            
            # Position size adjustment based on volatility
            volatility_position_multiplier = 1.0
            if market_volatility > 10:  # High volatility
                volatility_position_multiplier = 0.7  # Reduce position size
            elif market_volatility < 3:  # Low volatility
                volatility_position_multiplier = 1.2  # Increase position size
            
            risk_params = DynamicRiskParameters(
                symbol=symbol,
                current_price=entry_price,
                volatility_adjusted_stop=stop_loss_price,
                volatility_adjusted_target=profit_target_price,
                trailing_stop_distance=trailing_stop_distance,
                profit_scaling_levels=profit_scaling_levels,
                max_risk_per_trade=base_params["max_risk_per_trade"],
                position_size_multiplier=volatility_position_multiplier
            )
            
            # Cache for real-time updates
            cache_key = f"dynamic_risk:{user_id}:{symbol}"
            await self.redis.set(
                cache_key,
                json.dumps(self._serialize_risk_params(risk_params)),
                ex=3600  # 1 hour cache
            )
            
            self.logger.info(
                f"🎯 Dynamic risk parameters calculated for {symbol}",
                user_id=user_id,
                stop_loss=f"${stop_loss_price:.4f}",
                profit_target=f"${profit_target_price:.4f}",
                volatility=f"{market_volatility:.2f}%",
                position_multiplier=f"{volatility_position_multiplier:.2f}x"
            )
            
            return {
                "success": True,
                "risk_parameters": self._serialize_risk_params(risk_params),
                "market_volatility": market_volatility,
                "volatility_multiplier": volatility_multiplier,
                "risk_mode": risk_mode
            }
            
        except Exception as e:
            self.logger.error("Dynamic risk calculation failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _get_current_volatility(self, symbol: str) -> float:
        """Get current market volatility for symbol."""
        try:
            from app.services.market_data_feeds import market_data_feeds
            
            # Get recent price data for volatility calculation
            price_data = await market_data_feeds.get_historical_prices(
                symbol=symbol,
                timeframe="1h",
                limit=24  # Last 24 hours
            )
            
            if price_data.get("success"):
                prices = [float(candle.get("close", 0)) for candle in price_data["data"]]
                
                if len(prices) > 1:
                    # Calculate hourly returns
                    returns = []
                    for i in range(1, len(prices)):
                        if prices[i-1] > 0:
                            return_pct = (prices[i] - prices[i-1]) / prices[i-1]
                            returns.append(return_pct)
                    
                    # Calculate volatility (standard deviation of returns)
                    if returns:
                        volatility = np.std(returns) * np.sqrt(24) * 100  # Annualized volatility %
                        return min(volatility, 200)  # Cap at 200%
            
            # Fallback volatility
            return 15.0  # 15% default volatility
            
        except Exception as e:
            self.logger.warning(f"Volatility calculation failed for {symbol}", error=str(e))
            return 15.0
    
    def _calculate_volatility_multiplier(self, volatility: float) -> float:
        """Calculate position and risk multipliers based on volatility."""
        
        # Volatility-based risk adjustment
        if volatility > 25:  # Very high volatility
            return 1.5  # Wider stops, larger targets
        elif volatility > 15:  # High volatility
            return 1.2
        elif volatility > 8:  # Medium volatility
            return 1.0  # Standard
        elif volatility > 3:  # Low volatility
            return 0.8  # Tighter stops
        else:  # Very low volatility
            return 0.6  # Very tight stops
    
    def _create_profit_scaling_levels(
        self,
        entry_price: float,
        final_target: float,
        position_side: str,
        volatility: float
    ) -> List[Dict[str, float]]:
        """Create profit scaling levels for partial profit taking."""
        
        scaling_levels = []
        
        # Calculate distance to target
        if position_side.lower() == "buy":
            target_distance = (final_target - entry_price) / entry_price
        else:
            target_distance = (entry_price - final_target) / entry_price
        
        # Create 3 scaling levels
        level_percentages = [0.33, 0.66, 1.0]  # 33%, 66%, 100% of target
        position_percentages = [0.25, 0.35, 0.4]  # 25%, 35%, 40% of position
        
        for i, (level_pct, pos_pct) in enumerate(zip(level_percentages, position_percentages)):
            if position_side.lower() == "buy":
                target_price = entry_price * (1 + target_distance * level_pct)
            else:
                target_price = entry_price * (1 - target_distance * level_pct)
            
            scaling_levels.append({
                "level": i + 1,
                "target_price": target_price,
                "position_percentage": pos_pct,
                "profit_percentage": target_distance * level_pct * 100,
                "triggered": False
            })
        
        return scaling_levels
    
    def _serialize_risk_params(self, params: DynamicRiskParameters) -> Dict[str, Any]:
        """Serialize risk parameters for JSON storage."""
        return {
            "symbol": params.symbol,
            "current_price": params.current_price,
            "volatility_adjusted_stop": params.volatility_adjusted_stop,
            "volatility_adjusted_target": params.volatility_adjusted_target,
            "trailing_stop_distance": params.trailing_stop_distance,
            "profit_scaling_levels": params.profit_scaling_levels,
            "max_risk_per_trade": params.max_risk_per_trade,
            "position_size_multiplier": params.position_size_multiplier
        }
    
    async def update_trailing_stops(self, user_id: str) -> Dict[str, Any]:
        """Update trailing stops for all open positions."""
        try:
            from app.services.trade_execution import TradeExecutionService
            from app.services.market_data_feeds import market_data_feeds
            
            # Get user's open positions
            trade_service = TradeExecutionService()
            positions = await trade_service.get_user_positions(user_id)
            
            if not positions.get("success"):
                return {"success": False, "error": "Failed to get positions"}
            
            updates = []
            
            for position in positions.get("positions", []):
                symbol = position.get("symbol")
                entry_price = position.get("entry_price", 0)
                current_quantity = position.get("quantity", 0)
                position_side = position.get("side", "buy")
                
                # Get current market price
                price_data = await market_data_feeds.get_real_time_price(symbol)
                
                if not price_data.get("success"):
                    continue
                
                current_price = price_data.get("price", 0)
                
                # Get cached risk parameters
                cache_key = f"dynamic_risk:{user_id}:{symbol}"
                risk_data = await self.redis.get(cache_key)
                
                if not risk_data:
                    continue
                
                risk_params = json.loads(risk_data)
                
                # Calculate current profit/loss
                if position_side.lower() == "buy":
                    unrealized_pnl_pct = (current_price - entry_price) / entry_price * 100
                else:
                    unrealized_pnl_pct = (entry_price - current_price) / entry_price * 100
                
                # Update trailing stop if in profit
                if unrealized_pnl_pct > risk_params["trailing_stop_distance"] * 100:
                    
                    # Calculate new trailing stop
                    trailing_distance = risk_params["trailing_stop_distance"]
                    
                    if position_side.lower() == "buy":
                        new_stop = current_price * (1 - trailing_distance)
                    else:
                        new_stop = current_price * (1 + trailing_distance)
                    
                    # Only move stop in favorable direction
                    current_stop = risk_params["volatility_adjusted_stop"]
                    
                    should_update = False
                    if position_side.lower() == "buy" and new_stop > current_stop:
                        should_update = True
                    elif position_side.lower() == "sell" and new_stop < current_stop:
                        should_update = True
                    
                    if should_update:
                        # Update stop loss
                        risk_params["volatility_adjusted_stop"] = new_stop
                        
                        # Cache updated parameters
                        await self.redis.set(
                            cache_key,
                            json.dumps(risk_params),
                            ex=3600
                        )
                        
                        updates.append({
                            "symbol": symbol,
                            "action": "trailing_stop_updated",
                            "old_stop": current_stop,
                            "new_stop": new_stop,
                            "current_profit_pct": unrealized_pnl_pct
                        })
                        
                        self.logger.info(
                            f"📈 Trailing stop updated for {symbol}",
                            user_id=user_id,
                            old_stop=f"${current_stop:.4f}",
                            new_stop=f"${new_stop:.4f}",
                            profit=f"{unrealized_pnl_pct:.2f}%"
                        )
                
                # Check profit scaling levels
                for level in risk_params.get("profit_scaling_levels", []):
                    if not level.get("triggered", False):
                        target_price = level["target_price"]
                        
                        # Check if level reached
                        level_reached = False
                        if position_side.lower() == "buy" and current_price >= target_price:
                            level_reached = True
                        elif position_side.lower() == "sell" and current_price <= target_price:
                            level_reached = True
                        
                        if level_reached:
                            # Trigger partial profit taking
                            profit_quantity = current_quantity * level["position_percentage"]
                            
                            # Execute partial profit taking
                            profit_result = await trade_service.execute_real_trade(
                                symbol=symbol,
                                side="sell" if position_side.lower() == "buy" else "buy",
                                quantity=profit_quantity,
                                order_type="market",
                                exchange="binance",  # Use primary exchange
                                user_id=user_id
                            )
                            
                            if profit_result.get("success"):
                                level["triggered"] = True
                                
                                updates.append({
                                    "symbol": symbol,
                                    "action": "partial_profit_taken",
                                    "level": level["level"],
                                    "quantity_sold": profit_quantity,
                                    "price": current_price,
                                    "profit_percentage": level["profit_percentage"]
                                })
                                
                                self.logger.info(
                                    f"💰 Partial profit taken for {symbol}",
                                    user_id=user_id,
                                    level=level["level"],
                                    quantity=profit_quantity,
                                    price=f"${current_price:.4f}",
                                    profit=f"{level['profit_percentage']:.1f}%"
                                )
            
            return {
                "success": True,
                "updates": updates,
                "positions_monitored": len(positions.get("positions", [])),
                "trailing_stops_updated": len([u for u in updates if u["action"] == "trailing_stop_updated"]),
                "profit_levels_triggered": len([u for u in updates if u["action"] == "partial_profit_taken"])
            }
            
        except Exception as e:
            self.logger.error("Trailing stop update failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def monitor_position_risk(
        self,
        user_id: str,
        symbol: str,
        current_price: float,
        position_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Monitor individual position risk and trigger actions if needed."""
        try:
            # Get cached risk parameters
            cache_key = f"dynamic_risk:{user_id}:{symbol}"
            risk_data = await self.redis.get(cache_key)
            
            if not risk_data:
                return {"success": False, "error": "No risk parameters found"}
            
            risk_params = json.loads(risk_data)
            
            entry_price = position_data.get("entry_price", 0)
            position_side = position_data.get("side", "buy")
            current_quantity = position_data.get("quantity", 0)
            
            # Calculate current P&L
            if position_side.lower() == "buy":
                unrealized_pnl = (current_price - entry_price) * current_quantity
                unrealized_pnl_pct = (current_price - entry_price) / entry_price * 100
            else:
                unrealized_pnl = (entry_price - current_price) * current_quantity
                unrealized_pnl_pct = (entry_price - current_price) / entry_price * 100
            
            # Risk monitoring actions
            actions = []
            
            # 1. Check stop loss trigger
            stop_loss_price = risk_params["volatility_adjusted_stop"]
            
            stop_triggered = False
            if position_side.lower() == "buy" and current_price <= stop_loss_price:
                stop_triggered = True
            elif position_side.lower() == "sell" and current_price >= stop_loss_price:
                stop_triggered = True
            
            if stop_triggered:
                actions.append({
                    "action_type": "stop_loss_triggered",
                    "urgency": "immediate",
                    "recommended_action": f"Close position at market price",
                    "reason": f"Price ${current_price:.4f} hit stop loss ${stop_loss_price:.4f}"
                })
            
            # 2. Check profit target
            profit_target = risk_params["volatility_adjusted_target"]
            
            target_reached = False
            if position_side.lower() == "buy" and current_price >= profit_target:
                target_reached = True
            elif position_side.lower() == "sell" and current_price <= profit_target:
                target_reached = True
            
            if target_reached:
                actions.append({
                    "action_type": "profit_target_reached",
                    "urgency": "high",
                    "recommended_action": "Consider taking full or partial profits",
                    "reason": f"Price ${current_price:.4f} reached target ${profit_target:.4f}"
                })
            
            # 3. Check time-based risk (positions held too long)
            position_age_hours = self._calculate_position_age_hours(position_data)
            
            if position_age_hours > 24:  # Position held > 24 hours
                actions.append({
                    "action_type": "time_risk_warning",
                    "urgency": "medium",
                    "recommended_action": "Review position - consider taking profits or tightening stop",
                    "reason": f"Position held for {position_age_hours:.1f} hours"
                })
            
            return {
                "success": True,
                "symbol": symbol,
                "current_price": current_price,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_pct": unrealized_pnl_pct,
                "risk_actions": actions,
                "stop_loss_price": stop_loss_price,
                "profit_target_price": profit_target,
                "position_age_hours": position_age_hours
            }
            
        except Exception as e:
            self.logger.error("Position risk monitoring failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    def _calculate_position_age_hours(self, position_data: Dict[str, Any]) -> float:
        """Calculate how long position has been held."""
        try:
            entry_time_str = position_data.get("entry_time") or position_data.get("created_at")
            
            if entry_time_str:
                entry_time = datetime.fromisoformat(entry_time_str.replace('Z', '+00:00'))
                age = datetime.utcnow() - entry_time.replace(tzinfo=None)
                return age.total_seconds() / 3600
            
            return 0
            
        except Exception as e:
            self.logger.warning("Exception in dynamic risk management", error=str(e))
            return 0
    
    async def execute_risk_management_action(
        self,
        user_id: str,
        symbol: str,
        action: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute risk management action (stop loss, profit taking, etc.)."""
        try:
            from app.services.trade_execution import TradeExecutionService
            
            trade_service = TradeExecutionService()
            action_type = action.get("action_type")
            
            if action_type == "stop_loss_triggered":
                # Execute immediate market close
                close_result = await trade_service.close_position(
                    symbol=symbol,
                    user_id=user_id,
                    close_type="market"
                )
                
                return {
                    "success": close_result.get("success", False),
                    "action_executed": "stop_loss",
                    "execution_result": close_result
                }
            
            elif action_type == "profit_target_reached":
                # Execute profit taking (could be partial or full)
                profit_result = await trade_service.take_partial_profit(
                    symbol=symbol,
                    user_id=user_id,
                    percentage=50  # Take 50% profit
                )
                
                return {
                    "success": profit_result.get("success", False),
                    "action_executed": "profit_taking",
                    "execution_result": profit_result
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown action type: {action_type}"
                }
                
        except Exception as e:
            self.logger.error("Risk management action failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def get_user_risk_dashboard(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive risk management dashboard for user."""
        try:
            from app.services.trade_execution import TradeExecutionService
            
            trade_service = TradeExecutionService()
            
            # Get all open positions
            positions = await trade_service.get_user_positions(user_id)
            
            if not positions.get("success"):
                return {"success": False, "error": "Failed to get positions"}
            
            risk_dashboard = {
                "total_positions": 0,
                "total_risk_exposure": 0.0,
                "positions_at_risk": 0,
                "positions_in_profit": 0,
                "trailing_stops_active": 0,
                "profit_levels_triggered": 0,
                "position_details": []
            }
            
            for position in positions.get("positions", []):
                symbol = position.get("symbol")
                
                # Monitor this position
                current_price = await self._get_current_price(symbol)
                
                if current_price > 0:
                    risk_analysis = await self.monitor_position_risk(
                        user_id, symbol, current_price, position
                    )
                    
                    if risk_analysis.get("success"):
                        risk_dashboard["total_positions"] += 1
                        
                        unrealized_pnl_pct = risk_analysis.get("unrealized_pnl_pct", 0)
                        
                        if unrealized_pnl_pct > 0:
                            risk_dashboard["positions_in_profit"] += 1
                        
                        if len(risk_analysis.get("risk_actions", [])) > 0:
                            risk_dashboard["positions_at_risk"] += 1
                        
                        risk_dashboard["position_details"].append({
                            "symbol": symbol,
                            "unrealized_pnl_pct": unrealized_pnl_pct,
                            "risk_actions": risk_analysis.get("risk_actions", []),
                            "stop_loss_price": risk_analysis.get("stop_loss_price", 0),
                            "profit_target_price": risk_analysis.get("profit_target_price", 0)
                        })
            
            return {
                "success": True,
                "risk_dashboard": risk_dashboard,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error("Risk dashboard failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _get_current_price(self, symbol: str) -> float:
        """Get current price for symbol."""
        try:
            from app.services.market_data_feeds import market_data_feeds
            
            price_data = await market_data_feeds.get_real_time_price(symbol)
            return price_data.get("price", 0) if price_data.get("success") else 0
            
        except Exception as e:
            self.logger.warning("Exception in dynamic risk management", error=str(e))
            return 0


# Global service instance
dynamic_risk_management = DynamicRiskManagement()


async def get_dynamic_risk_management() -> DynamicRiskManagement:
    """Dependency injection for FastAPI."""
    if dynamic_risk_management.redis is None:
        await dynamic_risk_management.async_init()
    return dynamic_risk_management