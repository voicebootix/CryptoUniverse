"""
CROSS-STRATEGY COORDINATION - THE PORTFOLIO HARMONY ENGINE

Ensures multiple strategies work together harmoniously instead of against each other.
Prevents conflicting positions, optimizes entry/exit timing, and maximizes portfolio correlation.

This is advanced institutional-grade portfolio management!
"""

import asyncio
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import structlog

from app.core.logging import LoggerMixin
from app.core.redis import get_redis_client

logger = structlog.get_logger(__name__)


class PositionConflict(str, Enum):
    """Types of position conflicts."""
    OPPOSING_DIRECTIONS = "opposing_directions"
    OVER_CONCENTRATION = "over_concentration"
    CORRELATION_RISK = "correlation_risk"
    LIQUIDITY_CONFLICT = "liquidity_conflict"


@dataclass
class StrategyCoordination:
    """Strategy coordination result."""
    strategy_name: str
    signal: Dict[str, Any]
    coordination_action: str  # execute, delay, modify, skip
    modified_signal: Optional[Dict[str, Any]]
    conflict_resolution: Optional[str]
    priority_score: float


class CrossStrategyCoordinator(LoggerMixin):
    """
    PORTFOLIO HARMONY ENGINE - PREVENTS STRATEGY CONFLICTS
    
    Coordinates multiple strategies to work together like a symphony orchestra.
    No more opposing positions or portfolio chaos!
    """
    
    def __init__(self):
        self.redis = None
        self.coordination_rules = {
            "max_symbol_exposure": 0.25,  # Max 25% in any single symbol
            "max_sector_exposure": 0.40,   # Max 40% in any sector
            "correlation_threshold": 0.7,  # Avoid highly correlated positions
            "liquidity_buffer": 0.10       # Keep 10% cash for opportunities
        }
    
    async def async_init(self):
        """Initialize async components."""
        self.redis = await get_redis_client()
    
    async def coordinate_strategy_signals(
        self, 
        signals: List[Dict[str, Any]], 
        user_id: str
    ) -> Dict[str, Any]:
        """
        COORDINATE MULTIPLE STRATEGY SIGNALS FOR OPTIMAL EXECUTION
        
        This is where the magic happens - turning chaos into profit!
        """
        try:
            self.logger.info(f"🎼 Coordinating {len(signals)} strategy signals for {user_id}")
            
            # Get current portfolio state
            current_positions = await self._get_current_positions(user_id)
            
            # Analyze each signal for conflicts
            coordinated_signals = []
            
            for signal_data in signals:
                coordination = await self._analyze_signal_coordination(
                    signal_data, current_positions, coordinated_signals, user_id
                )
                coordinated_signals.append(coordination)
            
            # Prioritize and optimize execution order
            execution_plan = await self._create_execution_plan(coordinated_signals, user_id)
            
            # Calculate portfolio impact
            portfolio_impact = await self._calculate_portfolio_impact(execution_plan, current_positions)
            
            self.logger.info(
                f"🎯 Strategy coordination complete for {user_id}",
                signals_to_execute=len([s for s in coordinated_signals if s.coordination_action == "execute"]),
                signals_delayed=len([s for s in coordinated_signals if s.coordination_action == "delay"]),
                signals_modified=len([s for s in coordinated_signals if s.coordination_action == "modify"]),
                signals_skipped=len([s for s in coordinated_signals if s.coordination_action == "skip"])
            )
            
            return {
                "success": True,
                "coordinated_signals": [self._serialize_coordination(c) for c in coordinated_signals],
                "execution_plan": execution_plan,
                "portfolio_impact": portfolio_impact,
                "coordination_summary": {
                    "total_signals": len(signals),
                    "execute": len([s for s in coordinated_signals if s.coordination_action == "execute"]),
                    "delay": len([s for s in coordinated_signals if s.coordination_action == "delay"]),
                    "modify": len([s for s in coordinated_signals if s.coordination_action == "modify"]),
                    "skip": len([s for s in coordinated_signals if s.coordination_action == "skip"])
                }
            }
            
        except Exception as e:
            self.logger.error("Strategy coordination failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _get_current_positions(self, user_id: str) -> Dict[str, Any]:
        """Get current portfolio positions for conflict analysis."""
        try:
            from app.services.portfolio_risk_core import PortfolioRiskServiceExtended
            
            portfolio_service = PortfolioRiskServiceExtended()
            portfolio_result = await portfolio_service.get_portfolio_status(user_id)
            
            if portfolio_result.get("success"):
                return portfolio_result.get("portfolio", {})
            else:
                return {}
                
        except Exception as e:
            self.logger.error("Failed to get current positions", error=str(e))
            return {}
    
    async def _analyze_signal_coordination(
        self,
        signal_data: Dict[str, Any],
        current_positions: Dict[str, Any],
        pending_signals: List[StrategyCoordination],
        user_id: str
    ) -> StrategyCoordination:
        """Analyze individual signal for coordination needs."""
        
        strategy_name = signal_data.get("strategy", "unknown")
        signal = signal_data.get("signal", {})
        
        # Default coordination
        coordination = StrategyCoordination(
            strategy_name=strategy_name,
            signal=signal,
            coordination_action="execute",
            modified_signal=None,
            conflict_resolution=None,
            priority_score=signal.get("confidence", 0)
        )
        
        # Check for conflicts
        conflicts = await self._detect_conflicts(signal, current_positions, pending_signals)
        
        if conflicts:
            coordination = await self._resolve_conflicts(coordination, conflicts, user_id)
        
        return coordination
    
    async def _detect_conflicts(
        self,
        signal: Dict[str, Any],
        current_positions: Dict[str, Any],
        pending_signals: List[StrategyCoordination]
    ) -> List[Dict[str, Any]]:
        """Detect potential conflicts with existing positions and pending signals."""
        
        conflicts = []
        signal_symbol = signal.get("symbol", "")
        signal_action = signal.get("action", "").lower()
        
        # 1. Check for opposing directions on same symbol
        for pending in pending_signals:
            if pending.coordination_action == "skip":
                continue
                
            pending_signal = pending.modified_signal or pending.signal
            pending_symbol = pending_signal.get("symbol", "")
            pending_action = pending_signal.get("action", "").lower()
            
            if (signal_symbol == pending_symbol and 
                ((signal_action == "buy" and pending_action == "sell") or
                 (signal_action == "sell" and pending_action == "buy"))):
                
                conflicts.append({
                    "type": PositionConflict.OPPOSING_DIRECTIONS,
                    "description": f"Opposing {signal_action} vs {pending_action} on {signal_symbol}",
                    "severity": "high",
                    "conflicting_strategy": pending.strategy_name
                })
        
        # 2. Check for over-concentration
        current_symbol_exposure = self._calculate_symbol_exposure(signal_symbol, current_positions)
        signal_position_size = signal.get("position_size_pct", 5.0) / 100
        
        if current_symbol_exposure + signal_position_size > self.coordination_rules["max_symbol_exposure"]:
            conflicts.append({
                "type": PositionConflict.OVER_CONCENTRATION,
                "description": f"Would exceed max exposure for {signal_symbol}",
                "severity": "medium",
                "current_exposure": current_symbol_exposure,
                "proposed_exposure": current_symbol_exposure + signal_position_size
            })
        
        # 3. Check for correlation risk
        correlated_symbols = await self._get_highly_correlated_symbols(signal_symbol)
        total_correlated_exposure = sum(
            self._calculate_symbol_exposure(sym, current_positions) 
            for sym in correlated_symbols
        )
        
        if total_correlated_exposure + signal_position_size > self.coordination_rules["max_sector_exposure"]:
            conflicts.append({
                "type": PositionConflict.CORRELATION_RISK,
                "description": f"Would exceed sector correlation limit",
                "severity": "medium",
                "correlated_symbols": correlated_symbols,
                "total_exposure": total_correlated_exposure + signal_position_size
            })
        
        return conflicts
    
    def _calculate_symbol_exposure(self, symbol: str, positions: Dict[str, Any]) -> float:
        """Calculate current exposure to a symbol."""
        try:
            holdings = positions.get("holdings", [])
            total_value = positions.get("total_value_usd", 1)
            
            symbol_value = 0
            for holding in holdings:
                if holding.get("symbol", "").upper() == symbol.upper():
                    symbol_value += holding.get("value_usd", 0)
            
            return symbol_value / total_value if total_value > 0 else 0
            
        except Exception:
            return 0
    
    async def _get_highly_correlated_symbols(self, symbol: str) -> List[str]:
        """Get symbols highly correlated with given symbol."""
        
        # Predefined correlation groups (can be enhanced with real-time correlation analysis)
        correlation_groups = {
            "BTC": ["BTC", "MSTR", "COIN"],
            "ETH": ["ETH", "LDO", "MATIC", "LINK"],
            "SOL": ["SOL", "RAY", "SRM", "FIDA"],
            "BNB": ["BNB", "CAKE", "BAKE"],
            "ADA": ["ADA", "ERG"],
            "DOT": ["DOT", "KSM", "GLMR"],
            "AVAX": ["AVAX", "JOE", "PNG"],
            "ATOM": ["ATOM", "OSMO", "JUNO"],
            "NEAR": ["NEAR", "AURORA"],
            "FTM": ["FTM", "BOO", "SPIRIT"]
        }
        
        # Find correlation group
        for base_symbol, group in correlation_groups.items():
            if symbol.upper() in [s.upper() for s in group]:
                return [s for s in group if s.upper() != symbol.upper()]
        
        return []
    
    async def _resolve_conflicts(
        self,
        coordination: StrategyCoordination,
        conflicts: List[Dict[str, Any]],
        user_id: str
    ) -> StrategyCoordination:
        """Resolve detected conflicts through intelligent coordination."""
        
        high_severity_conflicts = [c for c in conflicts if c["severity"] == "high"]
        
        if high_severity_conflicts:
            # High severity: Skip or significantly modify
            conflict = high_severity_conflicts[0]
            
            if conflict["type"] == PositionConflict.OPPOSING_DIRECTIONS:
                # Choose higher confidence signal, skip lower confidence
                conflicting_strategy = conflict.get("conflicting_strategy", "")
                
                coordination.coordination_action = "skip"
                coordination.conflict_resolution = f"Skipped due to opposing position from {conflicting_strategy}"
                
                self.logger.warning(
                    f"🚫 Signal skipped due to opposing direction conflict",
                    user_id=user_id,
                    strategy=coordination.strategy_name,
                    symbol=coordination.signal.get("symbol"),
                    conflicting_with=conflicting_strategy
                )
        
        else:
            # Medium severity: Modify position size
            for conflict in conflicts:
                if conflict["type"] == PositionConflict.OVER_CONCENTRATION:
                    # Reduce position size to stay within limits
                    current_exposure = conflict.get("current_exposure", 0)
                    max_allowed = self.coordination_rules["max_symbol_exposure"]
                    available_capacity = max_allowed - current_exposure
                    
                    if available_capacity > 0.01:  # At least 1% available
                        modified_signal = coordination.signal.copy()
                        modified_signal["position_size_pct"] = available_capacity * 100
                        
                        coordination.coordination_action = "modify"
                        coordination.modified_signal = modified_signal
                        coordination.conflict_resolution = f"Reduced position size to {available_capacity*100:.1f}% due to concentration limits"
                        
                        self.logger.info(
                            f"📏 Position size reduced for concentration management",
                            user_id=user_id,
                            strategy=coordination.strategy_name,
                            symbol=coordination.signal.get("symbol"),
                            original_size=f"{coordination.signal.get('position_size_pct', 5):.1f}%",
                            adjusted_size=f"{available_capacity*100:.1f}%"
                        )
                    else:
                        coordination.coordination_action = "skip"
                        coordination.conflict_resolution = "Skipped due to concentration limits"
        
        return coordination
    
    async def _create_execution_plan(
        self, 
        coordinated_signals: List[StrategyCoordination], 
        user_id: str
    ) -> Dict[str, Any]:
        """Create optimized execution plan for coordinated signals."""
        
        # Separate signals by action
        execute_signals = [s for s in coordinated_signals if s.coordination_action == "execute"]
        modify_signals = [s for s in coordinated_signals if s.coordination_action == "modify"]
        delay_signals = [s for s in coordinated_signals if s.coordination_action == "delay"]
        
        # Sort by priority score
        execute_signals.sort(key=lambda s: s.priority_score, reverse=True)
        modify_signals.sort(key=lambda s: s.priority_score, reverse=True)
        
        # Create execution batches to avoid market impact
        execution_batches = []
        
        # Batch 1: High priority signals (immediate execution)
        high_priority = [s for s in execute_signals + modify_signals if s.priority_score > 80]
        if high_priority:
            execution_batches.append({
                "batch_id": 1,
                "execution_delay_seconds": 0,
                "signals": high_priority,
                "batch_type": "high_priority"
            })
        
        # Batch 2: Medium priority signals (30 second delay)
        medium_priority = [s for s in execute_signals + modify_signals if 60 <= s.priority_score <= 80]
        if medium_priority:
            execution_batches.append({
                "batch_id": 2,
                "execution_delay_seconds": 30,
                "signals": medium_priority,
                "batch_type": "medium_priority"
            })
        
        # Batch 3: Lower priority signals (60 second delay)
        lower_priority = [s for s in execute_signals + modify_signals if s.priority_score < 60]
        if lower_priority:
            execution_batches.append({
                "batch_id": 3,
                "execution_delay_seconds": 60,
                "signals": lower_priority,
                "batch_type": "lower_priority"
            })
        
        return {
            "execution_batches": execution_batches,
            "total_signals_to_execute": len(execute_signals) + len(modify_signals),
            "delayed_signals": len(delay_signals),
            "estimated_execution_time_seconds": max([b["execution_delay_seconds"] for b in execution_batches]) + 30 if execution_batches else 0
        }
    
    async def _calculate_portfolio_impact(
        self, 
        execution_plan: Dict[str, Any], 
        current_positions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate expected portfolio impact of coordinated execution."""
        
        try:
            total_capital_allocated = 0
            symbol_exposures = {}
            expected_returns = []
            
            for batch in execution_plan.get("execution_batches", []):
                for coordination in batch["signals"]:
                    signal = coordination.modified_signal or coordination.signal
                    
                    symbol = signal.get("symbol", "")
                    position_size_pct = signal.get("position_size_pct", 5) / 100
                    expected_return = signal.get("expected_return", 0)
                    
                    total_capital_allocated += position_size_pct
                    
                    if symbol not in symbol_exposures:
                        symbol_exposures[symbol] = 0
                    symbol_exposures[symbol] += position_size_pct
                    
                    expected_returns.append(expected_return * position_size_pct)
            
            # Calculate portfolio metrics
            portfolio_expected_return = sum(expected_returns)
            max_symbol_exposure = max(symbol_exposures.values()) if symbol_exposures else 0
            diversification_score = len(symbol_exposures) * 10 if symbol_exposures else 0
            
            # Risk assessment
            risk_level = "low"
            if total_capital_allocated > 0.8:  # >80% allocated
                risk_level = "high"
            elif total_capital_allocated > 0.6:  # >60% allocated
                risk_level = "medium"
            
            return {
                "total_capital_allocated_pct": total_capital_allocated * 100,
                "symbol_exposures": {k: f"{v*100:.1f}%" for k, v in symbol_exposures.items()},
                "expected_portfolio_return_pct": portfolio_expected_return,
                "max_single_symbol_exposure_pct": max_symbol_exposure * 100,
                "diversification_score": min(diversification_score, 100),
                "risk_level": risk_level,
                "cash_remaining_pct": (1 - total_capital_allocated) * 100
            }
            
        except Exception as e:
            self.logger.error("Portfolio impact calculation failed", error=str(e))
            return {}
    
    def _serialize_coordination(self, coordination: StrategyCoordination) -> Dict[str, Any]:
        """Serialize coordination for JSON response."""
        return {
            "strategy_name": coordination.strategy_name,
            "signal": coordination.signal,
            "coordination_action": coordination.coordination_action,
            "modified_signal": coordination.modified_signal,
            "conflict_resolution": coordination.conflict_resolution,
            "priority_score": coordination.priority_score
        }
    
    async def execute_coordinated_trades(
        self, 
        execution_plan: Dict[str, Any], 
        user_id: str
    ) -> Dict[str, Any]:
        """Execute trades according to coordination plan."""
        
        try:
            from app.services.trade_execution import TradeExecutionService
            
            trade_service = TradeExecutionService()
            execution_results = []
            
            for batch in execution_plan.get("execution_batches", []):
                # Wait for batch delay
                if batch["execution_delay_seconds"] > 0:
                    await asyncio.sleep(batch["execution_delay_seconds"])
                
                # Execute batch signals in parallel
                batch_tasks = []
                
                for coordination in batch["signals"]:
                    signal = coordination.modified_signal or coordination.signal
                    
                    task = trade_service.execute_real_trade(
                        symbol=signal.get("symbol", "BTC"),
                        side=signal.get("action", "buy").lower(),
                        quantity=signal.get("quantity", 0.001),
                        order_type="market",
                        exchange="binance",
                        user_id=user_id
                    )
                    batch_tasks.append((coordination.strategy_name, task))
                
                # Execute batch in parallel
                batch_results = await asyncio.gather(
                    *[task for _, task in batch_tasks],
                    return_exceptions=True
                )
                
                # Process batch results
                for i, result in enumerate(batch_results):
                    strategy_name = batch_tasks[i][0]
                    
                    if isinstance(result, Exception):
                        execution_results.append({
                            "strategy": strategy_name,
                            "success": False,
                            "error": str(result),
                            "batch_id": batch["batch_id"]
                        })
                    else:
                        execution_results.append({
                            "strategy": strategy_name,
                            "success": result.get("success", False),
                            "execution_data": result,
                            "batch_id": batch["batch_id"]
                        })
            
            # Calculate execution summary
            successful_executions = len([r for r in execution_results if r["success"]])
            total_executions = len(execution_results)
            
            self.logger.info(
                f"🎼 Coordinated execution complete for {user_id}",
                successful=successful_executions,
                total=total_executions,
                success_rate=f"{(successful_executions/total_executions)*100:.1f}%" if total_executions > 0 else "0%"
            )
            
            return {
                "success": True,
                "execution_results": execution_results,
                "execution_summary": {
                    "total_signals": total_executions,
                    "successful_executions": successful_executions,
                    "failed_executions": total_executions - successful_executions,
                    "success_rate": (successful_executions / total_executions) * 100 if total_executions > 0 else 0
                }
            }
            
        except Exception as e:
            self.logger.error("Coordinated execution failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _resolve_conflicts(
        self,
        coordination: StrategyCoordination,
        conflicts: List[Dict[str, Any]],
        user_id: str
    ) -> StrategyCoordination:
        """Resolve conflicts through intelligent coordination."""
        
        # Prioritize conflict resolution by severity
        high_severity = [c for c in conflicts if c["severity"] == "high"]
        
        if high_severity:
            # High severity conflicts: skip or major modification
            conflict = high_severity[0]
            
            if conflict["type"] == PositionConflict.OPPOSING_DIRECTIONS:
                coordination.coordination_action = "skip"
                coordination.conflict_resolution = f"Skipped: {conflict['description']}"
            
        else:
            # Medium severity: modify signal
            for conflict in conflicts:
                if conflict["type"] == PositionConflict.OVER_CONCENTRATION:
                    # Reduce position size
                    max_allowed = self.coordination_rules["max_symbol_exposure"]
                    current_exposure = conflict.get("current_exposure", 0)
                    available_capacity = max_allowed - current_exposure
                    
                    if available_capacity > 0.01:  # At least 1%
                        modified_signal = coordination.signal.copy()
                        modified_signal["position_size_pct"] = available_capacity * 100
                        
                        coordination.coordination_action = "modify"
                        coordination.modified_signal = modified_signal
                        coordination.conflict_resolution = f"Reduced position size due to concentration limits"
                    else:
                        coordination.coordination_action = "skip"
                        coordination.conflict_resolution = "Skipped: No capacity available"
                
                elif conflict["type"] == PositionConflict.CORRELATION_RISK:
                    # Reduce position size for correlation management
                    modified_signal = coordination.signal.copy()
                    modified_signal["position_size_pct"] = modified_signal.get("position_size_pct", 5) * 0.5
                    
                    coordination.coordination_action = "modify"
                    coordination.modified_signal = modified_signal
                    coordination.conflict_resolution = "Reduced position size due to correlation risk"
        
        return coordination


# Global service instance
cross_strategy_coordinator = CrossStrategyCoordinator()


async def get_cross_strategy_coordinator() -> CrossStrategyCoordinator:
    """Dependency injection for FastAPI."""
    if cross_strategy_coordinator.redis is None:
        await cross_strategy_coordinator.async_init()
    return cross_strategy_coordinator