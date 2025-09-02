"""
Market Analysis Service - Compatibility wrapper

This module serves as a compatibility layer that re-exports the main 
MarketAnalysisService from the core implementation. This prevents
circular imports while maintaining backward compatibility.
"""

# Re-export everything from the core implementation
from app.services.market_analysis_core import (
    MarketAnalysisService, 
    market_analysis_service,
    ExchangeConfigurations
)
