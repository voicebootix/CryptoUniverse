"""
AI Consensus Service Types

Shared types and classes for AI consensus functionality.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class AIModelProvider(str, Enum):
    """AI model provider enumeration."""
    GPT4 = "gpt4"
    CLAUDE = "claude"
    GEMINI = "gemini"


class ConsensusFunction(str, Enum):
    """Consensus function types."""
    ANALYZE_OPPORTUNITY = "analyze_opportunity"
    VALIDATE_TRADE = "validate_trade"
    RISK_ASSESSMENT = "risk_assessment"
    PORTFOLIO_REVIEW = "portfolio_review"
    MARKET_ANALYSIS = "market_analysis"
    CONSENSUS_DECISION = "consensus_decision"


@dataclass
class CircuitBreakerState:
    """Circuit breaker state for AI model."""
    failures: int = 0
    last_failure: Optional[datetime] = None
    is_open: bool = False
    success_count: int = 0


@dataclass
class AIModelResponse:
    """AI model response container."""
    provider: AIModelProvider
    content: str
    confidence: float
    reasoning: str
    cost: float
    response_time: float
    success: bool
    error: Optional[str] = None
