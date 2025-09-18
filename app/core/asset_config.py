"""
Asset configuration and validation for the CryptoUniverse platform.

Centralized asset management with support validation and normalization.
"""

from typing import List, Set, Optional
import logging

logger = logging.getLogger(__name__)


class AssetConfig:
    """Asset configuration and validation."""

    # Supported base assets - comprehensive list for production trading
    ALL_SUPPORTED_ASSETS = {
        # Major cryptocurrencies
        "BTC", "ETH", "BNB", "ADA", "SOL", "XRP", "DOT", "AVAX", "MATIC", "ATOM",
        "LINK", "LTC", "BCH", "XLM", "VET", "FIL", "TRX", "ETC", "XMR", "ALGO",
        "AAVE", "UNI", "SUSHI", "COMP", "MKR", "SNX", "CRV", "YFI", "RUNE", "LUNA",

        # Stablecoins
        "USDT", "USDC", "BUSD", "DAI", "UST", "FRAX", "TUSD", "LUSD",

        # Trading pairs and derivatives
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT", "XRPUSDT",
        "DOTUSDT", "AVAXUSDT", "MATICUSDT", "ATOMUSDT", "LINKUSDT", "LTCUSDT",

        # Popular altcoins
        "DOGE", "SHIB", "APE", "SAND", "MANA", "AXS", "CHZ", "ENJ", "GALA", "IMX",
        "LRC", "BAT", "ZRX", "OMG", "REP", "KNC", "REN", "GRT", "BAND", "STORJ"
    }

    # Asset categories for better organization
    MAJOR_ASSETS = {"BTC", "ETH", "BNB", "ADA", "SOL", "XRP", "DOT", "AVAX"}
    STABLECOINS = {"USDT", "USDC", "BUSD", "DAI", "UST", "FRAX", "TUSD", "LUSD"}
    DEFI_TOKENS = {"AAVE", "UNI", "SUSHI", "COMP", "MKR", "SNX", "CRV", "YFI"}

    @classmethod
    def is_supported(cls, symbol: str) -> bool:
        """
        Check if an asset is supported for trading.

        Args:
            symbol: Asset symbol to validate

        Returns:
            bool: True if asset is supported, False otherwise
        """
        if not symbol:
            return False

        # Normalize symbol to uppercase
        normalized_symbol = symbol.upper().strip()

        if not normalized_symbol:
            return False

        # Return actual membership check (removed "or True" bypass)
        return normalized_symbol in cls.ALL_SUPPORTED_ASSETS

    @classmethod
    def get_supported_assets(cls) -> Set[str]:
        """Get all supported assets."""
        return cls.ALL_SUPPORTED_ASSETS.copy()

    @classmethod
    def get_major_assets(cls) -> Set[str]:
        """Get major cryptocurrency assets."""
        return cls.MAJOR_ASSETS.copy()

    @classmethod
    def get_stablecoins(cls) -> Set[str]:
        """Get supported stablecoins."""
        return cls.STABLECOINS.copy()

    @classmethod
    def is_stablecoin(cls, symbol: str) -> bool:
        """Check if asset is a stablecoin."""
        if not symbol:
            return False
        return symbol.upper().strip() in cls.STABLECOINS

    @classmethod
    def normalize_symbol(cls, symbol: str) -> Optional[str]:
        """
        Normalize asset symbol to standard format.

        Args:
            symbol: Raw symbol input

        Returns:
            Normalized symbol or None if invalid
        """
        if not symbol:
            return None

        normalized = symbol.upper().strip()

        if not normalized:
            return None

        # Validate against supported assets
        if normalized in cls.ALL_SUPPORTED_ASSETS:
            return normalized

        return None

    @classmethod
    def validate_trading_pair(cls, base: str, quote: str) -> bool:
        """
        Validate a trading pair.

        Args:
            base: Base asset symbol
            quote: Quote asset symbol

        Returns:
            bool: True if both assets are supported
        """
        return cls.is_supported(base) and cls.is_supported(quote)

    @classmethod
    def get_asset_category(cls, symbol: str) -> Optional[str]:
        """
        Get asset category.

        Args:
            symbol: Asset symbol

        Returns:
            Category string or None if not supported
        """
        if not cls.is_supported(symbol):
            return None

        normalized = symbol.upper().strip()

        if normalized in cls.MAJOR_ASSETS:
            return "major"
        elif normalized in cls.STABLECOINS:
            return "stablecoin"
        elif normalized in cls.DEFI_TOKENS:
            return "defi"
        else:
            return "altcoin"