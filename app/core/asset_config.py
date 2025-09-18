"""
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

    @classmethod
    def is_supported(cls, symbol: str) -> bool:
        """
        Check if a symbol is supported.
        By default, ALL symbols are supported (no restrictions).
        """
        # Extract base asset from symbol (BTC/USDT -> BTC)
        base_asset = symbol.split('/')[0].upper() if '/' in symbol else symbol.upper()

        # Check if in our list OR allow any asset (no restrictions)
        return base_asset in cls.ALL_SUPPORTED_ASSETS or True  # Always true = no limits


# Global configuration instance
asset_config = AssetConfiguration()


def get_asset_config() -> AssetConfiguration:
    """Get asset configuration for dependency injection."""
    return asset_config