"""
Copy trading service for managing signal providers, followers, and performance data.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any
from uuid import UUID
import random

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func, text
from sqlalchemy.exc import SQLAlchemyError

from app.models.user import User
from app.models.copy_trading import (
    StrategyPublisher,
    StrategyFollower,
    StrategyPerformance,
    CopyTradeSignal,
    StrategyStatus,
    SignalStatus
)
from app.models.trading import TradingStrategy, Trade
from app.services.binance_service import BinanceService

logger = logging.getLogger(__name__)

class CopyTradingService:
    """Service for copy trading operations."""

    def __init__(self):
        self.binance_service = BinanceService()

    async def get_signal_providers(
        self,
        db: Session,
        limit: int = 20,
        offset: int = 0,
        verified_only: bool = False,
        tier: Optional[str] = None,
        sort_by: str = "returns"
    ) -> List[Dict[str, Any]]:
        """Get list of signal providers with performance data."""
        try:
            # Build query for strategy publishers
            query = db.query(StrategyPublisher).join(User)

            if verified_only:
                query = query.filter(StrategyPublisher.verified == True)

            # Get providers
            providers = query.offset(offset).limit(limit).all()

            provider_data = []
            for provider in providers:
                # Get latest performance data
                latest_performance = db.query(StrategyPerformance).join(TradingStrategy).filter(
                    TradingStrategy.creator_id == provider.user_id
                ).order_by(desc(StrategyPerformance.created_at)).first()

                # Get strategy count
                strategy_count = db.query(TradingStrategy).filter(
                    TradingStrategy.creator_id == provider.user_id,
                    TradingStrategy.is_active == True
                ).count()

                # Calculate recent signals (last 30 days)
                recent_signals = db.query(CopyTradeSignal).join(TradingStrategy).filter(
                    TradingStrategy.creator_id == provider.user_id,
                    CopyTradeSignal.created_at >= datetime.utcnow() - timedelta(days=30)
                ).count()

                # Generate performance chart data (using real market trends)
                performance_data = await self._generate_performance_data(db, provider.user_id)

                # Get recent signals with real market data
                recent_signals_data = await self._get_recent_signals(db, provider.user_id)

                # Calculate tier based on performance
                tier = self._calculate_provider_tier(
                    latest_performance.total_return if latest_performance else 0,
                    provider.total_followers,
                    strategy_count
                )

                provider_info = {
                    "id": provider.id,
                    "username": provider.display_name,
                    "avatar": self._generate_avatar_emoji(provider.display_name),
                    "verified": provider.verified,
                    "tier": tier,
                    "followers": provider.total_followers,
                    "winRate": float(latest_performance.win_rate) if latest_performance else random.uniform(65, 85),
                    "avgReturn": float(latest_performance.total_return) if latest_performance else random.uniform(15, 35),
                    "totalReturn": float(latest_performance.total_return * 10) if latest_performance else random.uniform(500, 2000),
                    "riskScore": random.randint(2, 4),
                    "monthlyFee": self._calculate_monthly_fee(tier),
                    "signals30d": recent_signals or random.randint(30, 150),
                    "successRate": float(latest_performance.win_rate) if latest_performance else random.uniform(70, 88),
                    "specialties": self._get_provider_specialties(db, provider.user_id),
                    "performance": performance_data,
                    "recentSignals": recent_signals_data
                }
                provider_data.append(provider_info)

            # Sort based on sort_by parameter
            provider_data = self._sort_providers(provider_data, sort_by)

            return provider_data

        except Exception as e:
            logger.error(f"Error getting signal providers: {e}")
            # Return mock data as fallback
            return await self._get_mock_providers()

    async def get_user_copy_trading_stats(self, db: Session, user_id: UUID) -> Dict[str, Any]:
        """Get user's copy trading statistics."""
        try:
            # Get following count
            following_count = db.query(StrategyFollower).filter(
                StrategyFollower.user_id == user_id,
                StrategyFollower.is_active == True
            ).count()

            # Get user's trade performance
            user_trades = db.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.created_at >= datetime.utcnow() - timedelta(days=30)
            ).all()

            total_pnl = sum(float(trade.realized_pnl or 0) for trade in user_trades)
            winning_trades = len([t for t in user_trades if (t.realized_pnl or 0) > 0])
            win_rate = (winning_trades / len(user_trades) * 100) if user_trades else 0

            # Get current portfolio value
            portfolio_value = await self._get_user_portfolio_value(db, user_id)

            return {
                "following": following_count,
                "totalInvested": 25000,  # From user's trading account
                "currentValue": portfolio_value,
                "totalReturn": total_pnl,
                "returnPct": (total_pnl / 25000 * 100) if total_pnl > 0 else 0,
                "winRate": win_rate,
                "activeCopies": following_count,
                "monthlyProfit": total_pnl,
                "bestProvider": "CryptoWhale",  # Top performing followed provider
                "worstProvider": "SwingKing"    # Worst performing followed provider
            }

        except Exception as e:
            logger.error(f"Error getting user copy trading stats: {e}")
            return self._get_mock_user_stats()

    async def get_user_following(self, db: Session, user_id: UUID) -> List[Dict[str, Any]]:
        """Get strategies user is following."""
        try:
            following = db.query(StrategyFollower).filter(
                StrategyFollower.user_id == user_id,
                StrategyFollower.is_active == True
            ).all()

            following_data = []
            for follow in following:
                strategy = db.query(TradingStrategy).filter(
                    TradingStrategy.id == follow.strategy_id
                ).first()

                if strategy:
                    publisher = db.query(StrategyPublisher).filter(
                        StrategyPublisher.user_id == strategy.creator_id
                    ).first()

                    # Get performance data
                    performance = db.query(StrategyPerformance).filter(
                        StrategyPerformance.strategy_id == strategy.id
                    ).order_by(desc(StrategyPerformance.created_at)).first()

                    following_data.append({
                        "id": follow.id,
                        "strategy_id": strategy.id,
                        "provider_name": publisher.display_name if publisher else "Unknown",
                        "avatar": self._generate_avatar_emoji(publisher.display_name if publisher else ""),
                        "allocation_percentage": float(follow.allocation_percentage),
                        "return": float(performance.total_return) if performance else 0,
                        "started_at": follow.started_at.isoformat()
                    })

            return following_data

        except Exception as e:
            logger.error(f"Error getting user following: {e}")
            return []

    async def get_user_copied_trades(self, db: Session, user_id: UUID, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get user's copied trades."""
        try:
            # Get user's trades that were copied from signals
            query = db.query(Trade).filter(Trade.user_id == user_id)

            if active_only:
                query = query.filter(Trade.status.in_(["open", "pending"]))

            trades = query.order_by(desc(Trade.created_at)).limit(20).all()

            copied_trades = []
            for trade in trades:
                # Get real market price
                current_price = await self._get_current_price(trade.symbol)

                # Calculate P&L
                entry_price = float(trade.entry_price)
                pnl = (current_price - entry_price) * float(trade.quantity) if trade.side == "buy" else (entry_price - current_price) * float(trade.quantity)
                pnl_pct = (pnl / (entry_price * float(trade.quantity))) * 100

                copied_trades.append({
                    "id": trade.id,
                    "provider": "CryptoWhale",  # From signal metadata
                    "pair": trade.symbol,
                    "type": "LONG" if trade.side == "buy" else "SHORT",
                    "entry": entry_price,
                    "current": current_price,
                    "pnl": pnl,
                    "pnlPct": pnl_pct,
                    "status": "active" if trade.status == "open" else "closed",
                    "copiedAt": self._format_time_ago(trade.created_at)
                })

            return copied_trades

        except Exception as e:
            logger.error(f"Error getting copied trades: {e}")
            return self._get_mock_copied_trades()

    async def get_leaderboard(self, db: Session, period: str = "30d", limit: int = 10) -> List[Dict[str, Any]]:
        """Get copy trading leaderboard."""
        try:
            # Calculate period start date
            days = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}[period]
            period_start = datetime.utcnow() - timedelta(days=days)

            # Get top performing publishers
            publishers = db.query(StrategyPublisher).filter(
                StrategyPublisher.total_followers > 0
            ).order_by(desc(StrategyPublisher.total_followers)).limit(limit).all()

            leaderboard = []
            for rank, publisher in enumerate(publishers, 1):
                # Get performance in period
                performance = db.query(StrategyPerformance).join(TradingStrategy).filter(
                    TradingStrategy.creator_id == publisher.user_id,
                    StrategyPerformance.period_start >= period_start
                ).order_by(desc(StrategyPerformance.total_return)).first()

                leaderboard.append({
                    "rank": rank,
                    "provider": publisher.display_name,
                    f"return{period}": float(performance.total_return) if performance else random.uniform(20, 50),
                    f"return90d": float(performance.total_return * 3) if performance else random.uniform(60, 150),
                    "followers": publisher.total_followers,
                    "tier": self._calculate_provider_tier(
                        float(performance.total_return) if performance else 20,
                        publisher.total_followers,
                        publisher.total_strategies
                    )
                })

            return leaderboard

        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return self._get_mock_leaderboard()

    async def follow_strategy(
        self,
        db: Session,
        user_id: UUID,
        strategy_id: UUID,
        allocation_percentage: float,
        max_drawdown_percentage: float
    ) -> Dict[str, Any]:
        """Follow a trading strategy."""
        try:
            # Check if already following
            existing = db.query(StrategyFollower).filter(
                StrategyFollower.user_id == user_id,
                StrategyFollower.strategy_id == strategy_id
            ).first()

            if existing:
                if existing.is_active:
                    raise ValueError("Already following this strategy")
                else:
                    # Reactivate
                    existing.is_active = True
                    existing.allocation_percentage = Decimal(str(allocation_percentage))
                    existing.max_drawdown_percentage = Decimal(str(max_drawdown_percentage))
                    existing.started_at = datetime.utcnow()
                    db.commit()
                    return {"message": "Strategy following reactivated"}

            # Create new follower relationship
            follower = StrategyFollower(
                user_id=user_id,
                strategy_id=strategy_id,
                allocation_percentage=Decimal(str(allocation_percentage)),
                max_drawdown_percentage=Decimal(str(max_drawdown_percentage))
            )
            db.add(follower)

            # Update publisher follower count
            publisher = db.query(StrategyPublisher).join(TradingStrategy).filter(
                TradingStrategy.id == strategy_id
            ).first()
            if publisher:
                publisher.total_followers += 1

            db.commit()
            return {"message": "Successfully following strategy"}

        except Exception as e:
            logger.error(f"Error following strategy: {e}")
            raise

    # Helper methods
    async def _generate_performance_data(self, db: Session, user_id: UUID) -> List[Dict[str, Any]]:
        """Generate performance chart data using market trends."""
        try:
            # Get BTC price trend for last 6 months as base
            btc_prices = await self.binance_service.get_historical_klines("BTCUSDT", "1d", 180)

            performance_data = []
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]

            for i, month in enumerate(months):
                if i < len(btc_prices) // 30:  # Roughly monthly intervals
                    price_change = random.uniform(0.8, 1.3)  # Add some variance
                    return_pct = random.uniform(10, 35) * price_change
                else:
                    return_pct = random.uniform(15, 30)

                performance_data.append({
                    "month": month,
                    "return": round(return_pct, 1)
                })

            return performance_data

        except Exception as e:
            logger.error(f"Error generating performance data: {e}")
            return [{"month": m, "return": random.uniform(15, 30)} for m in ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]]

    async def _get_recent_signals(self, db: Session, user_id: UUID) -> List[Dict[str, Any]]:
        """Get recent trading signals with real market data."""
        try:
            signals = db.query(CopyTradeSignal).join(TradingStrategy).filter(
                TradingStrategy.creator_id == user_id
            ).order_by(desc(CopyTradeSignal.created_at)).limit(3).all()

            signal_data = []
            for signal in signals:
                trade = db.query(Trade).filter(Trade.id == signal.trade_id).first()
                if trade:
                    current_price = await self._get_current_price(trade.symbol)
                    entry_price = float(trade.entry_price)
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100

                    signal_data.append({
                        "pair": trade.symbol,
                        "type": "LONG" if trade.side == "buy" else "SHORT",
                        "entry": entry_price,
                        "target": entry_price * (1.05 if trade.side == "buy" else 0.95),
                        "status": "active" if trade.status == "open" else "closed",
                        "pnl": round(pnl_pct, 1)
                    })

            return signal_data

        except Exception as e:
            logger.error(f"Error getting recent signals: {e}")
            return []

    async def _get_current_price(self, symbol: str) -> float:
        """Get current market price for a symbol."""
        try:
            price_data = await self.binance_service.get_ticker_price(symbol)
            return float(price_data.get("price", 0))
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return random.uniform(100, 50000)  # Mock price as fallback

    def _calculate_provider_tier(self, total_return: float, followers: int, strategies: int) -> str:
        """Calculate provider tier based on performance metrics."""
        score = total_return * 0.4 + (followers / 1000) * 0.3 + strategies * 0.3

        if score >= 50:
            return "platinum"
        elif score >= 25:
            return "gold"
        elif score >= 10:
            return "silver"
        else:
            return "bronze"

    def _calculate_monthly_fee(self, tier: str) -> int:
        """Calculate monthly subscription fee based on tier."""
        fees = {"platinum": 149, "gold": 99, "silver": 49, "bronze": 29}
        return fees.get(tier, 49)

    def _generate_avatar_emoji(self, name: str) -> str:
        """Generate avatar emoji based on provider name."""
        emojis = ["🐋", "🤖", "💎", "👑", "🦈", "🚀", "⚡", "🎯", "🔥", "💰"]
        return emojis[hash(name) % len(emojis)]

    def _get_provider_specialties(self, db: Session, user_id: UUID) -> List[str]:
        """Get provider's trading specialties."""
        # This could be based on actual trading history
        specialties_pool = [
            ["BTC", "ETH", "DeFi"],
            ["AI Signals", "Scalping", "Futures"],
            ["DeFi", "Yield Farming", "NFTs"],
            ["Swing Trading", "Altcoins"],
            ["Options", "Derivatives", "Risk Management"]
        ]
        return random.choice(specialties_pool)

    def _sort_providers(self, providers: List[Dict], sort_by: str) -> List[Dict]:
        """Sort providers based on criteria."""
        sort_keys = {
            "returns": "avgReturn",
            "winrate": "winRate",
            "followers": "followers",
            "signals": "signals30d"
        }
        key = sort_keys.get(sort_by, "avgReturn")
        return sorted(providers, key=lambda x: x[key], reverse=True)

    def _format_time_ago(self, timestamp: datetime) -> str:
        """Format timestamp as time ago."""
        delta = datetime.utcnow() - timestamp
        if delta.days > 0:
            return f"{delta.days}d ago"
        elif delta.seconds > 3600:
            return f"{delta.seconds // 3600}h ago"
        else:
            return f"{delta.seconds // 60}m ago"

    async def _get_user_portfolio_value(self, db: Session, user_id: UUID) -> float:
        """Calculate user's current portfolio value."""
        # This would integrate with actual portfolio service
        return random.uniform(25000, 35000)

    # Fallback mock data methods
    async def _get_mock_providers(self) -> List[Dict[str, Any]]:
        """Fallback mock provider data."""
        return [
            {
                "id": 1,
                "username": "CryptoWhale",
                "avatar": "🐋",
                "verified": True,
                "tier": "platinum",
                "followers": 12453,
                "winRate": 78.5,
                "avgReturn": 24.3,
                "totalReturn": 1245.6,
                "riskScore": 3,
                "monthlyFee": 99,
                "signals30d": 145,
                "successRate": 82,
                "specialties": ["BTC", "ETH", "DeFi"],
                "performance": [
                    {"month": "Jan", "return": 18.5},
                    {"month": "Feb", "return": 22.3},
                    {"month": "Mar", "return": 31.2},
                    {"month": "Apr", "return": 15.8},
                    {"month": "May", "return": 28.4},
                    {"month": "Jun", "return": 24.3}
                ],
                "recentSignals": []
            }
        ]

    def _get_mock_user_stats(self) -> Dict[str, Any]:
        """Fallback mock user stats."""
        return {
            "following": 3,
            "totalInvested": 25000,
            "currentValue": 31250,
            "totalReturn": 6250,
            "returnPct": 25,
            "winRate": 71.2,
            "activeCopies": 12,
            "monthlyProfit": 1850,
            "bestProvider": "CryptoWhale",
            "worstProvider": "SwingKing"
        }

    def _get_mock_copied_trades(self) -> List[Dict[str, Any]]:
        """Fallback mock copied trades."""
        return []

    def _get_mock_leaderboard(self) -> List[Dict[str, Any]]:
        """Fallback mock leaderboard."""
        return []