"""
Autonomous Trading Engine - Next Generation

Real-time event-driven autonomous trading system that eliminates Flowise limitations.
Operates on market events, not fixed schedules, with parallel strategy execution
and intelligent market adaptation.

This is the brain of a true autonomous hedge fund.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum
import uuid

import structlog
from app.core.config import get_settings
from app.core.logging import LoggerMixin
from app.core.redis import get_redis_client
from app.services.websocket import manager

settings = get_settings()
logger = structlog.get_logger(__name__)


class MarketRegime(str, Enum):
    """Market regime classification."""
    TRENDING_BULL = "trending_bull"
    TRENDING_BEAR = "trending_bear"
    RANGE_BOUND = "range_bound"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"


class TradingIntensity(str, Enum):
    """Trading intensity levels."""
    HIBERNATION = "hibernation"     # 0-2 trades/day
    CONSERVATIVE = "conservative"   # 3-8 trades/day
    ACTIVE = "active"              # 10-25 trades/day
    AGGRESSIVE = "aggressive"      # 30-60 trades/day
    HYPERACTIVE = "hyperactive"    # 100+ trades/day


@dataclass
class MarketEvent:
    """Market event that triggers strategy evaluation."""
    event_type: str
    symbol: str
    price: float
    volume: float
    timestamp: datetime
    significance: float  # 0-100
    data: Dict[str, Any]


@dataclass
class AutonomousConfig:
    """Enhanced autonomous configuration."""
    user_id: str
    target_daily_return: float
    max_daily_loss: float
    risk_tolerance: float  # 0-100
    trading_intensity: TradingIntensity
    preferred_strategies: List[str]
    excluded_strategies: List[str]
    market_regimes: List[MarketRegime]
    auto_compound: bool
    emergency_stop_loss: float
    profit_taking_strategy: str
    rebalance_frequency: int  # minutes


class AutonomousEngine(LoggerMixin):
    """
    Next-generation autonomous trading engine.
    
    Real-time, event-driven, multi-strategy execution with intelligent
    market adaptation and risk management.
    """
    
    def __init__(self):
        self.active_sessions: Dict[str, AutonomousConfig] = {}
        self.market_events_queue = asyncio.Queue()
        self.strategy_results_queue = asyncio.Queue()
        self.execution_queue = asyncio.Queue()
        
        # Real-time market monitoring
        self.price_streams: Dict[str, float] = {}
        self.volume_streams: Dict[str, float] = {}
        self.market_regime_cache: Dict[str, MarketRegime] = {}
        
        # Performance tracking
        self.session_metrics: Dict[str, Dict] = {}
        
        # Strategy orchestration
        self.strategy_pool = asyncio.Queue(maxsize=1000)
        self.execution_pool = asyncio.Queue(maxsize=500)
        
        self.running = False
        self.redis = None
    
    async def start_autonomous_session(self, config: AutonomousConfig) -> Dict[str, Any]:
        """Start autonomous trading session for user."""
        try:
            user_id = config.user_id
            
            # Validate user has exchange connections
            from app.services.user_exchange_service import user_exchange_service
            exchange_summary = await user_exchange_service.get_user_exchange_summary(user_id)
            
            if exchange_summary.get("active_exchanges", 0) == 0:
                return {
                    "success": False,
                    "error": "No active exchange connections found"
                }
            
            # Store session configuration
            self.active_sessions[user_id] = config
            
            # Initialize session metrics
            self.session_metrics[user_id] = {
                "session_id": str(uuid.uuid4()),
                "started_at": datetime.utcnow(),
                "trades_executed": 0,
                "total_pnl": 0.0,
                "current_drawdown": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.0,
                "last_trade_at": None,
                "emergency_stops": 0,
                "regime_changes": 0
            }
            
            # Store in Redis for persistence
            if not self.redis:
                self.redis = await get_redis_client()
            
            await self.redis.hset(
                f"autonomous_session:{user_id}",
                mapping={
                    "config": json.dumps(config.__dict__, default=str),
                    "started_at": datetime.utcnow().isoformat(),
                    "status": "active"
                }
            )
            
            # Start real-time monitoring for this user
            await self._start_user_monitoring(user_id)
            
            self.logger.info(
                "🚀 AUTONOMOUS SESSION STARTED",
                user_id=user_id,
                target_return=config.target_daily_return,
                intensity=config.trading_intensity.value
            )
            
            return {
                "success": True,
                "session_id": self.session_metrics[user_id]["session_id"],
                "message": f"Autonomous trading started with {config.trading_intensity.value} intensity",
                "estimated_trades_per_day": self._estimate_daily_trades(config.trading_intensity),
                "target_daily_return": config.target_daily_return
            }
            
        except Exception as e:
            self.logger.error("Failed to start autonomous session", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _start_user_monitoring(self, user_id: str):
        """Start real-time monitoring for user."""
        # Add user to real-time price stream monitoring
        # This would connect to exchange WebSocket feeds
        pass
    
    def _estimate_daily_trades(self, intensity: TradingIntensity) -> int:
        """Estimate daily trade count based on intensity."""
        estimates = {
            TradingIntensity.HIBERNATION: 2,
            TradingIntensity.CONSERVATIVE: 8,
            TradingIntensity.ACTIVE: 25,
            TradingIntensity.AGGRESSIVE: 60,
            TradingIntensity.HYPERACTIVE: 150
        }
        return estimates.get(intensity, 25)
    
    async def process_market_event(self, event: MarketEvent):
        """Process market event and trigger strategy evaluation."""
        try:
            # Add to event queue for processing
            await self.market_events_queue.put(event)
            
            # Check if event is significant enough to trigger immediate action
            if event.significance > 80:
                # High significance event - trigger immediate strategy evaluation
                await self._trigger_immediate_evaluation(event)
            
        except Exception as e:
            self.logger.error("Failed to process market event", error=str(e))
    
    async def _trigger_immediate_evaluation(self, event: MarketEvent):
        """Trigger immediate strategy evaluation for high-significance events."""
        # Evaluate all active sessions that might be interested in this symbol
        for user_id, config in self.active_sessions.items():
            if (event.symbol in config.preferred_strategies or 
                event.significance > 90):  # Very high significance affects everyone
                
                # Queue strategy evaluation
                await self.strategy_pool.put({
                    "user_id": user_id,
                    "trigger_event": event,
                    "priority": "high",
                    "timestamp": datetime.utcnow()
                })
    
    async def run_strategy_orchestrator(self):
        """Main strategy orchestration loop - runs continuously."""
        self.logger.info("🎯 Strategy orchestrator started")
        
        while self.running:
            try:
                # Process strategy evaluation requests
                if not self.strategy_pool.empty():
                    strategy_request = await self.strategy_pool.get()
                    await self._evaluate_strategies_for_user(strategy_request)
                
                # Process execution requests
                if not self.execution_queue.empty():
                    execution_request = await self.execution_queue.get()
                    await self._execute_trade_request(execution_request)
                
                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error("Strategy orchestrator error", error=str(e))
                await asyncio.sleep(1)
    
    async def _evaluate_strategies_for_user(self, request: Dict[str, Any]):
        """Evaluate strategies for specific user based on market event."""
        user_id = request["user_id"]
        trigger_event = request["trigger_event"]
        
        try:
            config = self.active_sessions.get(user_id)
            if not config:
                return
            
            # Determine current market regime
            current_regime = await self._detect_market_regime(trigger_event.symbol)
            
            # Select strategies based on regime and user preferences
            active_strategies = self._select_strategies_for_regime(
                current_regime, 
                config.preferred_strategies,
                config.excluded_strategies
            )
            
            # Run strategies in parallel (not sequential!)
            strategy_tasks = []
            for strategy in active_strategies[:5]:  # Limit to top 5 for performance
                task = self._run_strategy_analysis(
                    strategy, trigger_event, config, current_regime
                )
                strategy_tasks.append(task)
            
            # Execute strategies in parallel
            results = await asyncio.gather(*strategy_tasks, return_exceptions=True)
            
            # Process results and queue best opportunities
            for result in results:
                if isinstance(result, Exception):
                    continue
                
                if (result.get("success") and 
                    result.get("signal", {}).get("confidence", 0) > 70):
                    
                    # Queue for execution
                    await self.execution_queue.put({
                        "user_id": user_id,
                        "signal": result["signal"],
                        "strategy": result["strategy"],
                        "priority": self._calculate_execution_priority(result),
                        "timestamp": datetime.utcnow()
                    })
            
        except Exception as e:
            self.logger.error(f"Strategy evaluation failed for user {user_id}", error=str(e))
    
    async def _detect_market_regime(self, symbol: str) -> MarketRegime:
        """Detect current market regime using real-time data."""
        # This would analyze:
        # - Price volatility
        # - Volume patterns  
        # - Trend strength
        # - Support/resistance levels
        
        # For now, return a default
        return MarketRegime.TRENDING_BULL
    
    def _select_strategies_for_regime(
        self, 
        regime: MarketRegime, 
        preferred: List[str],
        excluded: List[str]
    ) -> List[str]:
        """Select optimal strategies for current market regime."""
        
        regime_strategies = {
            MarketRegime.TRENDING_BULL: [
                "spot_momentum_strategy", "spot_breakout_strategy", 
                "futures_trade", "scalping_strategy"
            ],
            MarketRegime.TRENDING_BEAR: [
                "spot_mean_reversion", "futures_trade", "options_trade"
            ],
            MarketRegime.RANGE_BOUND: [
                "spot_mean_reversion", "market_making", "grid_trading"
            ],
            MarketRegime.HIGH_VOLATILITY: [
                "scalping_strategy", "spot_breakout_strategy", "options_trade"
            ],
            MarketRegime.BREAKOUT: [
                "spot_breakout_strategy", "spot_momentum_strategy", "futures_trade"
            ]
        }
        
        optimal_strategies = regime_strategies.get(regime, ["spot_momentum_strategy"])
        
        # Filter by user preferences
        if preferred:
            optimal_strategies = [s for s in optimal_strategies if s in preferred]
        
        # Remove excluded strategies
        optimal_strategies = [s for s in optimal_strategies if s not in excluded]
        
        return optimal_strategies
    
    async def _run_strategy_analysis(
        self, 
        strategy: str, 
        event: MarketEvent, 
        config: AutonomousConfig,
        regime: MarketRegime
    ) -> Dict[str, Any]:
        """Run individual strategy analysis."""
        try:
            from app.services.trading_strategies import trading_strategies_service
            
            # Create market data context
            market_data = {
                "trigger_event": event.__dict__,
                "current_regime": regime.value,
                "symbol_analysis": {
                    event.symbol: {
                        "price": event.price,
                        "volume": event.volume,
                        "opportunity_score": event.significance
                    }
                }
            }
            
            # Generate signal
            result = await trading_strategies_service.generate_trading_signal(
                strategy_type=strategy,
                market_data=market_data,
                risk_mode=self._map_intensity_to_risk_mode(config.trading_intensity),
                user_id=config.user_id
            )
            
            return {**result, "strategy": strategy}
            
        except Exception as e:
            self.logger.error(f"Strategy analysis failed: {strategy}", error=str(e))
            return {"success": False, "error": str(e), "strategy": strategy}
    
    def _map_intensity_to_risk_mode(self, intensity: TradingIntensity) -> str:
        """Map trading intensity to risk mode."""
        mapping = {
            TradingIntensity.HIBERNATION: "conservative",
            TradingIntensity.CONSERVATIVE: "conservative", 
            TradingIntensity.ACTIVE: "balanced",
            TradingIntensity.AGGRESSIVE: "aggressive",
            TradingIntensity.HYPERACTIVE: "beast_mode"
        }
        return mapping.get(intensity, "balanced")
    
    def _calculate_execution_priority(self, result: Dict[str, Any]) -> int:
        """Calculate execution priority (1-100)."""
        signal = result.get("signal", {})
        confidence = signal.get("confidence", 0)
        expected_return = signal.get("expected_return", 0)
        
        # Higher priority for high confidence + high return
        priority = (confidence * 0.6) + (expected_return * 0.4)
        return min(100, max(1, int(priority)))
    
    async def _execute_trade_request(self, request: Dict[str, Any]):
        """Execute trade request from strategy signal."""
        user_id = request["user_id"]
        signal = request["signal"]
        
        try:
            from app.services.trade_execution import TradeExecutionService
            trade_executor = TradeExecutionService()
            
            # Execute real trade
            result = await trade_executor.execute_real_trade(
                symbol=signal["symbol"],
                side=signal["action"],
                quantity=signal.get("position_size", 0.1),
                user_id=user_id
            )
            
            # Update session metrics
            if user_id in self.session_metrics:
                metrics = self.session_metrics[user_id]
                metrics["trades_executed"] += 1
                metrics["last_trade_at"] = datetime.utcnow()
                
                if result.get("success"):
                    # Update P&L
                    trade_pnl = result.get("profit_generated_usd", 0)
                    metrics["total_pnl"] += trade_pnl
                    
                    # Send real-time update to user
                    await self._send_realtime_update(user_id, {
                        "type": "trade_executed",
                        "data": {
                            "symbol": signal["symbol"],
                            "action": signal["action"],
                            "pnl": trade_pnl,
                            "total_pnl": metrics["total_pnl"]
                        }
                    })
            
        except Exception as e:
            self.logger.error("Trade execution failed", error=str(e), user_id=user_id)
    
    async def _send_realtime_update(self, user_id: str, update: Dict[str, Any]):
        """Send real-time update to user via WebSocket."""
        try:
            await manager.send_personal_message(json.dumps(update), user_id)
        except Exception as e:
            self.logger.warning("Failed to send real-time update", error=str(e))


# Global autonomous engine
autonomous_engine = AutonomousEngine()


async def get_autonomous_engine() -> AutonomousEngine:
    """Dependency injection for FastAPI."""
    return autonomous_engine