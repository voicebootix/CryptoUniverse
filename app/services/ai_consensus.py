"""
AI Consensus Service - MIGRATED FROM FLOWISE

Advanced multi-AI decision engine using GPT-4, Claude, and Gemini for 
institutional-grade trading consensus with confidence scoring and cost optimization.

FUNCTIONS MIGRATED:
- analyze_opportunity - Multi-AI opportunity analysis with consensus scoring
- validate_trade - Trade validation across multiple AI models
- risk_assessment - Comprehensive risk analysis with AI consensus
- portfolio_review - Portfolio analysis with multi-AI insights  
- market_analysis - Market condition analysis with AI consensus
- consensus_decision - Final decision making with weighted AI opinions

ADVANCED FEATURES:
- Circuit breaker pattern for API reliability
- Cost optimization with intelligent model selection
- Confidence threshold-based decision making
- Real-time AI model performance tracking
- Sophisticated retry logic with exponential backoff
- Multi-AI consensus scoring and weighting

ALL SOPHISTICATION PRESERVED - NO SIMPLIFICATION
Enterprise-grade multi-AI orchestration for trading decisions.
"""

import asyncio
import json
import time
import hashlib
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid

import aiohttp
import numpy as np
import structlog
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.redis import redis_manager
from app.core.logging import LoggerMixin
from app.models.ai import AIModel, AIConsensus, AISignal
from app.models.trading import Trade, Position
from app.models.user import User
from app.models.analytics import PerformanceMetric

settings = get_settings()
logger = structlog.get_logger(__name__)


from app.services.ai_consensus_types import (
    AIModelProvider,
    ConsensusFunction,
    CircuitBreakerState,
    AIModelResponse
)


# Import the complete AI consensus service implementation
from app.services.ai_consensus_core import AIConsensusService, ai_consensus_service
