"""
Real Performance Tracking Service
Enterprise-grade performance tracking with actual trade data

Tracks and calculates real strategy performance metrics based on
actual trades, not mock data.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import json
import uuid
import numpy as np
import pandas as pd

import structlog
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_database
from app.core.logging import LoggerMixin
from app.models.trading import Trade, TradingStrategy
from app.models.market_data import StrategyPerformanceHistory
from app.models.user import User

logger = structlog.get_logger(__name__)


class RealPerformanceTracker(LoggerMixin):
    """
    Enterprise performance tracking service.

    Calculates real performance metrics from actual trade history
    and market data.
    """

    def __init__(self):
        self.metrics_cache = {}
        self.cache_ttl = 300  # 5 minutes cache

    async def track_strategy_performance(
        self,
        strategy_id: str,
        user_id: str,
        period_days: int = 30,
        include_simulations: bool = False,
    ) -> Dict[str, Any]:
        """
        Calculate REAL strategy performance from actual trades.

        Args:
            strategy_id: Strategy identifier
            user_id: User identifier
            period_days: Period to analyze

        Returns:
            Real performance metrics
        """
        try:
            async for db in get_database():
                if not strategy_id:
                    return self._empty_performance_metrics("unknown", "missing_strategy_id")

                try:
                    strategy_uuid = uuid.UUID(str(strategy_id))
                except (ValueError, TypeError) as exc:
                    self.logger.warning(
                        "Invalid strategy_id for performance tracking",
                        strategy_id=strategy_id,
                        error=str(exc),
                    )
                    return self._empty_performance_metrics(str(strategy_id), "invalid_strategy_id")

                try:
                    user_uuid = uuid.UUID(str(user_id))
                except (ValueError, TypeError) as exc:
                    self.logger.warning(
                        "Invalid user_id for performance tracking",
                        strategy_id=strategy_id,
                        user_id=user_id,
                        error=str(exc),
                    )
                    return self._empty_performance_metrics(str(strategy_uuid), "invalid_user_id")

                strategy_id_str = str(strategy_uuid)
                user_id_str = str(user_uuid)

                # Get actual trades for this strategy
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=period_days)

                base_conditions = [
                    Trade.strategy_id == strategy_uuid,
                    Trade.user_id == user_uuid,
                    Trade.created_at >= start_date,
                    Trade.created_at <= end_date,
                ]

                stmt = select(Trade).where(*base_conditions).order_by(Trade.created_at)

                if not include_simulations:
                    stmt = stmt.where(Trade.is_simulation.is_(False))

                result = await db.execute(stmt)
                trades = result.scalars().all()

                if not trades:
                    if not include_simulations:
                        # Check if simulation trades exist for transparency
                        sim_stmt = select(func.count()).where(
                            *base_conditions,
                            Trade.is_simulation.is_(True),
                        )
                        sim_count = (await db.execute(sim_stmt)).scalar() or 0

                        if sim_count:
                            empty_metrics = self._empty_performance_metrics(strategy_id_str, "no_real_trades")
                            empty_metrics["simulation_trades"] = int(sim_count)
                            return empty_metrics

                    return self._empty_performance_metrics(strategy_id_str, "no_trades_yet")

                real_trades = [t for t in trades if not getattr(t, "is_simulation", False)]
                simulation_trades = [t for t in trades if getattr(t, "is_simulation", False)]

                metrics: Dict[str, Any]
                if real_trades:
                    metrics = await self._calculate_real_metrics(
                        real_trades,
                        strategy_id_str,
                        user_id_str,
                        period_days,
                    )
                    metrics.setdefault("status", "live")
                    metrics["data_quality"] = "real"
                    metrics["real_trades"] = len(real_trades)
                    metrics["simulation_trades"] = len(simulation_trades)

                    await self._store_performance_history(
                        db,
                        strategy_id_str,
                        user_id_str,
                        metrics,
                        start_date,
                        end_date,
                        is_live=True,
                        data_source="real_trades",
                    )
                    self.logger.info(
                        "✅ Calculated performance metrics",
                        strategy_id=strategy_id_str,
                        total_trades=len(real_trades),
                        include_simulations=include_simulations,
                        data_quality="real",
                    )
                    return metrics

                if include_simulations and simulation_trades:
                    metrics = await self._calculate_real_metrics(
                        simulation_trades,
                        strategy_id_str,
                        user_id_str,
                        period_days,
                    )
                    metrics["status"] = "simulation_only"
                    metrics["data_quality"] = "simulation"
                    metrics["real_trades"] = 0
                    metrics["simulation_trades"] = len(simulation_trades)

                    await self._store_performance_history(
                        db,
                        strategy_id_str,
                        user_id_str,
                        metrics,
                        start_date,
                        end_date,
                        is_live=False,
                        data_source="simulation_trades",
                    )
                    self.logger.info(
                        "✅ Calculated performance metrics",
                        strategy_id=strategy_id_str,
                        total_trades=len(simulation_trades),
                        include_simulations=include_simulations,
                        data_quality="simulation",
                    )
                    return metrics

                # No qualifying trades found
                empty_metrics = self._empty_performance_metrics(strategy_id_str, "no_real_trades")
                empty_metrics["simulation_trades"] = len(simulation_trades)
                return empty_metrics

        except Exception as e:
            self.logger.exception(
                "Failed to track strategy performance",
                strategy_id=strategy_id,
                user_id=user_id,
                period_days=period_days,
                error=str(e)
            )
            return self._empty_performance_metrics(str(strategy_id), "error")

    async def _calculate_real_metrics(
        self,
        trades: List[Trade],
        strategy_id: str,
        user_id: str,
        period_days: int
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics from real trades.
        """
        # Convert trades to dataframe for easier analysis
        trade_data = []
        for t in trades:
            action = getattr(t.action, "name", str(t.action))
            status = getattr(t.status, "name", str(t.status))
            trade_data.append({
                'timestamp': t.created_at,
                'symbol': t.symbol,
                'action': action,
                'quantity': float(t.executed_quantity or 0),
                'executed_price': float(t.executed_price or 0),
                'pnl': float(t.profit_realized_usd or 0),
                'fees': float(t.fees_paid or 0),
                'status': status,
            })

        df = pd.DataFrame(trade_data)

        # Calculate core metrics
        total_trades = len(df)
        completed_trades = df[df['status'] == 'COMPLETED']

        if len(completed_trades) == 0:
            # All trades still open
            return {
                'strategy_id': strategy_id,
                'user_id': user_id,
                'total_trades': total_trades,
                'open_trades': total_trades,
                'completed_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'status': 'all_positions_open',
                'source': 'real_performance_tracker'
            }

        # Real win/loss analysis
        winning_trades = completed_trades[completed_trades['pnl'] > 0]
        losing_trades = completed_trades[completed_trades['pnl'] < 0]

        win_rate = len(winning_trades) / len(completed_trades) if len(completed_trades) > 0 else 0

        # PnL calculations
        total_pnl = completed_trades['pnl'].sum()
        total_fees = completed_trades['fees'].sum()
        net_pnl = total_pnl - total_fees

        # Risk metrics - use returns instead of raw PnL
        # Approximate returns per trade as pnl divided by notional; fallback if notional unknown
        import numpy as np
        notional = (completed_trades['executed_price'] * completed_trades['quantity']).replace(0, np.nan)
        ret_series = (completed_trades['pnl'] / notional).replace([np.inf, -np.inf], np.nan).dropna()
        returns = ret_series.values

        if len(returns) > 1:
            sharpe_ratio = self._calculate_sharpe_ratio(returns)
            max_drawdown = self._calculate_max_drawdown(returns)
        else:
            sharpe_ratio = 0
            max_drawdown = 0

        # Profit factor depends on wins/losses, not return series length
        profit_factor = self._calculate_profit_factor(
            winning_trades['pnl'].values, losing_trades['pnl'].values
        )

        # Trade analysis
        avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0
        best_trade = completed_trades['pnl'].max()
        worst_trade = completed_trades['pnl'].min()

        # Time analysis
        trade_duration = []
        for _, trade in completed_trades.iterrows():
            if trade['status'] == 'COMPLETED':
                # In real implementation, we'd track entry/exit times
                trade_duration.append(1)  # Placeholder

        # Symbol distribution
        symbol_performance = completed_trades.groupby('symbol')['pnl'].agg(['sum', 'count', 'mean'])
        best_symbol = symbol_performance['sum'].idxmax() if len(symbol_performance) > 0 else None

        return {
            'strategy_id': strategy_id,
            'user_id': user_id,
            'period_days': period_days,  # Requested window length
            'active_days': len(set(df['timestamp'].dt.date)),  # Unique active trade days

            # Trade statistics
            'total_trades': total_trades,
            'completed_trades': len(completed_trades),
            'open_trades': total_trades - len(completed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': float(win_rate),

            # Financial metrics
            'total_pnl': float(total_pnl),
            'net_pnl': float(net_pnl),
            'total_fees': float(total_fees),
            'avg_trade_pnl': float(completed_trades['pnl'].mean()),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'best_trade': float(best_trade),
            'worst_trade': float(worst_trade),

            # Risk metrics
            'sharpe_ratio': float(sharpe_ratio),
            'max_drawdown': float(max_drawdown),
            'profit_factor': float(profit_factor),
            'expectancy': float((win_rate * avg_win) + ((1 - win_rate) * avg_loss)),

            # Additional insights
            'best_performing_symbol': best_symbol,
            'unique_symbols_traded': len(completed_trades['symbol'].unique()),
            'avg_trade_duration_hours': np.mean(trade_duration) if trade_duration else 0,

            # Metadata
            'last_updated': datetime.utcnow().isoformat(),
            'source': 'real_performance_tracker',
            'data_quality': 'verified_real_trades'
        }

    def _calculate_sharpe_ratio(self, returns: np.ndarray, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio from returns."""
        if len(returns) < 2:
            return 0

        excess_returns = returns - (risk_free_rate / 365)  # Daily risk-free rate

        if np.std(excess_returns) == 0:
            return 0

        return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(365)

    def _calculate_max_drawdown(self, returns: np.ndarray) -> float:
        """Calculate maximum drawdown from returns."""
        if len(returns) == 0:
            return 0

        # Returns are already fractions (pnl/notional), don't divide by 100 again
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max

        # Return as positive percentage (magnitude of peak-to-trough loss)
        return float(abs(np.min(drawdown)) * 100) if len(drawdown) > 0 else 0

    def _calculate_profit_factor(self, wins: np.ndarray, losses: np.ndarray) -> float:
        """Calculate profit factor (gross wins / gross losses)."""
        total_wins = np.sum(wins) if len(wins) > 0 else 0
        total_losses = abs(np.sum(losses)) if len(losses) > 0 else 0

        if total_losses == 0:
            return float('inf') if total_wins > 0 else 0

        return total_wins / total_losses

    async def _store_performance_history(
        self,
        db: AsyncSession,
        strategy_id: str,
        user_id: str,
        metrics: Dict[str, Any],
        start_date: datetime,
        end_date: datetime,
        *,
        is_live: bool = True,
        data_source: str = "real_trades",
    ):
        """Store performance metrics in database for historical tracking."""
        try:
            history = StrategyPerformanceHistory(
                strategy_id=strategy_id,
                strategy_name=metrics.get('strategy_name', strategy_id),
                user_id=user_id,
                period_start=start_date,
                period_end=end_date,
                timeframe='custom',
                total_trades=metrics.get('total_trades', 0),
                winning_trades=metrics.get('winning_trades', 0),
                losing_trades=metrics.get('losing_trades', 0),
                win_rate=(Decimal(str(metrics.get('win_rate', 0))) * Decimal('100')).quantize(Decimal('0.01')),
                starting_balance=Decimal('10000'),  # TODO: replace with real balance
                ending_balance=Decimal('10000') + Decimal(str(metrics.get('net_pnl', 0))),
                total_pnl=Decimal(str(metrics.get('total_pnl', 0))),
                total_pnl_pct=(Decimal(str(metrics.get('total_pnl', 0))) / Decimal('10000')) * Decimal('100'),
                max_drawdown=Decimal(str(metrics.get('max_drawdown', 0))),
                sharpe_ratio=Decimal(str(metrics.get('sharpe_ratio', 0))),
                best_trade_pnl=Decimal(str(metrics.get('best_trade', 0))),
                worst_trade_pnl=Decimal(str(metrics.get('worst_trade', 0))),
                avg_trade_pnl=Decimal(str(metrics.get('avg_trade_pnl', 0))),
                total_fees=Decimal(str(metrics.get('total_fees', 0))),
                is_live=is_live,
                data_source=data_source
            )

            db.add(history)
            await db.commit()

            self.logger.info("✅ Stored performance history", strategy_id=strategy_id)

        except Exception as e:
            # Rollback the transaction
            await db.rollback()

            # Log full traceback with context
            self.logger.exception(
                "Failed to store performance history",
                strategy_id=strategy_id,
                user_id=user_id,
                error=str(e)
            )

            # Re-raise to let caller handle the failure
            raise

    def _empty_performance_metrics(self, strategy_id: str, reason: str) -> Dict[str, Any]:
        """Return empty but properly structured metrics."""
        return {
            'strategy_id': strategy_id,
            'total_trades': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'net_pnl': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'status': reason,
            'source': 'real_performance_tracker',
            'data_quality': 'no_data',
            'real_trades': 0,
            'simulation_trades': 0,
        }

    async def get_strategy_comparison(
        self,
        user_id: str,
        strategy_ids: List[str],
        period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Compare performance across multiple strategies.
        """
        comparison_data = {}

        for strategy_id in strategy_ids:
            metrics = await self.track_strategy_performance(
                strategy_id, user_id, period_days
            )
            comparison_data[strategy_id] = metrics

        # Rank strategies
        ranked = sorted(
            comparison_data.items(),
            key=lambda x: x[1].get('total_pnl', 0),
            reverse=True
        )

        return {
            'strategies': comparison_data,
            'rankings': [{'rank': i+1, 'strategy_id': s[0], 'pnl': s[1].get('total_pnl', 0)}
                        for i, s in enumerate(ranked)],
            'best_performer': ranked[0][0] if ranked else None,
            'comparison_period': period_days,
            'source': 'real_performance_tracker'
        }


# Global service instance
real_performance_tracker = RealPerformanceTracker()


async def get_real_performance_tracker() -> RealPerformanceTracker:
    """Dependency injection for FastAPI."""
    return real_performance_tracker