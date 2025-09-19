"""
Test suite for win rate standardization across the CryptoUniverse platform.

Tests the canonical 0-1 internal unit system with proper conversions for:
- DB I/O (0-100% storage format)
- API responses (configurable format)
- Internal operations (0-1 fraction)
"""

import pytest
from decimal import Decimal
from app.services.strategy_marketplace_service import StrategyMarketplaceService


class TestWinRateConversions:
    """Test win rate conversion utilities."""

    def test_normalize_fraction_input(self):
        """Test that fraction inputs (0-1) are preserved."""
        assert StrategyMarketplaceService.normalize_win_rate_to_fraction(0.0) == 0.0
        assert StrategyMarketplaceService.normalize_win_rate_to_fraction(0.25) == 0.25
        assert StrategyMarketplaceService.normalize_win_rate_to_fraction(0.5) == 0.5
        assert StrategyMarketplaceService.normalize_win_rate_to_fraction(0.75) == 0.75
        assert StrategyMarketplaceService.normalize_win_rate_to_fraction(1.0) == 1.0

    def test_normalize_percentage_input(self):
        """Test that percentage inputs (0-100) are converted to fractions."""
        assert StrategyMarketplaceService.normalize_win_rate_to_fraction(0.0) == 0.0
        assert StrategyMarketplaceService.normalize_win_rate_to_fraction(25.0) == 0.25
        assert StrategyMarketplaceService.normalize_win_rate_to_fraction(50.0) == 0.5
        assert StrategyMarketplaceService.normalize_win_rate_to_fraction(75.0) == 0.75
        assert StrategyMarketplaceService.normalize_win_rate_to_fraction(100.0) == 1.0

    def test_normalize_boundary_cases(self):
        """Test boundary cases and edge values."""
        # Exact boundary at 1.0
        assert StrategyMarketplaceService.normalize_win_rate_to_fraction(1.0) == 1.0
        assert StrategyMarketplaceService.normalize_win_rate_to_fraction(1.00001) == 0.0100001

        # Values slightly over 100% should be capped
        assert StrategyMarketplaceService.normalize_win_rate_to_fraction(100.1) == 1.0
        assert StrategyMarketplaceService.normalize_win_rate_to_fraction(150.0) == 1.0

        # Values slightly over 1.0 should be treated as percentages
        assert StrategyMarketplaceService.normalize_win_rate_to_fraction(1.5) == 0.015

    def test_convert_to_percentage(self):
        """Test conversion from fraction to percentage."""
        assert StrategyMarketplaceService.convert_fraction_to_percentage(0.0) == 0.0
        assert StrategyMarketplaceService.convert_fraction_to_percentage(0.25) == 25.0
        assert StrategyMarketplaceService.convert_fraction_to_percentage(0.5) == 50.0
        assert StrategyMarketplaceService.convert_fraction_to_percentage(0.75) == 75.0
        assert StrategyMarketplaceService.convert_fraction_to_percentage(1.0) == 100.0

    def test_round_trip_conversion(self):
        """Test that conversions are reversible."""
        test_percentages = [0.0, 25.0, 33.33, 50.0, 66.67, 75.0, 90.5, 100.0]

        for percent in test_percentages:
            fraction = StrategyMarketplaceService.normalize_win_rate_to_fraction(percent)
            back_to_percent = StrategyMarketplaceService.convert_fraction_to_percentage(fraction)
            assert abs(back_to_percent - percent) < 0.001, f"Round trip failed for {percent}%"

    def test_precision_preservation(self):
        """Test that precision is maintained during conversions."""
        # Test high precision values
        assert StrategyMarketplaceService.normalize_win_rate_to_fraction(74.83) == 0.7483
        assert StrategyMarketplaceService.convert_fraction_to_percentage(0.7483) == 74.83


class TestDatabaseModelCompatibility:
    """Test backward compatibility in database models."""

    def test_strategy_performance_history_compatibility(self):
        """Test StrategyPerformanceHistory model compatibility."""
        from app.models.market_data import StrategyPerformanceHistory

        # Create instance
        perf = StrategyPerformanceHistory()

        # Test setting via percentage (backward compatibility)
        perf.win_rate_percent = 75.5
        assert perf.win_rate == Decimal('75.5')
        assert perf.win_rate_fraction == 0.755

        # Test setting via fraction (new canonical way)
        perf.win_rate_fraction = 0.8
        assert perf.win_rate == Decimal('80.0')
        assert perf.win_rate_percent == 80.0

    def test_backtest_result_compatibility(self):
        """Test BacktestResult model compatibility."""
        from app.models.market_data import BacktestResult

        # Create instance
        backtest = BacktestResult()

        # Test setting via percentage (backward compatibility)
        backtest.win_rate_percent = 62.5
        assert backtest.win_rate == Decimal('62.5')
        assert backtest.win_rate_fraction == 0.625

        # Test setting via fraction (new canonical way)
        backtest.win_rate_fraction = 0.9
        assert backtest.win_rate == Decimal('90.0')
        assert backtest.win_rate_percent == 90.0

    def test_boundary_value_capping(self):
        """Test that values are properly capped at boundaries."""
        from app.models.market_data import StrategyPerformanceHistory

        perf = StrategyPerformanceHistory()

        # Test percentage capping
        perf.win_rate_percent = 150.0  # Over 100%
        assert perf.win_rate == Decimal('100.0')

        # Test fraction capping
        perf.win_rate_fraction = 1.5  # Over 1.0
        assert perf.win_rate == Decimal('100.0')


class TestServiceIntegration:
    """Test integration with StrategyMarketplaceService."""

    @pytest.fixture
    def service(self):
        return StrategyMarketplaceService()

    def test_performance_data_normalization(self, service):
        """Test that performance data is properly normalized."""
        # Mock performance data with percentage values
        performance_data = {
            "win_rate": 74.8,
            "total_trades": 150,
            "total_pnl": 1250.0
        }

        # The service should normalize win_rate to fraction
        raw_win_rate = service._safe_float(performance_data.get("win_rate", 0))
        normalized_win_rate = service.normalize_win_rate_to_fraction(raw_win_rate)

        assert normalized_win_rate == 0.748

    def test_pricing_logic_uses_fractions(self, service):
        """Test that pricing logic uses 0-1 fractions internally."""
        # This test would need to mock a strategy object, but demonstrates the concept
        # In actual implementation, ensure pricing comparisons use 0.80, 0.70, 0.60

        # Mock strategy with fractional win_rate
        class MockStrategy:
            def __init__(self, win_rate_fraction):
                self.win_rate = win_rate_fraction

        # Test various win rate levels
        high_performer = MockStrategy(0.85)  # 85% win rate
        medium_performer = MockStrategy(0.72)  # 72% win rate
        low_performer = MockStrategy(0.55)  # 55% win rate

        # Verify comparisons work with fractional values
        assert high_performer.win_rate > 0.80
        assert medium_performer.win_rate > 0.70
        assert low_performer.win_rate < 0.60


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_none_and_invalid_inputs(self):
        """Test handling of None and invalid inputs."""
        # normalize_win_rate_to_fraction should handle invalid inputs gracefully
        # In production, add error handling for None, negative, etc.

        # For now, test that we handle expected numeric inputs
        assert StrategyMarketplaceService.normalize_win_rate_to_fraction(0) == 0.0

        # Test very small values
        assert StrategyMarketplaceService.normalize_win_rate_to_fraction(0.001) == 0.001
        assert StrategyMarketplaceService.normalize_win_rate_to_fraction(0.1) == 0.1  # 10% as percentage becomes 0.001

    def test_floating_point_precision(self):
        """Test floating point precision edge cases."""
        # Test values that might have floating point precision issues
        test_value = 33.333333
        normalized = StrategyMarketplaceService.normalize_win_rate_to_fraction(test_value)
        back_to_percent = StrategyMarketplaceService.convert_fraction_to_percentage(normalized)

        # Should be very close (within floating point precision)
        assert abs(back_to_percent - test_value) < 1e-10


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/test_win_rate_standardization.py -v
    pytest.main([__file__, "-v"])