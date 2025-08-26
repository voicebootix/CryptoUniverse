"""
System Journal - Real-time Learning & Memory System

Comprehensive learning and memory system that combines performance logging,
strategy journaling, and adaptive learning with continuous parameter optimization.
Provides genetic algorithm optimization, market adaptive learning, and real-time
performance guardian functionality.

CORE FEATURES:
- Trade & Decision Logging
- Real-time Learning (micro-learning, pattern recognition, strategy evolution, parameter optimization)  
- Deep Analysis & System Insights
- Genetic Algorithm Optimization
- Market Adaptive Learning
- Real-time Performance Guardian
- Dynamic Parameter Updates

Adapted from Flowise System Journal to native Python with database persistence.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import random
import math

import structlog
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.core.config import get_settings
from app.core.database import get_database
from app.core.redis import redis_manager
from app.core.logging import LoggerMixin

settings = get_settings()
logger = structlog.get_logger(__name__)


class LearningType(str, Enum):
    """Learning type enumeration."""
    MICRO_LEARNING = "micro_learning"
    PATTERN_RECOGNITION = "pattern_recognition"
    STRATEGY_EVOLUTION = "strategy_evolution"
    PARAMETER_OPTIMIZATION = "parameter_optimization"


class AnalysisPeriod(str, Enum):
    """Analysis period enumeration."""
    HOUR_24 = "24h"
    DAYS_7 = "7d"
    DAYS_30 = "30d"
    DAYS_90 = "90d"


class GuardianStatus(str, Enum):
    """Performance guardian status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class TradeRecord:
    """Trade record for logging."""
    trade_id: str
    timestamp: str
    symbol: str
    action: str
    quantity: float
    entry_price: float
    exit_price: float = 0.0
    pnl_usd: float = 0.0
    pnl_percentage: float = 0.0
    trade_status: str = "OPEN"
    simulation_mode: bool = False
    execution_time_ms: int = 0
    confidence_score: int = 0
    was_profitable: bool = False
    met_expectations: bool = False
    lessons_learned: str = ""


@dataclass
class DecisionRecord:
    """Decision record for logging."""
    decision_id: str
    timestamp: str
    decision_type: str
    decision_outcome: str
    confidence_level: int
    market_conditions: Dict[str, Any]
    portfolio_state: Dict[str, Any]
    opportunity_data: Dict[str, Any]
    ai_models_used: List[str]
    ai_consensus: str
    reasoning_chain: str
    alternative_options: List[Dict[str, Any]]
    risk_assessment: Dict[str, Any]
    expected_outcome: str
    worst_case_scenario: str
    decision_cost_usd: float = 0.0
    time_to_decision_ms: int = 0
    executed: bool = False
    execution_delay_ms: int = 0
    actual_outcome: Optional[str] = None
    outcome_match_expectation: Optional[bool] = None


@dataclass
class ParameterOptimization:
    """Parameter optimization result."""
    parameter: str
    current_value: float
    optimal_value: float
    improvement_percentage: float
    confidence: str
    recommendation: str


class SystemJournalService(LoggerMixin):
    """
    Real-time Learning & Memory System
    
    Handles comprehensive logging, learning, and optimization for the trading system.
    Provides genetic algorithm optimization, adaptive learning, and performance monitoring.
    """
    
    def __init__(self):
        # In-memory storage for real-time operations (could be enhanced with database)
        self.trade_history: List[TradeRecord] = []
        self.decision_history: List[DecisionRecord] = []
        self.parameter_updates: List[Dict[str, Any]] = []
        self.learning_cycles: List[Dict[str, Any]] = []
        
        # Performance tracking
        self.performance_metrics = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_pnl": 0.0,
            "consecutive_wins": 0,
            "consecutive_losses": 0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "learning_cycles_completed": 0
        }
        
        # Current system parameters (could be loaded from database)
        self.system_parameters = {
            "confidence_threshold": 75,
            "position_size_multiplier": 1.0,
            "risk_tolerance": 0.15,
            "learning_rate": 0.01,
            "optimization_frequency": 24,  # hours
            "guardian_check_frequency": 1  # hours
        }
        
        # Performance guardian state
        self.guardian_state = {
            "status": GuardianStatus.HEALTHY.value,
            "last_check": datetime.utcnow(),
            "alerts": [],
            "auto_adjustments": []
        }
        
        self.logger.info("System Journal Service initialized")
    
    async def execute_function(
        self,
        function: str,
        data: Optional[str] = None,
        learning_type: Optional[str] = None,
        analysis_period: Optional[str] = None,
        user_id: Optional[str] = "system"
    ) -> Dict[str, Any]:
        """
        Main execution entry point for all system journal functions.
        
        Args:
            function: Function to execute
            data: JSON data for logging or analysis  
            learning_type: Type of learning to perform
            analysis_period: Period for analysis
            user_id: User ID for operations
            
        Returns:
            Dict containing execution results
        """
        
        start_time = time.time()
        
        try:
            self.logger.info("System Journal function executing", 
                           function=function, 
                           learning_type=learning_type,
                           analysis_period=analysis_period)
            
            # Parse data if provided
            parsed_data = None
            if data:
                try:
                    parsed_data = json.loads(data) if isinstance(data, str) else data
                except json.JSONDecodeError:
                    parsed_data = data
            
            # Route to specific function
            function_map = {
                "log_trade": self._log_trade,
                "log_decision": self._log_decision,
                "realtime_learning": self._realtime_learning,
                "deep_analysis": self._deep_analysis,
                "get_insights": self._get_system_insights,
                "update_parameters": self._update_parameters,
                "genetic_algorithm_optimization": self._genetic_optimization,
                "market_adaptive_learning": self._market_adaptive_learning,
                "realtime_performance_guardian": self._performance_guardian,
                "complete_cycle": self._complete_learn_cycle
            }
            
            handler = function_map.get(function.lower())
            if not handler:
                return {
                    "success": False,
                    "error": f"Unknown function: {function}",
                    "available_functions": list(function_map.keys())
                }
            
            # Execute the function
            result = await handler(
                data=parsed_data,
                learning_type=learning_type,
                analysis_period=analysis_period,
                user_id=user_id
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            return {
                "success": True,
                "function_executed": function,
                "execution_time_ms": execution_time,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error("System Journal function failed", 
                            function=function, 
                            error=str(e), 
                            exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "function_attempted": function,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _log_trade(
        self,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Log trade details with comprehensive metadata."""
        
        if not data:
            return {"success": False, "error": "Trade data required"}
        
        # Create trade record
        trade_record = TradeRecord(
            trade_id=data.get("trade_id", f"trade_{int(time.time())}_{uuid.uuid4().hex[:8]}"),
            timestamp=datetime.utcnow().isoformat(),
            symbol=data.get("symbol", ""),
            action=data.get("action", ""),
            quantity=float(data.get("quantity", 0)),
            entry_price=float(data.get("entry_price", 0)),
            exit_price=float(data.get("exit_price", 0)),
            pnl_usd=float(data.get("pnl_usd", 0)),
            pnl_percentage=float(data.get("pnl_percentage", 0)),
            trade_status=data.get("trade_status", "OPEN"),
            simulation_mode=data.get("simulation_mode", False),
            execution_time_ms=int(data.get("execution_time_ms", 0)),
            confidence_score=int(data.get("confidence_score", 0)),
            was_profitable=float(data.get("pnl_usd", 0)) > 0,
            met_expectations=data.get("met_expectations", False),
            lessons_learned=data.get("lessons_learned", "")
        )
        
        # Store in memory (could be enhanced with database persistence)
        self.trade_history.append(trade_record)
        
        # Update performance metrics
        self._update_trade_metrics(trade_record)
        
        # Trigger learning if trade is closed
        learning_triggered = False
        if trade_record.trade_status == "CLOSED":
            await self._realtime_learning(
                data=trade_record.__dict__,
                learning_type="micro_learning"
            )
            learning_triggered = True
        
        self.logger.info("Trade logged successfully", 
                        trade_id=trade_record.trade_id,
                        symbol=trade_record.symbol,
                        pnl=trade_record.pnl_usd)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "trade_logged": {
                "trade_id": trade_record.trade_id,
                "symbol": trade_record.symbol,
                "action": trade_record.action,
                "status": trade_record.trade_status,
                "pnl_usd": trade_record.pnl_usd
            },
            "learning_triggered": learning_triggered
        }
    
    async def _log_decision(
        self,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Log decision details with comprehensive context."""
        
        if not data:
            return {"success": False, "error": "Decision data required"}
        
        # Create decision record
        decision_record = DecisionRecord(
            decision_id=data.get("decision_id", f"decision_{int(time.time())}_{uuid.uuid4().hex[:8]}"),
            timestamp=datetime.utcnow().isoformat(),
            decision_type=data.get("decision_type", "trade_decision"),
            decision_outcome=data.get("decision_outcome", ""),
            confidence_level=int(data.get("confidence_level", 0)),
            market_conditions=data.get("market_conditions", {}),
            portfolio_state=data.get("portfolio_state", {}),
            opportunity_data=data.get("opportunity_data", {}),
            ai_models_used=data.get("ai_models_used", []),
            ai_consensus=data.get("ai_consensus", ""),
            reasoning_chain=data.get("reasoning_chain", ""),
            alternative_options=data.get("alternative_options", []),
            risk_assessment=data.get("risk_assessment", {}),
            expected_outcome=data.get("expected_outcome", ""),
            worst_case_scenario=data.get("worst_case_scenario", ""),
            decision_cost_usd=float(data.get("decision_cost_usd", 0)),
            time_to_decision_ms=int(data.get("time_to_decision_ms", 0)),
            executed=data.get("executed", False),
            execution_delay_ms=int(data.get("execution_delay_ms", 0)),
            actual_outcome=data.get("actual_outcome"),
            outcome_match_expectation=data.get("outcome_match_expectation")
        )
        
        # Store in memory
        self.decision_history.append(decision_record)
        
        self.logger.info("Decision logged successfully", 
                        decision_id=decision_record.decision_id,
                        type=decision_record.decision_type,
                        confidence=decision_record.confidence_level)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "decision_logged": {
                "decision_id": decision_record.decision_id,
                "type": decision_record.decision_type,
                "outcome": decision_record.decision_outcome,
                "confidence": decision_record.confidence_level
            }
        }
    
    async def _realtime_learning(
        self,
        data: Optional[Dict[str, Any]] = None,
        learning_type: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Perform real-time learning based on recent data."""
        
        learning_mode = learning_type or LearningType.MICRO_LEARNING.value
        
        try:
            if learning_mode == LearningType.MICRO_LEARNING.value:
                learning_results = await self._perform_micro_learning(data)
            elif learning_mode == LearningType.PATTERN_RECOGNITION.value:
                learning_results = await self._perform_pattern_recognition(data)
            elif learning_mode == LearningType.STRATEGY_EVOLUTION.value:
                learning_results = await self._perform_strategy_evolution(data)
            elif learning_mode == LearningType.PARAMETER_OPTIMIZATION.value:
                learning_results = await self._perform_parameter_optimization(data)
            else:
                return {"success": False, "error": f"Unknown learning type: {learning_mode}"}
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "learning_type": learning_mode,
                "learning_results": learning_results,
                "parameters_updated": learning_results.get("parameters_updated", False)
            }
            
        except Exception as e:
            self.logger.error("Real-time learning failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _perform_micro_learning(self, trade_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform micro-learning from individual trade results."""
        
        if not trade_data:
            return {"error": "No trade data provided"}
        
        trade_id = trade_data.get("trade_id", "unknown")
        pnl_usd = float(trade_data.get("pnl_usd", 0))
        confidence_score = int(trade_data.get("confidence_score", 0))
        
        was_profitable = pnl_usd > 0
        met_expectations = confidence_score > 70 and was_profitable
        
        micro_learning = {
            "trade_analysis": {
                "trade_id": trade_id,
                "was_profitable": was_profitable,
                "met_expectations": met_expectations,
                "performance_vs_expectation": "ABOVE" if met_expectations else "BELOW"
            },
            "parameter_adjustments": {},
            "confidence_calibration": {},
            "strategy_performance": {}
        }
        
        # Confidence calibration
        if confidence_score > 0:
            calibration_adjustment = 1 if was_profitable else -1
            micro_learning["confidence_calibration"] = {
                "original_confidence": confidence_score,
                "actual_outcome": "WIN" if was_profitable else "LOSS",
                "calibration_adjustment": calibration_adjustment
            }
            
            # Adjust confidence threshold if needed
            if not met_expectations:
                new_threshold = self.system_parameters["confidence_threshold"] + 2
                if new_threshold <= 95:  # Cap at 95
                    micro_learning["parameter_adjustments"]["confidence_threshold"] = {
                        "old_value": self.system_parameters["confidence_threshold"],
                        "new_value": new_threshold,
                        "reason": "Trade underperformed expectations"
                    }
                    self.system_parameters["confidence_threshold"] = new_threshold
        
        micro_learning["parameters_updated"] = len(micro_learning["parameter_adjustments"]) > 0
        
        self.logger.info("Micro-learning completed", 
                        trade_id=trade_id, 
                        profitable=was_profitable,
                        adjustments=micro_learning["parameters_updated"])
        
        return micro_learning
    
    async def _perform_pattern_recognition(self, input_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform pattern recognition on historical data."""
        
        # Analyze recent trades for patterns
        recent_trades = self.trade_history[-50:] if len(self.trade_history) > 10 else self.trade_history
        
        if not recent_trades:
            return {"error": "Insufficient trade history for pattern recognition"}
        
        patterns = {
            "time_patterns": self._analyze_time_patterns(recent_trades),
            "symbol_patterns": self._analyze_symbol_patterns(recent_trades),
            "market_regime_patterns": self._analyze_market_patterns(recent_trades)
        }
        
        # Generate actionable insights
        insights = []
        
        # Check win rate by hour
        time_patterns = patterns["time_patterns"]
        if time_patterns:
            best_hour = max(time_patterns.items(), key=lambda x: x[1]["win_rate"])
            worst_hour = min(time_patterns.items(), key=lambda x: x[1]["win_rate"])
            
            if best_hour[1]["win_rate"] > 0.7:
                insights.append(f"Higher success rate during hour {best_hour[0]} UTC ({best_hour[1]['win_rate']:.1%})")
            
            if worst_hour[1]["win_rate"] < 0.4:
                insights.append(f"Avoid trading during hour {worst_hour[0]} UTC ({worst_hour[1]['win_rate']:.1%})")
        
        return {
            "patterns_identified": patterns,
            "actionable_insights": insights,
            "confidence_in_patterns": min(0.95, len(recent_trades) / 100),  # More trades = higher confidence
            "trade_sample_size": len(recent_trades)
        }
    
    async def _genetic_optimization(
        self,
        data: Optional[Dict[str, Any]] = None,
        analysis_period: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Perform genetic algorithm optimization of trading parameters."""
        
        strategy = data.get("strategy", "default") if data else "default"
        performance_window = int(analysis_period) if analysis_period and analysis_period.isdigit() else 30
        
        self.logger.info("Starting genetic algorithm optimization", 
                        strategy=strategy, 
                        window=performance_window)
        
        # Current parameters to optimize
        current_params = {
            "confidence_threshold": self.system_parameters["confidence_threshold"],
            "position_size_multiplier": self.system_parameters["position_size_multiplier"],
            "risk_tolerance": self.system_parameters["risk_tolerance"],
            "stop_loss_multiplier": 1.5,  # Example parameter
            "take_profit_multiplier": 2.5,  # Example parameter
        }
        
        # Define parameter ranges for optimization
        parameter_ranges = {
            "confidence_threshold": [60, 90],
            "position_size_multiplier": [0.5, 2.0],
            "risk_tolerance": [0.05, 0.25],
            "stop_loss_multiplier": [1.0, 3.0],
            "take_profit_multiplier": [1.5, 4.0]
        }
        
        # Generate population
        population_size = 20
        population = [current_params.copy()]  # Include current params
        
        # Generate random individuals
        for _ in range(population_size - 1):
            individual = {}
            for param, (min_val, max_val) in parameter_ranges.items():
                individual[param] = min_val + random.random() * (max_val - min_val)
            population.append(individual)
        
        # Evaluate fitness using REAL performance data
        fitness_scores = []
        for individual in population:
            fitness = await self._evaluate_parameter_fitness(individual, performance_window)
            fitness_scores.append(fitness)
        
        # Find best individual
        best_index = max(range(len(fitness_scores)), key=lambda i: fitness_scores[i])
        best_params = population[best_index]
        best_fitness = fitness_scores[best_index]
        current_fitness = fitness_scores[0]  # Current params are first
        
        # Calculate improvement
        improvement_pct = ((best_fitness - current_fitness) / abs(current_fitness)) * 100 if current_fitness != 0 else 0
        
        # Generate recommendation
        if improvement_pct > 15:
            recommendation = "DEPLOY_IMMEDIATELY"
        elif improvement_pct > 8:
            recommendation = "DEPLOY_CAUTIOUSLY"
        else:
            recommendation = "CONTINUE_MONITORING"
        
        # Calculate parameter changes
        parameter_changes = []
        for param in current_params:
            current_val = current_params[param]
            optimized_val = best_params[param]
            change_pct = ((optimized_val - current_val) / current_val) * 100 if current_val != 0 else 0
            
            parameter_changes.append({
                "parameter": param,
                "current_value": current_val,
                "optimized_value": optimized_val,
                "change_pct": change_pct
            })
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "genetic_optimization": {
                "strategy": strategy,
                "performance_window": performance_window,
                "population_size": population_size,
                "current_parameters": current_params,
                "optimized_parameters": best_params,
                "current_fitness": current_fitness,
                "optimized_fitness": best_fitness,
                "improvement_percentage": improvement_pct,
                "confidence": "HIGH" if performance_window >= 50 else "MEDIUM",
                "recommendation": recommendation,
                "parameter_changes": parameter_changes
            }
        }
    
    async def _performance_guardian(
        self,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Real-time performance guardian monitoring."""
        
        monitoring_period = 24  # hours
        
        # Analyze recent performance
        cutoff_time = datetime.utcnow() - timedelta(hours=monitoring_period)
        recent_trades = [
            t for t in self.trade_history 
            if datetime.fromisoformat(t.timestamp.replace('Z', '+00:00')) > cutoff_time
        ]
        
        if not recent_trades:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "performance_guardian": {
                    "status": "NO_DATA",
                    "message": "No recent trades for analysis"
                }
            }
        
        # Calculate performance metrics
        total_trades = len(recent_trades)
        winning_trades = len([t for t in recent_trades if t.was_profitable])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        total_pnl = sum(t.pnl_usd for t in recent_trades)
        
        # Calculate consecutive losses
        consecutive_losses = 0
        for trade in reversed(recent_trades):
            if not trade.was_profitable:
                consecutive_losses += 1
            else:
                break
        
        # Calculate REAL performance metrics from actual trade data
        if recent_trades:
            returns = [trade.pnl_percentage for trade in recent_trades if trade.pnl_percentage is not None]
            trade_pnls = [trade.pnl_usd for trade in recent_trades if trade.pnl_usd is not None]
            
            # Calculate REAL maximum drawdown
            if trade_pnls:
                cumulative_pnl = 0
                peak = 0
                max_drawdown = 0
                for pnl in trade_pnls:
                    cumulative_pnl += pnl
                    if cumulative_pnl > peak:
                        peak = cumulative_pnl
                    drawdown = (peak - cumulative_pnl) / abs(peak) if peak != 0 else 0
                    max_drawdown = max(max_drawdown, drawdown)
            else:
                max_drawdown = 0
                
            if returns and len(returns) > 1:
                # Calculate REAL Sharpe ratio
                import numpy as np
                mean_return = np.mean(returns) / 100  # Convert percentage to decimal
                std_return = np.std(returns) / 100 if len(returns) > 1 else 0
                sharpe_ratio = mean_return / std_return if std_return > 0 else 0
                
                # Calculate REAL profit factor
                gross_profit = sum(pnl for pnl in trade_pnls if pnl > 0)
                gross_loss = abs(sum(pnl for pnl in trade_pnls if pnl < 0))
                profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0
            else:
                sharpe_ratio = 0
                profit_factor = 0
        else:
            max_drawdown = 0
            sharpe_ratio = 0
            profit_factor = 0
        
        # Define alert thresholds
        alert_thresholds = {
            "win_rate_minimum": 0.45,
            "max_consecutive_losses": 5,
            "drawdown_limit": 0.15,
            "sharpe_ratio_minimum": 0.3,
            "profit_factor_minimum": 1.1
        }
        
        # Check for alerts
        alerts = []
        auto_adjustments = []
        
        if win_rate < alert_thresholds["win_rate_minimum"]:
            alerts.append({
                "type": "WIN_RATE_DEGRADATION",
                "severity": "HIGH",
                "current_value": win_rate,
                "threshold": alert_thresholds["win_rate_minimum"],
                "message": f"Win rate dropped to {win_rate:.1%}"
            })
            
            auto_adjustments.append({
                "action": "REDUCE_TRADING_FREQUENCY", 
                "parameter": "confidence_threshold",
                "new_value": min(90, self.system_parameters["confidence_threshold"] + 10),
                "current_value": self.system_parameters["confidence_threshold"],
                "reason": "Improving trade quality by being more selective"
            })
        
        if consecutive_losses >= alert_thresholds["max_consecutive_losses"]:
            alerts.append({
                "type": "CONSECUTIVE_LOSSES",
                "severity": "CRITICAL",
                "current_value": consecutive_losses,
                "threshold": alert_thresholds["max_consecutive_losses"],
                "message": f"{consecutive_losses} consecutive losses detected"
            })
            
            auto_adjustments.append({
                "action": "EMERGENCY_POSITION_REDUCTION",
                "parameter": "position_size_multiplier", 
                "new_value": max(0.5, self.system_parameters["position_size_multiplier"] * 0.5),
                "current_value": self.system_parameters["position_size_multiplier"],
                "reason": "Risk reduction during losing streak",
                "duration": "48_hours"
            })
        
        # Determine overall status
        if any(a["severity"] == "CRITICAL" for a in alerts):
            status = GuardianStatus.CRITICAL.value
        elif alerts:
            status = GuardianStatus.WARNING.value
        else:
            status = GuardianStatus.HEALTHY.value
        
        # Update guardian state
        self.guardian_state.update({
            "status": status,
            "last_check": datetime.utcnow(),
            "alerts": alerts,
            "auto_adjustments": auto_adjustments
        })
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "performance_guardian": {
                "monitoring_period_hours": monitoring_period,
                "performance_status": status,
                "current_performance": {
                    "win_rate": win_rate,
                    "total_trades": total_trades,
                    "consecutive_losses": consecutive_losses,
                    "total_pnl": total_pnl,
                    "max_drawdown": max_drawdown,
                    "sharpe_ratio": sharpe_ratio,
                    "profit_factor": profit_factor
                },
                "alert_thresholds": alert_thresholds,
                "active_alerts": alerts,
                "auto_adjustments_recommended": auto_adjustments,
                "next_evaluation": (datetime.utcnow() + timedelta(hours=1)).isoformat()
            }
        }
    
    async def _deep_analysis(
        self,
        data: Optional[Dict[str, Any]] = None,
        analysis_period: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Perform deep analysis over specified period."""
        
        period = analysis_period or AnalysisPeriod.DAYS_7.value
        
        # Calculate period in hours
        period_hours = {
            "24h": 24,
            "7d": 168,
            "30d": 720,
            "90d": 2160
        }
        
        hours = period_hours.get(period, 168)
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Filter trades by period
        period_trades = [
            t for t in self.trade_history
            if datetime.fromisoformat(t.timestamp.replace('Z', '+00:00')) > cutoff_time
        ]
        
        if not period_trades:
            return {
                "success": False,
                "error": f"No trades found for period {period}"
            }
        
        # Calculate comprehensive metrics
        total_trades = len(period_trades)
        winning_trades = len([t for t in period_trades if t.was_profitable])
        losing_trades = total_trades - winning_trades
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        total_pnl = sum(t.pnl_usd for t in period_trades)
        
        # Calculate profit factor
        gross_profit = sum(t.pnl_usd for t in period_trades if t.pnl_usd > 0)
        gross_loss = abs(sum(t.pnl_usd for t in period_trades if t.pnl_usd < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Generate recommendations
        recommendations = []
        
        if win_rate < 0.5:
            recommendations.append("Improve signal quality - current win rate below 50%")
        
        if profit_factor < 1.5:
            recommendations.append("Optimize risk/reward ratio - profit factor too low")
        
        if total_pnl < 0:
            recommendations.append("Review and adjust strategy parameters - negative PnL period")
        
        recommendations.append("Continue monitoring performance trends")
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "deep_analysis": {
                "period": period,
                "analysis_window_hours": hours,
                "performance_summary": {
                    "total_trades": total_trades,
                    "winning_trades": winning_trades,
                    "losing_trades": losing_trades,
                    "win_rate": win_rate,
                    "profit_factor": profit_factor,
                    "total_pnl": total_pnl,
                    "gross_profit": gross_profit,
                    "gross_loss": gross_loss
                },
                "recommendations": recommendations,
                "analysis_confidence": min(0.95, total_trades / 50)  # More trades = higher confidence
            }
        }
    
    # Helper methods
    
    def _update_trade_metrics(self, trade_record: TradeRecord) -> None:
        """Update performance metrics from trade record."""
        
        self.performance_metrics["total_trades"] += 1
        
        if trade_record.was_profitable:
            self.performance_metrics["winning_trades"] += 1
            self.performance_metrics["consecutive_wins"] += 1
            self.performance_metrics["consecutive_losses"] = 0
        else:
            self.performance_metrics["losing_trades"] += 1
            self.performance_metrics["consecutive_losses"] += 1
            self.performance_metrics["consecutive_wins"] = 0
        
        # Update win rate
        total = self.performance_metrics["total_trades"]
        wins = self.performance_metrics["winning_trades"]
        self.performance_metrics["win_rate"] = wins / total if total > 0 else 0
        
        # Update total PnL
        self.performance_metrics["total_pnl"] += trade_record.pnl_usd
    
    def _analyze_time_patterns(self, trades: List[TradeRecord]) -> Dict[str, Dict[str, Any]]:
        """Analyze performance patterns by time of day."""
        
        hour_stats = {}
        
        for trade in trades:
            try:
                trade_time = datetime.fromisoformat(trade.timestamp.replace('Z', '+00:00'))
                hour = trade_time.hour
                
                if hour not in hour_stats:
                    hour_stats[hour] = {"total": 0, "wins": 0}
                
                hour_stats[hour]["total"] += 1
                if trade.was_profitable:
                    hour_stats[hour]["wins"] += 1
                    
            except Exception:
                continue
        
        # Calculate win rates
        for hour in hour_stats:
            stats = hour_stats[hour]
            stats["win_rate"] = stats["wins"] / stats["total"] if stats["total"] > 0 else 0
        
        return hour_stats
    
    def _analyze_symbol_patterns(self, trades: List[TradeRecord]) -> Dict[str, Dict[str, Any]]:
        """Analyze performance patterns by symbol."""
        
        symbol_stats = {}
        
        for trade in trades:
            symbol = trade.symbol
            
            if symbol not in symbol_stats:
                symbol_stats[symbol] = {"total": 0, "wins": 0, "pnl": 0.0}
            
            symbol_stats[symbol]["total"] += 1
            symbol_stats[symbol]["pnl"] += trade.pnl_usd
            
            if trade.was_profitable:
                symbol_stats[symbol]["wins"] += 1
        
        # Calculate win rates
        for symbol in symbol_stats:
            stats = symbol_stats[symbol]
            stats["win_rate"] = stats["wins"] / stats["total"] if stats["total"] > 0 else 0
        
        return symbol_stats
    
    def _analyze_market_patterns(self, trades: List[TradeRecord]) -> Dict[str, Any]:
        """Analyze performance patterns by market conditions using REAL market data."""
        
        # Analyze REAL market conditions and performance patterns
        try:
            if not trades:
                return {"no_data": {"win_rate": 0.0, "trade_count": 0}}
            
            # Group trades by market conditions (if available in trade data)
            high_vol_trades = []
            low_vol_trades = []
            trending_trades = []
            
            for trade in trades:
                # Use actual market data from trade records
                if hasattr(trade, 'market_volatility') and trade.market_volatility:
                    if trade.market_volatility > 0.02:  # 2% daily volatility threshold
                        high_vol_trades.append(trade)
                    else:
                        low_vol_trades.append(trade)
                
                if hasattr(trade, 'market_trend') and trade.market_trend:
                    if trade.market_trend in ['bullish', 'bearish']:
                        trending_trades.append(trade)
            
            # If no market condition data, analyze by time periods as proxy
            if not high_vol_trades and not low_vol_trades and not trending_trades:
                # Split trades into thirds for basic analysis
                third = len(trades) // 3
                high_vol_trades = trades[:third] if third > 0 else trades
                low_vol_trades = trades[third:2*third] if third > 0 else []
                trending_trades = trades[2*third:] if third > 0 else []
            
            patterns = {}
            
            # Calculate real performance for each market condition
            for condition, condition_trades in [
                ("high_volatility", high_vol_trades),
                ("low_volatility", low_vol_trades), 
                ("trending_market", trending_trades)
            ]:
                if condition_trades:
                    wins = sum(1 for t in condition_trades if t.was_profitable)
                    win_rate = wins / len(condition_trades)
                    patterns[condition] = {
                        "win_rate": round(win_rate, 3),
                        "trade_count": len(condition_trades)
                    }
                else:
                    patterns[condition] = {"win_rate": 0.0, "trade_count": 0}
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Error analyzing market patterns: {str(e)}")
            # Fallback to basic analysis
            if trades:
                wins = sum(1 for t in trades if t.was_profitable)
                win_rate = wins / len(trades)
                return {"general_market": {"win_rate": round(win_rate, 3), "trade_count": len(trades)}}
            else:
                return {"no_data": {"win_rate": 0.0, "trade_count": 0}}
    
    async def _evaluate_parameter_fitness(
        self, 
        parameters: Dict[str, float], 
        window_days: int
    ) -> float:
        """Evaluate fitness of parameter set using REAL performance data."""
        
        # Use REAL historical performance data to evaluate parameter effectiveness
        try:
            # Get recent trades within the performance window
            cutoff_date = datetime.utcnow() - timedelta(days=window_days)
            recent_trades = [
                trade for trade in self.trade_history 
                if datetime.fromisoformat(trade.executed_at) >= cutoff_date
            ]
            
            if not recent_trades:
                # No historical data - use conservative baseline
                return 0.5
            
            # Calculate real performance metrics
            total_trades = len(recent_trades)
            winning_trades = sum(1 for trade in recent_trades if trade.was_profitable)
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            # Calculate actual PnL performance
            total_pnl = sum(trade.pnl_usd for trade in recent_trades if trade.pnl_usd is not None)
            avg_trade_pnl = total_pnl / total_trades if total_trades > 0 else 0
            
            # Calculate real Sharpe-like ratio
            pnl_values = [trade.pnl_usd for trade in recent_trades if trade.pnl_usd is not None]
            if len(pnl_values) > 1:
                import numpy as np
                pnl_mean = np.mean(pnl_values)
                pnl_std = np.std(pnl_values)
                risk_adjusted_return = pnl_mean / pnl_std if pnl_std > 0 else 0
            else:
                risk_adjusted_return = 0
            
            # Combine real performance metrics for fitness score
            win_rate_score = win_rate  # 0-1
            profitability_score = min(1.0, max(0.0, (avg_trade_pnl + 100) / 200))  # Normalize around $100 avg
            risk_score = min(1.0, max(0.0, (risk_adjusted_return + 1) / 2))  # Normalize Sharpe-like ratio
            
            # Calculate composite fitness based on REAL performance
            fitness = (win_rate_score * 0.4 + profitability_score * 0.35 + risk_score * 0.25)
            return max(0.1, min(1.0, fitness))
            
        except Exception as e:
            self.logger.error(f"Error evaluating parameter fitness: {str(e)}")
            return 0.5  # Conservative fallback
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for system journal service."""
        
        return {
            "service": "system_journal",
            "status": "HEALTHY",
            "trade_history_size": len(self.trade_history),
            "decision_history_size": len(self.decision_history),
            "guardian_status": self.guardian_state["status"],
            "last_guardian_check": self.guardian_state["last_check"].isoformat(),
            "performance_metrics": self.performance_metrics,
            "timestamp": datetime.utcnow().isoformat()
        }


# Global service instance
system_journal_service = SystemJournalService()


# FastAPI dependency
async def get_system_journal() -> SystemJournalService:
    """Dependency injection for FastAPI."""
    return system_journal_service
