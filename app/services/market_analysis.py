"""
Market Analysis Service - MIGRATED FROM FLOWISE

Enterprise-grade market analysis with ALL 20+ functions preserved from the 
original 6000+ line Flowise Market_Analysis_Service_Consolidated.

This service provides comprehensive market intelligence including:
- Real-time price tracking across multiple exchanges
- Technical analysis with 15+ indicators
- Cross-exchange arbitrage detection
- Market sentiment analysis
- Institutional flow tracking
- Alpha generation algorithms
- Volatility and momentum analysis
- Support/resistance detection

NO SIMPLIFICATION - All sophisticated algorithms preserved and enhanced
with database integration, multi-tenancy, and enterprise features.
"""

import asyncio
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
import uuid
import base64

import aiohttp
import numpy as np
import pandas as pd
import structlog
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.core.config import get_settings
from app.core.database import get_database
from app.core.redis import redis_manager
from app.core.logging import LoggerMixin
from app.models.market import MarketData, Symbol, TechnicalIndicator
from app.models.trading import Trade, Position
from app.models.user import User
from app.models.credit import CreditAccount, CreditTransaction
from app.models.analytics import PerformanceMetric, RiskMetric
from app.models.system import AuditLog, SystemHealth

settings = get_settings()
logger = structlog.get_logger(__name__)


class ExchangeConfigurations:
    """Exchange API configurations for market data - ported from Flowise."""
    
    BINANCE = {
        "base_url": "https://api.binance.com",
        "endpoints": {
            "ticker": "/api/v3/ticker/24hr",
            "price": "/api/v3/ticker/price", 
            "depth": "/api/v3/depth",
            "klines": "/api/v3/klines",
            "trades": "/api/v3/trades",
            "avg_price": "/api/v3/avgPrice",
            "exchange_info": "/api/v3/exchangeInfo"
        },
        "rate_limit": 1200,  # requests per minute
        "weight_limits": {
            "ticker": 1,
            "price": 1,
            "depth": 1,
            "klines": 1
        }
    }
    
    KRAKEN = {
        "base_url": "https://api.kraken.com",
        "endpoints": {
            "ticker": "/0/public/Ticker",
            "depth": "/0/public/Depth",
            "trades": "/0/public/Trades",
            "ohlc": "/0/public/OHLC",
            "asset_pairs": "/0/public/AssetPairs",
            "assets": "/0/public/Assets"
        },
        "rate_limit": 60,  # requests per minute
        "counter_limit": 15  # API counter
    }
    
    KUCOIN = {
        "base_url": "https://api.kucoin.com",
        "endpoints": {
            "ticker": "/api/v1/market/allTickers",
            "stats": "/api/v1/market/stats",
            "orderbook": "/api/v1/market/orderbook/level2_20",
            "klines": "/api/v1/market/candles",
            "trades": "/api/v1/market/histories",
            "symbols": "/api/v1/symbols"
        },
        "rate_limit": 1800,  # requests per minute
        "weight_limits": {
            "ticker": 1,
            "stats": 1,
            "orderbook": 1
        }
    }
    
    @classmethod
    def get_all_exchanges(cls) -> List[str]:
        """Get list of all supported exchanges."""
        return ["binance", "kraken", "kucoin", "coinbase", "bybit", "okx", "bitget", "gateio"]
    
    @classmethod
    def get_config(cls, exchange: str) -> Dict[str, Any]:
        """Get configuration for specific exchange."""
        configs = {
            "binance": cls.BINANCE,
            "kraken": cls.KRAKEN, 
            "kucoin": cls.KUCOIN,
            "coinbase": {"base_url": "https://api.exchange.coinbase.com", "rate_limit": 600},
            "bybit": {"base_url": "https://api.bybit.com", "rate_limit": 600},
            "okx": {"base_url": "https://www.okx.com", "rate_limit": 600},
            "bitget": {"base_url": "https://api.bitget.com", "rate_limit": 600},
            "gateio": {"base_url": "https://api.gateio.ws", "rate_limit": 300}
        }
        return configs.get(exchange.lower(), {})


# Import the complete market analysis service implementation
from app.services.market_analysis_core import MarketAnalysisService, market_analysis_service
