"""
Master System Controller - THE $100M AUTONOMOUS HEDGE FUND BRAIN

Adapted from your Flowise orchestration masterpiece for native Python architecture.
Orchestrates all trading services with sophisticated 5-phase execution flow,
multiple trading cycles, emergency protocols, and autonomous operation.

CORE ORCHESTRATION FEATURES:
- 5-Phase Validated Execution Flow
- 4 Trading Cycles (Arbitrage, Momentum, Portfolio, Deep Analysis)  
- 4 Trading Modes (Conservative, Balanced, Aggressive, Beast Mode)
- Timezone-based Strategy Optimization (6 time zones)
- Emergency Circuit Breakers & Recovery
- Autonomous Profit Compounding
- Real-time Risk Management

ALL SOPHISTICATION PRESERVED - ADAPTED FOR PYTHON EXCELLENCE
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import uuid

import structlog
from app.core.config import get_settings
from app.services.market_data_coordinator import market_data_coordinator
from app.core.logging import LoggerMixin
from app.core.redis import get_redis_client
from app.services.websocket import manager
from app.services.emergency_manager import emergency_manager, EmergencyLevel

settings = get_settings()
logger = structlog.get_logger(__name__)


class TradingMode(str, Enum):
    """Trading mode enumeration with risk profiles."""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced" 
    AGGRESSIVE = "aggressive"
    BEAST_MODE = "beast_mode"


class TradingCycle(str, Enum):
    """Trading cycle types."""
    ARBITRAGE_HUNTER = "arbitrage_hunter"
    MOMENTUM_FUTURES = "momentum_futures"
    PORTFOLIO_OPTIMIZATION = "portfolio_optimization"
    DEEP_ANALYSIS = "deep_analysis"



@dataclass
class TradingModeConfig:
    """Trading mode configuration with AI model weights and autonomous frequency."""
    daily_target_pct: float
    monthly_target_pct: float
    max_drawdown_pct: float
    min_win_rate_pct: float
    max_leverage: float
    max_position_pct: float
    validation_threshold: float
    profit_take_pct: float
    stop_loss_pct: float
    cash_target_pct: float
    # NEW: AI Model Configuration
    ai_model_weights: Dict[str, float]  # User-configurable AI model weights
    autonomous_frequency_minutes: int   # How often autonomous trading runs
    emergency_stop_loss_pct: float     # Emergency liquidation threshold


class MasterSystemController(LoggerMixin):
    """
    THE $100M AUTONOMOUS HEDGE FUND BRAIN - PYTHON EDITION
    
    Orchestrates all trading services using the sophisticated 5-phase execution flow
    with multiple trading cycles, emergency protocols, and autonomous operation.
    
    ADAPTED FROM YOUR FLOWISE MASTERPIECE FOR PYTHON EXCELLENCE
    """
    
    def __init__(self):
        self.current_mode = TradingMode.BALANCED
        self.is_active = False
        self.performance_metrics = {
            "cycles_executed": 0,
            "trades_executed": 0,
            "total_profit_usd": 0.0,
            "success_rate": 0.0,
            "uptime_hours": 0.0,
            "consecutive_wins": 0,
            "consecutive_losses": 0,
            "last_emergency_level": EmergencyLevel.NORMAL.value
        }
        self.start_time = datetime.utcnow()
        self.redis = None  # Will be initialized lazily
        self._redis_initialized = False
        
        # Trading mode configurations with AI model weights and autonomous frequency
        self.mode_configs = {
            TradingMode.CONSERVATIVE: TradingModeConfig(
                daily_target_pct=1.5,
                monthly_target_pct=30.0,
                max_drawdown_pct=5.0,
                min_win_rate_pct=70.0,
                max_leverage=1.0,
                max_position_pct=5.0,
                validation_threshold=80.0,
                profit_take_pct=5.0,
                stop_loss_pct=2.0,
                cash_target_pct=40.0,
                # AI Model Configuration - Conservative: Favor accuracy over speed
                ai_model_weights={"gpt4": 0.4, "claude": 0.4, "gemini": 0.2},
                autonomous_frequency_minutes=15,  # Conservative: Less frequent trading
                emergency_stop_loss_pct=7.0      # Conservative: Quick emergency stop
            ),
            TradingMode.BALANCED: TradingModeConfig(
                daily_target_pct=3.5,
                monthly_target_pct=70.0,
                max_drawdown_pct=10.0,
                min_win_rate_pct=65.0,
                max_leverage=3.0,
                max_position_pct=10.0,
                validation_threshold=75.0,
                profit_take_pct=10.0,
                stop_loss_pct=5.0,
                cash_target_pct=20.0,
                # AI Model Configuration - Balanced: Equal weighting
                ai_model_weights={"gpt4": 0.33, "claude": 0.34, "gemini": 0.33},
                autonomous_frequency_minutes=10,  # Balanced: Moderate frequency
                emergency_stop_loss_pct=15.0     # Balanced: Standard emergency threshold
            ),
            TradingMode.AGGRESSIVE: TradingModeConfig(
                daily_target_pct=7.5,
                monthly_target_pct=200.0,
                max_drawdown_pct=20.0,
                min_win_rate_pct=60.0,
                max_leverage=5.0,
                max_position_pct=20.0,
                validation_threshold=70.0,
                profit_take_pct=15.0,
                stop_loss_pct=7.0,
                cash_target_pct=10.0,
                # AI Model Configuration - Aggressive: Favor speed and opportunity detection
                ai_model_weights={"gpt4": 0.3, "claude": 0.3, "gemini": 0.4},
                autonomous_frequency_minutes=5,   # Aggressive: More frequent trading
                emergency_stop_loss_pct=20.0     # Aggressive: Higher risk tolerance
            ),
            TradingMode.BEAST_MODE: TradingModeConfig(
                daily_target_pct=25.0,
                monthly_target_pct=500.0,
                max_drawdown_pct=50.0,
                min_win_rate_pct=55.0,
                max_leverage=10.0,
                max_position_pct=50.0,
                validation_threshold=60.0,
                profit_take_pct=20.0,
                stop_loss_pct=0.0,  # Diamond hands
                cash_target_pct=5.0,
                # AI Model Configuration - Beast Mode: Optimized for maximum performance
                ai_model_weights={"gpt4": 0.35, "claude": 0.35, "gemini": 0.3},
                autonomous_frequency_minutes=1,   # Beast Mode: Maximum frequency
                emergency_stop_loss_pct=25.0     # Beast Mode: Highest risk tolerance
            )
        }
    
    async def _ensure_redis(self) -> Optional[Any]:
        """ENTERPRISE: Ensure Redis client is available with graceful degradation."""
        if not self._redis_initialized:
            try:
                from app.core.redis import get_redis_client
                self.redis = await get_redis_client()
                self._redis_initialized = True
                if self.redis:
                    self.logger.info("Redis client initialized for Master Controller")
                else:
                    self.logger.warning("Redis unavailable - operating in degraded mode")
            except Exception as e:
                self.logger.error("Failed to initialize Redis client", error=str(e))
                self.redis = None
                self._redis_initialized = True
        return self.redis
        
        # Timezone strategies
        self.timezone_strategies = {
            # Asian Degen Hours (00:00-04:00 UTC)
            "asian_degen": {
                "hours": (0, 4),
                "strategy_focus": "aggressive_momentum",
                "position_size_pct": 15.0,
                "leverage_multiplier": 1.5,
                "preferred_strategies": ["scalping_strategy", "spot_momentum_strategy"],
                "description": "Exploit thin orderbooks and volatile new listings"
            },
            # Asia-Europe Overlap (04:00-08:00 UTC)  
            "arbitrage_prime": {
                "hours": (4, 8),
                "strategy_focus": "arbitrage_hunting",
                "position_size_pct": 25.0,
                "leverage_multiplier": 1.0,
                "preferred_strategies": ["arbitrage_execution", "triangular_arbitrage"],
                "description": "Maximum arbitrage opportunities across regions"
            },
            # European Institutional (08:00-12:00 UTC)
            "institutional_flow": {
                "hours": (8, 12), 
                "strategy_focus": "follow_smart_money",
                "position_size_pct": 18.0,
                "leverage_multiplier": 1.2,
                "preferred_strategies": ["institutional_flow", "options_trading"],
                "description": "Track institutional movements and whale activity"
            },
            # US Opening Bell (12:00-16:00 UTC)
            "volatility_breakout": {
                "hours": (12, 16),
                "strategy_focus": "breakout_plays",
                "position_size_pct": 22.0,
                "leverage_multiplier": 1.3,
                "preferred_strategies": ["spot_breakout_strategy", "spot_momentum_strategy"],
                "description": "Capitalize on news-driven volatility spikes"
            },
            # US Power Hour (16:00-20:00 UTC)
            "momentum_continuation": {
                "hours": (16, 20),
                "strategy_focus": "momentum_riding",
                "position_size_pct": 18.0,
                "leverage_multiplier": 1.1,
                "preferred_strategies": ["spot_momentum_strategy", "swing_trading"],
                "description": "Ride momentum waves during high activity"
            },
            # Global Consolidation (20:00-00:00 UTC)
            "mean_reversion": {
                "hours": (20, 24),
                "strategy_focus": "range_trading",
                "position_size_pct": 12.0,
                "leverage_multiplier": 0.8,
                "preferred_strategies": ["spot_mean_reversion", "grid_trading"],
                "description": "Exploit range-bound consolidation patterns"
            }
        }
        
        # Cycle schedule (minute-based)
        self.cycle_schedule = {
            # Arbitrage Hunter: Every few minutes for rapid execution
            TradingCycle.ARBITRAGE_HUNTER.value: [
                1, 4, 6, 9, 11, 14, 16, 19, 21, 24, 26, 29, 
                31, 34, 36, 39, 41, 44, 46, 49, 51, 54, 56, 59
            ],
            # Momentum & Futures: Specific intervals  
            TradingCycle.MOMENTUM_FUTURES.value: [5, 10, 20, 25, 35, 40, 50, 55],
            # Portfolio Optimization: Mid-hour intervals
            TradingCycle.PORTFOLIO_OPTIMIZATION.value: [15, 45],
            # Deep Analysis: Top and bottom of hour
            TradingCycle.DEEP_ANALYSIS.value: [0, 30]
        }
        
        # Start autonomous operation
        self.logger.info("🚀 AUTONOMOUS HEDGE FUND BRAIN INITIALIZING")
        
    def get_current_timezone_strategy(self) -> Dict[str, Any]:
        """Get current timezone strategy based on UTC hour."""
        utc_hour = datetime.utcnow().hour
        
        for strategy_name, config in self.timezone_strategies.items():
            start_hour, end_hour = config["hours"]
            if start_hour <= utc_hour < end_hour:
                return {**config, "name": strategy_name}
        
        # Fallback to balanced approach
        return {
            "name": "balanced_default",
            "hours": (utc_hour, utc_hour + 1),
            "strategy_focus": "balanced",
            "position_size_pct": 15.0,
            "leverage_multiplier": 1.0,
            "preferred_strategies": ["spot_momentum_strategy", "spot_mean_reversion"],
            "description": "Balanced default strategy"
        }
    
    async def check_emergency_conditions(self, portfolio_data: Dict[str, Any]) -> EmergencyLevel:
        """Check for emergency conditions using real portfolio metrics."""
        
        # Extract REAL portfolio metrics from actual data
        portfolio_metrics = portfolio_data.get("portfolio_metrics", {})
        risk_metrics = portfolio_data.get("risk_metrics", {})
        performance_data = portfolio_data.get("performance_data", {})
        
        # Real daily P&L calculation
        daily_pnl_pct = performance_data.get("daily_pnl_percentage", 0)
        if not daily_pnl_pct and portfolio_metrics.get("total_value_usd"):
            # Calculate from position changes if not directly available
            current_value = float(portfolio_metrics.get("total_value_usd", 0))
            initial_value = float(portfolio_metrics.get("initial_daily_value_usd", current_value))
            daily_pnl_pct = ((current_value - initial_value) / initial_value) * 100 if initial_value > 0 else 0
        
        # Real consecutive losses from trading history
        consecutive_losses = performance_data.get("consecutive_losses", 0)
        
        # Real margin usage from exchange positions
        margin_usage_pct = portfolio_metrics.get("margin_usage_percentage", 0)
        if not margin_usage_pct and portfolio_metrics.get("margin_used_usd"):
            # Calculate margin usage if not directly available
            margin_used = float(portfolio_metrics.get("margin_used_usd", 0))
            margin_available = float(portfolio_metrics.get("margin_available_usd", 1))
            margin_usage_pct = (margin_used / (margin_used + margin_available)) * 100 if (margin_used + margin_available) > 0 else 0
        
        # Additional real risk metrics
        current_drawdown = risk_metrics.get("current_drawdown_percentage", 0)
        portfolio_volatility = risk_metrics.get("portfolio_volatility", 0)
        leverage_ratio = portfolio_metrics.get("average_leverage", 1.0)
        
        # LEVEL 3: EMERGENCY (Immediate intervention required)
        emergency_conditions = [
            daily_pnl_pct < -7.0,  # Lost more than 7% in a day
            margin_usage_pct > 90,  # Margin critically high
            current_drawdown > 15.0,  # Drawdown exceeds 15%
            leverage_ratio > 8.0 and daily_pnl_pct < -3.0,  # High leverage + losses
        ]
        if any(emergency_conditions):
            self.logger.critical("EMERGENCY CONDITIONS DETECTED", 
                               daily_pnl=daily_pnl_pct, 
                               margin_usage=margin_usage_pct,
                               drawdown=current_drawdown,
                               leverage=leverage_ratio)
            return EmergencyLevel.EMERGENCY
        
        # LEVEL 2: CRITICAL (High risk, immediate attention needed)
        critical_conditions = [
            daily_pnl_pct < -5.0,  # Lost more than 5% in a day
            consecutive_losses > 5,  # 5+ consecutive losing trades
            margin_usage_pct > 85,  # Very high margin usage
            current_drawdown > 10.0,  # Significant drawdown
            leverage_ratio > 6.0 and daily_pnl_pct < -2.0,  # High leverage + moderate losses
        ]
        if any(critical_conditions):
            self.logger.error("CRITICAL CONDITIONS DETECTED", 
                            daily_pnl=daily_pnl_pct, 
                            consecutive_losses=consecutive_losses,
                            margin_usage=margin_usage_pct)
            return EmergencyLevel.CRITICAL
        
        # LEVEL 1: WARNING (Elevated risk, monitor closely)
        warning_conditions = [
            daily_pnl_pct < -3.0,  # Lost more than 3% in a day
            consecutive_losses > 3,  # 3+ consecutive losses
            margin_usage_pct > 70,  # High margin usage
            current_drawdown > 7.0,  # Notable drawdown
            leverage_ratio > 4.0 and daily_pnl_pct < -1.0,  # Moderate leverage + small losses
            portfolio_volatility > 25.0,  # Portfolio very volatile
        ]
        if any(warning_conditions):
            self.logger.warning("WARNING CONDITIONS DETECTED", 
                              daily_pnl=daily_pnl_pct,
                              volatility=portfolio_volatility)
            return EmergencyLevel.WARNING
        
        return EmergencyLevel.NORMAL
    
    async def execute_emergency_protocol(
        self,
        level: EmergencyLevel
    ) -> TradingMode:
        """Execute emergency protocol and return recommended mode."""
        
        # Import services here to avoid circular imports
        try:
            from app.services.telegram_commander import telegram_commander_service
            telegram_service = telegram_commander_service
        except:
            telegram_service = None
        
        if level == EmergencyLevel.EMERGENCY:
            # Emergency: Close all positions except arbitrage
            if telegram_service:
                await telegram_service.send_alert(
                    "🚨 EMERGENCY PROTOCOL ACTIVATED 🚨\n"
                    "Daily loss > 7% or margin critical\n"
                    "Closing all risky positions immediately",
                    priority="critical"
                )
            return TradingMode.CONSERVATIVE
            
        elif level == EmergencyLevel.CRITICAL:
            # Critical: Switch to conservative, halt risky strategies
            if telegram_service:
                await telegram_service.send_alert(
                    "⚠️ CRITICAL RISK LEVEL ⚠️\n"
                    "Switching to conservative mode\n" 
                    "Halting aggressive strategies",
                    priority="high"
                )
            return TradingMode.CONSERVATIVE
            
        elif level == EmergencyLevel.WARNING:
            # Warning: Reduce risk, increase validation
            if telegram_service:
                await telegram_service.send_alert(
                    "🟡 WARNING: Elevated Risk\n"
                    "Reducing position sizes by 50%\n"
                    "Increasing validation thresholds",
                    priority="normal"
                )
            # Move to more conservative mode
            mode_hierarchy = [TradingMode.BEAST_MODE, TradingMode.AGGRESSIVE, TradingMode.BALANCED, TradingMode.CONSERVATIVE]
            current_index = mode_hierarchy.index(self.current_mode)
            if current_index > 0:
                return mode_hierarchy[current_index - 1]
        
        return self.current_mode
    
    async def validate_real_trade_execution(
        self,
        signal_data: Dict[str, Any],
        sizing_data: Dict[str, Any],
        portfolio_data: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Comprehensive validation before executing real trades.
        Returns validation result with go/no-go decision.
        """
        
        validation_results = {
            "approved": False,
            "reason": "",
            "checks": {},
            "adjustments": {}
        }
        
        try:
            # Check 1: Position Size Validation
            position_size = sizing_data.get("recommended_size", 0)
            position_value = sizing_data.get("position_value_usd", 0)
            
            if position_size <= 0:
                validation_results["reason"] = "Invalid position size (zero or negative)"
                return validation_results
            
            validation_results["checks"]["position_size"] = "PASS"
            
            # Check 2: Portfolio Balance Validation
            portfolio_balance = portfolio_data.get("portfolio_metrics", {}).get("available_balance_usd", 0)
            if position_value > portfolio_balance * 0.95:  # Keep 5% buffer
                validation_results["reason"] = f"Insufficient balance. Required: ${position_value}, Available: ${portfolio_balance}"
                return validation_results
            
            validation_results["checks"]["balance"] = "PASS"
            
            # Check 3: Risk Limits Validation
            mode_config = self.mode_configs[self.current_mode]
            portfolio_value = portfolio_data.get("portfolio_metrics", {}).get("total_value_usd", 10000)
            max_position_value = portfolio_value * (mode_config.max_position_pct / 100)
            
            adjusted_size = position_size
            adjusted_value = position_value
            
            if position_value > max_position_value:
                # Scale down position
                scale_factor = max_position_value / position_value
                adjusted_size = position_size * scale_factor
                adjusted_value = position_value * scale_factor
                
                validation_results["adjustments"]["position_scaled"] = {
                    "original_size": position_size,
                    "adjusted_size": adjusted_size,
                    "scale_factor": scale_factor
                }
            
            validation_results["checks"]["risk_limits"] = "PASS"
            
            # Check 4: Market Conditions Validation
            symbol = signal_data.get("symbol", "")
            if not symbol:
                validation_results["reason"] = "Missing symbol in signal data"
                return validation_results
            
            # Import market analysis service for real-time checks
            from app.services.market_analysis import market_analysis_service
            
            # Get current market data for the symbol
            market_check = await market_analysis_service.get_symbol_analysis(
                symbol=symbol,
                user_id=user_id
            )
            
            if not market_check.get("success"):
                validation_results["reason"] = f"Cannot validate market conditions for {symbol}"
                return validation_results
            
            # Check if market is liquid enough
            liquidity_data = market_check.get("liquidity_analysis", {})
            min_liquidity_usd = adjusted_value * 10  # Need 10x liquidity for safe execution
            
            if liquidity_data.get("total_liquidity_usd", 0) < min_liquidity_usd:
                validation_results["reason"] = f"Insufficient market liquidity for {symbol}"
                return validation_results
            
            validation_results["checks"]["market_conditions"] = "PASS"
            
            # Check 5: Exchange Status Validation
            target_exchange = signal_data.get("exchange", "binance")
            
            from app.services.trade_execution import trade_execution_service
            exchange_status = await trade_execution_service.get_exchange_status(exchange=target_exchange)
            
            if not exchange_status.get("operational", False):
                validation_results["reason"] = f"Exchange {target_exchange} is not operational"
                return validation_results
            
            validation_results["checks"]["exchange_status"] = "PASS"
            
            # All checks passed
            validation_results["approved"] = True
            validation_results["reason"] = "All validation checks passed"
            validation_results["final_position_size"] = adjusted_size
            validation_results["final_position_value"] = adjusted_value
            
            return validation_results
            
        except Exception as e:
            validation_results["reason"] = f"Validation error: {str(e)}"
            validation_results["error"] = str(e)
            return validation_results
    
    async def execute_5_phase_flow(
        self,
        cycle_type: TradingCycle,
        focus_strategies: List[str] = None,
        user_id: str = "system",
        risk_tolerance: str = "balanced"
    ) -> Dict[str, Any]:
        """Execute the complete 5-phase validated execution flow."""
        
        start_time = time.time()
        phases_executed = []
        trades_executed = 0
        profit_generated = 0.0
        
        try:
            # Import your existing sophisticated services
            from app.services.market_analysis_core import MarketAnalysisService
            from app.services.trading_strategies import trading_strategies_service
            from app.services.portfolio_risk_core import PortfolioRiskServiceExtended
            from app.services.ai_consensus_core import ai_consensus_service
            from app.services.trade_execution import TradeExecutionService
            from app.services.telegram_core import TelegramService
            
            # Initialize service instances
            market_analysis_service = MarketAnalysisService()
            portfolio_risk_service = PortfolioRiskServiceExtended()
            trade_execution_service = TradeExecutionService()
            telegram_service = TelegramService()
            
            # Get sentiment analysis for strategy optimization
            try:
                from app.services.realtime_sentiment_engine import realtime_sentiment_engine
                sentiment_result = await realtime_sentiment_engine.get_sentiment_for_strategy_optimization(
                    symbols=["BTC", "ETH", "SOL", "BNB"], 
                    user_id=user_id
                )
            except Exception as e:
                self.logger.warning(f"Failed to fetch sentiment data: {e}")
                sentiment_result = {"success": False}  # Fallback for sentiment operations
            
            # PHASE 0: Emergency Checks & Timezone Strategy
            phase_start = time.time()
            
            # Get current timezone strategy
            timezone_strategy = self.get_current_timezone_strategy()
            
            # Get REAL portfolio data using your sophisticated PortfolioRiskServiceExtended
            portfolio_result = await portfolio_risk_service.get_portfolio_status(user_id=user_id)
            emergency_level = EmergencyLevel.NORMAL
            
            if portfolio_result.get("success"):
                portfolio_data = portfolio_result.get("portfolio", {})
                
                # Enhance portfolio data with your sophisticated risk analysis
                risk_assessment = await portfolio_risk_service.risk_analysis(
                    user_id=user_id,
                    analysis_type="comprehensive"
                )
                if risk_assessment.get("success"):
                    portfolio_data["risk_metrics"] = risk_assessment.get("risk_analysis", {})
                
                # Get performance metrics using your advanced analytics
                performance_data = await portfolio_risk_service.portfolio_performance_analysis(
                    user_id=user_id,
                    timeframe="daily"
                )
                if performance_data.get("success"):
                    portfolio_data["performance_data"] = performance_data.get("performance_analysis", {})
                
                emergency_level = await self.check_emergency_conditions(portfolio_data)
                
                if emergency_level != EmergencyLevel.NORMAL:
                    self.current_mode = await self.execute_emergency_protocol(emergency_level)
            
            phases_executed.append({
                "phase": "emergency_check",
                "success": True,
                "data": {"emergency_level": emergency_level.value, "timezone_strategy": timezone_strategy},
                "execution_time_ms": (time.time() - phase_start) * 1000
            })
            
            # PHASE 1: Comprehensive Market Analysis using your sophisticated service
            phase_start = time.time()
            market_result = await market_analysis_service.complete_market_assessment(
                symbols="SMART_ADAPTIVE",
                exchanges="all", 
                user_id=user_id
            )
            
            phases_executed.append({
                "phase": "market_analysis",
                "success": market_result.get("success", False),
                "data": market_result,
                "execution_time_ms": (time.time() - phase_start) * 1000
            })
            
            if not market_result.get("success"):
                raise Exception("Market analysis failed")
            
            # PHASE 2: Generate Strategy Signals using your sophisticated strategies
            phase_start = time.time()
            
            # Get USER'S PURCHASED STRATEGIES (no hardcoded strategies!)
            if focus_strategies is None:
                from app.services.strategy_marketplace_service import strategy_marketplace_service
                
                # Get user's purchased strategy portfolio
                user_portfolio = await strategy_marketplace_service.get_user_strategy_portfolio(user_id)
                
                if user_portfolio.get("success") and user_portfolio.get("active_strategies"):
                    # Extract strategy function names from user's purchased strategies
                    focus_strategies = []
                    for strategy in user_portfolio["active_strategies"]:
                        strategy_id = strategy["strategy_id"]
                        if strategy_id.startswith("ai_"):
                            strategy_func = strategy_id.replace("ai_", "")
                            focus_strategies.append(strategy_func)
                    
                    self.logger.info(f"Using {len(focus_strategies)} purchased strategies for user {user_id}", 
                                   strategies=focus_strategies)
                else:
                    # Fallback to basic free strategies if user has no purchased strategies
                    focus_strategies = ["spot_momentum_strategy"]
                    self.logger.warning(f"User {user_id} has no purchased strategies, using free basic strategy")
            
            # ADVANCED MARKET INTELLIGENCE: Filter strategies based on real-time conditions
            market_assessment = market_result.get("market_assessment", {})
            sentiment = market_assessment.get("sentiment", "neutral")
            volatility = market_assessment.get("volatility_level", "medium")
            trend = market_assessment.get("trend", "sideways")
            
            # Get strategy performance data for intelligent selection
            strategy_performance = {}
            for strategy in focus_strategies:
                try:
                    perf_data = await trading_strategies_service._get_strategy_performance_data(
                        strategy, "1d", user_id
                    )
                    strategy_performance[strategy] = perf_data.get("avg_return", 0)
                except:
                    strategy_performance[strategy] = 0
            
            # INTELLIGENT STRATEGY SELECTION based on market conditions + performance
            optimal_strategies = []
            
            # Market condition-based filtering from user's purchased strategies
            if volatility == "low" and trend == "sideways":
                # Low volatility sideways: market making, mean reversion, grid trading
                condition_strategies = [s for s in focus_strategies 
                                      if any(t in s.lower() for t in ["market_making", "mean_reversion", "grid"])]
            elif volatility == "high" and sentiment == "bullish":
                # High volatility bull: momentum, breakout, scalping
                condition_strategies = [s for s in focus_strategies 
                                      if any(t in s.lower() for t in ["momentum", "breakout", "scalping"])]
            elif volatility == "high" and sentiment == "bearish":
                # High volatility bear: short strategies, futures, options
                condition_strategies = [s for s in focus_strategies 
                                      if any(t in s.lower() for t in ["short", "futures", "options", "mean_reversion"])]
            else:
                # Balanced conditions: use top performing strategies
                condition_strategies = focus_strategies
            
            # If no strategies match conditions, use all purchased strategies
            if not condition_strategies:
                condition_strategies = focus_strategies
            
            # ADVANCED PERFORMANCE-BASED SORTING using real-time rankings
            try:
                # Get user's strategy rankings (auto-updated from real trades)
                rankings_key = f"strategy_rankings:{user_id}"
                rankings_data = await self.redis.get(rankings_key)
                
                if rankings_data:
                    strategy_rankings = json.loads(rankings_data)
                    ranking_scores = {r["strategy"]: r["score"] for r in strategy_rankings}
                    
                    # Sort by real performance rankings
                    performance_sorted = sorted(
                        condition_strategies,
                        key=lambda s: ranking_scores.get(s, strategy_performance.get(s, 0)),
                        reverse=True
                    )
                    
                    self.logger.info(
                        f"Using real-time performance rankings for {user_id}",
                        top_performer=performance_sorted[0] if performance_sorted else "none",
                        ranking_data_available=True
                    )
                else:
                    # Fallback to basic performance data
                    performance_sorted = sorted(
                        condition_strategies,
                        key=lambda s: strategy_performance.get(s, 0),
                        reverse=True
                    )
                    
                    self.logger.info(f"Using basic performance data for {user_id} - no ranking history yet")
                    
            except Exception as e:
                self.logger.warning("Failed to use performance rankings, using basic sort", error=str(e))
                performance_sorted = sorted(
                    condition_strategies,
                    key=lambda s: strategy_performance.get(s, 0),
                    reverse=True
                )
            
            # Limit strategies based on risk mode and performance
            max_strategies = {
                "conservative": min(2, len(performance_sorted)),
                "balanced": min(4, len(performance_sorted)), 
                "aggressive": min(6, len(performance_sorted)),
                "beast_mode": len(performance_sorted)  # Use all purchased strategies
            }.get(self.current_mode.value, 4)
            
            focus_strategies = performance_sorted[:max_strategies]
            
            # Always prioritize arbitrage if available and opportunities exist
            arbitrage_opportunities = market_assessment.get("arbitrage_opportunities", 0)
            if arbitrage_opportunities > 0:
                arbitrage_strategies = [s for s in focus_strategies if "arbitrage" in s.lower()]
                if arbitrage_strategies:
                    # Move arbitrage to front
                    focus_strategies = arbitrage_strategies + [s for s in focus_strategies if s not in arbitrage_strategies]
            
            self.logger.info(
                f"🎯 INTELLIGENT STRATEGY SELECTION for {user_id}",
                market_conditions=f"{sentiment}/{volatility}/{trend}",
                total_purchased=len(user_portfolio.get("active_strategies", [])),
                selected_count=len(focus_strategies),
                selected_strategies=focus_strategies,
                arbitrage_opportunities=arbitrage_opportunities
            )
            
            # 🚀 EXECUTE ALL STRATEGIES WITH CROSS-COORDINATION
            all_signals = []
            strategy_tasks = []
            
            # Enhanced strategy execution with sentiment integration
            for strategy in focus_strategies:
                # Get sentiment-optimized symbols for this strategy
                optimal_symbols = await self._get_sentiment_optimized_symbols(strategy, sentiment_result)
                
                # Enhance market data with sentiment-optimized symbols
                enhanced_market_data = market_result.copy()
                if optimal_symbols:
                    # Add preferred symbols to market data for strategy to use
                    enhanced_market_data["preferred_symbols"] = optimal_symbols
                
                task = trading_strategies_service.generate_trading_signal(
                    strategy_type=strategy,
                    market_data=enhanced_market_data,
                    risk_mode=risk_tolerance,  # Use risk_tolerance from kwargs
                    user_id=user_id
                )
                strategy_tasks.append((strategy, task))
            
            # Execute all strategies in parallel
            strategy_results = await asyncio.gather(
                *[task for _, task in strategy_tasks], 
                return_exceptions=True
            )
            
            # Process results
            for i, result in enumerate(strategy_results):
                strategy_name = strategy_tasks[i][0]
                
                if isinstance(result, Exception):
                    self.logger.warning(f"Strategy {strategy_name} failed", error=str(result))
                    continue
                
                if result.get("success"):
                    signal_data = result.get("signal", {})
                    all_signals.append({
                        "strategy": strategy_name,
                        "signal": signal_data,
                        "confidence": signal_data.get("confidence", 0),
                        "expected_return": signal_data.get("expected_return", 0)
                    })
            
            # 🎼 COORDINATE SIGNALS TO AVOID CONFLICTS
            from app.services.cross_strategy_coordinator import cross_strategy_coordinator
            
            coordination_result = await cross_strategy_coordinator.coordinate_strategy_signals(
                all_signals, user_id
            )
            
            if coordination_result.get("success"):
                coordinated_signals = coordination_result["coordinated_signals"]
                
                # Filter for signals approved for execution
                executable_signals = [
                    s for s in coordinated_signals 
                    if s["coordination_action"] in ["execute", "modify"]
                ]
                
                # Sort by priority score (confidence + coordination adjustments)
                best_signals = sorted(executable_signals, key=lambda x: x["priority_score"], reverse=True)
                
                # Apply risk mode limits to coordinated signals
                max_signals = {
                    "conservative": 1,
                    "balanced": 2, 
                    "aggressive": 3,
                    "beast_mode": 5
                }.get(self.current_mode.value, 2)
                
                best_signals = best_signals[:max_signals]
                best_signal = best_signals[0] if best_signals else None
                
                self.logger.info(
                    f"🎼 Signal coordination complete",
                    user_id=user_id,
                    original_signals=len(all_signals),
                    coordinated_signals=len(executable_signals),
                    final_signals=len(best_signals),
                    coordination_summary=coordination_result.get("coordination_summary", {})
                )
            else:
                # Fallback to original logic if coordination fails
                best_signals = sorted(all_signals, key=lambda x: x["confidence"], reverse=True)
                max_signals = {
                    "conservative": 1,
                    "balanced": 2, 
                    "aggressive": 3,
                    "beast_mode": 5
                }.get(self.current_mode.value, 2)
                
                best_signals = best_signals[:max_signals]
                best_signal = best_signals[0] if best_signals else None
                
                self.logger.warning("Signal coordination failed, using fallback selection")
            
            phases_executed.append({
                "phase": "signal_generation",
                "success": len(all_signals) > 0,
                "data": {"signals_generated": len(all_signals), "best_signal": best_signal},
                "execution_time_ms": (time.time() - phase_start) * 1000
            })
            
            if not best_signal:
                raise Exception("No viable trading signals generated")
            
            # PHASE 3: INTELLIGENT CAPITAL ALLOCATION
            phase_start = time.time()
            
            # Enhanced opportunity data with strategy performance context
            opportunity_data = {
                "symbol": best_signal["signal"].get("symbol", "BTC"),
                "confidence": best_signal["confidence"],
                "expected_return": best_signal["signal"].get("expected_return", 5.0),
                "strategy_name": best_signal["strategy"],
                "strategy_performance": strategy_performance.get(best_signal["strategy"], 0),
                "market_conditions": {
                    "sentiment": sentiment,
                    "volatility": volatility,
                    "trend": trend
                },
                "total_signals": len(best_signals),  # For diversification calculation
                "signal_rank": 1  # This is the best signal
            }
            
            # ADVANCED POSITION SIZING with multi-signal allocation
            if len(best_signals) > 1:
                # Multi-strategy allocation: distribute capital intelligently
                total_confidence = sum(s["confidence"] for s in best_signals)
                allocation_weight = best_signal["confidence"] / total_confidence if total_confidence > 0 else 1.0
                opportunity_data["allocation_weight"] = allocation_weight
                opportunity_data["is_multi_strategy"] = True
                
                self.logger.info(
                    f"Multi-strategy allocation for {user_id}",
                    total_strategies=len(best_signals),
                    primary_weight=allocation_weight,
                    primary_strategy=best_signal["strategy"]
                )
            
            # 🛡️ DYNAMIC RISK MANAGEMENT INTEGRATION
            from app.services.dynamic_risk_management import dynamic_risk_management
            
            # Calculate dynamic risk parameters first
            dynamic_risk_result = await dynamic_risk_management.calculate_dynamic_risk_parameters(
                symbol=best_signal["signal"].get("symbol", "BTC"),
                entry_price=best_signal["signal"].get("entry_price", 0),
                position_side="buy",  # Assuming long positions for now
                risk_mode=self.current_mode.value,
                user_id=user_id
            )
            
            # Enhance opportunity data with dynamic risk parameters
            if dynamic_risk_result.get("success"):
                risk_params = dynamic_risk_result["risk_parameters"]
                opportunity_data.update({
                    "dynamic_stop_loss": risk_params["volatility_adjusted_stop"],
                    "dynamic_profit_target": risk_params["volatility_adjusted_target"],
                    "position_size_multiplier": risk_params["position_size_multiplier"],
                    "market_volatility": dynamic_risk_result["market_volatility"]
                })
            
            # Use your sophisticated PortfolioRiskServiceExtended with enhanced data
            sizing_result = await portfolio_risk_service.position_sizing(
                opportunity=json.dumps(opportunity_data),
                user_id=user_id,
                mode=self.current_mode.value
            )
            
            phases_executed.append({
                "phase": "position_sizing",
                "success": sizing_result.get("success", False),
                "data": sizing_result,
                "execution_time_ms": (time.time() - phase_start) * 1000
            })
            
            if not sizing_result.get("success"):
                raise Exception("Position sizing failed")
            
            # PHASE 4: AI Validation
            phase_start = time.time()
            
            # Prepare validation request
            validation_data = {
                "signal": best_signal["signal"],
                "position_sizing": sizing_result.get("position_sizing", {}),
                "market_context": market_result
            }
            
            mode_config = self.mode_configs[self.current_mode]
            
            # Use your sophisticated AI consensus service for validation
            validation_result = await ai_consensus_service.validate_trade(
                analysis_request=json.dumps(validation_data),
                confidence_threshold=mode_config.validation_threshold,
                ai_models="all",  # Use all AI models for maximum consensus
                user_id=user_id
            )
            
            phases_executed.append({
                "phase": "ai_validation",
                "success": validation_result.get("success", False),
                "data": validation_result,
                "execution_time_ms": (time.time() - phase_start) * 1000
            })
            
            # PHASE 5: Execution (if validated)
            if (validation_result.get("success") and 
                validation_result.get("trade_validation", {}).get("approval_status") == "APPROVED"):
                
                phase_start = time.time()
                
                # Execute the REAL trade with comprehensive validation
                signal_data = best_signal["signal"]
                sizing_data = sizing_result.get("position_sizing", {})
                
                # COMPREHENSIVE PRE-TRADE VALIDATION
                trade_validation = await self.validate_real_trade_execution(
                    signal_data=signal_data,
                    sizing_data=sizing_data,
                    portfolio_data=portfolio_data,
                    user_id=user_id
                )
                
                if not trade_validation.get("approved", False):
                    self.logger.error("Trade validation FAILED", 
                                    reason=trade_validation.get("reason"),
                                    checks=trade_validation.get("checks"))
                    raise Exception(f"Trade validation failed: {trade_validation.get('reason')}")
                
                # Use validated position size
                final_position_size = trade_validation.get("final_position_size")
                final_position_value = trade_validation.get("final_position_value")
                
                # Log validation success with any adjustments
                if trade_validation.get("adjustments"):
                    self.logger.info("Trade validation PASSED with adjustments", 
                                   adjustments=trade_validation.get("adjustments"))
                else:
                    self.logger.info("Trade validation PASSED - no adjustments needed")
                
                # Execute REAL trade with validated parameters
                execution_result = await trade_execution_service.execute_real_trade(
                    symbol=signal_data.get("symbol", "BTC"),
                    side=signal_data.get("action", "buy").lower(),
                    quantity=final_position_size,  # Use VALIDATED position size
                    order_type="market",
                    exchange="binance",
                    user_id=user_id
                )
                
                if execution_result.get("success"):
                    trades_executed = 1
                    # Calculate REAL profit from execution data
                    executed_price = execution_result.get("execution_price", 0)
                    executed_quantity = execution_result.get("executed_quantity", 0)
                    expected_price = signal_data.get("entry_price", executed_price)
                    
                    # Real profit calculation based on actual execution vs expected
                    if signal_data.get("action", "buy").lower() == "buy":
                        price_improvement = (executed_price - expected_price) / expected_price if expected_price > 0 else 0
                    else:
                        price_improvement = (expected_price - executed_price) / expected_price if expected_price > 0 else 0
                    
                    profit_generated = executed_quantity * executed_price * price_improvement
                    
                    # Add expected profit from signal if position is held
                    expected_return_pct = signal_data.get("expected_return", 0) / 100
                    potential_profit = executed_quantity * executed_price * expected_return_pct
                    
                    # REAL-TIME STRATEGY PERFORMANCE TRACKING
                    await self._update_strategy_performance_metrics(
                        user_id=user_id,
                        strategy_name=best_signal["strategy"],
                        trade_result={
                            "success": True,
                            "profit_usd": profit_generated + potential_profit,
                            "execution_price": executed_price,
                            "expected_price": expected_price,
                            "confidence": best_signal["confidence"],
                            "symbol": signal_data.get("symbol"),
                            "timestamp": datetime.utcnow()
                        }
                    )
                    
                    # Log real execution details
                    self.logger.info("REAL TRADE EXECUTED", 
                                   symbol=signal_data.get("symbol"),
                                   action=signal_data.get("action"),
                                   quantity=executed_quantity,
                                   price=executed_price,
                                   immediate_profit=profit_generated,
                                   potential_profit=potential_profit,
                                   strategy=best_signal["strategy"])
                
                phases_executed.append({
                    "phase": "trade_execution", 
                    "success": execution_result.get("success", False),
                    "data": execution_result,
                    "execution_time_ms": (time.time() - phase_start) * 1000
                })
            
            return {
                "success": True,
                "cycle_type": cycle_type.value,
                "trading_mode": self.current_mode.value,
                "phases_executed": phases_executed,
                "total_execution_time_ms": (time.time() - start_time) * 1000,
                "trades_executed": trades_executed,
                "profit_generated_usd": profit_generated,
                "emergency_level": emergency_level.value,
                "timezone_strategy": timezone_strategy
            }
            
        except Exception as e:
            self.logger.error("5-phase flow failed", error=str(e), cycle=cycle_type.value)
            return {
                "success": False,
                "cycle_type": cycle_type.value,
                "trading_mode": self.current_mode.value,
                "phases_executed": phases_executed,
                "total_execution_time_ms": (time.time() - start_time) * 1000,
                "trades_executed": trades_executed,
                "profit_generated_usd": profit_generated,
                "emergency_level": EmergencyLevel.WARNING.value,
                "error": str(e)
            }
    
    async def execute_arbitrage_cycle(self, user_id: str = "system") -> Dict[str, Any]:
        """
        EXECUTE MULTI-EXCHANGE ARBITRAGE COORDINATION CYCLE
        
        Coordinates arbitrage across ALL user's connected exchanges simultaneously
        for maximum profit extraction!
        """
        
        start_time = time.time()
        
        try:
            from app.services.market_analysis_core import MarketAnalysisService
            from app.services.trade_execution import TradeExecutionService
            from app.services.telegram_core import TelegramService
            # Initialize services
            market_service = MarketAnalysisService()
            trade_service = TradeExecutionService()
            telegram_service = TelegramService()
            
            # Get user's connected exchanges for coordinated arbitrage
            from app.core.database import get_async_session
            from app.models.exchange import ExchangeAccount
            from sqlalchemy import select
            
            async with get_async_session() as db:
                # Get user's exchange accounts
                result = await db.execute(
                    select(ExchangeAccount).where(
                        ExchangeAccount.user_id == user_id,
                        ExchangeAccount.is_active == True
                    )
                )
                exchange_accounts = result.scalars().all()
                
                user_exchanges = {
                    "success": True,
                    "accounts": [
                        {"exchange": acc.exchange, "is_active": acc.is_active}
                        for acc in exchange_accounts
                    ]
                }
            
            if not user_exchanges.get("success") or len(user_exchanges.get("accounts", [])) < 2:
                return {
                    "success": False,
                    "reason": "Multi-exchange arbitrage requires at least 2 connected exchanges",
                    "user_exchanges": len(user_exchanges.get("accounts", [])),
                    "cycle_type": TradingCycle.ARBITRAGE_HUNTER.value
                }
            
            connected_exchanges = [acc["exchange"] for acc in user_exchanges["accounts"]]
            
            self.logger.info(
                f"🔄 Multi-exchange arbitrage scan starting",
                user_id=user_id,
                connected_exchanges=connected_exchanges
            )
            
            # Enhanced arbitrage scanning across user's specific exchanges
            arbitrage_result = await market_service.cross_exchange_arbitrage_scanner(
                symbols="SMART_ADAPTIVE",  # Dynamic symbol selection
                exchanges=connected_exchanges,  # Only user's exchanges
                min_profit_bps=3,  # More aggressive (0.03% minimum)
                user_id=user_id
            )
            
            trades_executed = 0
            profit_generated = 0.0
            coordinated_executions = []
            
            # 🚀 COORDINATED MULTI-EXCHANGE EXECUTION
            if arbitrage_result.get("success") and arbitrage_result.get("opportunities"):
                opportunities = arbitrage_result.get("opportunities", [])
                
                # Group opportunities by symbol for coordinated execution
                symbol_opportunities = {}
                for opp in opportunities:
                    symbol = opp.get("symbol", "BTC")
                    if symbol not in symbol_opportunities:
                        symbol_opportunities[symbol] = []
                    symbol_opportunities[symbol].append(opp)
                
                # Execute coordinated arbitrage for each symbol
                for symbol, symbol_ops in symbol_opportunities.items():
                    if len(symbol_ops) < 2:  # Need at least 2 exchanges for arbitrage
                        continue
                    
                    # Sort by profit potential
                    symbol_ops.sort(key=lambda x: x.get("profit_percentage", 0), reverse=True)
                    best_opportunity = symbol_ops[0]
                    
                    if best_opportunity.get("profit_percentage", 0) > 0.03:  # Min 0.03% profit
                        
                        # 🎯 COORDINATED EXECUTION: Buy on cheap exchange, sell on expensive exchange
                        buy_exchange = best_opportunity.get("buy_exchange")
                        sell_exchange = best_opportunity.get("sell_exchange")
                        optimal_quantity = best_opportunity.get("optimal_quantity", 0.01)
                        
                        # Execute buy and sell simultaneously
                        buy_task = trade_service.execute_real_trade(
                            symbol=symbol,
                            side="buy",
                            quantity=optimal_quantity,
                            order_type="market",
                            exchange=buy_exchange,
                            user_id=user_id
                        )
                        
                        sell_task = trade_service.execute_real_trade(
                            symbol=symbol,
                            side="sell", 
                            quantity=optimal_quantity,
                            order_type="market",
                            exchange=sell_exchange,
                            user_id=user_id
                        )
                        
                        # Execute both legs simultaneously
                        buy_result, sell_result = await asyncio.gather(
                            buy_task, sell_task, return_exceptions=True
                        )
                        
                        # Process coordinated execution results
                        if (not isinstance(buy_result, Exception) and buy_result.get("success") and
                            not isinstance(sell_result, Exception) and sell_result.get("success")):
                            
                            trades_executed += 2  # Both legs
                            
                            # Calculate REAL coordinated arbitrage profit
                            buy_price = buy_result.get("execution_price", 0)
                            sell_price = sell_result.get("execution_price", 0)
                            executed_qty = min(
                                buy_result.get("executed_quantity", 0),
                                sell_result.get("executed_quantity", 0)
                            )
                            
                            # Net arbitrage profit
                            gross_profit = (sell_price - buy_price) * executed_qty
                            total_fees = (buy_result.get("fees_paid_usd", 0) + 
                                        sell_result.get("fees_paid_usd", 0))
                            net_arbitrage_profit = gross_profit - total_fees
                            
                            profit_generated += net_arbitrage_profit
                            
                            coordinated_executions.append({
                                "symbol": symbol,
                                "buy_exchange": buy_exchange,
                                "sell_exchange": sell_exchange,
                                "buy_price": buy_price,
                                "sell_price": sell_price,
                                "quantity": executed_qty,
                                "gross_profit": gross_profit,
                                "fees": total_fees,
                                "net_profit": net_arbitrage_profit,
                                "profit_percentage": (net_arbitrage_profit / (buy_price * executed_qty)) * 100
                            })
                            
                            self.logger.info(
                                "🎯 COORDINATED ARBITRAGE SUCCESS",
                                symbol=symbol,
                                buy_exchange=buy_exchange,
                                sell_exchange=sell_exchange,
                                net_profit=f"${net_arbitrage_profit:.4f}",
                                profit_pct=f"{((net_arbitrage_profit / (buy_price * executed_qty)) * 100):.3f}%"
                            )
                        else:
                            self.logger.warning(
                                "Coordinated arbitrage failed",
                                symbol=symbol,
                                buy_success=buy_result.get("success") if not isinstance(buy_result, Exception) else False,
                                sell_success=sell_result.get("success") if not isinstance(sell_result, Exception) else False
                            )
            
            # Enhanced notification with coordination details
            if trades_executed > 0:
                # Get owner chat ID and send directly
                from app.services.telegram_core import telegram_service
                from app.services.telegram_commander import RecipientType
                owner_chat_id = await telegram_service._get_chat_id_for_recipient(RecipientType.OWNER)
                if owner_chat_id:
                    await telegram_service.send_direct_message(
                        chat_id=owner_chat_id,
                        message_content=f"🚀 Multi-Exchange Arbitrage: {len(coordinated_executions)} coordinated trades, ${profit_generated:.4f} profit across {len(connected_exchanges)} exchanges",
                        message_type="trade",
                        priority="normal"
                    )
            
            return {
                "success": True,
                "cycle_type": TradingCycle.ARBITRAGE_HUNTER.value,
                "trading_mode": self.current_mode.value,
                "total_execution_time_ms": (time.time() - start_time) * 1000,
                "trades_executed": trades_executed,
                "profit_generated_usd": profit_generated,
                "opportunities_found": len(arbitrage_result.get("opportunities", [])),
                "coordinated_executions": coordinated_executions,
                "connected_exchanges": connected_exchanges,
                "emergency_level": EmergencyLevel.NORMAL.value
            }
            
        except Exception as e:
            self.logger.error("Multi-exchange arbitrage cycle failed", error=str(e))
            return {
                "success": False,
                "cycle_type": TradingCycle.ARBITRAGE_HUNTER.value,
                "error": str(e),
                "total_execution_time_ms": (time.time() - start_time) * 1000,
                "trades_executed": 0,
                "profit_generated_usd": 0.0
            }
    
    async def update_real_performance_metrics(
        self,
        cycle_result: Dict[str, Any],
        execution_results: List[Dict[str, Any]] = None
    ) -> None:
        """Update performance metrics with real trading data."""
        
        try:
            # Update basic counters
            self.performance_metrics["cycles_executed"] += 1
            self.performance_metrics["trades_executed"] += cycle_result.get("trades_executed", 0)
            
            # Calculate real profit from execution results
            real_profit = 0.0
            if execution_results:
                for exec_result in execution_results:
                    if exec_result.get("success"):
                        # Extract real profit data
                        real_profit += exec_result.get("realized_pnl_usd", 0)
                        real_profit += exec_result.get("unrealized_pnl_usd", 0) * 0.5  # Weight unrealized lower
            
            # Use cycle-reported profit if no detailed execution data
            if real_profit == 0:
                real_profit = cycle_result.get("profit_generated_usd", 0)
            
            self.performance_metrics["total_profit_usd"] += real_profit
            
            # Update success rate using weighted recent performance
            cycle_success = cycle_result.get("success", False)
            recent_cycles = min(self.performance_metrics["cycles_executed"], 100)  # Last 100 cycles
            current_success_rate = self.performance_metrics["success_rate"]
            
            # Weighted moving average (recent cycles weighted more heavily)
            if recent_cycles > 0:
                weight = 1.0 / recent_cycles
                new_success_value = 1.0 if cycle_success else 0.0
                self.performance_metrics["success_rate"] = (current_success_rate * (1 - weight)) + (new_success_value * weight)
            
            # Track consecutive performance
            if cycle_success and cycle_result.get("trades_executed", 0) > 0:
                if real_profit > 0:
                    self.performance_metrics["consecutive_wins"] = self.performance_metrics.get("consecutive_wins", 0) + 1
                    self.performance_metrics["consecutive_losses"] = 0
                else:
                    self.performance_metrics["consecutive_losses"] = self.performance_metrics.get("consecutive_losses", 0) + 1
                    self.performance_metrics["consecutive_wins"] = 0
            
            # Update uptime
            uptime_hours = (datetime.utcnow() - self.start_time).total_seconds() / 3600
            self.performance_metrics["uptime_hours"] = uptime_hours
            
            # Log performance update
            self.logger.info("Performance metrics updated",
                           cycle_profit=real_profit,
                           total_profit=self.performance_metrics["total_profit_usd"],
                           success_rate=f"{self.performance_metrics['success_rate']:.2%}",
                           cycles_executed=self.performance_metrics["cycles_executed"])
            
            # Broadcast update to user
            user_id = cycle_result.get("user_id")
            if user_id:
                status_update = await self.get_system_status(user_id)
                await manager.broadcast(status_update, user_id)
            
        except Exception as e:
            self.logger.error("Failed to update performance metrics", error=str(e))
    
    # Service management functions
    
    async def system_health(self) -> Dict[str, Any]:
        """Comprehensive system health check."""
        
        try:
            # Use your existing service instances (no duplication)
            from app.services.market_analysis import market_analysis_service
            from app.services.trading_strategies import trading_strategies_service
            from app.services.portfolio_risk_core import PortfolioRiskServiceExtended
            from app.services.ai_consensus_core import ai_consensus_service
            from app.services.trade_execution import TradeExecutionService
            from app.services.telegram_core import TelegramService
            
            # Initialize only if needed (some are already global instances)
            portfolio_risk_service = PortfolioRiskServiceExtended()
            trade_execution_service = TradeExecutionService()
            telegram_service = TelegramService()
            
            # Check all services in parallel
            health_checks = await asyncio.gather(
                market_analysis_service.health_check(),
                trading_strategies_service.health_check(),
                portfolio_risk_service.health_check(),
                ai_consensus_service.health_check(),
                trade_execution_service.health_check(),
                telegram_commander_service.health_check(),
                return_exceptions=True
            )
            
            service_names = ["market_analysis", "trading_strategies", "portfolio_risk", "ai_consensus", "trade_execution", "telegram_commander"]
            service_status = {}
            healthy_count = 0
            
            for i, result in enumerate(health_checks):
                service_name = service_names[i]
                if isinstance(result, Exception):
                    service_status[service_name] = {"status": "ERROR", "error": str(result)}
                elif result and (result.get("healthy") or result.get("status") == "HEALTHY"):
                    service_status[service_name] = {"status": "HEALTHY", "details": result}
                    healthy_count += 1
                else:
                    service_status[service_name] = {"status": "DEGRADED", "details": result}
            
            # Calculate overall health score
            health_score = (healthy_count / len(service_names)) * 100
            
            overall_status = "HEALTHY" if health_score > 80 else "DEGRADED" if health_score > 60 else "CRITICAL"
            
            return {
                "success": True,
                "overall_status": overall_status,
                "health_score": round(health_score, 1),
                "services": service_status,
                "autonomous_active": self.is_active,
                "current_mode": self.current_mode.value,
                "uptime_hours": self.performance_metrics["uptime_hours"],
                "cycles_executed": self.performance_metrics["cycles_executed"],
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error("System health check failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "overall_status": "CRITICAL",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def start_autonomous_mode(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Start autonomous trading mode for a user."""
        user_id = config.get("user_id")
        mode = config.get("mode", "balanced")
        
        self.logger.info(f"🤖 Starting autonomous mode for user {user_id}", mode=mode)
        
        try:
            # Generate session ID
            session_id = f"auto_{user_id}_{int(time.time())}"
            
            # Store user config
            await self.redis.hset(
                f"autonomous_config:{user_id}",
                mapping={
                    "session_id": session_id,
                    "mode": mode,
                    "started_at": datetime.utcnow().isoformat(),
                    "max_daily_loss_pct": config.get("max_daily_loss_pct", 5.0),
                    "max_position_size_pct": config.get("max_position_size_pct", 10.0),
                    "allowed_symbols": json.dumps(config.get("allowed_symbols", ["BTC", "ETH", "SOL"])),
                    "excluded_symbols": json.dumps(config.get("excluded_symbols", [])),
                    "trading_hours": json.dumps(config.get("trading_hours", {"start": "00:00", "end": "23:59"}))
                }
            )
            
            # Mark as active
            await self.redis.set(f"autonomous_active:{user_id}", "true", ex=86400)
            
            # Estimate trades based on mode
            trade_estimates = {
                "conservative": 5,
                "balanced": 10,
                "aggressive": 20,
                "beast_mode": 50
            }
            
            return {
                "success": True,
                "session_id": session_id,
                "estimated_trades": trade_estimates.get(mode, 10),
                "message": f"Autonomous trading started in {mode} mode"
            }
            
        except Exception as e:
            self.logger.error("Failed to start autonomous mode", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def stop_autonomous_mode(self, user_id: str) -> Dict[str, Any]:
        """Stop autonomous trading mode for a user."""
        self.logger.info(f"🛑 Stopping autonomous mode for user {user_id}")
        
        try:
            # Get current config
            config = await self.redis.hgetall(f"autonomous_config:{user_id}") if self.redis else {}
            
            if config:
                session_duration = 0
                if config.get("started_at"):
                    start_time = datetime.fromisoformat(config["started_at"])
                    session_duration = (datetime.utcnow() - start_time).total_seconds()
                
                # Remove autonomous state
                await self.redis.delete(f"autonomous_config:{user_id}")
                await self.redis.delete(f"autonomous_active:{user_id}")
                
                # Get trading stats (mock for now)
                trades_executed = 0
                total_pnl = 0.0
                
                return {
                    "success": True,
                    "session_duration": session_duration,
                    "trades_executed": trades_executed,
                    "total_pnl": total_pnl,
                    "message": "Autonomous trading stopped successfully"
                }
            else:
                return {
                    "success": True,
                    "message": "No active autonomous session found"
                }
                
        except Exception as e:
            self.logger.error("Failed to stop autonomous mode", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def get_system_status(self, user_id: str) -> Dict[str, Any]:
        """Get system status for a specific user."""
        try:
            # ENTERPRISE REDIS RESILIENCE
            redis_client = await self._ensure_redis()
            if not redis_client:
                # Graceful degradation when Redis is unavailable
                return {
                    "success": True,
                    "user_id": user_id,
                    "mode": "standalone",
                    "autonomous_active": False,
                    "system_health": "unknown",
                    "timestamp": datetime.utcnow().isoformat(),
                    "warning": "Operating in degraded mode (Redis unavailable)"
                }
            
            # Check if autonomous mode is active
            autonomous_active = await redis_client.get(f"autonomous_active:{user_id}")
            autonomous_config = await redis_client.hgetall(f"autonomous_config:{user_id}") if autonomous_active else {}
            
            # Get system health
            system_health = await redis_client.get("system_health")
            health_status = "normal"
            if system_health:
                try:
                    import json
                    # Decode bytes if necessary
                    if isinstance(system_health, bytes):
                        system_health = system_health.decode('utf-8')
                    # Only parse if it's not empty
                    if system_health and system_health.strip():
                        health_data = json.loads(system_health)
                        health_status = "warning" if health_data.get("alerts") else "normal"
                    else:
                        health_status = "normal"
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    logger.debug(f"System health data not in JSON format: {e}")
                    health_status = "normal"  # Default to normal if no data
            
            # Mock performance data (would be real in production)
            performance_today = {
                "trades": 5,
                "profit_loss": 125.50,
                "win_rate": 80.0,
                "best_trade": 45.30,
                "worst_trade": -12.10
            }
            
            # Get active strategies
            active_strategies = ["spot_momentum_strategy", "arbitrage_hunter"]
            if autonomous_config.get("mode") == "aggressive":
                active_strategies.append("high_frequency_scalping")
            
            # Calculate next action ETA (mock)
            next_action_eta = 300  # 5 minutes
            
            return {
                "autonomous_mode": bool(autonomous_active),
                "simulation_mode": True,  # Would check user setting
                "trading_mode": autonomous_config.get("mode", "balanced"),
                "health": health_status,
                "active_strategies": active_strategies,
                "performance_today": performance_today,
                "risk_level": health_status,
                "next_action_eta": next_action_eta,
                "session_id": autonomous_config.get("session_id"),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error("Failed to get system status", error=str(e))
            return {
                "autonomous_mode": False,
                "simulation_mode": True,
                "trading_mode": "balanced",
                "health": "error",
                "active_strategies": [],
                "performance_today": {},
                "risk_level": "error",
                "next_action_eta": None,
                "error": str(e)
            }
    
    async def get_global_system_status(self) -> Dict[str, Any]:
        """Get global system status for admin."""
        try:
            # Count active autonomous sessions
            autonomous_keys = await self.redis.keys("autonomous_active:*")
            active_sessions = len(autonomous_keys)
            
            # Get system health
            system_health = await self.redis.get("system_health")
            health_status = "normal"
            error_rate = 0.0
            
            if system_health:
                try:
                    import json
                    # Decode bytes if necessary
                    if isinstance(system_health, bytes):
                        system_health = system_health.decode('utf-8')
                    # Only parse if it's not empty
                    if system_health and system_health.strip():
                        health_data = json.loads(system_health)
                        health_status = "warning" if health_data.get("alerts") else "normal"
                    else:
                        health_status = "normal"
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    logger.debug(f"System health data not in JSON format: {e}")
                    health_status = "normal"  # Default to normal if no data
            
            # Mock system metrics (would be real)
            return {
                "health": health_status,
                "active_autonomous_sessions": active_sessions,
                "uptime_hours": 24.5,
                "error_rate_percent": error_rate,
                "avg_response_time_ms": 150,
                "uptime_percentage": 99.9,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error("Failed to get global system status", error=str(e))
            return {
                "health": "error",
                "active_autonomous_sessions": 0,
                "error": str(e)
            }
    
    async def emergency_stop(self, user_id: str) -> Dict[str, Any]:
        """Execute emergency stop for specific user."""
        self.logger.critical(f"🚨 EMERGENCY STOP for user {user_id}")
        
        try:
            # Stop autonomous mode
            await self.stop_autonomous_mode(user_id)
            
            # Mark emergency state
            await self.redis.set(f"emergency_stop:{user_id}", "true", ex=3600)
            
            return {
                "success": True,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Emergency stop executed successfully"
            }
            
        except Exception as e:
            self.logger.error("Emergency stop failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def emergency_stop_all_users(self) -> Dict[str, Any]:
        """Execute emergency stop for all users."""
        self.logger.critical("🚨 PLATFORM-WIDE EMERGENCY STOP")
        
        try:
            # Get all active autonomous sessions
            autonomous_keys = await self.redis.keys("autonomous_active:*")
            affected_users = []
            stopped_sessions = 0
            
            for key in autonomous_keys:
                user_id = key.decode().split(":")[-1]
                result = await self.emergency_stop(user_id)
                if result.get("success"):
                    affected_users.append(user_id)
                    stopped_sessions += 1
            
            # Set global emergency state
            await self.redis.set("global_emergency_stop", "true", ex=3600)
            
            return {
                "success": True,
                "affected_users": len(affected_users),
                "stopped_sessions": stopped_sessions,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error("Global emergency stop failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def configure_service_interval(self, service: str, interval: int) -> bool:
        """Configure service interval."""
        try:
            await self.redis.hset("service_intervals", service, interval)
            self.logger.info(f"Service interval configured: {service} = {interval}s")
            return True
        except Exception as e:
            self.logger.error("Failed to configure service interval", error=str(e))
            return False
    
    async def set_maintenance_mode(self, enabled: bool) -> bool:
        """Set maintenance mode."""
        try:
            if enabled:
                await self.redis.set("maintenance_mode", "true")
                self.logger.warning("🔧 Maintenance mode ENABLED")
            else:
                await self.redis.delete("maintenance_mode")
                self.logger.info("✅ Maintenance mode DISABLED")
            return True
        except Exception as e:
            self.logger.error("Failed to set maintenance mode", error=str(e))
            return False
    
    async def run_global_autonomous_cycle(self):
        """Run autonomous trading cycle for all active users."""
        try:
            # ENTERPRISE REDIS RESILIENCE
            redis_client = await self._ensure_redis()
            if not redis_client:
                self.logger.warning("Global autonomous cycle skipped - Redis unavailable")
                return
            
            # Get all active autonomous sessions
            autonomous_keys = await redis_client.keys("autonomous_active:*")
            
            self.logger.info(f"🤖 Running autonomous cycle for {len(autonomous_keys)} users")
            
            # PERFORMANCE OPTIMIZATION: Skip expensive operations if no users are active
            if len(autonomous_keys) == 0:
                self.logger.debug("No active autonomous users - skipping cycle")
                return
            
            for key in autonomous_keys:
                user_id = key.decode().split(":")[-1]
                
                # Check if emergency stop is active
                emergency = await self.redis.get(f"emergency_stop:{user_id}")
                if emergency:
                    continue
                
                # Get user config
                config = await self.redis.hgetall(f"autonomous_config:{user_id}") if self.redis else {}
                if not config:
                    continue
            
                # Enhanced: Check profit potential and exchange connections before trading
                from app.services.portfolio_risk_core import PortfolioRiskServiceExtended
                from app.services.profit_sharing_service import profit_sharing_service
                
                # Check if user has remaining profit potential
                profit_status = await profit_sharing_service.calculate_profit_potential_usage(
                    user_id=user_id,
                    period_start=datetime.utcnow() - timedelta(days=365),
                    period_end=datetime.utcnow()
                )
                
                if not profit_status.get("success") or profit_status.get("needs_more_credits", False):
                    self.logger.info(f"Skipping cycle for user {user_id} - profit potential exhausted")
                    # Send notification that user needs to buy more credits
                    await self._notify_user_needs_credits(user_id, profit_status)
                    continue
                
                # Check portfolio status
                portfolio_service = PortfolioRiskServiceExtended()
                portfolio_status = await portfolio_service.get_portfolio_status(user_id)
                if not portfolio_status.get("success"):
                    self.logger.warning(f"Skipping cycle for user {user_id} - portfolio unavailable")
                    continue
                
                portfolio_data = portfolio_status.get("portfolio", {})
                if portfolio_data.get("total_value_usd", 0) < 100:  # Minimum $100 to trade
                    self.logger.debug(f"Skipping cycle for user {user_id} - insufficient balance")
                    continue
                
                # Run enhanced trading cycle for this user
                await self._run_user_autonomous_cycle(user_id, config)
                
        except Exception as e:
            self.logger.error("Global autonomous cycle failed", error=str(e))
    
    async def _run_user_autonomous_cycle(self, user_id: str, config: Dict):
        """
        ENTERPRISE AUTONOMOUS CYCLE - USES 5-PHASE PIPELINE
        
        This is the CORE autonomous trading cycle that executes the 5-phase pipeline
        every 60 seconds for maximum profit optimization.
        """
        try:
            mode = config.get("mode", "balanced")
            self.logger.info(f"🤖 ENTERPRISE Autonomous Cycle Starting", 
                           user_id=user_id, mode=mode)
            
            # Set trading mode for this user
            self.current_mode = TradingMode(mode)
            
            # ENTERPRISE: Execute 5-Phase Pipeline for autonomous trading
            pipeline_result = await self.execute_5_phase_autonomous_cycle(
                user_id=user_id,
                source="autonomous",
                symbols=None,  # Uses dynamic discovery
                risk_tolerance=config.get("risk_tolerance", "balanced")  # Pass risk tolerance from config
            )
            
            # Log pipeline execution results
            if pipeline_result.get("success"):
                completed_phases = pipeline_result.get("phases_completed", "0/5")
                execution_time = pipeline_result.get("execution_time_ms", 0)
                
                self.logger.info("✅ ENTERPRISE Autonomous Pipeline Completed",
                               user_id=user_id,
                               phases_completed=completed_phases,
                               execution_time_ms=execution_time)
                
                # Update performance metrics
                self.performance_metrics["cycles_executed"] += 1
                self.performance_metrics["avg_cycle_time_ms"] = (
                    (self.performance_metrics.get("avg_cycle_time_ms", 0) + execution_time) / 
                    max(self.performance_metrics["cycles_executed"], 1)
                )
                
                # Check if any trades were executed
                phase_5 = pipeline_result.get("phases", {}).get("phase_5", {})
                if phase_5.get("status") == "completed" and phase_5.get("trade_executed"):
                    self.performance_metrics["successful_trades"] += 1
                    self.logger.info("💰 Autonomous Trade Executed", 
                                   user_id=user_id,
                                   symbol=pipeline_result.get("phases", {}).get("phase_2", {}).get("symbol"),
                                   action=pipeline_result.get("phases", {}).get("phase_2", {}).get("action"))
                
            else:
                self.logger.warning("⚠️ ENTERPRISE Autonomous Pipeline Failed",
                                  user_id=user_id,
                                  error=pipeline_result.get("error", "Unknown"),
                                  phases=pipeline_result.get("phases", {}))
                                  
            return pipeline_result
            
        except Exception as e:
            self.logger.error("💥 ENTERPRISE Autonomous Cycle Failed", 
                            user_id=user_id, 
                            error=str(e))
            return {"success": False, "error": str(e)}
    
            
            # Get USER'S PURCHASED STRATEGIES for autonomous trading
            from app.services.strategy_marketplace_service import strategy_marketplace_service
            
            user_portfolio = await strategy_marketplace_service.get_user_strategy_portfolio(user_id)
            
            if user_portfolio.get("success") and user_portfolio.get("active_strategies"):
                # Use user's purchased strategies
                preferred_strategies = []
                for strategy in user_portfolio["active_strategies"]:
                    strategy_id = strategy["strategy_id"]
                    if strategy_id.startswith("ai_"):
                        strategy_func = strategy_id.replace("ai_", "")
                        preferred_strategies.append(strategy_func)
                
                self.logger.info(f"Autonomous using {len(preferred_strategies)} purchased strategies", 
                               user_id=user_id, strategies=preferred_strategies)
            else:
                # Fallback to free basic strategy
                preferred_strategies = ["spot_momentum_strategy"]
                self.logger.warning(f"User {user_id} autonomous mode using free strategy - no purchased strategies")
            
            # 🚀 PURE MARKET-CONDITION-BASED CYCLE SELECTION (NO TIME LIMITS!)
            # Get comprehensive market intelligence
            market_conditions = await self._assess_current_market_conditions(user_id)
            
            # Get predictive intelligence for optimal timing
            from app.services.predictive_market_intelligence import predictive_intelligence
            prediction_result = await predictive_intelligence.should_trade_now(user_id)
            
            # Get real-time sentiment analysis
            from app.services.realtime_sentiment_engine import realtime_sentiment_engine
            sentiment_result = await realtime_sentiment_engine.get_sentiment_for_strategy_optimization(
                symbols=["BTC", "ETH", "SOL", "BNB"], 
                user_id=user_id
            )
            
            # INTELLIGENT CYCLE SELECTION based on MARKET CONDITIONS ONLY
            available_cycles = [
                TradingCycle.ARBITRAGE_HUNTER.value,
                TradingCycle.MOMENTUM_FUTURES.value,
                TradingCycle.PORTFOLIO_OPTIMIZATION.value,
                TradingCycle.DEEP_ANALYSIS.value
            ]
            
            selected_cycles = await self._select_cycles_by_market_intelligence(
                available_cycles,
                market_conditions,
                prediction_result,
                sentiment_result,
                config.get("intensity", "balanced")
            )
            
            self.logger.info(
                f"🎯 Selected {len(selected_cycles)} of {len(active_cycles)} cycles",
                selected=selected_cycles,
                market_conditions=market_conditions.get("summary", "unknown")
            )
            
            # Execute selected cycles
            cycle_results = []
            total_profit = 0.0
            total_trades = 0
            
            for cycle in selected_cycles:
                try:
                    if cycle == TradingCycle.ARBITRAGE_HUNTER.value:
                        # Fast arbitrage execution using your cross_exchange_arbitrage_scanner
                        result = await self.execute_arbitrage_cycle(user_id)
                    else:
                        # Full 5-phase execution using your sophisticated services
                        cycle_enum = TradingCycle(cycle)
                        result = await self.execute_5_phase_flow(
                            cycle_type=cycle_enum,
                            focus_strategies=preferred_strategies,
                            user_id=user_id,
                            risk_tolerance=config.get("risk_tolerance", "balanced")  # Pass risk tolerance from config
                        )
                    
                    cycle_results.append(result)
                    
                    if result.get("success"):
                        total_trades += result.get("trades_executed", 0)
                        total_profit += result.get("profit_generated_usd", 0.0)
                        
                        self.logger.info(
                            f"✅ CYCLE COMPLETED: {cycle}",
                            user_id=user_id,
                            trades=result.get("trades_executed", 0),
                            profit=result.get("profit_generated_usd", 0.0)
                        )
                    else:
                        self.logger.warning(
                            f"⚠️ CYCLE FAILED: {cycle}",
                            user_id=user_id,
                            error=result.get("error")
                        )
                        
                except Exception as e:
                    self.logger.error(f"Cycle {cycle} failed for user {user_id}", error=str(e))
                    continue
            
            # Update performance metrics
            self.performance_metrics["cycles_executed"] += len(cycle_results)
            self.performance_metrics["trades_executed"] += total_trades
            self.performance_metrics["total_profit_usd"] += total_profit
            
            if total_trades > 0:
                if total_profit > 0:
                    self.performance_metrics["consecutive_wins"] += 1
                    self.performance_metrics["consecutive_losses"] = 0
                else:
                    self.performance_metrics["consecutive_losses"] += 1
                    self.performance_metrics["consecutive_wins"] = 0
            
            # Calculate success rate
            total_cycles = self.performance_metrics["cycles_executed"]
            successful_cycles = sum(1 for result in cycle_results if result.get("success"))
            if total_cycles > 0:
                self.performance_metrics["success_rate"] = (successful_cycles / total_cycles) * 100
            
            # Send Telegram update if significant activity
            if total_trades > 0 or total_profit != 0:
                try:
                    from app.services.telegram_commander import telegram_commander_service
                    await telegram_commander_service.send_autonomous_update(
                        user_id=user_id,
                        cycles_run=len(active_cycles),
                        trades_executed=total_trades,
                        profit_generated=total_profit,
                        mode=mode
                    )
                except Exception as e:
                    self.logger.warning("Failed to send Telegram update", error=str(e))
            
            # Update last cycle time and metrics
            await self.redis.hset(
                f"autonomous_config:{user_id}",
                "last_cycle",
                datetime.utcnow().isoformat()
            )
            
            await self.redis.hset(
                f"autonomous_metrics:{user_id}",
                "total_profit_today",
                str(total_profit)
            )
            
            self.logger.info(
                f"🎉 AUTONOMOUS CYCLE COMPLETED for user {user_id}",
                cycles_run=len(active_cycles),
                trades_executed=total_trades,
                profit_generated=total_profit,
                mode=mode
            )
            
        except Exception as e:
            self.logger.error(f"User autonomous cycle failed for {user_id}", error=str(e))
    
    async def _assess_current_market_conditions(self, user_id: str) -> Dict[str, Any]:
        """Assess current market conditions using your MarketAnalysisService."""
        try:
            from app.services.market_analysis_core import MarketAnalysisService
            market_service = MarketAnalysisService()
            
            # Use your sophisticated market sentiment analysis
            sentiment_result = await market_service.market_sentiment(
                symbols="BTC,ETH,SOL,ADA",
                user_id=user_id
            )
            
            if sentiment_result.get("success"):
                sentiment_data = sentiment_result.get("sentiment_analysis", {})
                overall_sentiment = sentiment_data.get("overall_market_sentiment", "neutral")
                volatility = sentiment_data.get("market_volatility", "medium")
                
                return {
                    "summary": f"{overall_sentiment}_{volatility}",
                    "sentiment": overall_sentiment,
                    "volatility": volatility,
                    "should_trade": overall_sentiment != "extremely_bearish",
                    "preferred_strategies": self._get_strategies_for_conditions(overall_sentiment, volatility)
                }
            
            # Fallback to neutral conditions
            return {
                "summary": "neutral_medium",
                "sentiment": "neutral", 
                "volatility": "medium",
                "should_trade": True,
                "preferred_strategies": ["spot_momentum_strategy"]
            }
            
        except Exception as e:
            self.logger.error("Market conditions assessment failed", error=str(e))
            return {"summary": "unknown", "should_trade": False}
    
    def _select_optimal_cycles(
        self, 
        available_cycles: List[str], 
        market_conditions: Dict[str, Any],
        intensity: str
    ) -> List[str]:
        """Select optimal cycles based on market conditions and user intensity."""
        
        # Don't trade if market conditions are unfavorable
        if not market_conditions.get("should_trade", True):
            return []
        
        # Intensity-based cycle selection
        intensity_limits = {
            "hibernation": 1,    # Only 1 cycle max
            "conservative": 1,   # 1 cycle
            "balanced": 2,       # Up to 2 cycles
            "active": 3,         # Up to 3 cycles  
            "aggressive": 4,     # Up to 4 cycles
            "hyperactive": len(available_cycles)  # All cycles
        }
        
        max_cycles = intensity_limits.get(intensity, 2)
        
        # Prioritize cycles based on market conditions
        cycle_priorities = {
            "arbitrage_hunter": 100,  # Always high priority
            "momentum_futures": 80 if market_conditions.get("sentiment") == "bullish" else 40,
            "portfolio_optimization": 60,
            "deep_analysis": 50
        }
        
        # Sort by priority and take top N
        sorted_cycles = sorted(
            available_cycles,
            key=lambda c: cycle_priorities.get(c, 30),
            reverse=True
        )
        
        return sorted_cycles[:max_cycles]
    
    def _get_strategies_for_conditions(self, sentiment: str, volatility: str) -> List[str]:
        """Get optimal strategies for market conditions."""
        
        strategy_map = {
            ("bullish", "high"): ["spot_momentum_strategy", "spot_breakout_strategy", "scalping_strategy"],
            ("bullish", "medium"): ["spot_momentum_strategy", "futures_trade"],
            ("bullish", "low"): ["spot_momentum_strategy", "market_making"],
            ("bearish", "high"): ["spot_mean_reversion", "futures_trade"],
            ("bearish", "medium"): ["spot_mean_reversion", "options_trade"],
            ("bearish", "low"): ["market_making", "spot_mean_reversion"],
            ("neutral", "high"): ["scalping_strategy", "arbitrage_execution"],
            ("neutral", "medium"): ["spot_momentum_strategy", "spot_mean_reversion"],
            ("neutral", "low"): ["market_making", "grid_trading"]
        }
        
        return strategy_map.get((sentiment, volatility), ["spot_momentum_strategy"])
    
    async def _notify_user_needs_credits(self, user_id: str, profit_status: Dict[str, Any]):
        """Notify user that they need to purchase more credits to continue trading."""
        try:
            from app.services.telegram_core import TelegramService
            telegram_service = TelegramService()
            
            profit_earned = profit_status.get("total_profit_earned", 0)
            profit_potential = profit_status.get("profit_potential", 0)
            
            message = (
                f"🎉 PROFIT CEILING REACHED!\n\n"
                f"💰 You've earned ${profit_earned:,.2f}\n"
                f"🎯 Your profit potential was ${profit_potential:,.2f}\n\n"
                f"🚀 Buy more credits to continue earning!\n"
                f"💡 More strategies = Faster profits"
            )
            
            await telegram_service.send_profit_ceiling_notification(
                user_id=user_id,
                message=message,
                profit_earned=profit_earned
            )
            
        except Exception as e:
            self.logger.error("Failed to send credit notification", error=str(e))
    
    async def _update_strategy_performance_metrics(
        self, 
        user_id: str, 
        strategy_name: str, 
        trade_result: Dict[str, Any]
    ):
        """Update real-time strategy performance metrics for continuous optimization."""
        try:
            # Store individual trade performance
            performance_key = f"strategy_performance:{user_id}:{strategy_name}"
            
            trade_data = {
                "timestamp": trade_result["timestamp"].isoformat(),
                "profit_usd": trade_result["profit_usd"],
                "success": trade_result["success"],
                "confidence": trade_result["confidence"],
                "symbol": trade_result["symbol"],
                "execution_price": trade_result["execution_price"],
                "expected_price": trade_result["expected_price"]
            }
            
            # Add to performance history (keep last 100 trades per strategy)
            await self.redis.lpush(performance_key, json.dumps(trade_data))
            await self.redis.ltrim(performance_key, 0, 99)  # Keep last 100
            await self.redis.expire(performance_key, 30 * 24 * 3600)  # 30 days
            
            # Update aggregate performance metrics
            aggregate_key = f"strategy_aggregate:{user_id}:{strategy_name}"
            
            # Get current aggregates
            current_data = await self.redis.hgetall(aggregate_key)
            
            total_trades = int(current_data.get(b"total_trades", 0)) + 1
            total_profit = float(current_data.get(b"total_profit", 0)) + trade_result["profit_usd"]
            successful_trades = int(current_data.get(b"successful_trades", 0)) + (1 if trade_result["success"] else 0)
            
            # Calculate moving averages
            success_rate = (successful_trades / total_trades) * 100 if total_trades > 0 else 0
            avg_profit_per_trade = total_profit / total_trades if total_trades > 0 else 0
            
            # Update aggregates
            await self.redis.hset(aggregate_key, mapping={
                "total_trades": total_trades,
                "total_profit": total_profit,
                "successful_trades": successful_trades,
                "success_rate": success_rate,
                "avg_profit_per_trade": avg_profit_per_trade,
                "last_updated": datetime.utcnow().isoformat()
            })
            await self.redis.expire(aggregate_key, 30 * 24 * 3600)  # 30 days
            
            # AUTO-OPTIMIZATION: Update strategy rankings
            await self._update_user_strategy_rankings(user_id)
            
            self.logger.info(
                f"Strategy performance updated: {strategy_name}",
                user_id=user_id,
                total_trades=total_trades,
                success_rate=f"{success_rate:.1f}%",
                avg_profit=f"${avg_profit_per_trade:.2f}",
                this_trade_profit=f"${trade_result['profit_usd']:.2f}"
            )
            
        except Exception as e:
            self.logger.error("Failed to update strategy performance", error=str(e))
    
    async def _update_user_strategy_rankings(self, user_id: str):
        """Update user's strategy rankings based on real performance for auto-optimization."""
        try:
            # Get all user's strategies
            from app.services.strategy_marketplace_service import strategy_marketplace_service
            user_portfolio = await strategy_marketplace_service.get_user_strategy_portfolio(user_id)
            
            if not user_portfolio.get("success"):
                return
            
            strategy_rankings = []
            
            for strategy in user_portfolio["active_strategies"]:
                strategy_name = strategy["strategy_id"].replace("ai_", "")
                aggregate_key = f"strategy_aggregate:{user_id}:{strategy_name}"
                
                performance_data = await self.redis.hgetall(aggregate_key)
                
                if performance_data:
                    success_rate = float(performance_data.get(b"success_rate", 0))
                    avg_profit = float(performance_data.get(b"avg_profit_per_trade", 0))
                    total_trades = int(performance_data.get(b"total_trades", 0))
                    
                    # Calculate composite score (success rate + profit + trade volume)
                    composite_score = (success_rate * 0.4) + (avg_profit * 0.4) + (min(total_trades, 50) * 0.2)
                    
                    strategy_rankings.append({
                        "strategy": strategy_name,
                        "score": composite_score,
                        "success_rate": success_rate,
                        "avg_profit": avg_profit,
                        "total_trades": total_trades
                    })
            
            # Sort by composite score
            strategy_rankings.sort(key=lambda x: x["score"], reverse=True)
            
            # Store rankings for future strategy selection optimization
            rankings_key = f"strategy_rankings:{user_id}"
            await self.redis.set(
                rankings_key, 
                json.dumps(strategy_rankings), 
                ex=24 * 3600  # 24 hours
            )
            
            self.logger.info(
                f"Strategy rankings updated for {user_id}",
                top_strategy=strategy_rankings[0]["strategy"] if strategy_rankings else "none",
                total_strategies=len(strategy_rankings)
            )
            
        except Exception as e:
            self.logger.error("Failed to update strategy rankings", error=str(e))
    
    async def _select_cycles_by_market_intelligence(
        self,
        available_cycles: List[str],
        market_conditions: Dict[str, Any],
        prediction_result: Dict[str, Any],
        sentiment_result: Dict[str, Any],
        intensity: str
    ) -> List[str]:
        """
        INTELLIGENT CYCLE SELECTION BASED ON PURE MARKET CONDITIONS
        
        No more arbitrary time schedules - pure market intelligence!
        """
        
        selected_cycles = []
        
        # Check if we should trade at all
        if not prediction_result.get("should_trade", True):
            self.logger.info("🚫 Predictive intelligence says wait for better opportunity")
            return []
        
        if not market_conditions.get("should_trade", True):
            self.logger.info("🚫 Market conditions unfavorable for trading")
            return []
        
        # Get market intelligence data
        volatility = market_conditions.get("volatility_level", "medium")
        sentiment = market_conditions.get("sentiment", "neutral")
        arbitrage_opportunities = market_conditions.get("arbitrage_opportunities", 0)
        
        sentiment_data = sentiment_result.get("optimization_data", {}) if sentiment_result.get("success") else {}
        
        # 1. ARBITRAGE HUNTER - Always prioritize if opportunities exist
        if arbitrage_opportunities > 0:
            selected_cycles.append(TradingCycle.ARBITRAGE_HUNTER.value)
            self.logger.info(f"🎯 Arbitrage cycle selected - {arbitrage_opportunities} opportunities detected")
        
        # 2. MOMENTUM FUTURES - High volatility + bullish sentiment
        if (volatility in ["high", "extreme"] and 
            sentiment in ["bullish", "strongly_bullish"] and
            len(sentiment_data.get("momentum_signals", [])) > 0):
            selected_cycles.append(TradingCycle.MOMENTUM_FUTURES.value)
            self.logger.info("🚀 Momentum cycle selected - high volatility + bullish sentiment")
        
        # 3. DEEP ANALYSIS - High sentiment volume or conflicting signals
        if (len(sentiment_data.get("scalping_opportunities", [])) > 3 or
            (sentiment == "neutral" and volatility == "high")):
            selected_cycles.append(TradingCycle.DEEP_ANALYSIS.value)
            self.logger.info("🧠 Deep analysis cycle selected - complex market conditions")
        
        # 4. PORTFOLIO OPTIMIZATION - Always run for risk management
        if len(selected_cycles) > 0 or market_conditions.get("portfolio_rebalance_needed", False):
            selected_cycles.append(TradingCycle.PORTFOLIO_OPTIMIZATION.value)
            self.logger.info("⚖️ Portfolio optimization cycle selected - risk management")
        
        # Apply intensity limits
        intensity_limits = {
            "hibernation": 1,
            "conservative": 1,
            "balanced": 2,
            "active": 3,
            "aggressive": 4,
            "hyperactive": len(available_cycles)
        }
        
        max_cycles = intensity_limits.get(intensity, 2)
        
        # Prioritize cycles by market impact potential
        cycle_priorities = {
            TradingCycle.ARBITRAGE_HUNTER.value: 100,  # Risk-free profit
            TradingCycle.MOMENTUM_FUTURES.value: 90,   # High profit potential
            TradingCycle.DEEP_ANALYSIS.value: 80,      # Complex opportunities
            TradingCycle.PORTFOLIO_OPTIMIZATION.value: 70  # Risk management
        }
        
        # Sort by priority and limit
        selected_cycles.sort(key=lambda c: cycle_priorities.get(c, 50), reverse=True)
        selected_cycles = selected_cycles[:max_cycles]
        
        # Log intelligent selection reasoning
        self.logger.info(
            "🎯 MARKET-INTELLIGENT CYCLE SELECTION",
            volatility=volatility,
            sentiment=sentiment,
            arbitrage_ops=arbitrage_opportunities,
            momentum_signals=len(sentiment_data.get("momentum_signals", [])),
            selected_cycles=selected_cycles,
            intensity=intensity
        )
        
        return selected_cycles
    
    async def _get_sentiment_optimized_symbols(
        self, 
        strategy: str, 
        sentiment_result: Dict[str, Any]
    ) -> List[str]:
        """Get sentiment-optimized symbols for strategy execution."""
        
        try:
            if not sentiment_result.get("success"):
                return ["BTC", "ETH", "SOL"]  # Fallback
            
            sentiment_data = sentiment_result.get("optimization_data", {})
            
            # Strategy-specific symbol optimization
            if "momentum" in strategy.lower():
                # Momentum strategies prefer bullish sentiment
                momentum_symbols = [s["symbol"] for s in sentiment_data.get("momentum_signals", [])]
                return momentum_symbols[:5] if momentum_symbols else ["BTC", "ETH"]
            
            elif "mean_reversion" in strategy.lower():
                # Mean reversion prefers extreme sentiment (oversold/overbought)
                reversion_symbols = [s["symbol"] for s in sentiment_data.get("mean_reversion_signals", [])]
                return reversion_symbols[:5] if reversion_symbols else ["BTC", "ETH"]
            
            elif "scalping" in strategy.lower():
                # Scalping prefers high volume sentiment
                scalping_symbols = [s["symbol"] for s in sentiment_data.get("scalping_opportunities", [])]
                return scalping_symbols[:5] if scalping_symbols else ["BTC", "ETH"]
            
            elif "arbitrage" in strategy.lower():
                # Arbitrage doesn't depend on sentiment, use high volume symbols
                high_volume_symbols = sentiment_result.get("trading_recommendations", {}).get("high_volume_symbols", [])
                return high_volume_symbols[:5] if high_volume_symbols else ["BTC", "ETH", "SOL"]
            
            else:
                # Default: use top bullish opportunities
                bullish_opportunities = sentiment_result.get("trading_recommendations", {}).get("top_bullish_opportunities", [])
                return [s["symbol"] for s in bullish_opportunities[:5]] or ["BTC", "ETH", "SOL"]
                
        except Exception as e:
            self.logger.warning("Sentiment symbol optimization failed", error=str(e))
            return ["BTC", "ETH", "SOL"]

    async def performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        
        uptime = (datetime.utcnow() - self.start_time).total_seconds() / 3600
        self.performance_metrics["uptime_hours"] = uptime
        
        return {
            "success": True,
            "performance_metrics": self.performance_metrics,
            "current_mode": self.current_mode.value,
            "mode_config": self.mode_configs[self.current_mode].__dict__,
            "autonomous_active": self.is_active,
            "current_timezone_strategy": self.get_current_timezone_strategy(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def set_trading_mode(self, mode: str) -> Dict[str, Any]:
        """Set trading mode manually."""
        
        try:
            new_mode = TradingMode(mode)
            old_mode = self.current_mode
            self.current_mode = new_mode
            
            try:
                from app.services.telegram_core import telegram_service
                from app.services.telegram_commander import RecipientType
                # Get owner chat ID and send directly
                owner_chat_id = await telegram_service._get_chat_id_for_recipient(RecipientType.OWNER)
                if owner_chat_id:
                    await telegram_service.send_direct_message(
                        chat_id=owner_chat_id,
                        message_content=f"🎯 Trading mode changed: {old_mode.value} → {new_mode.value}",
                        message_type="system",
                        priority="normal"
                    )
            except Exception as e:
                logger.exception("Failed to send trading mode change notification", error=str(e))
            
            return {
                "success": True,
                "old_mode": old_mode.value,
                "new_mode": new_mode.value,
                "config": self.mode_configs[new_mode].__dict__
            }
            
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid trading mode: {mode}",
                "valid_modes": [m.value for m in TradingMode]
            }
    
    async def update_user_ai_model_weights(
        self,
        user_id: str,
        ai_model_weights: Dict[str, float],
        autonomous_frequency_minutes: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Update user's custom AI model weights and autonomous frequency.
        
        Args:
            user_id: User identifier
            ai_model_weights: Custom AI model weights {"gpt4": 0.4, "claude": 0.3, "gemini": 0.3}
            autonomous_frequency_minutes: Custom autonomous trading frequency
            
        Returns:
            Success/failure result
        """
        
        try:
            # Validate weights sum to 1.0
            total_weight = sum(ai_model_weights.values())
            if abs(total_weight - 1.0) > 0.01:
                return {
                    "success": False,
                    "error": f"AI model weights must sum to 1.0, got {total_weight:.3f}"
                }
            
            # Validate weight values
            for model, weight in ai_model_weights.items():
                if not 0 <= weight <= 1:
                    return {
                        "success": False,
                        "error": f"Weight for {model} must be between 0 and 1, got {weight}"
                    }
                
                if model not in ["gpt4", "claude", "gemini"]:
                    return {
                        "success": False,
                        "error": f"Invalid AI model: {model}. Must be one of: gpt4, claude, gemini"
                    }
            
            # Validate autonomous frequency
            if autonomous_frequency_minutes is not None:
                if not 1 <= autonomous_frequency_minutes <= 60:
                    return {
                        "success": False,
                        "error": "Autonomous frequency must be between 1 and 60 minutes"
                    }
            
            # Get user's current trading mode
            user_config = await self._get_user_config(user_id)
            current_mode = TradingMode(user_config.get("trading_mode", "balanced"))
            
            # Create custom config based on current mode
            base_config = self.mode_configs[current_mode]
            
            # Store custom AI weights in Redis
            redis = await self._ensure_redis()
            if redis:
                custom_config = {
                    "ai_model_weights": ai_model_weights,
                    "autonomous_frequency_minutes": autonomous_frequency_minutes or base_config.autonomous_frequency_minutes,
                    "base_trading_mode": current_mode.value,
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                await redis.set(
                    f"user_ai_config:{user_id}",
                    json.dumps(custom_config),
                    ex=86400 * 30  # 30 days expiry
                )
            
            self.logger.info(
                "AI model weights updated",
                user_id=user_id,
                weights=ai_model_weights,
                frequency=autonomous_frequency_minutes,
                base_mode=current_mode.value
            )
            
            return {
                "success": True,
                "message": "AI model weights updated successfully",
                "ai_model_weights": ai_model_weights,
                "autonomous_frequency_minutes": autonomous_frequency_minutes or base_config.autonomous_frequency_minutes,
                "base_trading_mode": current_mode.value
            }
            
        except Exception as e:
            self.logger.error("Failed to update AI model weights", user_id=user_id, error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_user_config(self, user_id: str) -> Dict[str, Any]:
        """Get user's cached config from Redis following UnifiedAIManager pattern."""
        try:
            # Attempt to get cached config from Redis
            redis = await self._ensure_redis()
            if redis:
                config_data = await redis.get(f"user_ai_config:{user_id}")
                if config_data:
                    try:
                        # Parse JSON config
                        parsed_config = json.loads(config_data)
                        return parsed_config
                    except json.JSONDecodeError:
                        self.logger.warning("Invalid JSON in user config, using defaults", user_id=user_id)
        except Exception as e:
            self.logger.warning("Failed to get user config from Redis", user_id=user_id, error=str(e))
        
        # Return default config when Redis unavailable or cache missing/invalid
        return {
            "trading_mode": "balanced",
            "autonomous_frequency_minutes": 10,
            "ai_model_weights": {
                "gpt4": 0.33,
                "claude": 0.34,
                "gemini": 0.33
            }
        }
    
    async def get_user_ai_model_weights(self, user_id: str) -> Dict[str, Any]:
        """Get user's current AI model weights and autonomous frequency."""
        
        try:
            # Try to get custom config first
            redis = await self._ensure_redis()
            if redis:
                custom_config_str = await redis.get(f"user_ai_config:{user_id}")
                if custom_config_str is not None:
                    # Guard against double-decoding - inspect type and parse accordingly
                    if isinstance(custom_config_str, bytes):
                        # Decode bytes to string first, then JSON parse
                        custom_config = json.loads(custom_config_str.decode('utf-8'))
                    elif isinstance(custom_config_str, str):
                        # Parse string as JSON
                        custom_config = json.loads(custom_config_str)
                    elif isinstance(custom_config_str, (dict, list)):
                        # Already deserialized - use directly
                        custom_config = custom_config_str
                    else:
                        # Unknown type - skip and use defaults
                        custom_config = None
                    
                    # Only return custom config if we successfully parsed it
                    if custom_config and isinstance(custom_config, dict):
                        return {
                            "success": True,
                            "ai_model_weights": custom_config.get("ai_model_weights", {}),
                            "autonomous_frequency_minutes": custom_config.get("autonomous_frequency_minutes", 10),
                            "base_trading_mode": custom_config.get("base_trading_mode", "balanced"),
                        "is_custom": True,
                        "updated_at": custom_config.get("updated_at")
                    }
            
            # Fall back to default based on trading mode
            user_config = await self._get_user_config(user_id)
            current_mode = TradingMode(user_config.get("trading_mode", "balanced"))
            mode_config = self.mode_configs[current_mode]
            
            return {
                "success": True,
                "ai_model_weights": mode_config.ai_model_weights,
                "autonomous_frequency_minutes": mode_config.autonomous_frequency_minutes,
                "base_trading_mode": current_mode.value,
                "is_custom": False
            }
            
        except Exception as e:
            self.logger.error("Failed to get AI model weights", user_id=user_id, error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    async def emergency_stop(self, user_id: str, reason: str = "manual_stop") -> Dict[str, Any]:
        """
        Emergency stop for specific user - integrates with EmergencyManager.
        """
        
        try:
            self.logger.critical(
                "🚨 EMERGENCY STOP ACTIVATED",
                user_id=user_id,
                reason=reason
            )
            
            # Stop autonomous trading for this user
            self.is_active = False
            
            # Set emergency flag in Redis - use both keys for compatibility
            redis = await self._ensure_redis()
            if redis:
                await redis.set(f"emergency_stop:{user_id}", reason, ex=3600)  # 1 hour
                await redis.set(f"emergency_halt:{user_id}", reason, ex=3600)  # Compatible with emergency_manager
            
            # Send WebSocket notification
            await manager.broadcast({
                "type": "emergency_stop",
                "user_id": user_id,
                "reason": reason,
                "message": "🚨 Emergency stop activated - all trading halted",
                "timestamp": datetime.utcnow().isoformat()
            }, user_id)
            
            return {
                "success": True,
                "message": "Emergency stop activated",
                "user_id": user_id,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error("Emergency stop failed", user_id=user_id, error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    async def resume_operations(self, user_id: str) -> Dict[str, Any]:
        """Resume operations after emergency stop."""
        
        try:
            # Remove emergency flag
            redis = await self._ensure_redis()
            if redis:
                await redis.delete(f"emergency_stop:{user_id}")
            
            # Resume autonomous trading
            self.is_active = True
            
            self.logger.info("Operations resumed", user_id=user_id)
            
            # Send WebSocket notification
            await manager.broadcast({
                "type": "operations_resumed",
                "user_id": user_id,
                "message": "✅ Operations resumed - trading active",
                "timestamp": datetime.utcnow().isoformat()
            }, user_id)
            
            return {
                "success": True,
                "message": "Operations resumed successfully",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error("Failed to resume operations", user_id=user_id, error=str(e))
            return {
                "success": False,
                "error": str(e)
            }

    async def health_check(self) -> Dict[str, Any]:
        """Health check for master controller."""
        
        try:
            uptime = (datetime.utcnow() - self.start_time).total_seconds() / 3600
            
            return {
                "service": "master_controller",
                "status": "HEALTHY",
                "autonomous_active": self.is_active,
                "current_mode": self.current_mode.value,
                "uptime_hours": round(uptime, 2),
                "cycles_executed": self.performance_metrics["cycles_executed"],
                "success_rate": self.performance_metrics["success_rate"],
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "service": "master_controller",
                "status": "UNHEALTHY",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    # ===============================================================================
    # ENTERPRISE 5-PHASE TRADING PIPELINE ORCHESTRATION
    # ===============================================================================
    
    async def execute_5_phase_autonomous_cycle(
        self, 
        user_id: str = "system", 
        source: str = "autonomous",
        symbols: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        ENTERPRISE 5-PHASE TRADING PIPELINE ORCHESTRATION
        
        This is the core coordinated trading pipeline that ALL components should use.
        No more direct service calls - everything routes through this pipeline.
        
        Phase 1: Market Analysis → Phase 2: Trading Strategy → Phase 3: Portfolio Risk 
        → Phase 4: AI Consensus → Phase 5: Trade Execution
        """
        
        cycle_id = f"{source}_{user_id}_{int(time.time())}"
        start_time = time.time()
        
        # Extract risk tolerance from kwargs for pipeline execution
        risk_tolerance = kwargs.get('risk_tolerance', 'balanced')
        
        self.logger.info(f"🚀 ENTERPRISE 5-Phase Pipeline Starting", 
                        cycle_id=cycle_id, source=source, user_id=user_id, risk_tolerance=risk_tolerance)
        
        pipeline_result = {
            "success": False,
            "cycle_id": cycle_id,
            "source": source,
            "user_id": user_id,
            "phases": {},
            "execution_time_ms": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # =============================================================================
            # PHASE 1: MARKET ANALYSIS SERVICE - DYNAMIC DISCOVERY & ANALYSIS
            # =============================================================================
            
            phase_1_start = time.time()
            self.logger.info("📊 Phase 1: Market Analysis Starting", cycle_id=cycle_id)
            
            try:
                from app.services.market_analysis_core import MarketAnalysisService
                market_analysis = MarketAnalysisService()
                
                # Dynamic asset discovery if no symbols provided (NO HARDCODED LIMITATIONS)
                if not symbols:
                    symbols_str = "SMART_ADAPTIVE"  # This triggers dynamic discovery
                else:
                    symbols_str = ",".join(symbols)
                
                market_data = await market_analysis.complete_market_assessment(
                    symbols=symbols_str,
                    depth="comprehensive",
                    user_id=user_id
                )
                
                phase_1_time = (time.time() - phase_1_start) * 1000
                pipeline_result["phases"]["phase_1"] = {
                    "status": "completed",
                    "service": "market_analysis",
                    "execution_time_ms": phase_1_time,
                    "opportunities_found": len(market_data.get("assessment", {}).get("arbitrage_opportunities", [])),
                    "symbols_analyzed": len(market_data.get("assessment", {}).get("technical_analysis", {}))
                }
                
                self.logger.info("✅ Phase 1 Completed", 
                               cycle_id=cycle_id, 
                               execution_time_ms=phase_1_time,
                               opportunities=pipeline_result["phases"]["phase_1"]["opportunities_found"])
                
            except Exception as e:
                self.logger.exception("❌ Phase 1 Failed", cycle_id=cycle_id)
                pipeline_result["phases"]["phase_1"] = {"status": "failed", "error": str(e)}
                return pipeline_result
            
            # =============================================================================
            # PHASE 2: TRADING STRATEGY SERVICE - SIGNAL GENERATION
            # =============================================================================
            
            if market_data.get("success"):
                phase_2_start = time.time()
                self.logger.info("⚡ Phase 2: Trading Strategy Starting", cycle_id=cycle_id)
                
                try:
                    from app.services.trading_strategies import trading_strategies_service
                    
                    # Extract best opportunity from market analysis
                    opportunities = market_data.get("assessment", {}).get("arbitrage_opportunities", [])
                    best_symbol = "BTC"  # Default fallback
                    
                    if opportunities:
                        best_opportunity = max(opportunities, key=lambda x: x.get("profit_bps", 0))
                        best_symbol = best_opportunity.get("symbol", "BTC")
                    
                    # Select strategy based on market conditions
                    strategy_type = self._select_strategy_based_on_market(market_data, best_symbol)
                    
                    # Extract relevant parameters for the strategy
                    strategy_params = self._extract_strategy_parameters(market_data, best_symbol, strategy_type)
                    
                    # Generate trading signal based on market analysis
                    trade_signal = await trading_strategies_service.generate_trading_signal(
                        strategy_type=strategy_type,
                        market_data=strategy_params,
                        risk_mode=risk_tolerance  # Use risk_tolerance from kwargs
                    )
                    
                    phase_2_time = (time.time() - phase_2_start) * 1000
                    pipeline_result["phases"]["phase_2"] = {
                        "status": "completed",
                        "service": "trading_strategies",
                        "execution_time_ms": phase_2_time,
                        "symbol": best_symbol,
                        "action": trade_signal.get("signal", {}).get("action", "HOLD"),
                        "confidence": trade_signal.get("signal", {}).get("confidence", 0)
                    }
                    
                    self.logger.info("✅ Phase 2 Completed", 
                                   cycle_id=cycle_id,
                                   symbol=best_symbol,
                                   action=pipeline_result["phases"]["phase_2"]["action"])
                    
                except Exception as e:
                    self.logger.exception("❌ Phase 2 Failed", cycle_id=cycle_id)
                    pipeline_result["phases"]["phase_2"] = {"status": "failed", "error": str(e)}
                    return pipeline_result
            
            # =============================================================================
            # PHASE 3: PORTFOLIO & RISK SERVICE - POSITION SIZING
            # =============================================================================
            
            if trade_signal.get("success"):
                phase_3_start = time.time()
                self.logger.info("🛡️ Phase 3: Portfolio Risk Starting", cycle_id=cycle_id)
                
                try:
                    from app.services.portfolio_risk_core import PortfolioRiskServiceExtended
                    portfolio_risk = PortfolioRiskServiceExtended()
                    
                    sized_position = await portfolio_risk.position_sizing(
                        opportunity=json.dumps(trade_signal),
                        user_id=user_id
                    )
                    
                    phase_3_time = (time.time() - phase_3_start) * 1000
                    pipeline_result["phases"]["phase_3"] = {
                        "status": "completed",
                        "service": "portfolio_risk",
                        "execution_time_ms": phase_3_time,
                        "position_size_usd": sized_position.get("position_size_usd", 0),
                        "risk_score": sized_position.get("risk_metrics", {}).get("var_1d", 0)
                    }
                    
                    self.logger.info("✅ Phase 3 Completed", 
                                   cycle_id=cycle_id,
                                   position_size=sized_position.get("position_size_usd", 0))
                    
                except Exception as e:
                    self.logger.exception("❌ Phase 3 Failed", cycle_id=cycle_id)
                    pipeline_result["phases"]["phase_3"] = {"status": "failed", "error": str(e)}
                    return pipeline_result
            
            # =============================================================================
            # PHASE 4: AI CONSENSUS SERVICE - VALIDATION
            # =============================================================================
            
            if sized_position.get("success"):
                phase_4_start = time.time()
                self.logger.info("🧠 Phase 4: AI Consensus Starting", cycle_id=cycle_id)
                
                try:
                    from app.services.ai_consensus_core import ai_consensus_service
                    
                    validation = await ai_consensus_service.validate_trade(
                        analysis_request=json.dumps({
                            "signal": trade_signal.get("signal", {}),
                            "position_size": sized_position.get("position_size_usd", 0),
                            "risk_metrics": sized_position.get("risk_metrics", {}),
                            "market_context": market_data.get("assessment", {}),
                            "user_id": user_id
                        }),
                        confidence_threshold=75.0,
                        ai_models="all"
                    )
                    
                    phase_4_time = (time.time() - phase_4_start) * 1000
                    pipeline_result["phases"]["phase_4"] = {
                        "status": "completed",
                        "service": "ai_consensus",
                        "execution_time_ms": phase_4_time,
                        "approved": validation.get("approved", False),
                        "consensus_confidence": validation.get("consensus_confidence", 0)
                    }
                    
                    self.logger.info("✅ Phase 4 Completed", 
                                   cycle_id=cycle_id,
                                   approved=validation.get("approved", False),
                                   confidence=validation.get("consensus_confidence", 0))
                    
                except Exception as e:
                    self.logger.exception("❌ Phase 4 Failed", cycle_id=cycle_id)
                    pipeline_result["phases"]["phase_4"] = {"status": "failed", "error": str(e)}
                    return pipeline_result
            
            # =============================================================================
            # PHASE 5: TRADE EXECUTION SERVICE - VALIDATED EXECUTION
            # =============================================================================
            
            if validation.get("approved"):
                phase_5_start = time.time()
                self.logger.info("⚡ Phase 5: Trade Execution Starting", cycle_id=cycle_id)
                
                try:
                    from app.services.trading_strategies import trading_strategies_service
                    
                    execution_result = await trading_strategies_service.execute_validated_trade(
                        action=trade_signal.get("signal", {}).get("action", "HOLD"),
                        symbol=pipeline_result["phases"]["phase_2"]["symbol"],
                        position_size_usd=sized_position.get("position_size_usd", 0),
                        ai_validation_token=validation.get("validation_token", ""),
                        user_id=user_id
                    )
                    
                    phase_5_time = (time.time() - phase_5_start) * 1000
                    pipeline_result["phases"]["phase_5"] = {
                        "status": "completed",
                        "service": "trade_execution",
                        "trade_executed": execution_result.get("success", False),
                        "filled_price": execution_result.get("filled_price", 0),
                        "execution_time_ms": execution_result.get("execution_time_ms", 0)
                    }
                    
                    self.logger.info("✅ Phase 5 Completed", 
                                   cycle_id=cycle_id,
                                   executed=execution_result.get("success", False))
                    
                except Exception as e:
                    self.logger.exception("❌ Phase 5 Failed", cycle_id=cycle_id)
                    pipeline_result["phases"]["phase_5"] = {"status": "failed", "error": str(e)}
                    
            else:
                pipeline_result["phases"]["phase_5"] = {
                    "status": "skipped",
                    "reason": "AI consensus rejected trade"
                }
                self.logger.info("⏭️ Phase 5 Skipped - Trade rejected by AI consensus", cycle_id=cycle_id)
            
            # =============================================================================
            # PIPELINE COMPLETION & METRICS
            # =============================================================================
            
            total_time = (time.time() - start_time) * 1000
            pipeline_result["success"] = True
            pipeline_result["execution_time_ms"] = total_time
            
            completed_phases = sum(1 for p in pipeline_result["phases"].values() if p.get("status") == "completed")
            pipeline_result["phases_completed"] = f"{completed_phases}/5"
            
            self.logger.info("🎯 ENTERPRISE Pipeline Completed", 
                           cycle_id=cycle_id,
                           total_time_ms=total_time,
                           phases_completed=completed_phases,
                           success=pipeline_result["success"])
            
            return pipeline_result
            
        except Exception as e:
            total_time = (time.time() - start_time) * 1000
            pipeline_result["execution_time_ms"] = total_time
            pipeline_result["error"] = str(e)
            
            self.logger.exception("💥 ENTERPRISE Pipeline Failed", 
                            cycle_id=cycle_id, 
                            total_time_ms=total_time)
            
            return pipeline_result
    
    async def trigger_pipeline(
        self, 
        analysis_type: str = "comprehensive",
        symbols: str = "BTC,ETH,SOL",
        timeframes: str = "1h,4h,1d",
        user_id: str = "system",
        source: str = "api",
        force_refresh: bool = False,
        bypass_coordinator: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        ENTERPRISE PIPELINE TRIGGER WITH COORDINATION
        
        Single entry point for ALL components to trigger the 5-phase pipeline.
        Integrated with MarketDataCoordinator for deduplication and batching.
        
        Usage:
        - Chat System: await master_controller.trigger_pipeline("asset_analysis", "BTC", user_id="chat")
        - Frontend: await master_controller.trigger_pipeline("market_overview", user_id="frontend")
        - Background: await master_controller.trigger_pipeline("autonomous_cycle", user_id="system")
        """
        
        # Prepare coordination parameters
        coordination_params = {
            'analysis_type': analysis_type,
            'symbols': symbols,
            'timeframes': timeframes,
            'user_id': user_id,
            'source': source,
            **kwargs
        }
        
        self.logger.info(f"🎯 Pipeline Trigger with Coordination", 
                        analysis_type=analysis_type, 
                        symbols=symbols,
                        user_id=user_id,
                        source=source,
                        bypass_coordinator=bypass_coordinator)
        
        try:
            # Use coordinator for request deduplication and batching (unless bypassed)
            if not bypass_coordinator:
                result, metadata = await market_data_coordinator.coordinate_request(
                    endpoint=f"pipeline/{analysis_type}",
                    params=coordination_params,
                    force_refresh=force_refresh,
                    batchable=self._is_analysis_batchable(analysis_type)
                )
                
                # Add coordination metadata to result
                if isinstance(result, dict):
                    result['coordination_metadata'] = metadata
                
                self.logger.info(f"✅ Pipeline Coordination Complete", 
                               analysis_type=analysis_type,
                               source=metadata.get('source', 'unknown'),
                               cache_hit=metadata.get('cache_hit', False))
                
                return result
            else:
                # Bypass coordinator - execute pipeline directly
                self.logger.info(f"🚀 Direct Pipeline Execution (bypassing coordinator)")
                
                # Convert string symbols to list if needed
                symbols_list = symbols.split(',') if isinstance(symbols, str) else symbols
                
                return await self.execute_5_phase_autonomous_cycle(
                    user_id=user_id,
                    source=source,
                    symbols=symbols_list,
                    **kwargs  # Forward all parameters including risk_tolerance
                )
            
        except Exception as e:
            self.logger.exception(f"Pipeline coordination failed", 
                            analysis_type=analysis_type)
            
            # Fallback to direct execution
            self.logger.info(f"Falling back to direct pipeline execution")
            
            # Convert string symbols to list if needed
            symbols_list = symbols.split(',') if isinstance(symbols, str) else symbols
            
            return await self.execute_5_phase_autonomous_cycle(
                user_id=user_id,
                source=source,
                symbols=symbols_list,
                **kwargs  # Forward all parameters including risk_tolerance
            )
    
    def _select_strategy_based_on_market(self, market_data: Dict[str, Any], symbol: str) -> str:
        """Select trading strategy based on market analysis."""
        
        try:
            # Defensive validation: early return if market_data is not a dict or symbol not present
            if not isinstance(market_data, dict) or not symbol:
                return "balanced_strategy"
            
            # Get market indicators for the symbol with defensive validation
            symbol_data = market_data.get(symbol, {})
            if not isinstance(symbol_data, dict):
                symbol_data = {}
            
            technical_indicators = symbol_data.get('technical_indicators', {})
            if not isinstance(technical_indicators, dict):
                technical_indicators = {}
                
            volatility = symbol_data.get('volatility', {})
            if not isinstance(volatility, dict):
                volatility = {}
            
            arbitrage_opportunities = market_data.get('arbitrage_opportunities', [])
            if not isinstance(arbitrage_opportunities, list):
                arbitrage_opportunities = []
            
            # Check for arbitrage opportunities with type guard
            if arbitrage_opportunities:
                symbol_arbitrage = [opp for opp in arbitrage_opportunities 
                                  if isinstance(opp, dict) and opp.get('symbol') == symbol]
                if symbol_arbitrage and len(symbol_arbitrage) > 0:
                    return "arbitrage_strategy"
            
            # Check momentum indicators with safe lookups and sensible defaults
            rsi = technical_indicators.get('rsi', 50)
            if not isinstance(rsi, (int, float)):
                rsi = 50
                
            macd_histogram = technical_indicators.get('macd_histogram', 0)
            if not isinstance(macd_histogram, (int, float)):
                macd_histogram = 0
            
            if (rsi > 70 or rsi < 30) and abs(macd_histogram) > 0.1:
                return "momentum_strategy"
            
            # Check volatility for mean reversion with safe lookup
            volatility_24h = volatility.get('volatility_24h', 0)
            if not isinstance(volatility_24h, (int, float)):
                volatility_24h = 0
                
            if volatility_24h < 0.02:  # Low volatility
                return "mean_reversion_strategy"
            
            # Default fallback strategy
            return "balanced_strategy"
            
        except Exception as e:
            self.logger.warning(f"Strategy selection failed for symbol {symbol}, using balanced_strategy fallback", 
                              symbol=symbol, error=str(e))
            return "balanced_strategy"
    
    def _extract_strategy_parameters(self, market_data: Dict[str, Any], symbol: str, strategy_type: str) -> Dict[str, Any]:
        """Extract relevant parameters for the selected strategy."""
        
        try:
            symbol_data = market_data.get(symbol, {})
            technical_indicators = symbol_data.get('technical_indicators', {})
            
            # Base parameters for all strategies
            params = {
                'symbol': symbol,
                'timeframe': '1h',
                'confidence_score': symbol_data.get('ai_consensus', {}).get('confidence_score', 0.5)
            }
            
            # Add strategy-specific parameters
            if strategy_type == "momentum_strategy":
                params.update({
                    'rsi': technical_indicators.get('rsi', 50),
                    'macd': technical_indicators.get('macd', 0),
                    'macd_signal': technical_indicators.get('macd_signal', 0),
                    'price_change_24h': symbol_data.get('price_change_24h', 0)
                })
            elif strategy_type == "arbitrage_strategy":
                arbitrage_opportunities = market_data.get('arbitrage_opportunities', [])
                symbol_arbitrage = [opp for opp in arbitrage_opportunities if opp.get('symbol') == symbol]
                if symbol_arbitrage:
                    best_opp = max(symbol_arbitrage, key=lambda x: x.get('profit_bps', 0))
                    params.update({
                        'buy_exchange': best_opp.get('buy_exchange'),
                        'sell_exchange': best_opp.get('sell_exchange'),
                        'profit_bps': best_opp.get('profit_bps', 0)
                    })
            elif strategy_type == "mean_reversion_strategy":
                params.update({
                    'sma_20': technical_indicators.get('sma_20', 0),
                    'sma_50': technical_indicators.get('sma_50', 0),
                    'bollinger_upper': technical_indicators.get('bollinger_upper', 0),
                    'bollinger_lower': technical_indicators.get('bollinger_lower', 0)
                })
            else:  # balanced_strategy
                params.update({
                    'rsi': technical_indicators.get('rsi', 50),
                    'sma_20': technical_indicators.get('sma_20', 0),
                    'volume_24h': symbol_data.get('volume_24h', 0)
                })
            
            return params
            
        except Exception as e:
            self.logger.warning(f"Parameter extraction failed, using minimal params", 
                              symbol=symbol, strategy_type=strategy_type, error=str(e))
            return {
                'symbol': symbol,
                'timeframe': '1h',
                'confidence_score': 0.5
            }
    
    def _is_analysis_batchable(self, analysis_type: str) -> bool:
        """Determine if analysis type can be batched."""
        
        batchable_types = {
            'price_tracking',
            'technical_analysis', 
            'sentiment_analysis',
            'volatility_analysis',
            'support_resistance',
            'asset_analysis'
        }
        
        return analysis_type in batchable_types


# Global service instance
master_controller = MasterSystemController()


# FastAPI dependency
async def get_master_controller() -> MasterSystemController:
    """Dependency injection for FastAPI."""
    global master_controller
    if master_controller is None:
        master_controller = MasterSystemController()
        # ENTERPRISE: Defer Redis initialization to first use
        # master_controller.redis = await get_redis_client()
    return master_controller
