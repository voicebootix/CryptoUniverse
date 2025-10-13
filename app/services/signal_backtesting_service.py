"""Signal strategy backtesting service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import structlog

from app.services.signal_generation_engine import signal_generation_engine, TechnicalSignal

logger = structlog.get_logger(__name__)


@dataclass
class BacktestTrade:
    """Individual trade in backtest."""

    entry_time: datetime
    exit_time: datetime
    symbol: str
    action: str
    entry_price: float
    exit_price: float
    profit_pct: float
    outcome: str  # "win" or "loss"
    reason: str


@dataclass
class BacktestResult:
    """Results from backtesting a strategy."""

    strategy_type: str
    symbols: List[str]
    timeframe: str
    start_date: str
    end_date: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_return_pct: float
    avg_win_pct: float
    avg_loss_pct: float
    best_trade_pct: float
    worst_trade_pct: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown_pct: float
    trades: List[BacktestTrade]


class SignalBacktestingService:
    """
    Backtest signal strategies against historical data.

    Tests how signals would have performed in the past.
    """

    def __init__(self):
        self.logger = logger
        self.engine = signal_generation_engine

    async def backtest_strategy(
        self,
        strategy_type: str,
        symbols: List[str],
        timeframe: str = "1h",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days_back: int = 30,
    ) -> BacktestResult:
        """
        Backtest a strategy over historical data.

        Args:
            strategy_type: "momentum", "breakout", "mean_reversion", "scalping"
            symbols: List of symbols to test
            timeframe: Candle timeframe
            start_date: ISO format start date (or use days_back)
            end_date: ISO format end date (or use today)
            days_back: Days to backtest if dates not provided
        """
        if not start_date:
            start_dt = datetime.utcnow() - timedelta(days=days_back)
            start_date = start_dt.isoformat()
        if not end_date:
            end_date = datetime.utcnow().isoformat()

        self.logger.info(
            "Starting backtest",
            strategy_type=strategy_type,
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
        )

        all_trades: List[BacktestTrade] = []

        # Backtest each symbol
        for symbol in symbols:
            try:
                symbol_trades = await self._backtest_symbol(
                    symbol=symbol,
                    strategy_type=strategy_type,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date,
                )
                all_trades.extend(symbol_trades)
            except Exception as e:
                self.logger.error("Backtest failed for symbol", symbol=symbol, error=str(e))

        # Calculate metrics
        total_trades = len(all_trades)
        winning_trades = sum(1 for t in all_trades if t.outcome == "win")
        losing_trades = sum(1 for t in all_trades if t.outcome == "loss")
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        wins = [t.profit_pct for t in all_trades if t.outcome == "win"]
        losses = [t.profit_pct for t in all_trades if t.outcome == "loss"]

        total_return_pct = sum(t.profit_pct for t in all_trades)
        avg_win_pct = (sum(wins) / len(wins)) if wins else 0
        avg_loss_pct = (sum(losses) / len(losses)) if losses else 0
        best_trade_pct = max([t.profit_pct for t in all_trades]) if all_trades else 0
        worst_trade_pct = min([t.profit_pct for t in all_trades]) if all_trades else 0

        # Profit factor: total wins / abs(total losses)
        total_wins = sum(wins)
        total_losses = abs(sum(losses))
        profit_factor = (total_wins / total_losses) if total_losses > 0 else 0

        # Sharpe ratio (simplified)
        returns = [t.profit_pct for t in all_trades]
        sharpe_ratio = self._calculate_sharpe_ratio(returns)

        # Max drawdown
        max_drawdown_pct = self._calculate_max_drawdown([t.profit_pct for t in all_trades])

        return BacktestResult(
            strategy_type=strategy_type,
            symbols=symbols,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_return_pct=total_return_pct,
            avg_win_pct=avg_win_pct,
            avg_loss_pct=avg_loss_pct,
            best_trade_pct=best_trade_pct,
            worst_trade_pct=worst_trade_pct,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            max_drawdown_pct=max_drawdown_pct,
            trades=all_trades,
        )

    async def _backtest_symbol(
        self,
        symbol: str,
        strategy_type: str,
        timeframe: str,
        start_date: str,
        end_date: str,
    ) -> List[BacktestTrade]:
        """Backtest a single symbol."""

        # Fetch historical data
        df = await self.engine._fetch_symbol_data(symbol, timeframe)
        if df is None or df.empty:
            return []

        # Filter by date range
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        df = df[(df.index >= start_dt) & (df.index <= end_dt)]

        if df.empty:
            return []

        trades: List[BacktestTrade] = []
        position = None  # Current open position

        # Simulate trading by walking through historical data
        for i in range(50, len(df)):  # Need 50 candles for indicators
            window = df.iloc[:i+1]

            # Calculate indicators for this point in time
            indicators = self.engine._calculate_indicators(window)

            # Generate signal
            signal = None
            if strategy_type == "momentum":
                signal = self.engine._generate_momentum_signal(symbol, window, indicators, timeframe)
            elif strategy_type == "breakout":
                signal = self.engine._generate_breakout_signal(symbol, window, indicators, timeframe)
            elif strategy_type == "mean_reversion":
                signal = self.engine._generate_mean_reversion_signal(symbol, window, indicators, timeframe)
            elif strategy_type == "scalping":
                signal = self.engine._generate_scalping_signal(symbol, window, indicators, timeframe)

            if not signal:
                # Check if we should close position
                if position:
                    current_price = float(window["close"].iloc[-1])
                    trade = self._check_exit(position, current_price, window.index[-1])
                    if trade:
                        trades.append(trade)
                        position = None
                continue

            # Open new position if we have signal and no position
            if not position and signal.action in ["BUY", "SELL"]:
                position = {
                    "entry_time": window.index[-1],
                    "symbol": symbol,
                    "action": signal.action,
                    "entry_price": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "take_profit": signal.take_profit,
                }

            # Check if existing position should exit
            elif position:
                current_price = float(window["close"].iloc[-1])
                trade = self._check_exit(position, current_price, window.index[-1])
                if trade:
                    trades.append(trade)
                    position = None

        # Close any remaining position at end
        if position:
            final_price = float(df["close"].iloc[-1])
            trade = self._check_exit(position, final_price, df.index[-1], force_close=True)
            if trade:
                trades.append(trade)

        return trades

    def _check_exit(
        self,
        position: Dict[str, Any],
        current_price: float,
        current_time: datetime,
        force_close: bool = False,
    ) -> Optional[BacktestTrade]:
        """Check if position should be closed."""

        entry_price = position["entry_price"]
        action = position["action"]
        stop_loss = position.get("stop_loss")
        take_profit = position.get("take_profit")

        outcome = None
        reason = ""

        if action == "BUY":
            if take_profit and current_price >= take_profit:
                outcome = "win"
                reason = "Take profit hit"
            elif stop_loss and current_price <= stop_loss:
                outcome = "loss"
                reason = "Stop loss hit"
            elif force_close:
                outcome = "win" if current_price > entry_price else "loss"
                reason = "Position closed at end"
        else:  # SELL
            if take_profit and current_price <= take_profit:
                outcome = "win"
                reason = "Take profit hit"
            elif stop_loss and current_price >= stop_loss:
                outcome = "loss"
                reason = "Stop loss hit"
            elif force_close:
                outcome = "win" if current_price < entry_price else "loss"
                reason = "Position closed at end"

        if not outcome:
            return None

        # Calculate profit
        if action == "BUY":
            profit_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            profit_pct = ((entry_price - current_price) / entry_price) * 100

        return BacktestTrade(
            entry_time=position["entry_time"],
            exit_time=current_time,
            symbol=position["symbol"],
            action=action,
            entry_price=entry_price,
            exit_price=current_price,
            profit_pct=profit_pct,
            outcome=outcome,
            reason=reason,
        )

    def _calculate_sharpe_ratio(self, returns: List[float]) -> float:
        """Calculate Sharpe ratio (simplified, annualized)."""
        if not returns or len(returns) < 2:
            return 0.0

        import numpy as np
        returns_array = np.array(returns)
        mean_return = np.mean(returns_array)
        std_return = np.std(returns_array)

        if std_return == 0:
            return 0.0

        # Annualize (assuming hourly returns)
        sharpe = (mean_return / std_return) * (365 * 24) ** 0.5
        return float(sharpe)

    def _calculate_max_drawdown(self, returns: List[float]) -> float:
        """Calculate maximum drawdown percentage."""
        if not returns:
            return 0.0

        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0

        for ret in returns:
            cumulative += ret
            peak = max(peak, cumulative)
            drawdown = peak - cumulative
            max_dd = max(max_dd, drawdown)

        return max_dd


signal_backtesting_service = SignalBacktestingService()
