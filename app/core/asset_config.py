"""
Asset configuration and validation for the CryptoUniverse platform.

Centralized asset management with proper separation of base assets and trading pairs.
"""

from typing import List, Set, Optional
import logging

logger = logging.getLogger(__name__)


class AssetConfig:
    """Asset configuration and validation with normalized trading pairs."""

    # Base assets - individual cryptocurrency symbols
    BASE_ASSETS = {
        # Major cryptocurrencies
        "BTC", "ETH", "BNB", "ADA", "SOL", "XRP", "DOT", "AVAX", "MATIC", "ATOM",
        "LINK", "LTC", "BCH", "XLM", "VET", "FIL", "TRX", "ETC", "XMR", "ALGO",
        "AAVE", "UNI", "SUSHI", "COMP", "MKR", "SNX", "CRV", "YFI", "RUNE", "LUNA",

        # Stablecoins
        "USDT", "USDC", "BUSD", "DAI", "UST", "FRAX", "TUSD", "LUSD",

        # Popular altcoins
        "DOGE", "SHIB", "APE", "SAND", "MANA", "AXS", "CHZ", "ENJ", "GALA", "IMX",
        "LRC", "BAT", "ZRX", "OMG", "REP", "KNC", "REN", "GRT", "BAND", "STORJ",

        # Additional tokens
        "QNT", "INJ", "HBAR", "OP", "NEAR", "STX", "FLOW", "EGLD", "XTZ", "THETA",
        "FTM", "KAVA", "ZIL", "WAVES", "MINA", "KSM", "QTUM", "CELO", "ROSE", "ONE",
        "CRO", "OKB", "LEO", "KCS", "HT", "FTT", "GT", "BGB", "MX", "DYDX",
        "FET", "OCEAN", "AGIX", "NMR", "CTSI", "GNO", "RLC", "VIDT", "DIA", "API3"
    }

    # Trading pairs in canonical slash-delimited format
    TRADING_PAIRS = {
        # Major pairs vs USDT
        "BTC/USDT", "ETH/USDT", "BNB/USDT", "ADA/USDT", "SOL/USDT", "XRP/USDT",
        "DOT/USDT", "AVAX/USDT", "MATIC/USDT", "ATOM/USDT", "LINK/USDT", "LTC/USDT",

        # Additional USDT pairs
        "DOGE/USDT", "SHIB/USDT", "APE/USDT", "SAND/USDT", "MANA/USDT", "AXS/USDT",
        "AAVE/USDT", "UNI/USDT", "SUSHI/USDT", "COMP/USDT", "MKR/USDT", "SNX/USDT",

        # USDC pairs
        "BTC/USDC", "ETH/USDC", "BNB/USDC", "SOL/USDC",

        # Cross pairs
        "ETH/BTC", "BNB/BTC", "ADA/BTC", "DOT/BTC", "LINK/BTC",
    }

    # Legacy support - combination for backward compatibility
    ALL_SUPPORTED_ASSETS = BASE_ASSETS | TRADING_PAIRS

    # Asset categories for better organization
    MAJOR_ASSETS = {"BTC", "ETH", "BNB", "ADA", "SOL", "XRP", "DOT", "AVAX"}
    STABLECOINS = {"USDT", "USDC", "BUSD", "DAI", "UST", "FRAX", "TUSD", "LUSD"}
    DEFI_TOKENS = {"AAVE", "UNI", "SUSHI", "COMP", "MKR", "SNX", "CRV", "YFI"}

    @classmethod
    def symbol_to_exchange(cls, symbol: str) -> str:
        """
        Convert canonical trading pair to exchange format.

        Args:
            symbol: Canonical format (e.g., "BTC/USDT")

        Returns:
            Exchange format (e.g., "BTCUSDT")
        """
        return symbol.replace("/", "")

    @classmethod
    def exchange_to_symbol(cls, exchange_symbol: str) -> Optional[str]:
        """
        Convert exchange format to canonical trading pair.

        Args:
            exchange_symbol: Exchange format (e.g., "BTCUSDT")

        Returns:
            Canonical format (e.g., "BTC/USDT") or None if not recognized
        """
        # Try to match against known patterns
        for pair in cls.TRADING_PAIRS:
            if cls.symbol_to_exchange(pair) == exchange_symbol.upper():
                return pair
        return None

    @classmethod
    def is_supported(cls, symbol: str) -> bool:
        """
        Check if an asset or trading pair is supported.

        Args:
            symbol: Asset symbol or trading pair to validate

        Returns:
            bool: True if asset is supported, False otherwise
        """
        if not symbol:
            return False

        # Normalize symbol to uppercase
        normalized_symbol = symbol.upper().strip()

        if not normalized_symbol:
            return False

        # Check both formats - canonical pairs and base assets
        if normalized_symbol in cls.TRADING_PAIRS:
            return True
        if normalized_symbol in cls.BASE_ASSETS:
            return True

        # Try converting from exchange format
        canonical = cls.exchange_to_symbol(normalized_symbol)
        if canonical and canonical in cls.TRADING_PAIRS:
            return True

        return False

    @classmethod
    def get_supported_assets(cls) -> Set[str]:
        """Get all supported base assets."""
        return cls.BASE_ASSETS.copy()

    @classmethod
    def get_trading_pairs(cls) -> Set[str]:
        """Get all supported trading pairs in canonical format."""
        return cls.TRADING_PAIRS.copy()

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

        # Check trading pairs first (canonical format)
        if normalized in cls.TRADING_PAIRS:
            return normalized

        # Check base assets
        if normalized in cls.BASE_ASSETS:
            return normalized

        # Try converting from exchange format
        canonical = cls.exchange_to_symbol(normalized)
        if canonical:
            return canonical

        return None

    @classmethod
    def validate_trading_pair(cls, base: str, quote: str) -> bool:
        """
        Validate a trading pair by base and quote assets.

        Args:
            base: Base asset symbol
            quote: Quote asset symbol

        Returns:
            bool: True if both assets are supported and pair exists
        """
        if not base or not quote:
            return False

        pair = f"{base.upper()}/{quote.upper()}"
        return pair in cls.TRADING_PAIRS

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

        # Extract base asset from trading pair if needed
        if "/" in normalized:
            base_asset = normalized.split("/")[0]
        else:
            base_asset = normalized

        if base_asset in cls.MAJOR_ASSETS:
            return "major"
        elif base_asset in cls.STABLECOINS:
            return "stablecoin"
        elif base_asset in cls.DEFI_TOKENS:
            return "defi"
        else:
            return "altcoin"