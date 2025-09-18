"""
<<<<<<< HEAD
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
=======
Asset Configuration - NO HARDCODED LIMITATIONS
Dynamic asset management for enterprise platform

This configuration allows unlimited assets and can be extended
without code changes.
"""

from typing import List, Dict, Any
import json
import os

class AssetConfiguration:
    """
    Dynamic asset configuration without hardcoded limits.
    """

    # Configuration flag - True allows all assets, False enforces whitelist
    ALLOW_ALL_ASSETS = True  # Default: allow all assets (current behavior)

    # Top 100+ crypto assets by market cap - NO LIMITATIONS
    ALL_SUPPORTED_ASSETS = [
        # Top 10 by Market Cap
        "BTC", "ETH", "BNB", "SOL", "XRP", "USDC", "ADA", "DOGE", "AVAX", "TRX",

        # DeFi Tokens (11-30)
        "LINK", "DOT", "MATIC", "UNI", "DAI", "LTC", "ICP", "ATOM", "ETC", "FIL",
        "APT", "ARB", "HBAR", "OP", "NEAR", "VET", "INJ", "GRT", "RUNE", "AAVE",

        # Layer 1/2 Solutions (31-50)
        "STX", "IMX", "ALGO", "FLOW", "EGLD", "XTZ", "SAND", "MANA", "AXS", "THETA",
        "FTM", "KAVA", "ZIL", "WAVES", "MINA", "KSM", "QTUM", "CELO", "ROSE", "ONE",

        # Exchange Tokens (51-70)
        "CRO", "OKB", "LEO", "KCS", "HT", "FTT", "GT", "BGB", "MX", "DYDX",
        "SRM", "RAY", "SUSHI", "CAKE", "QUICK", "JOE", "OSMO", "RUNE", "PERP", "GMX",

        # Gaming & Metaverse (71-90)
        "GALA", "ENJ", "CHZ", "ALICE", "SLP", "TLM", "GODS", "SUPER", "UFO", "HERO",
        "MBOX", "MOBOX", "PYR", "STAR", "WILD", "REV", "DPET", "SKILL", "MIST", "KMON",

        # AI & Data Tokens (91-100+)
        "FET", "OCEAN", "AGIX", "NMR", "CTSI", "GNO", "RLC", "VIDT", "DIA", "API3",

        # Stablecoins
        "USDT", "USDC", "BUSD", "DAI", "TUSD", "USDP", "FRAX", "LUSD", "USDD", "GUSD",

        # Privacy Coins
        "XMR", "ZEC", "DASH", "DCR", "ZEN", "XVG", "BEAM", "GRIN",

        # Additional Top 200
        "QNT", "MKR", "SNX", "CRV", "BAT", "LRC", "ENS", "1INCH", "COMP", "YFI",
        "BAL", "KNC", "REN", "BAND", "ALPHA", "BADGER", "CREAM", "PICKLE", "DODO", "MASK"
    ]

    @classmethod
    def get_all_symbols(cls, quote_currency: str = "USDT") -> List[str]:
        """
        Get all supported trading pairs.
        No limitations - returns ALL available assets.
        """
        return [f"{asset}/{quote_currency}" for asset in cls.ALL_SUPPORTED_ASSETS]

    @classmethod
    def get_symbols_by_category(cls, category: str, quote_currency: str = "USDT") -> List[str]:
        """
        Get symbols by category without limitations.
        """
        categories = {
            "large_cap": cls.ALL_SUPPORTED_ASSETS[:10],
            "defi": cls.ALL_SUPPORTED_ASSETS[10:30],
            "layer1": cls.ALL_SUPPORTED_ASSETS[30:50],
            "gaming": cls.ALL_SUPPORTED_ASSETS[70:90],
            "ai": cls.ALL_SUPPORTED_ASSETS[90:100],
            "all": cls.ALL_SUPPORTED_ASSETS  # NO LIMIT
        }

        assets = categories.get(category, cls.ALL_SUPPORTED_ASSETS)
        return [f"{asset}/{quote_currency}" for asset in assets]

    @classmethod
    def get_backtest_symbols(cls, count: int = None) -> List[str]:
        """
        Get symbols for backtesting.
        If count is None, returns ALL symbols (no limit).
        """
        all_symbols = cls.get_all_symbols()

        if count is None:
            return all_symbols  # Return ALL - no limitations

        # Diversified selection if count specified
        if count <= len(all_symbols):
            # Take from different categories for diversity
            step = max(1, len(all_symbols) // count)
            return all_symbols[::step][:count]

        return all_symbols

    @classmethod
    def load_custom_assets(cls, file_path: str = None) -> List[str]:
        """
        Load custom assets from configuration file.
        Allows unlimited extension without code changes.
        """
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    custom_config = json.load(f)
                    return custom_config.get('assets', cls.ALL_SUPPORTED_ASSETS)
            except Exception:
                pass

        # Check environment variable for custom assets
        custom_assets = os.environ.get('CRYPTO_ASSETS')
        if custom_assets:
            return custom_assets.split(',')

        return cls.ALL_SUPPORTED_ASSETS
>>>>>>> 74798ab3bb0b22f57424b2a99d41a082a3880f44

    @classmethod
    def is_supported(cls, symbol: str) -> bool:
        """
<<<<<<< HEAD
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
=======
        Check if a symbol is supported.
        Respects the ALLOW_ALL_ASSETS flag - if True, allows all symbols;
        if False, enforces the whitelist in ALL_SUPPORTED_ASSETS.
        """
        # Extract base asset from symbol (BTC/USDT -> BTC)
        base_asset = symbol.split('/')[0].upper() if '/' in symbol else symbol.upper()

        # If ALLOW_ALL_ASSETS is True, allow everything (current default behavior)
        if cls.ALLOW_ALL_ASSETS:
            return True

        # Otherwise, check if the parsed base_asset is in the whitelist
        return base_asset in cls.ALL_SUPPORTED_ASSETS


# Global configuration instance
asset_config = AssetConfiguration()


def get_asset_config() -> AssetConfiguration:
    """Get asset configuration for dependency injection."""
    return asset_config
>>>>>>> 74798ab3bb0b22f57424b2a99d41a082a3880f44
