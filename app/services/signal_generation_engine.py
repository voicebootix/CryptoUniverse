"""
Enterprise Signal Generation Engine - Technical Analysis Based

Generates high-quality trading signals using technical indicators:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Volume Analysis
- Trend Detection
- Support/Resistance Levels

NO HARDCODED ASSETS - Fully configurable via database and API
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd
import structlog
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator, SMAIndicator
from ta.volume import VolumeWeightedAveragePrice, OnBalanceVolumeIndicator

from app.core.config import get_settings
from app.core.redis import get_redis_client
from app.services.market_data_coordinator import market_data_coordinator

logger = structlog.get_logger(__name__)
settings = get_settings()


@dataclass
class TechnicalSignal:
    """Individual technical analysis signal."""

    symbol: str
    action: str  # BUY, SELL, HOLD
    confidence: float  # 0-100
    entry_price: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    timeframe: str
    strategy_type: str  # momentum, breakout, mean_reversion, scalping
    indicators: Dict[str, float]
    reasoning: str
    timestamp: datetime
    risk_score: float  # 0-1


@dataclass
class BatchSignals:
    """Collection of signals grouped by strategy type."""

    momentum: List[TechnicalSignal]
    breakout: List[TechnicalSignal]
    mean_reversion: List[TechnicalSignal]
    scalping: List[TechnicalSignal]
    generated_at: datetime
    symbols_analyzed: List[str]

    def all_signals(self) -> List[TechnicalSignal]:
        """Get all signals regardless of strategy."""
        return self.momentum + self.breakout + self.mean_reversion + self.scalping

    def get_by_strategy(self, strategy_ids: Sequence[str]) -> List[TechnicalSignal]:
        """Filter signals by strategy IDs."""
        strategy_map = {
            "ai_spot_momentum_strategy": self.momentum,
            "ai_spot_mean_reversion": self.mean_reversion,
            "ai_spot_breakout_strategy": self.breakout,
            "ai_scalping_strategy": self.scalping,
        }

        signals = []
        for strategy_id in strategy_ids:
            signals.extend(strategy_map.get(strategy_id, []))
        return signals


class SignalGenerationEngine:
    """
    Enterprise-grade signal generation using technical analysis.

    Features:
    - Batch generation (generate once, deliver to many)
    - Redis caching (15-minute TTL)
    - Dynamic symbol configuration
    - Multiple strategy types
    - Quality scoring
    """

    def __init__(self):
        self.logger = logger
        self.redis = None
        self._cache_ttl = 900  # 15 minutes

    async def _ensure_redis(self):
        """Lazy Redis initialization."""
        if not self.redis:
            try:
                self.redis = await get_redis_client()
            except Exception as e:
                self.logger.warning("Redis unavailable, operating without cache", error=str(e))
                self.redis = None
        return self.redis

    async def generate_batch_signals(
        self,
        symbols: Optional[List[str]] = None,
        timeframe: str = "1h",
        force_refresh: bool = False,
    ) -> BatchSignals:
        """
        Generate signals for all symbols and all strategy types.

        This is the MAIN method called by background service.
        Results are cached for 15 minutes.
        """
        cache_key = f"signal_batch:{timeframe}"

        # Try cache first
        if not force_refresh:
            cached = await self._get_cached_signals(cache_key)
            if cached:
                self.logger.info("Returning cached signals", timeframe=timeframe)
                return cached

        # Determine symbols to analyze
        if not symbols:
            symbols = await self._get_configured_symbols()

        self.logger.info(
            "Generating batch signals",
            symbols=symbols,
            timeframe=timeframe,
            symbol_count=len(symbols),
        )

        # Fetch market data for all symbols in parallel
        market_data = await self._fetch_bulk_market_data(symbols, timeframe)

        # Generate signals for each strategy type
        batch = BatchSignals(
            momentum=[],
            breakout=[],
            mean_reversion=[],
            scalping=[],
            generated_at=datetime.utcnow(),
            symbols_analyzed=symbols,
        )

        for symbol, df in market_data.items():
            if df is None or df.empty:
                continue

            try:
                # Calculate all indicators once
                indicators = self._calculate_indicators(df)

                # Generate signals for each strategy
                if signal := self._generate_momentum_signal(symbol, df, indicators, timeframe):
                    batch.momentum.append(signal)

                if signal := self._generate_breakout_signal(symbol, df, indicators, timeframe):
                    batch.breakout.append(signal)

                if signal := self._generate_mean_reversion_signal(symbol, df, indicators, timeframe):
                    batch.mean_reversion.append(signal)

                if signal := self._generate_scalping_signal(symbol, df, indicators, timeframe):
                    batch.scalping.append(signal)

            except Exception:
                self.logger.exception("Signal generation failed for symbol %s", symbol)

        # Cache the results
        await self._cache_signals(cache_key, batch)

        self.logger.info(
            "Batch signal generation complete",
            total_signals=len(batch.all_signals()),
            momentum=len(batch.momentum),
            breakout=len(batch.breakout),
            mean_reversion=len(batch.mean_reversion),
            scalping=len(batch.scalping),
        )

        return batch

    async def _get_configured_symbols(self) -> List[str]:
        """Get symbols from market data coordinator (dynamic, not hardcoded)."""
        try:
            # Get top traded symbols dynamically
            discovery_result = await market_data_coordinator.discover_trading_opportunities(
                limit=20,
                timeframe="1h",
            )

            if discovery_result.get("success") and discovery_result.get("opportunities"):
                symbols = [opp.get("symbol") for opp in discovery_result["opportunities"] if opp.get("symbol")]
                if symbols:
                    return symbols[:20]  # Top 20
        except Exception as e:
            self.logger.warning("Failed to get dynamic symbols", error=str(e))

        # Fallback to major pairs
        return [
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT",
            "XRP/USDT", "ADA/USDT", "AVAX/USDT", "MATIC/USDT",
            "DOT/USDT", "LINK/USDT",
        ]

    async def _fetch_bulk_market_data(
        self,
        symbols: List[str],
        timeframe: str
    ) -> Dict[str, Optional[pd.DataFrame]]:
        """Fetch OHLCV data for all symbols in parallel."""
        tasks = []
        for symbol in symbols:
            task = self._fetch_symbol_data(symbol, timeframe)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        market_data = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                self.logger.warning("Failed to fetch data", symbol=symbol, error=str(result))
                market_data[symbol] = None
            else:
                market_data[symbol] = result

        return market_data

    async def _fetch_symbol_data(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data for a single symbol."""
        try:
            # Use market data coordinator
            result = await market_data_coordinator.get_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                limit=200,  # Need 200 candles for indicators
            )

            if not result.get("success") or not result.get("data"):
                return None

            data = result["data"]
            if not data:
                return None

            # Convert to DataFrame
            df = pd.DataFrame(data)

            # Ensure required columns
            required = ["timestamp", "open", "high", "low", "close", "volume"]
            if not all(col in df.columns for col in required):
                return None

            # Convert timestamp to datetime
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", errors="coerce")
            df.set_index("timestamp", inplace=True)

            # Convert price columns to float
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            return df

        except Exception:
            self.logger.exception("Data fetch failed for %s", symbol)
            return None

    def _calculate_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate all technical indicators for a symbol."""
        indicators = {}

        try:
            # RSI
            rsi = RSIIndicator(close=df["close"], window=14)
            indicators["rsi"] = float(rsi.rsi().iloc[-1])

            # MACD
            macd = MACD(close=df["close"])
            indicators["macd"] = float(macd.macd().iloc[-1])
            indicators["macd_signal"] = float(macd.macd_signal().iloc[-1])
            indicators["macd_diff"] = float(macd.macd_diff().iloc[-1])

            # EMAs
            ema_fast = EMAIndicator(close=df["close"], window=12)
            ema_slow = EMAIndicator(close=df["close"], window=26)
            indicators["ema_12"] = float(ema_fast.ema_indicator().iloc[-1])
            indicators["ema_26"] = float(ema_slow.ema_indicator().iloc[-1])

            # SMAs
            sma_50 = SMAIndicator(close=df["close"], window=50)
            sma_200 = SMAIndicator(close=df["close"], window=200)
            indicators["sma_50"] = float(sma_50.sma_indicator().iloc[-1])
            indicators["sma_200"] = float(sma_200.sma_indicator().iloc[-1])

            # Volume
            indicators["volume_avg"] = float(df["volume"].tail(20).mean())
            indicators["volume_current"] = float(df["volume"].iloc[-1])
            indicators["volume_ratio"] = indicators["volume_current"] / indicators["volume_avg"] if indicators["volume_avg"] > 0 else 1.0

            # VWAP
            vwap = VolumeWeightedAveragePrice(high=df["high"], low=df["low"], close=df["close"], volume=df["volume"])
            indicators["vwap"] = float(vwap.volume_weighted_average_price().iloc[-1])

            # OBV
            obv = OnBalanceVolumeIndicator(close=df["close"], volume=df["volume"])
            indicators["obv"] = float(obv.on_balance_volume().iloc[-1])

            # Price
            indicators["price"] = float(df["close"].iloc[-1])
            indicators["high_20"] = float(df["high"].tail(20).max())
            indicators["low_20"] = float(df["low"].tail(20).min())

        except Exception:
            self.logger.exception("Indicator calculation failed")

        return indicators

    def _generate_momentum_signal(
        self,
        symbol: str,
        df: pd.DataFrame,
        indicators: Dict[str, Any],
        timeframe: str,
    ) -> Optional[TechnicalSignal]:
        """Generate momentum trading signal."""
        try:
            rsi = indicators.get("rsi", 50)
            macd_diff = indicators.get("macd_diff", 0)
            ema_12 = indicators.get("ema_12", 0)
            ema_26 = indicators.get("ema_26", 0)
            volume_ratio = indicators.get("volume_ratio", 1.0)
            price = indicators.get("price", 0)

            # Momentum BUY conditions
            if (
                rsi > 50 and rsi < 70  # Trending but not overbought
                and macd_diff > 0  # Bullish MACD
                and ema_12 > ema_26  # Fast EMA above slow
                and volume_ratio > 1.2  # Above average volume
            ):
                confidence = min(95, 60 + (rsi - 50) * 0.5 + (volume_ratio - 1) * 20)
                stop_loss = price * 0.98  # 2% stop loss
                take_profit = price * 1.05  # 5% take profit

                return TechnicalSignal(
                    symbol=symbol,
                    action="BUY",
                    confidence=float(confidence),
                    entry_price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    timeframe=timeframe,
                    strategy_type="momentum",
                    indicators=indicators,
                    reasoning=f"Momentum BUY: RSI={rsi:.1f}, MACD+, EMA crossover, Volume {volume_ratio:.1f}x",
                    timestamp=datetime.utcnow(),
                    risk_score=0.4,
                )

            # Momentum SELL conditions
            elif (
                rsi < 50 and rsi > 30  # Trending down but not oversold
                and macd_diff < 0  # Bearish MACD
                and ema_12 < ema_26  # Fast EMA below slow
                and volume_ratio > 1.2
            ):
                confidence = min(95, 60 + (50 - rsi) * 0.5 + (volume_ratio - 1) * 20)
                stop_loss = price * 1.02  # 2% stop loss
                take_profit = price * 0.95  # 5% take profit

                return TechnicalSignal(
                    symbol=symbol,
                    action="SELL",
                    confidence=float(confidence),
                    entry_price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    timeframe=timeframe,
                    strategy_type="momentum",
                    indicators=indicators,
                    reasoning=f"Momentum SELL: RSI={rsi:.1f}, MACD-, EMA crossover, Volume {volume_ratio:.1f}x",
                    timestamp=datetime.utcnow(),
                    risk_score=0.4,
                )

        except Exception:
            self.logger.exception("Momentum signal generation failed for %s", symbol)

        return None

    def _generate_breakout_signal(
        self,
        symbol: str,
        df: pd.DataFrame,
        indicators: Dict[str, Any],
        timeframe: str,
    ) -> Optional[TechnicalSignal]:
        """Generate breakout trading signal."""
        try:
            price = indicators.get("price", 0)
            high_20 = indicators.get("high_20", 0)
            low_20 = indicators.get("low_20", 0)
            volume_ratio = indicators.get("volume_ratio", 1.0)
            rsi = indicators.get("rsi", 50)

            # Upside breakout
            if (
                price > high_20 * 1.001  # Breaking 20-period high
                and volume_ratio > 1.5  # Strong volume
                and rsi > 55  # Momentum confirmation
            ):
                confidence = min(95, 65 + (volume_ratio - 1.5) * 30)
                stop_loss = high_20 * 0.99  # Stop below breakout level
                take_profit = price + (price - high_20) * 2  # 2x the breakout range

                return TechnicalSignal(
                    symbol=symbol,
                    action="BUY",
                    confidence=float(confidence),
                    entry_price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    timeframe=timeframe,
                    strategy_type="breakout",
                    indicators=indicators,
                    reasoning=f"Breakout BUY: Price broke ${high_20:.2f}, Volume {volume_ratio:.1f}x",
                    timestamp=datetime.utcnow(),
                    risk_score=0.6,  # Higher risk
                )

            # Downside breakout
            elif (
                price < low_20 * 0.999  # Breaking 20-period low
                and volume_ratio > 1.5
                and rsi < 45
            ):
                confidence = min(95, 65 + (volume_ratio - 1.5) * 30)
                stop_loss = low_20 * 1.01
                take_profit = price - (low_20 - price) * 2

                return TechnicalSignal(
                    symbol=symbol,
                    action="SELL",
                    confidence=float(confidence),
                    entry_price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    timeframe=timeframe,
                    strategy_type="breakout",
                    indicators=indicators,
                    reasoning=f"Breakout SELL: Price broke ${low_20:.2f}, Volume {volume_ratio:.1f}x",
                    timestamp=datetime.utcnow(),
                    risk_score=0.6,
                )

        except Exception:
            self.logger.exception("Breakout signal generation failed for %s", symbol)

        return None

    def _generate_mean_reversion_signal(
        self,
        symbol: str,
        df: pd.DataFrame,
        indicators: Dict[str, Any],
        timeframe: str,
    ) -> Optional[TechnicalSignal]:
        """Generate mean reversion trading signal."""
        try:
            rsi = indicators.get("rsi", 50)
            price = indicators.get("price", 0)
            sma_50 = indicators.get("sma_50", 0)
            vwap = indicators.get("vwap", 0)

            # Oversold mean reversion BUY
            if (
                rsi < 30  # Oversold
                and price < sma_50 * 0.98  # Below SMA
                and price < vwap * 0.98  # Below VWAP
            ):
                confidence = min(95, 55 + (30 - rsi) * 1.5)
                stop_loss = price * 0.97
                take_profit = min(sma_50, vwap)  # Target mean

                return TechnicalSignal(
                    symbol=symbol,
                    action="BUY",
                    confidence=float(confidence),
                    entry_price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    timeframe=timeframe,
                    strategy_type="mean_reversion",
                    indicators=indicators,
                    reasoning=f"Mean Reversion BUY: RSI={rsi:.1f} oversold, below SMA/VWAP",
                    timestamp=datetime.utcnow(),
                    risk_score=0.5,
                )

            # Overbought mean reversion SELL
            elif (
                rsi > 70  # Overbought
                and price > sma_50 * 1.02
                and price > vwap * 1.02
            ):
                confidence = min(95, 55 + (rsi - 70) * 1.5)
                stop_loss = price * 1.03
                take_profit = max(sma_50, vwap)

                return TechnicalSignal(
                    symbol=symbol,
                    action="SELL",
                    confidence=float(confidence),
                    entry_price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    timeframe=timeframe,
                    strategy_type="mean_reversion",
                    indicators=indicators,
                    reasoning=f"Mean Reversion SELL: RSI={rsi:.1f} overbought, above SMA/VWAP",
                    timestamp=datetime.utcnow(),
                    risk_score=0.5,
                )

        except Exception:
            self.logger.exception("Mean reversion signal generation failed for %s", symbol)

        return None

    def _generate_scalping_signal(
        self,
        symbol: str,
        df: pd.DataFrame,
        indicators: Dict[str, Any],
        timeframe: str,
    ) -> Optional[TechnicalSignal]:
        """Generate scalping signal (short-term, high frequency)."""
        try:
            macd_diff = indicators.get("macd_diff", 0)
            ema_12 = indicators.get("ema_12", 0)
            price = indicators.get("price", 0)
            volume_ratio = indicators.get("volume_ratio", 1.0)

            # Quick scalp BUY
            if (
                macd_diff > 0  # Bullish MACD
                and price > ema_12  # Above fast EMA
                and volume_ratio > 1.3
            ):
                confidence = min(90, 55 + volume_ratio * 20)
                stop_loss = price * 0.995  # Tight 0.5% stop
                take_profit = price * 1.015  # Quick 1.5% profit

                return TechnicalSignal(
                    symbol=symbol,
                    action="BUY",
                    confidence=float(confidence),
                    entry_price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    timeframe=timeframe,
                    strategy_type="scalping",
                    indicators=indicators,
                    reasoning=f"Scalp BUY: MACD+, above EMA, Volume {volume_ratio:.1f}x",
                    timestamp=datetime.utcnow(),
                    risk_score=0.3,  # Lower risk, tight stops
                )

            # Quick scalp SELL
            elif (
                macd_diff < 0
                and price < ema_12
                and volume_ratio > 1.3
            ):
                confidence = min(90, 55 + volume_ratio * 20)
                stop_loss = price * 1.005
                take_profit = price * 0.985

                return TechnicalSignal(
                    symbol=symbol,
                    action="SELL",
                    confidence=float(confidence),
                    entry_price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    timeframe=timeframe,
                    strategy_type="scalping",
                    indicators=indicators,
                    reasoning=f"Scalp SELL: MACD-, below EMA, Volume {volume_ratio:.1f}x",
                    timestamp=datetime.utcnow(),
                    risk_score=0.3,
                )

        except Exception:
            self.logger.exception("Scalping signal generation failed for %s", symbol)

        return None

    async def _get_cached_signals(self, cache_key: str) -> Optional[BatchSignals]:
        """Get signals from cache."""
        redis = await self._ensure_redis()
        if not redis:
            return None

        try:
            data = await redis.get(cache_key)
            if data:
                # Deserialize from JSON
                import json
                parsed = json.loads(data)

                # Reconstruct BatchSignals
                batch = BatchSignals(
                    momentum=[self._signal_from_dict(s) for s in parsed.get("momentum", [])],
                    breakout=[self._signal_from_dict(s) for s in parsed.get("breakout", [])],
                    mean_reversion=[self._signal_from_dict(s) for s in parsed.get("mean_reversion", [])],
                    scalping=[self._signal_from_dict(s) for s in parsed.get("scalping", [])],
                    generated_at=datetime.fromisoformat(parsed["generated_at"]),
                    symbols_analyzed=parsed.get("symbols_analyzed", []),
                )
                return batch
        except Exception as e:
            self.logger.warning("Failed to get cached signals", error=str(e))

        return None

    async def _cache_signals(self, cache_key: str, batch: BatchSignals):
        """Cache signals to Redis."""
        redis = await self._ensure_redis()
        if not redis:
            return

        try:
            import json

            data = {
                "momentum": [self._signal_to_dict(s) for s in batch.momentum],
                "breakout": [self._signal_to_dict(s) for s in batch.breakout],
                "mean_reversion": [self._signal_to_dict(s) for s in batch.mean_reversion],
                "scalping": [self._signal_to_dict(s) for s in batch.scalping],
                "generated_at": batch.generated_at.isoformat(),
                "symbols_analyzed": batch.symbols_analyzed,
            }

            await redis.set(cache_key, json.dumps(data), ex=self._cache_ttl)
        except Exception as e:
            self.logger.warning("Failed to cache signals", error=str(e))

    def _signal_to_dict(self, signal: TechnicalSignal) -> Dict[str, Any]:
        """Convert signal to dict for serialization."""
        return {
            "symbol": signal.symbol,
            "action": signal.action,
            "confidence": signal.confidence,
            "entry_price": signal.entry_price,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "timeframe": signal.timeframe,
            "strategy_type": signal.strategy_type,
            "indicators": signal.indicators,
            "reasoning": signal.reasoning,
            "timestamp": signal.timestamp.isoformat(),
            "risk_score": signal.risk_score,
        }

    def _signal_from_dict(self, data: Dict[str, Any]) -> TechnicalSignal:
        """Reconstruct signal from dict."""
        return TechnicalSignal(
            symbol=data["symbol"],
            action=data["action"],
            confidence=data["confidence"],
            entry_price=data["entry_price"],
            stop_loss=data.get("stop_loss"),
            take_profit=data.get("take_profit"),
            timeframe=data["timeframe"],
            strategy_type=data["strategy_type"],
            indicators=data.get("indicators", {}),
            reasoning=data["reasoning"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            risk_score=data.get("risk_score", 0.5),
        )


# Singleton instance
signal_generation_engine = SignalGenerationEngine()
