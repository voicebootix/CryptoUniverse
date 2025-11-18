"""
Real Backtesting Engine
Enterprise-grade backtesting with actual market data

Provides accurate backtesting using real historical data from exchanges
instead of synthetic data.
"""

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import json
import numpy as np
import pandas as pd

import structlog
from sqlalchemy import select, and_

from app.core.database import get_database
from app.core.logging import LoggerMixin
from app.models.market_data import BacktestResult, MarketDataOHLCV
from app.services.real_market_data import real_market_data_service
from app.services.trading_strategies import trading_strategies_service

logger = structlog.get_logger(__name__)


class RealBacktestingEngine(LoggerMixin):
    """
    Enterprise backtesting engine using real market data.
    """

    def __init__(self):
        self.backtest_cache = {}
        self.position_tracker = {}

    async def run_backtest(
        self,
        strategy_id: str,
        strategy_func: str,
        start_date: str,
        end_date: str,
        symbols: List[str],
        initial_capital: float = 10000,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run comprehensive backtest with real market data.

        Args:
            strategy_id: Strategy identifier
            strategy_func: Strategy function name
            start_date: Backtest start date (YYYY-MM-DD)
            end_date: Backtest end date (YYYY-MM-DD)
            symbols: List of symbols to trade
            initial_capital: Starting capital
            user_id: Optional user ID for personalized backtesting

        Returns:
            Detailed backtest results with real data
        """
        try:
            self.logger.info(
                "🚀 Starting REAL backtest",
                strategy=strategy_func,
                symbols=symbols,
                period=f"{start_date} to {end_date}"
            )

            # Initialize backtest state
            portfolio = {
                'cash': initial_capital,
                'positions': {},  # Active positions with entry details
                'closed_trades': [],  # Complete trade records with entry/exit
                'equity_curve': [],
                'trades': [],  # Legacy format for backward compatibility
                'current_value': initial_capital
            }

            # Fetch real historical data for all symbols
            historical_data = await self._fetch_all_historical_data(
                symbols, start_date, end_date
            )

            if not historical_data:
                return self._create_error_result("No historical data available")

            # Create unified timeline
            timeline = self._create_unified_timeline(historical_data)

            # Run backtest simulation
            for timestamp in timeline:
                # Update current prices
                current_prices = self._get_prices_at_timestamp(
                    historical_data, timestamp
                )

                # Generate signals using actual strategy
                signals = await self._generate_strategy_signals(
                    strategy_func,
                    symbols,
                    historical_data,
                    portfolio,
                    timestamp
                )

                # Execute trades based on signals
                if signals:
                    await self._execute_backtest_trades(
                        portfolio, signals, current_prices, timestamp
                    )
                
                # Check for stop loss / take profit exits
                await self._check_position_exits(
                    portfolio, current_prices, timestamp
                )

                # Update portfolio value
                portfolio_value = self._calculate_portfolio_value(
                    portfolio, current_prices
                )
                portfolio['current_value'] = portfolio_value
                portfolio['equity_curve'].append({
                    'timestamp': timestamp,
                    'value': portfolio_value
                })

            # Close any remaining open positions at end of backtest
            final_prices = self._get_prices_at_timestamp(historical_data, timeline[-1])
            for symbol, pos in list(portfolio['positions'].items()):
                if symbol in final_prices and pos['quantity'] > 0:
                    await self._close_position(
                        portfolio, symbol, pos, pos['quantity'],
                        final_prices[symbol], timeline[-1],
                        pos.get('position_type', 'LONG'),
                        exit_reason='BACKTEST_END'
                    )
            
            # Calculate final metrics
            results = self._calculate_backtest_metrics(
                portfolio, initial_capital, start_date, end_date
            )

            # Store results in database
            if user_id:
                await self._store_backtest_results(
                    strategy_id, strategy_func, user_id,
                    results, start_date, end_date, symbols
                )

            self.logger.info(
                "✅ Backtest completed with REAL data",
                total_return=results.get('total_return_pct'),
                sharpe_ratio=results.get('sharpe_ratio'),
                max_drawdown=results.get('max_drawdown')
            )

            payload = {"success": True, "results": deepcopy(results)}
            payload.update(results)

            return payload

        except Exception as e:
            self.logger.error("Backtest failed", error=str(e))
            return self._create_error_result(str(e))

    async def _fetch_all_historical_data(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch real historical data for all symbols.
        """
        historical_data = {}

        for symbol in symbols:
            try:
                # Calculate days needed
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                days_needed = (end_dt - start_dt).days

                # Fetch from real market data service (no artificial limit)
                ohlcv = await real_market_data_service.get_historical_ohlcv(
                    symbol=symbol,
                    timeframe='1d',
                    limit=days_needed,  # No hardcoded limit - fetch what's needed
                    exchange='binance'
                )

                if ohlcv:
                    df = pd.DataFrame(ohlcv)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df.set_index('timestamp', inplace=True)
                    historical_data[symbol] = df

                    self.logger.info(
                        f"✅ Fetched {len(df)} days of real data for {symbol}"
                    )
                else:
                    self.logger.warning(f"⚠️ No data for {symbol}")

            except Exception as e:
                self.logger.error(f"Failed to fetch data for {symbol}", error=str(e))

        return historical_data

    def _create_unified_timeline(
        self,
        historical_data: Dict[str, pd.DataFrame]
    ) -> List[datetime]:
        """
        Create unified timeline from all symbol data.
        """
        all_timestamps = set()

        for df in historical_data.values():
            all_timestamps.update(df.index.tolist())

        return sorted(list(all_timestamps))

    def _get_prices_at_timestamp(
        self,
        historical_data: Dict[str, pd.DataFrame],
        timestamp: datetime
    ) -> Dict[str, float]:
        """
        Get prices for all symbols at given timestamp.
        """
        prices = {}

        for symbol, df in historical_data.items():
            if timestamp in df.index:
                prices[symbol] = float(df.loc[timestamp, 'close'])
            elif len(df) > 0:
                # Use last known price if no data for this timestamp
                last_idx = df.index[df.index < timestamp]
                if len(last_idx) > 0:
                    prices[symbol] = float(df.loc[last_idx[-1], 'close'])

        return prices

    async def _generate_strategy_signals(
        self,
        strategy_func: str,
        symbols: List[str],
        historical_data: Dict[str, pd.DataFrame],
        portfolio: Dict,
        timestamp: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Generate trading signals using the trading strategies service in backtest mode.
        """
        try:
            price_snapshots: Dict[str, List[Dict[str, Any]]] = {}

            for symbol in symbols:
                df = historical_data.get(symbol)
                if df is None or df.empty:
                    continue

                history = df[df.index <= timestamp]
                if history.empty:
                    continue

                history = history.tail(250)
                snapshots: List[Dict[str, Any]] = []

                for idx, row in history.iterrows():
                    close_price = row.get('close') if 'close' in row else None
                    if close_price is None or pd.isna(close_price):
                        continue

                    snapshots.append({
                        'timestamp': idx.to_pydatetime() if hasattr(idx, 'to_pydatetime') else idx,
                        'open': float(row.get('open', close_price)),
                        'high': float(row.get('high', close_price)),
                        'low': float(row.get('low', close_price)),
                        'close': float(close_price),
                        'volume': float(row.get('volume', 0))
                    })

                if snapshots:
                    price_snapshots[symbol] = snapshots

            if not price_snapshots:
                return None

            portfolio_snapshot = deepcopy(portfolio)

            result = await trading_strategies_service.run_for_backtest(
                strategy_func=strategy_func,
                symbols=list(price_snapshots.keys()),
                price_snapshots=price_snapshots,
                portfolio_snapshot=portfolio_snapshot,
                as_of=timestamp
            )

            if result.get('success') and result.get('signals'):
                return result['signals']

            return None

        except Exception as e:
            self.logger.debug(f"Signal generation failed: {str(e)}")
            return None

    async def _execute_backtest_trades(
        self,
        portfolio: Dict,
        signals: Dict[str, Any],
        current_prices: Dict[str, float],
        timestamp: datetime
    ):
        """
        Execute trades in backtest based on signals.
        Enhanced to track stop loss, take profit, and position type.
        """
        for symbol, signal in signals.items():
            if symbol not in current_prices:
                continue

            price = current_prices[symbol]
            action = signal.get('action')
            quantity = signal.get('quantity', 0)
            
            # Extract risk management parameters from signal
            stop_loss = signal.get('stop_loss') or signal.get('stop_loss_price')
            take_profit = signal.get('take_profit') or signal.get('take_profit_price')

            if action == 'BUY' and quantity > 0:
                # Calculate cost including fees
                cost = price * quantity
                fees = cost * 0.001  # 0.1% trading fee
                total_cost = cost + fees

                if portfolio['cash'] >= total_cost:
                    # Execute buy (LONG position)
                    portfolio['cash'] -= total_cost

                    if symbol not in portfolio['positions']:
                        portfolio['positions'][symbol] = {
                            'quantity': 0,
                            'avg_price': 0,
                            'entry_trades': []  # Track multiple entries
                        }

                    # Update position
                    pos = portfolio['positions'][symbol]
                    total_quantity = pos['quantity'] + quantity
                    pos['avg_price'] = (
                        (pos['avg_price'] * pos['quantity'] + cost) / total_quantity
                    )
                    pos['quantity'] = total_quantity
                    
                    # Store entry details for this position
                    entry_trade = {
                        'entry_time': timestamp,
                        'entry_price': price,
                        'quantity': quantity,
                        'stop_loss': float(stop_loss) if stop_loss else None,
                        'take_profit': float(take_profit) if take_profit else None,
                        'position_type': 'LONG',  # BUY = LONG
                        'fees': fees
                    }
                    pos['entry_trades'].append(entry_trade)
                    
                    # Update position-level stop loss/take profit (use most recent)
                    if stop_loss:
                        pos['stop_loss'] = float(stop_loss)
                    if take_profit:
                        pos['take_profit'] = float(take_profit)
                    pos['position_type'] = 'LONG'

                    # Record trade (legacy format)
                    portfolio['trades'].append({
                        'timestamp': timestamp,
                        'symbol': symbol,
                        'action': 'BUY',
                        'quantity': quantity,
                        'price': price,
                        'fees': fees
                    })

            elif action == 'SELL' and symbol in portfolio['positions']:
                pos = portfolio['positions'][symbol]
                sell_quantity = min(quantity, pos['quantity'])

                if sell_quantity > 0:
                    # Close LONG position
                    await self._close_position(
                        portfolio, symbol, pos, sell_quantity, price, timestamp, 'LONG'
                    )

    async def _check_position_exits(
        self,
        portfolio: Dict,
        current_prices: Dict[str, float],
        timestamp: datetime
    ):
        """
        Check if any positions should be closed due to stop loss or take profit.
        """
        positions_to_close = []
        
        for symbol, pos in portfolio['positions'].items():
            if symbol not in current_prices or pos['quantity'] == 0:
                continue
                
            current_price = current_prices[symbol]
            position_type = pos.get('position_type', 'LONG')
            stop_loss = pos.get('stop_loss')
            take_profit = pos.get('take_profit')
            
            should_exit = False
            exit_reason = None
            
            if position_type == 'LONG':
                # Check take profit (price goes up)
                if take_profit and current_price >= take_profit:
                    should_exit = True
                    exit_reason = 'TAKE_PROFIT'
                # Check stop loss (price goes down)
                elif stop_loss and current_price <= stop_loss:
                    should_exit = True
                    exit_reason = 'STOP_LOSS'
            elif position_type == 'SHORT':
                # Check take profit (price goes down)
                if take_profit and current_price <= take_profit:
                    should_exit = True
                    exit_reason = 'TAKE_PROFIT'
                # Check stop loss (price goes up)
                elif stop_loss and current_price >= stop_loss:
                    should_exit = True
                    exit_reason = 'STOP_LOSS'
            
            if should_exit:
                positions_to_close.append((symbol, pos, exit_reason))
        
        # Close positions that hit stop loss or take profit
        for symbol, pos, exit_reason in positions_to_close:
            await self._close_position(
                portfolio, symbol, pos, pos['quantity'], 
                current_prices[symbol], timestamp, pos.get('position_type', 'LONG'),
                exit_reason=exit_reason
            )
    
    async def _close_position(
        self,
        portfolio: Dict,
        symbol: str,
        position: Dict,
        exit_quantity: float,
        exit_price: float,
        exit_time: datetime,
        position_type: str,
        exit_reason: str = 'MANUAL'
    ):
        """
        Close a position and create a complete trade record.
        """
        # Calculate proceeds
        proceeds = exit_price * exit_quantity
        fees = proceeds * 0.001
        net_proceeds = proceeds - fees

        # Calculate PnL
        cost_basis = position['avg_price'] * exit_quantity
        pnl = net_proceeds - cost_basis if position_type == 'LONG' else cost_basis - net_proceeds
        pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0

        # Update portfolio
        portfolio['cash'] += net_proceeds
        position['quantity'] -= exit_quantity

        # Create complete trade record
        # Match exit with most recent entry that hasn't been closed
        entry_trades = position.get('entry_trades', [])
        if entry_trades:
            # Use FIFO - close oldest entry first
            entry_trade = entry_trades[0]
            
            closed_trade = {
                'trade_id': f"{symbol}_{entry_trade['entry_time'].isoformat()}_{exit_time.isoformat()}",
                'symbol': symbol,
                'position_type': position_type,  # 'LONG' or 'SHORT'
                'entry_time': entry_trade['entry_time'].isoformat(),
                'exit_time': exit_time.isoformat(),
                'entry_price': float(entry_trade['entry_price']),
                'exit_price': float(exit_price),
                'quantity': float(exit_quantity),
                'stop_loss': entry_trade.get('stop_loss'),
                'take_profit': entry_trade.get('take_profit'),
                'exit_reason': exit_reason,  # 'TAKE_PROFIT', 'STOP_LOSS', 'MANUAL'
                'pnl': float(pnl),
                'pnl_pct': float(pnl_pct),
                'fees': float(fees),
                'cost_basis': float(cost_basis),
                'outcome': 'WIN' if pnl > 0 else 'LOSS' if pnl < 0 else 'BREAKEVEN'
            }
            
            portfolio['closed_trades'].append(closed_trade)
            
            # Remove closed entry
            entry_trades.pop(0)

        if position['quantity'] == 0:
            del portfolio['positions'][symbol]

        # Record trade (legacy format)
        portfolio['trades'].append({
            'timestamp': exit_time,
            'symbol': symbol,
            'action': 'SELL' if position_type == 'LONG' else 'BUY',
            'quantity': exit_quantity,
            'price': exit_price,
            'fees': fees,
            'pnl': pnl
        })

    def _calculate_portfolio_value(
        self,
        portfolio: Dict,
        current_prices: Dict[str, float]
    ) -> float:
        """
        Calculate total portfolio value.
        """
        value = portfolio['cash']

        for symbol, position in portfolio['positions'].items():
            if symbol in current_prices:
                value += position['quantity'] * current_prices[symbol]

        return value

    def _calculate_backtest_metrics(
        self,
        portfolio: Dict,
        initial_capital: float,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive backtest metrics.
        """
        final_value = portfolio['current_value']
        total_return = final_value - initial_capital
        total_return_pct = (total_return / initial_capital) * 100

        # Analyze trades
        trades_df = pd.DataFrame(portfolio['trades']) if portfolio['trades'] else pd.DataFrame()

        if not trades_df.empty and 'pnl' in trades_df.columns:
            winning_trades = trades_df[trades_df['pnl'] > 0]
            losing_trades = trades_df[trades_df['pnl'] < 0]

            win_rate = len(winning_trades) / len(trades_df) * 100
            avg_win = winning_trades['pnl'].mean() if not winning_trades.empty else 0
            avg_loss = losing_trades['pnl'].mean() if not losing_trades.empty else 0
            profit_factor = (
                winning_trades['pnl'].sum() / abs(losing_trades['pnl'].sum())
                if not losing_trades.empty and losing_trades['pnl'].sum() != 0
                else 0
            )
        else:
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            profit_factor = 0

        # Calculate risk metrics from equity curve
        equity_curve = pd.DataFrame(portfolio['equity_curve'])
        if not equity_curve.empty:
            returns = equity_curve['value'].pct_change().dropna()
            sharpe_ratio = self._calculate_sharpe_ratio(returns.values)
            max_drawdown = self._calculate_max_drawdown(equity_curve['value'].values)
        else:
            sharpe_ratio = 0
            max_drawdown = 0

        return {
            'success': True,
            'backtest_period': f"{start_date} to {end_date}",
            'initial_capital': initial_capital,
            'final_capital': final_value,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'total_trades': len(trades_df),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'equity_curve': portfolio['equity_curve'][-100:],  # Last 100 points
            'trade_log': portfolio['trades'][-50:],  # Last 50 trades (legacy format)
            'closed_trades': portfolio.get('closed_trades', []),  # Complete trade records
            'final_positions': portfolio['positions'],
            'total_fees': trades_df['fees'].sum() if not trades_df.empty else 0,
            'calculation_method': 'real_market_data_backtest',
            'data_source': 'ccxt_real_exchanges'
        }

    def _calculate_sharpe_ratio(self, returns: np.ndarray) -> float:
        """Calculate Sharpe ratio."""
        if len(returns) < 2:
            return 0

        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0

        return (mean_return / std_return) * np.sqrt(252)  # Annualized

    def _calculate_max_drawdown(self, values: np.ndarray) -> float:
        """Calculate maximum drawdown percentage."""
        if len(values) < 2:
            return 0

        peak = values[0]
        max_dd = 0

        for value in values:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100
            if dd > max_dd:
                max_dd = dd

        return max_dd

    async def _store_backtest_results(
        self,
        strategy_id: str,
        strategy_name: str,
        user_id: str,
        results: Dict,
        start_date: str,
        end_date: str,
        symbols: List[str]
    ):
        """Store backtest results in database."""
        try:
            async for db in get_database():
                backtest = BacktestResult(
                    strategy_id=strategy_id,
                    strategy_name=strategy_name,
                    user_id=user_id,
                    start_date=datetime.strptime(start_date, "%Y-%m-%d"),
                    end_date=datetime.strptime(end_date, "%Y-%m-%d"),
                    initial_capital=Decimal(str(results['initial_capital'])),
                    final_capital=Decimal(str(results['final_capital'])),
                    total_return=Decimal(str(results['total_return'])),
                    total_return_pct=Decimal(str(results['total_return_pct'])),
                    total_trades=results['total_trades'],
                    win_rate=Decimal(str(results['win_rate'])),
                    profit_factor=Decimal(str(results['profit_factor'])),
                    sharpe_ratio=Decimal(str(results['sharpe_ratio'])),
                    max_drawdown=Decimal(str(results['max_drawdown'])),
                    symbols=symbols,
                    equity_curve=results.get('equity_curve', []),
                    trade_log=results.get('trade_log', []),
                    # Store detailed trades in trade_log JSONB field
                    # Format: trade_log contains both legacy format and closed_trades
                    execution_params={
                        'closed_trades': results.get('closed_trades', []),
                        'total_closed_trades': len(results.get('closed_trades', []))
                    },
                    data_source='real_market_data',
                    data_quality_score=Decimal('95.0')  # High quality real data
                )

                db.add(backtest)
                await db.commit()

                self.logger.info("✅ Backtest results stored", strategy_id=strategy_id)

        except Exception as e:
            self.logger.error("Failed to store backtest results", error=str(e))

    def _create_error_result(self, error: str) -> Dict[str, Any]:
        """Create error result structure."""
        return {
            'success': False,
            'error': error,
            'calculation_method': 'real_market_data_backtest',
            'data_source': 'error'
        }


# Global service instance
real_backtesting_engine = RealBacktestingEngine()


async def get_real_backtesting_engine() -> RealBacktestingEngine:
    """Dependency injection for FastAPI."""
    return real_backtesting_engine
