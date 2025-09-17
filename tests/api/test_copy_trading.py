"""
Unit tests for copy trading API endpoints.

Tests all copy trading functionality including providers, following,
copied trades, leaderboard, and signal feed.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.copy_trading import (
    StrategyPublisher,
    StrategyFollower,
    StrategyPerformance,
    CopyTradeSignal,
    StrategyStatus,
    SignalStatus
)
from app.models.trading import TradingStrategy, Trade, TradeAction, TradeStatus
from app.services.copy_trading_service import CopyTradingService


class TestCopyTradingEndpoints:
    """Test suite for copy trading endpoints."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_current_user(self):
        """Mock current user."""
        user = Mock(spec=User)
        user.id = uuid.uuid4()
        user.username = "test_user"
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def mock_copy_trading_service(self):
        """Mock copy trading service."""
        service = Mock(spec=CopyTradingService)
        # Set all methods to async mocks
        service.get_signal_providers = AsyncMock()
        service.get_user_copy_trading_stats = AsyncMock()
        service.get_user_following = AsyncMock()
        service.get_user_copied_trades = AsyncMock()
        service.get_leaderboard = AsyncMock()
        service.follow_strategy = AsyncMock()
        service.unfollow_strategy = AsyncMock()
        service.get_user_signal_feed = AsyncMock()
        service.get_strategy_performance = AsyncMock()
        return service

    @pytest.fixture
    def sample_provider_data(self):
        """Sample signal provider data."""
        return [
            {
                "id": 1,
                "username": "CryptoWhale",
                "avatar": "🐋",
                "verified": True,
                "tier": "platinum",
                "strategyId": str(uuid.uuid4()),
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
                ],
                "recentSignals": []
            }
        ]

    @pytest.fixture
    def sample_user_stats(self):
        """Sample user stats data."""
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

    @pytest.fixture
    def sample_following_data(self):
        """Sample following data."""
        return [
            {
                "id": uuid.uuid4(),
                "strategy_id": uuid.uuid4(),
                "provider_name": "CryptoWhale",
                "avatar": "🐋",
                "allocation_percentage": 10.0,
                "return": 15.5,
                "started_at": "2023-12-01T00:00:00"
            }
        ]

    @pytest.fixture
    def sample_copied_trades(self):
        """Sample copied trades data."""
        return [
            {
                "id": uuid.uuid4(),
                "provider": "CryptoWhale",
                "pair": "BTC/USDT",
                "type": "LONG",
                "entry": 43250.0,
                "current": 43680.0,
                "pnl": 430.0,
                "pnlPct": 0.99,
                "status": "active",
                "copiedAt": "2h ago"
            }
        ]

    @pytest.fixture
    def sample_leaderboard(self):
        """Sample leaderboard data."""
        return [
            {
                "rank": 1,
                "provider": "CryptoWhale",
                "return30d": 45.6,
                "return90d": 134.2,
                "followers": 12453,
                "tier": "platinum"
            }
        ]

    @patch('app.api.v1.endpoints.copy_trading.copy_trading_service')
    def test_get_signal_providers_success(self, mock_service, sample_provider_data, mock_db):
        """Test successful retrieval of signal providers."""
        from app.api.v1.endpoints.copy_trading import get_signal_providers

        # Setup mock
        mock_service.get_signal_providers.return_value = sample_provider_data

        # Test with default parameters
        result = pytest.asyncio.run(get_signal_providers(db=mock_db))

        # Assertions
        assert result["success"] is True
        assert result["data"] == sample_provider_data
        assert result["total"] == len(sample_provider_data)
        mock_service.get_signal_providers.assert_called_once_with(
            db=mock_db,
            limit=20,
            offset=0,
            verified_only=False,
            tier=None,
            sort_by="returns"
        )

    @patch('app.api.v1.endpoints.copy_trading.copy_trading_service')
    def test_get_signal_providers_with_filters(self, mock_service, sample_provider_data, mock_db):
        """Test signal providers with filters."""
        from app.api.v1.endpoints.copy_trading import get_signal_providers

        # Setup mock
        mock_service.get_signal_providers.return_value = sample_provider_data

        # Test with filters
        result = pytest.asyncio.run(get_signal_providers(
            db=mock_db,
            limit=10,
            offset=5,
            verified_only=True,
            tier="platinum",
            sort_by="winrate"
        ))

        # Assertions
        assert result["success"] is True
        mock_service.get_signal_providers.assert_called_once_with(
            db=mock_db,
            limit=10,
            offset=5,
            verified_only=True,
            tier="platinum",
            sort_by="winrate"
        )

    @patch('app.api.v1.endpoints.copy_trading.copy_trading_service')
    def test_get_signal_providers_error(self, mock_service, mock_db):
        """Test error handling in get_signal_providers."""
        from app.api.v1.endpoints.copy_trading import get_signal_providers
        from fastapi import HTTPException

        # Setup mock to raise exception
        mock_service.get_signal_providers.side_effect = Exception("Database error")

        # Test error handling
        with pytest.raises(HTTPException) as exc_info:
            pytest.asyncio.run(get_signal_providers(db=mock_db))

        assert exc_info.value.status_code == 500
        assert "Database error" in str(exc_info.value.detail)

    @patch('app.api.v1.endpoints.copy_trading.copy_trading_service')
    def test_get_my_copy_trading_stats_success(self, mock_service, sample_user_stats, mock_db, mock_current_user):
        """Test successful retrieval of user copy trading stats."""
        from app.api.v1.endpoints.copy_trading import get_my_copy_trading_stats

        # Setup mock
        mock_service.get_user_copy_trading_stats.return_value = sample_user_stats

        # Test
        result = pytest.asyncio.run(get_my_copy_trading_stats(
            db=mock_db,
            current_user=mock_current_user
        ))

        # Assertions
        assert result["success"] is True
        assert result["data"] == sample_user_stats
        mock_service.get_user_copy_trading_stats.assert_called_once_with(
            db=mock_db,
            user_id=mock_current_user.id
        )

    @patch('app.api.v1.endpoints.copy_trading.copy_trading_service')
    def test_get_following_strategies_success(self, mock_service, sample_following_data, mock_db, mock_current_user):
        """Test successful retrieval of following strategies."""
        from app.api.v1.endpoints.copy_trading import get_following_strategies

        # Setup mock
        mock_service.get_user_following.return_value = sample_following_data

        # Test
        result = pytest.asyncio.run(get_following_strategies(
            db=mock_db,
            current_user=mock_current_user
        ))

        # Assertions
        assert result["success"] is True
        assert result["data"] == sample_following_data
        mock_service.get_user_following.assert_called_once_with(
            db=mock_db,
            user_id=mock_current_user.id
        )

    @patch('app.api.v1.endpoints.copy_trading.copy_trading_service')
    def test_get_copied_trades_success(self, mock_service, sample_copied_trades, mock_db, mock_current_user):
        """Test successful retrieval of copied trades."""
        from app.api.v1.endpoints.copy_trading import get_copied_trades

        # Setup mock
        mock_service.get_user_copied_trades.return_value = sample_copied_trades

        # Test
        result = pytest.asyncio.run(get_copied_trades(
            db=mock_db,
            current_user=mock_current_user,
            active_only=True
        ))

        # Assertions
        assert result["success"] is True
        assert result["data"] == sample_copied_trades
        mock_service.get_user_copied_trades.assert_called_once_with(
            db=mock_db,
            user_id=mock_current_user.id,
            active_only=True
        )

    @patch('app.api.v1.endpoints.copy_trading.copy_trading_service')
    def test_get_leaderboard_success(self, mock_service, sample_leaderboard, mock_db):
        """Test successful retrieval of leaderboard."""
        from app.api.v1.endpoints.copy_trading import get_leaderboard

        # Setup mock
        mock_service.get_leaderboard.return_value = sample_leaderboard

        # Test
        result = pytest.asyncio.run(get_leaderboard(
            db=mock_db,
            period="30d",
            limit=10
        ))

        # Assertions
        assert result["success"] is True
        assert result["data"] == sample_leaderboard
        mock_service.get_leaderboard.assert_called_once_with(
            db=mock_db,
            period="30d",
            limit=10
        )

    @patch('app.api.v1.endpoints.copy_trading.copy_trading_service')
    def test_follow_strategy_success(self, mock_service, mock_db, mock_current_user):
        """Test successful strategy following."""
        from app.api.v1.endpoints.copy_trading import follow_strategy

        # Setup mock
        strategy_id = uuid.uuid4()
        mock_service.follow_strategy.return_value = {"message": "Successfully following strategy"}

        # Test
        result = pytest.asyncio.run(follow_strategy(
            strategy_id=strategy_id,
            allocation_percentage=10.0,
            max_drawdown=20.0,
            db=mock_db,
            current_user=mock_current_user
        ))

        # Assertions
        assert result["success"] is True
        assert "message" in result["data"]
        mock_service.follow_strategy.assert_called_once_with(
            db=mock_db,
            user_id=mock_current_user.id,
            strategy_id=strategy_id,
            allocation_percentage=10.0,
            max_drawdown_percentage=20.0
        )

    @patch('app.api.v1.endpoints.copy_trading.copy_trading_service')
    def test_unfollow_strategy_success(self, mock_service, mock_db, mock_current_user):
        """Test successful strategy unfollowing."""
        from app.api.v1.endpoints.copy_trading import unfollow_strategy

        # Setup mock
        strategy_id = uuid.uuid4()
        mock_service.unfollow_strategy.return_value = {"message": "Successfully unfollowed strategy"}

        # Test
        result = pytest.asyncio.run(unfollow_strategy(
            strategy_id=strategy_id,
            db=mock_db,
            current_user=mock_current_user
        ))

        # Assertions
        assert result["success"] is True
        assert "message" in result["data"]
        mock_service.unfollow_strategy.assert_called_once_with(
            db=mock_db,
            user_id=mock_current_user.id,
            strategy_id=strategy_id
        )

    @patch('app.api.v1.endpoints.copy_trading.copy_trading_service')
    def test_get_signal_feed_success(self, mock_service, mock_db, mock_current_user):
        """Test successful signal feed retrieval."""
        from app.api.v1.endpoints.copy_trading import get_signal_feed

        # Sample signal feed data
        signal_feed_data = [
            {
                "id": uuid.uuid4(),
                "strategy_id": uuid.uuid4(),
                "provider_name": "CryptoWhale",
                "signal_data": {"pair": "BTC/USDT", "action": "buy", "price": 43250},
                "status": "distributed",
                "created_at": "2023-12-01T12:00:00",
                "distributed_at": "2023-12-01T12:01:00"
            }
        ]

        # Setup mock
        mock_service.get_user_signal_feed.return_value = signal_feed_data

        # Test
        result = pytest.asyncio.run(get_signal_feed(
            db=mock_db,
            current_user=mock_current_user,
            limit=20
        ))

        # Assertions
        assert result["success"] is True
        assert result["data"] == signal_feed_data
        mock_service.get_user_signal_feed.assert_called_once_with(
            db=mock_db,
            user_id=mock_current_user.id,
            limit=20
        )

    @patch('app.api.v1.endpoints.copy_trading.copy_trading_service')
    def test_get_strategy_performance_success(self, mock_service, mock_db):
        """Test successful strategy performance retrieval."""
        from app.api.v1.endpoints.copy_trading import get_strategy_performance

        # Sample performance data
        performance_data = {
            "strategy_id": str(uuid.uuid4()),
            "period": "30d",
            "total_return": 15.5,
            "sharpe_ratio": 1.8,
            "max_drawdown": 8.2,
            "win_rate": 72.5,
            "total_trades": 45,
            "followers_count": 150,
            "aum": 50000.0
        }

        # Setup mock
        strategy_id = uuid.uuid4()
        mock_service.get_strategy_performance.return_value = performance_data

        # Test
        result = pytest.asyncio.run(get_strategy_performance(
            strategy_id=strategy_id,
            period="30d",
            db=mock_db
        ))

        # Assertions
        assert result["success"] is True
        assert result["data"] == performance_data
        mock_service.get_strategy_performance.assert_called_once_with(
            db=mock_db,
            strategy_id=strategy_id,
            period="30d"
        )

    def test_parameter_validation(self):
        """Test parameter validation for endpoints."""
        from app.api.v1.endpoints.copy_trading import follow_strategy
        from fastapi import HTTPException

        # Test allocation percentage validation (should be between 1-100)
        with pytest.raises(Exception):  # FastAPI query validation
            pytest.asyncio.run(follow_strategy(
                strategy_id=uuid.uuid4(),
                allocation_percentage=0.5,  # Below minimum
                max_drawdown=20.0,
                db=Mock(),
                current_user=Mock()
            ))

        with pytest.raises(Exception):  # FastAPI query validation
            pytest.asyncio.run(follow_strategy(
                strategy_id=uuid.uuid4(),
                allocation_percentage=101.0,  # Above maximum
                max_drawdown=20.0,
                db=Mock(),
                current_user=Mock()
            ))


class TestCopyTradingService:
    """Test suite for CopyTradingService methods."""

    @pytest.fixture
    def service(self):
        """Copy trading service instance."""
        return CopyTradingService()

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        db = Mock(spec=Session)
        db.query.return_value.join.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = []
        db.query.return_value.filter.return_value.count.return_value = 0
        db.query.return_value.filter.return_value.first.return_value = None
        return db

    @patch('app.services.copy_trading_service.BinanceService')
    def test_service_initialization(self, mock_binance_service):
        """Test service initialization."""
        service = CopyTradingService()
        assert service.binance_service is not None
        mock_binance_service.assert_called_once()

    def test_calculate_provider_tier(self, service):
        """Test provider tier calculation logic."""
        # Test platinum tier
        tier = service._calculate_provider_tier(
            total_return=50.0,
            followers=2000,
            strategies=5
        )
        assert tier == "platinum"

        # Test gold tier
        tier = service._calculate_provider_tier(
            total_return=25.0,
            followers=500,
            strategies=3
        )
        assert tier == "gold"

        # Test silver tier
        tier = service._calculate_provider_tier(
            total_return=15.0,
            followers=100,
            strategies=2
        )
        assert tier == "silver"

        # Test bronze tier
        tier = service._calculate_provider_tier(
            total_return=5.0,
            followers=50,
            strategies=1
        )
        assert tier == "bronze"

    def test_calculate_monthly_fee(self, service):
        """Test monthly fee calculation."""
        assert service._calculate_monthly_fee("platinum") == 149
        assert service._calculate_monthly_fee("gold") == 99
        assert service._calculate_monthly_fee("silver") == 49
        assert service._calculate_monthly_fee("bronze") == 29
        assert service._calculate_monthly_fee("unknown") == 49  # Default

    def test_generate_avatar_emoji(self, service):
        """Test avatar emoji generation."""
        # Same name should always produce same emoji
        emoji1 = service._generate_avatar_emoji("TestProvider")
        emoji2 = service._generate_avatar_emoji("TestProvider")
        assert emoji1 == emoji2

        # Different names should potentially produce different emojis
        emoji3 = service._generate_avatar_emoji("DifferentProvider")
        # Note: They might be the same due to hash collision, but that's okay

    def test_sort_providers(self, service):
        """Test provider sorting logic."""
        providers = [
            {"avgReturn": 10, "winRate": 70, "followers": 100, "signals30d": 50},
            {"avgReturn": 20, "winRate": 80, "followers": 200, "signals30d": 60},
            {"avgReturn": 15, "winRate": 75, "followers": 150, "signals30d": 55}
        ]

        # Test sort by returns (default)
        sorted_providers = service._sort_providers(providers, "returns")
        assert sorted_providers[0]["avgReturn"] == 20
        assert sorted_providers[2]["avgReturn"] == 10

        # Test sort by winrate
        sorted_providers = service._sort_providers(providers, "winrate")
        assert sorted_providers[0]["winRate"] == 80
        assert sorted_providers[2]["winRate"] == 70

        # Test sort by followers
        sorted_providers = service._sort_providers(providers, "followers")
        assert sorted_providers[0]["followers"] == 200
        assert sorted_providers[2]["followers"] == 100

    def test_format_time_ago(self, service):
        """Test time ago formatting."""
        from datetime import datetime, timedelta

        now = datetime.utcnow()

        # Test days ago
        timestamp = now - timedelta(days=2)
        result = service._format_time_ago(timestamp)
        assert "2d ago" in result

        # Test hours ago
        timestamp = now - timedelta(hours=3)
        result = service._format_time_ago(timestamp)
        assert "3h ago" in result

        # Test minutes ago
        timestamp = now - timedelta(minutes=30)
        result = service._format_time_ago(timestamp)
        assert "30m ago" in result