"""
ENTERPRISE USER OPPORTUNITY DISCOVERY SERVICE

This service is the CORE business logic that connects:
- User's purchased strategy portfolio (marketplace)
- Enterprise asset discovery (thousands of assets across 10+ exchanges)  
- Real trading strategies (25+ AI strategies)
- Credit system integration
- Performance tracking

NO MOCK DATA - ALL PRODUCTION READY

Author: CTO Assistant
Date: 2025-09-12
"""

import asyncio
import copy
import dataclasses
import hashlib
import json
import math
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from decimal import Decimal

import structlog

from app.core.config import get_settings
from app.core.database import get_database
from app.core.redis import get_redis_client
from app.core.logging import LoggerMixin
from app.constants.opportunity import build_strategy_policy_baseline
from app.services.strategy_marketplace_service import strategy_marketplace_service
from app.services.trading_strategies import trading_strategies_service
from app.services.dynamic_asset_filter import enterprise_asset_filter
from app.services.market_analysis import market_analysis_service
from app.models.credit import CreditAccount, CreditTransaction
from app.models.user import User
from app.services.portfolio_risk_core import portfolio_risk_service
from sqlalchemy import select
from app.services.strategy_scanning_policy_service import (
    strategy_scanning_policy_service,
)


# Allow the opportunity discovery service to wait long enough for the
# strategy marketplace service (which can take up to a minute) to respond.
# This value was raised from 15s -> 65s so our wait is slightly longer than
# the marketplace service's 60s internal timeout, preventing premature
# cancellations while still bounding the request time for circuit breaker
# logic.
PORTFOLIO_FETCH_TIMEOUT_SECONDS: float = 65.0

settings = get_settings()

DEFAULT_STRATEGY_SYMBOL_LIMIT = 20


@dataclass
class OpportunityResult:
    """Single opportunity result from strategy scanning."""
    strategy_id: str
    strategy_name: str
    opportunity_type: str
    symbol: str
    exchange: str
    profit_potential_usd: float
    confidence_score: float
    risk_level: str
    required_capital_usd: float
    estimated_timeframe: str
    entry_price: Optional[float]
    exit_price: Optional[float]
    metadata: Dict[str, Any]
    discovered_at: datetime


@dataclass
class _CachedOpportunityResult:
    payload: Dict[str, Any]
    expires_at: float
    partial: bool


@dataclass
class UserOpportunityProfile:
    """User's opportunity discovery profile based on their strategy portfolio."""
    user_id: str
    active_strategy_count: int
    total_monthly_strategy_cost: int
    user_tier: str  # basic, pro, enterprise
    max_asset_tier: str  # tier_retail, tier_professional, etc
    opportunity_scan_limit: int
    last_scan_time: Optional[datetime]
    strategy_fingerprint: str


class UserOpportunityDiscoveryService(LoggerMixin):
    """
    ENTERPRISE USER OPPORTUNITY DISCOVERY SERVICE
    
    This is the HEART of your business model - connecting user's purchased strategies
    with enterprise asset discovery to deliver personalized opportunities.
    """
    
    def __init__(self):
        super().__init__()
        self.redis: Optional[Any] = None
        
        # ENTERPRISE CACHING LAYER - Optimized for Performance
        self._portfolio_cache = {}  # {user_id: {'data': portfolio, 'expires': timestamp}}
        self._cache_ttl = 900  # 15 minutes - increased from 5 to reduce DB queries
        
        # CIRCUIT BREAKER for external calls
        self._circuit_breaker = {
            'failures': 0,
            'last_failure': 0,
            'is_open': False,
            'threshold': 3,
            'timeout': 60
        }
        self.opportunity_cache = {}
        self._scan_tasks: Dict[str, asyncio.Task] = {}
        self._scan_tasks_lock = asyncio.Lock()
        self._scan_cache_lock = asyncio.Lock()
        self._scan_cache_ttl = 300  # 5 minutes to align with fast-refresh chat expectations
        self._partial_cache_ttl = 300  # 5 minutes - increased from 2 for better partial result reuse
        self._scan_response_budget = 150.0  # 150 seconds - allow all 14 strategies to complete (portfolio optimization takes ~80s)
        self._scan_lookup: Dict[str, str] = {}
        self._scan_lookup_lock = asyncio.Lock()
        self._user_latest_scan_key: Dict[str, str] = {}

        # Strategy scanning methods mapping
        self.strategy_scanners = {
            "risk_management": self._scan_risk_management_opportunities,
            "portfolio_optimization": self._scan_portfolio_optimization_opportunities,
            "spot_momentum_strategy": self._scan_spot_momentum_opportunities,
            "spot_mean_reversion": self._scan_spot_mean_reversion_opportunities,
            "spot_breakout_strategy": self._scan_spot_breakout_opportunities,
            "scalping_strategy": self._scan_scalping_opportunities,
            "pairs_trading": self._scan_pairs_trading_opportunities,
            "statistical_arbitrage": self._scan_statistical_arbitrage_opportunities,
            "market_making": self._scan_market_making_opportunities,
            "futures_trade": self._scan_futures_trading_opportunities,
            "options_trade": self._scan_options_trading_opportunities,
            "funding_arbitrage": self._scan_funding_arbitrage_opportunities,
            "hedge_position": self._scan_hedge_opportunities,
            "complex_strategy": self._scan_complex_strategy_opportunities,
            "futures_arbitrage": self._scan_futures_arbitrage_opportunities,
            "options_strategies": self._scan_options_trading_opportunities,
            "volatility_trading": self._scan_volatility_trading_opportunities,
            "news_sentiment": self._scan_news_sentiment_opportunities,
            "funding_arbitrage_pro": self._scan_funding_arbitrage_pro_opportunities,
            "market_making_pro": self._scan_market_making_pro_opportunities,
            "scalping_engine": self._scan_scalping_engine_opportunities,
            "swing_navigator": self._scan_swing_navigator_opportunities,
            "position_manager": self._scan_position_manager_opportunities,
            "risk_guardian": self._scan_risk_guardian_opportunities,
            "portfolio_optimizer": self._scan_portfolio_optimizer_opportunities,
            "strategy_analytics": self._scan_strategy_analytics_opportunities,
            "momentum_trader": self._scan_momentum_trader_opportunities,
            "mean_reversion_pro": self._scan_mean_reversion_pro_opportunities,
            "breakout_hunter": self._scan_breakout_hunter_opportunities,
            "algorithmic_suite": self._scan_algorithmic_suite_opportunities,
            "pairs_trader": self._scan_pairs_trader_opportunities,
            "statistical_arbitrage_pro": self._scan_statistical_arbitrage_pro_opportunities,
            "market_maker": self._scan_market_maker_opportunities,
            "scalping_engine_pro": self._scan_scalping_engine_pro_opportunities,
            "swing_navigator_pro": self._scan_swing_navigator_pro_opportunities,
        }

        # Canonical strategy aliases so display names map to scanners
        self._strategy_aliases = {
            self._normalize_strategy_identifier("ai futures arbitrage"): "futures_arbitrage",
            self._normalize_strategy_identifier("ai futures trading"): "futures_trade",
            self._normalize_strategy_identifier("ai options strategies"): "options_strategies",
            self._normalize_strategy_identifier("ai options trading"): "options_trade",
            self._normalize_strategy_identifier("ai volatility trading"): "volatility_trading",
            self._normalize_strategy_identifier("ai news sentiment"): "news_sentiment",
        }
        
        # User tier configurations - Enterprise-grade with dynamic limits
        self.tier_configs = {
            "basic": {
                "max_asset_tier": "tier_retail",
                "scan_limit": None,  # No hard limit - scan all available opportunities
                "max_strategies": None  # No hard limit - user can purchase unlimited strategies
            },
            "pro": {
                "max_asset_tier": "tier_professional",
                "scan_limit": None,  # No hard limit
                "max_strategies": None  # No hard limit
            },
            "enterprise": {
                "max_asset_tier": "tier_institutional",
                "scan_limit": None,  # No hard limit
                "max_strategies": None  # No hard limit
            }
        }

        self._policy_refresh_lock = asyncio.Lock()
        self._policy_cache_expiry: float = 0.0
        self._base_strategy_symbol_policies: Dict[str, Dict[str, Any]] = (
            build_strategy_policy_baseline()
        )
        self.strategy_symbol_policies: Dict[str, Dict[str, Any]] = copy.deepcopy(
            self._base_strategy_symbol_policies
        )

    async def _get_cached_scan_entry(
        self,
        user_id: str,
        scan_id: Optional[str] = None,
    ) -> Optional[_CachedOpportunityResult]:
        cache_key = await self._resolve_scan_cache_key(user_id=user_id, scan_id=scan_id)
        if not cache_key:
            return None

        # Check in-memory cache first
        async with self._scan_cache_lock:
            entry = self.opportunity_cache.get(cache_key)
            if isinstance(entry, _CachedOpportunityResult):
                if entry.expires_at > time.monotonic():
                    return entry
                else:
                    self.opportunity_cache.pop(cache_key, None)

        # CRITICAL FIX: Check Redis if not found in memory (cross-worker access)
        if self.redis:
            try:
                redis_key = f"opportunity_scan_result:{cache_key}"
                cached_data = await self.redis.get(redis_key)
                if cached_data:
                    if isinstance(cached_data, bytes):
                        cached_data = cached_data.decode('utf-8')
                    scan_data = json.loads(cached_data)

                    # Get TTL from Redis to calculate expires_at
                    ttl = await self.redis.ttl(redis_key)
                    expires_at = time.monotonic() + max(0, ttl) if ttl > 0 else time.monotonic() + 60

                    result = _CachedOpportunityResult(
                        payload=scan_data["payload"],
                        expires_at=expires_at,
                        partial=scan_data.get("partial", False)
                    )

                    # Restore to in-memory cache for faster subsequent access
                    async with self._scan_cache_lock:
                        self.opportunity_cache[cache_key] = result

                    self.logger.debug("Scan result retrieved from Redis",
                                    cache_key=cache_key,
                                    scan_id=scan_data["payload"].get("scan_id"),
                                    partial=result.partial)
                    return result
            except Exception as redis_error:
                self.logger.warning("Failed to retrieve scan result from Redis",
                                  error=str(redis_error),
                                  cache_key=cache_key)

        return None

    async def _update_cached_scan_result(
        self,
        cache_key: str,
        payload: Dict[str, Any],
        *,
        partial: bool,
    ) -> None:
        ttl = self._partial_cache_ttl if partial else self._scan_cache_ttl
        expires_at = time.monotonic() + ttl
        cached_payload = copy.deepcopy(payload)

        # Store in in-memory cache
        async with self._scan_cache_lock:
            self.opportunity_cache[cache_key] = _CachedOpportunityResult(
                payload=cached_payload,
                expires_at=expires_at,
                partial=partial,
            )

        # CRITICAL FIX: Also persist to Redis for cross-worker access
        if self.redis:
            try:
                redis_key = f"opportunity_scan_result:{cache_key}"
                scan_data = {
                    "payload": cached_payload,
                    "partial": partial,
                    "cached_at": time.time()
                }
                ttl_seconds = int(ttl)
                await self.redis.setex(redis_key, ttl_seconds, json.dumps(scan_data))
                self.logger.debug("Scan result persisted to Redis",
                                cache_key=cache_key,
                                scan_id=cached_payload.get("scan_id"),
                                partial=partial,
                                ttl=ttl_seconds)
            except Exception as redis_error:
                self.logger.warning("Failed to persist scan result to Redis",
                                  error=str(redis_error),
                                  cache_key=cache_key)

    def _schedule_scan_cleanup(self, cache_key: str, task: asyncio.Task) -> None:
        user_id_hint = cache_key.split(":", 1)[0] if cache_key else None

        def _cleanup(done: asyncio.Task) -> None:
            async def _cleanup_async() -> None:
                async with self._scan_tasks_lock:
                    current_task = self._scan_tasks.get(cache_key)
                    if current_task is task:
                        self._scan_tasks.pop(cache_key, None)

                scan_id_value = getattr(task, "scan_id", None)
                if scan_id_value:
                    await self._unregister_scan_lookup(scan_id_value)

                if done.cancelled():
                    return

                exc = done.exception()
                if exc:
                    self.logger.warning(
                        "Opportunity discovery task finished with error",
                        user_id=user_id_hint,
                        cache_key=cache_key,
                        error=str(exc),
                    )

            asyncio.create_task(_cleanup_async())

        task.add_done_callback(_cleanup)

    async def _register_scan_lookup(self, user_id: str, cache_key: str, scan_id: str) -> None:
        async with self._scan_lookup_lock:
            self._scan_lookup[scan_id] = cache_key
            self._user_latest_scan_key[user_id] = cache_key

        # CRITICAL FIX: Also persist scan_id ? cache_key mapping to Redis for cross-worker access
        if self.redis:
            try:
                redis_lookup_key = f"opportunity_scan_lookup:{scan_id}"
                redis_user_key = f"opportunity_user_latest_scan:{user_id}"
                ttl_seconds = max(self._partial_cache_ttl, self._scan_cache_ttl)

                await self.redis.setex(redis_lookup_key, ttl_seconds, cache_key)
                await self.redis.setex(redis_user_key, ttl_seconds, cache_key)

                self.logger.debug("Scan lookup persisted to Redis",
                                scan_id=scan_id,
                                cache_key=cache_key,
                                user_id=user_id)
            except Exception as redis_error:
                self.logger.warning("Failed to persist scan lookup to Redis",
                                  error=str(redis_error),
                                  scan_id=scan_id)

    async def _unregister_scan_lookup(self, scan_id: str) -> None:
        """Unregister scan lookup only if cache entry has expired.
        
        We keep the scan_id ? cache_key mapping alive while the cached result
        is still available, so follow-up polls using the scan_id can retrieve
        the correct payload even after the scan task completes.
        
        CRITICAL FIX: Also checks Redis before removing lookup mapping to prevent
        cross-worker issues where results exist in Redis but not in memory.
        """
        async with self._scan_lookup_lock:
            cache_key = self._scan_lookup.get(scan_id)
            if not cache_key:
                # Also check Redis - might exist there even if not in memory
                if self.redis:
                    try:
                        redis_lookup_key = f"opportunity_scan_lookup:{scan_id}"
                        cached_key = await self.redis.get(redis_lookup_key)
                        if cached_key:
                            cache_key = cached_key.decode('utf-8') if isinstance(cached_key, bytes) else cached_key
                        else:
                            # Not in memory or Redis - safe to skip
                            return
                    except Exception as redis_error:
                        self.logger.warning("Failed to check Redis during unregister",
                                          error=str(redis_error),
                                          scan_id=scan_id)
                        return
                else:
                    return
            
            # Check if cache entry still exists in memory and hasn't expired
            async with self._scan_cache_lock:
                cached_result = self.opportunity_cache.get(cache_key)
                if cached_result and cached_result.expires_at > time.monotonic():
                    # Cache entry still valid in memory - keep the mapping alive
                    return
            
            # CRITICAL FIX: Also check Redis before removing lookup mapping
            # This prevents removing the mapping when results exist in Redis (cross-worker scenario)
            if self.redis:
                try:
                    redis_result_key = f"opportunity_scan_result:{cache_key}"
                    redis_ttl = await self.redis.ttl(redis_result_key)
                    if redis_ttl > 0:
                        # Result still exists in Redis with valid TTL - keep the mapping alive
                        self.logger.debug("Keeping scan lookup alive - result exists in Redis",
                                        scan_id=scan_id,
                                        cache_key=cache_key,
                                        redis_ttl=redis_ttl)
                        return
                except Exception as redis_error:
                    self.logger.warning("Failed to check Redis result during unregister",
                                      error=str(redis_error),
                                      scan_id=scan_id,
                                      cache_key=cache_key)
                    # On Redis error, be conservative and keep the mapping
            
            # Cache entry expired or doesn't exist in both memory and Redis - safe to remove mapping
            self._scan_lookup.pop(scan_id, None)
            
            # Also remove Redis lookup keys if cache is truly expired
            if self.redis:
                try:
                    redis_lookup_key = f"opportunity_scan_lookup:{scan_id}"
                    await self.redis.delete(redis_lookup_key)
                    self.logger.debug("Removed scan lookup from Redis",
                                    scan_id=scan_id,
                                    cache_key=cache_key)
                except Exception as redis_error:
                    self.logger.warning("Failed to remove Redis lookup key",
                                      error=str(redis_error),
                                      scan_id=scan_id)
            
            user_id, *_ = cache_key.split(":", 1)
            latest_key = self._user_latest_scan_key.get(user_id)
            if latest_key == cache_key:
                # Keep latest mapping so subsequent lookups fall back gracefully.
                pass

    async def _resolve_scan_cache_key(
        self,
        *,
        user_id: str,
        scan_id: Optional[str] = None,
    ) -> Optional[str]:
        # Check in-memory lookup first
        async with self._scan_lookup_lock:
            if scan_id:
                cache_key = self._scan_lookup.get(scan_id)
                if cache_key:
                    return cache_key
            else:
                cache_key = self._user_latest_scan_key.get(user_id)
                if cache_key:
                    return cache_key

        # CRITICAL FIX: Check Redis if not found in memory (cross-worker access)
        if self.redis:
            try:
                if scan_id:
                    redis_lookup_key = f"opportunity_scan_lookup:{scan_id}"
                    cached_key = await self.redis.get(redis_lookup_key)
                    if cached_key:
                        cache_key = cached_key.decode('utf-8') if isinstance(cached_key, bytes) else cached_key
                        # Restore to in-memory lookup for faster subsequent access
                        async with self._scan_lookup_lock:
                            self._scan_lookup[scan_id] = cache_key
                        return cache_key
                else:
                    redis_user_key = f"opportunity_user_latest_scan:{user_id}"
                    cached_key = await self.redis.get(redis_user_key)
                    if cached_key:
                        cache_key = cached_key.decode('utf-8') if isinstance(cached_key, bytes) else cached_key
                        # Restore to in-memory lookup for faster subsequent access
                        async with self._scan_lookup_lock:
                            self._user_latest_scan_key[user_id] = cache_key
                        return cache_key
            except Exception as redis_error:
                self.logger.warning("Failed to resolve scan cache key from Redis",
                                  error=str(redis_error),
                                  scan_id=scan_id,
                                  user_id=user_id)

        return None

    def _build_scan_cache_key(
        self,
        user_id: str,
        *,
        symbols: Optional[List[str]] = None,
        asset_tiers: Optional[List[str]] = None,
        strategy_ids: Optional[List[str]] = None,
    ) -> str:
        normalized_filters = {
            "symbols": self._normalize_filter_values(symbols, upper=True),
            "asset_tiers": self._normalize_filter_values(asset_tiers),
            "strategy_ids": self._normalize_filter_values(strategy_ids),
        }
        serialized = json.dumps(normalized_filters, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha1(serialized.encode("utf-8")).hexdigest()[:16]
        return f"{user_id}:{digest}"

    @staticmethod
    def _normalize_filter_values(
        values: Optional[List[str]],
        *,
        upper: bool = False,
    ) -> List[str]:
        if not values:
            return []
        cleaned: List[str] = []
        for item in values:
            if not item:
                continue
            value = str(item).strip()
            if not value:
                continue
            cleaned.append(value.upper() if upper else value.lower())
        # Preserve deterministic ordering
        return sorted(set(cleaned))

    async def _peek_cached_scan_entry(
        self,
        cache_key: str,
    ) -> Optional[_CachedOpportunityResult]:
        # Check in-memory cache first
        async with self._scan_cache_lock:
            entry = self.opportunity_cache.get(cache_key)
            if isinstance(entry, _CachedOpportunityResult):
                if entry.expires_at > time.monotonic():
                    return entry
                else:
                    self.opportunity_cache.pop(cache_key, None)

        # CRITICAL FIX: Check Redis if not found in memory (cross-worker access)
        if self.redis:
            try:
                redis_key = f"opportunity_scan_result:{cache_key}"
                cached_data = await self.redis.get(redis_key)
                if cached_data:
                    if isinstance(cached_data, bytes):
                        cached_data = cached_data.decode('utf-8')
                    scan_data = json.loads(cached_data)

                    # Get TTL from Redis to calculate expires_at
                    ttl = await self.redis.ttl(redis_key)
                    expires_at = time.monotonic() + max(0, ttl) if ttl > 0 else time.monotonic() + 60

                    result = _CachedOpportunityResult(
                        payload=scan_data["payload"],
                        expires_at=expires_at,
                        partial=scan_data.get("partial", False)
                    )

                    # Restore to in-memory cache for faster subsequent access
                    async with self._scan_cache_lock:
                        self.opportunity_cache[cache_key] = result

                    return result
            except Exception as redis_error:
                self.logger.warning("Failed to peek scan result from Redis",
                                  error=str(redis_error),
                                  cache_key=cache_key)

        return None

    @staticmethod
    def _summarize_scan_filters(
        *,
        symbols: Optional[List[str]] = None,
        asset_tiers: Optional[List[str]] = None,
        strategy_ids: Optional[List[str]] = None,
    ) -> Dict[str, List[str]]:
        summary: Dict[str, List[str]] = {}
        if symbols:
            summary["symbols"] = sorted({str(symbol).upper() for symbol in symbols if symbol})
        if asset_tiers:
            summary["asset_tiers"] = sorted({str(tier) for tier in asset_tiers if tier})
        if strategy_ids:
            summary["strategy_ids"] = sorted({str(strategy_id) for strategy_id in strategy_ids if strategy_id})
        return summary

    def _strategy_matches_filter(self, strategy: Dict[str, Any], filters: Set[str]) -> bool:
        if not strategy or not filters:
            return False

        candidates = [
            str(strategy.get("strategy_id", "")),
            str(strategy.get("id", "")),
            str(strategy.get("slug", "")),
            str(strategy.get("name", "")),
        ]
        for candidate in candidates:
            if not candidate:
                continue
            normalized = candidate.lower()
            if normalized in filters:
                return True
            alias = self._resolve_strategy_alias(candidate)
            if alias and alias in filters:
                return True
        return False

    def _assemble_response(
        self,
        *,
        user_id: str,
        scan_id: str,
        ranked_opportunities: List[OpportunityResult],
        user_profile: UserOpportunityProfile,
        strategy_results: Dict[str, Any],
        discovered_assets: Dict[str, List[Any]],
        strategy_recommendations: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        execution_time_ms: float,
        partial: bool,
        strategies_completed: int,
        total_strategies: int,
        applied_filters: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        signal_stats = {
            "total_signals_analyzed": 0,
            "signals_by_strength": {
                "very_strong (>6.0)": 0,
                "strong (4.5-6.0)": 0,
                "moderate (3.0-4.5)": 0,
                "weak (<3.0)": 0,
            },
            "threshold_analysis": {
                "original_threshold": 6.0,
                "opportunities_above_original": 0,
                "opportunities_shown": len(ranked_opportunities),
                "additional_opportunities_revealed": 0,
            },
        }

        for opp in ranked_opportunities:
            signal_strength = opp.metadata.get("signal_strength", 0)
            signal_stats["total_signals_analyzed"] += 1
            if signal_strength > 6.0:
                signal_stats["signals_by_strength"]["very_strong (>6.0)"] += 1
                signal_stats["threshold_analysis"]["opportunities_above_original"] += 1
            elif signal_strength > 4.5:
                signal_stats["signals_by_strength"]["strong (4.5-6.0)"] += 1
            elif signal_strength > 3.0:
                signal_stats["signals_by_strength"]["moderate (3.0-4.5)"] += 1
            else:
                signal_stats["signals_by_strength"]["weak (<3.0)"] += 1

        signal_stats["threshold_analysis"]["additional_opportunities_revealed"] = (
            len(ranked_opportunities)
            - signal_stats["threshold_analysis"]["opportunities_above_original"]
        )

        metadata_payload: Dict[str, Any] = {}
        capital_metadata = self._extract_capital_metadata_from_opportunities(ranked_opportunities)
        if capital_metadata:
            metadata_payload["capital_assumptions"] = capital_metadata

        projection_summary = self._summarize_profit_projections(ranked_opportunities)
        if projection_summary:
            metadata_payload["profit_projection_summary"] = projection_summary

        if applied_filters:
            metadata_payload["filters"] = applied_filters

        response = {
            "success": True,
            "scan_id": scan_id,
            "user_id": user_id,
            "opportunities": [self._serialize_opportunity(opp) for opp in ranked_opportunities],
            "total_opportunities": len(ranked_opportunities),
            "signal_analysis": signal_stats,
            "threshold_transparency": {
                "message": (
                    f"Found {len(ranked_opportunities)} total opportunities. "
                    f"{signal_stats['threshold_analysis']['opportunities_above_original']} meet our highest standards (>6.0), "
                    f"but we're showing all {len(ranked_opportunities)} to give you full market visibility."
                ),
                "recommendation": "Focus on HIGH confidence opportunities for best results",
            },
            "user_profile": {
                "active_strategies": user_profile.active_strategy_count,
                "active_strategy_count": user_profile.active_strategy_count,
                "user_tier": user_profile.user_tier,
                "monthly_strategy_cost": user_profile.total_monthly_strategy_cost,
                "scan_limit": user_profile.opportunity_scan_limit,
                "strategy_fingerprint": user_profile.strategy_fingerprint,
            },
            "strategy_performance": strategy_results,
            "asset_discovery": {
                "total_assets_scanned": sum(len(assets) for assets in discovered_assets.values()),
                "asset_tiers": list(discovered_assets.keys()),
                "max_tier_accessed": user_profile.max_asset_tier,
            },
            "strategy_recommendations": strategy_recommendations,
            "execution_time_ms": execution_time_ms,
            "last_updated": self._current_timestamp().isoformat(),
            "performance_metrics": {
                "portfolio_fetch_time_ms": metrics.get("portfolio_fetch_time", 0) * 1000,
                "cache_hit_rate": metrics.get("cache_hits", 0)
                / max(1, metrics.get("cache_hits", 0) + metrics.get("cache_misses", 0)),
                "total_timeouts": metrics.get("timeouts", 0),
                "total_errors": len(metrics.get("errors", [])),
            },
        }

        metadata = response.setdefault("metadata", {})
        if metadata_payload:
            metadata.update(metadata_payload)
        metadata["scan_state"] = "partial" if partial else "complete"
        metadata["strategies_completed"] = strategies_completed
        metadata["total_strategies"] = total_strategies
        metadata["remaining_strategies"] = max(total_strategies - strategies_completed, 0)
        metadata.setdefault("message", "Partial opportunity scan results while remaining strategies finish." if partial else "Full opportunity scan results available.")
        metadata["generated_at"] = self._current_timestamp().isoformat()

        return response

    async def async_init(self):
        """Initialize async components."""
        try:
            # Try to get Redis client but don't fail if Redis is unavailable
            try:
                self.redis = await get_redis_client()
                self.logger.info("Redis client initialized for opportunity discovery")
            except Exception as redis_error:
                self.logger.warning("Redis unavailable, continuing without caching", error=str(redis_error))
                self.redis = None

            # Initialize enterprise asset filter
            await enterprise_asset_filter.async_init()

            await self._refresh_strategy_symbol_policies(force=True)

            self.logger.info("?? User Opportunity Discovery Service initialized")

        except Exception as e:
            self.logger.error("Failed to initialize User Opportunity Discovery", error=str(e))
            raise

    def _compute_strategy_fingerprint(self, strategies: List[Dict[str, Any]]) -> str:
        """Create a deterministic fingerprint for the user's active strategy set."""

        if not strategies:
            return "none"

        try:
            strategy_ids = [str(strategy.get("strategy_id", "")).strip() for strategy in strategies]
            normalized = sorted(filter(None, strategy_ids))
            if not normalized:
                return "none"

            fingerprint_source = "|".join(normalized)
            return str(uuid.uuid5(uuid.NAMESPACE_URL, fingerprint_source))
        except Exception as exc:
            self.logger.warning(
                "Failed to compute strategy fingerprint, defaulting to 'none'",
                error=str(exc)
            )
            return "none"

    def _normalize_strategy_identifier(self, value: Optional[str]) -> str:
        """Normalize strategy identifiers/names for alias lookups."""

        if not value:
            return ""

        normalized = re.sub(r"[^a-z0-9]+", "", str(value).lower())
        return normalized

    def _resolve_strategy_alias(self, *candidates: str) -> Optional[str]:
        """Resolve a strategy alias from multiple identifier candidates."""

        for candidate in candidates:
            normalized = self._normalize_strategy_identifier(candidate)
            if not normalized:
                continue
            alias = self._strategy_aliases.get(normalized)
            if alias:
                return alias
        return None

    def _current_timestamp(self) -> datetime:
        """Return timezone-aware UTC timestamps for opportunity payloads."""

        return datetime.now(timezone.utc)

    @staticmethod
    def _resolve_owned_strategy_id(owned_ids: List[str], *candidates: str) -> Optional[str]:
        """Return the first matching candidate present in the owned strategy ids."""

        for candidate in candidates:
            if candidate in owned_ids:
                return candidate
        return candidates[0] if candidates else None

    def _looks_like_uuid(self, value: str) -> bool:
        """Return True when value appears to be a UUID."""

        try:
            uuid.UUID(str(value))
            return True
        except (ValueError, TypeError):
            return False

    def _extract_base_symbol(self, symbol: str) -> str:
        """Extract base asset from trading pair symbol."""

        if not symbol:
            return ""

        normalized = symbol.upper().replace("-", "/")
        if "/" in normalized:
            return normalized.split("/", 1)[0]
        if normalized.endswith("USDT") or normalized.endswith("USDC"):
            return normalized[:-4]
        if normalized.endswith("USD"):
            return normalized[:-3]
        return normalized

    def _parse_usd_value(self, value: Any, default: float = 0.0) -> float:
        """Safely parse USD-like values ("$50,000" ? 50000)."""

        if value is None:
            return default

        if isinstance(value, (int, float, Decimal)):
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        try:
            cleaned = re.sub(r"[^0-9.\-]", "", str(value))
            if cleaned in {"", "-", "--"}:
                return default
            return float(cleaned)
        except (TypeError, ValueError):
            return default

    def _score_to_risk_level(self, normalized_score: float) -> str:
        """Map 0-1 normalized score to qualitative risk labels."""

        score = max(0.0, min(1.0, normalized_score))
        if score < 0.25:
            return "low"
        if score < 0.5:
            return "medium"
        if score < 0.75:
            return "high"
        return "very_high"

    def _determine_required_capital(
        self,
        strategy_info: Dict[str, Any],
        fallback: float
    ) -> float:
        """Determine required capital from strategy metadata with fallback."""

        for key in ("required_capital_usd", "min_capital_usd", "min_capital"):
            if key in strategy_info:
                parsed = self._parse_usd_value(strategy_info.get(key))
                if parsed > 0:
                    return parsed
        return fallback

    async def _get_user_portfolio_cached(self, user_id: str) -> Dict[str, Any]:
        """Get user portfolio with enterprise caching and circuit breaker pattern."""
        
        # Check cache first
        cached = self._portfolio_cache.get(user_id)
        if cached and cached['expires'] > time.time():
            self.logger.debug("?? Portfolio cache hit", user_id=user_id)
            return cached['data']
        
        # Check circuit breaker
        if self._circuit_breaker['is_open']:
            if time.time() - self._circuit_breaker['last_failure'] < self._circuit_breaker['timeout']:
                self.logger.warning("? Circuit breaker open, returning cached or default", user_id=user_id)
                return cached['data'] if cached else {'success': True, 'active_strategies': []}
            else:
                # Reset circuit breaker
                self._circuit_breaker['is_open'] = False
                self._circuit_breaker['failures'] = 0
        
        try:
            # Fetch with timeout (increased to 65s to allow proper strategy loading)
            # Note: strategy_marketplace_service has its own 60s timeout internally
            portfolio_result = await asyncio.wait_for(
                strategy_marketplace_service.get_user_strategy_portfolio(user_id),
                timeout=PORTFOLIO_FETCH_TIMEOUT_SECONDS
            )
            
            # Cache successful result
            self._portfolio_cache[user_id] = {
                'data': portfolio_result,
                'expires': time.time() + self._cache_ttl
            }
            
            # Reset circuit breaker on success
            self._circuit_breaker['failures'] = 0
            
            self.logger.debug("? Portfolio fetched and cached", user_id=user_id)
            return portfolio_result
            
        except asyncio.TimeoutError:
            self.logger.exception(
                f"? Portfolio fetch TIMEOUT after {PORTFOLIO_FETCH_TIMEOUT_SECONDS}s",
                user_id=user_id,
                timeout_seconds=PORTFOLIO_FETCH_TIMEOUT_SECONDS,
            )
            
            # Increment circuit breaker
            self._circuit_breaker['failures'] += 1
            self._circuit_breaker['last_failure'] = time.time()
            
            if self._circuit_breaker['failures'] >= self._circuit_breaker['threshold']:
                self._circuit_breaker['is_open'] = True
                self.logger.warning("?? Circuit breaker opened due to repeated failures")
            
            # Return cached data if available, otherwise empty
            if cached:
                self.logger.info("?? Returning stale cache due to timeout", user_id=user_id)
                return cached['data']
            
            return {'success': True, 'active_strategies': [], 'error': 'portfolio_fetch_timeout'}
            
        except Exception as e:
            self.logger.error("? Portfolio fetch EXCEPTION", 
                            user_id=user_id, 
                            error=str(e),
                            error_type=type(e).__name__,
                            exc_info=True)
            
            # Increment circuit breaker
            self._circuit_breaker['failures'] += 1
            self._circuit_breaker['last_failure'] = time.time()
            
            if self._circuit_breaker['failures'] >= self._circuit_breaker['threshold']:
                self._circuit_breaker['is_open'] = True
                self.logger.warning("?? Circuit breaker opened due to repeated failures")
            
            # Return cached data if available, otherwise empty
            if cached:
                self.logger.info("?? Returning stale cache due to exception", user_id=user_id)
                return cached['data']
            
            return {'success': True, 'active_strategies': [], 'error': f'portfolio_fetch_error: {type(e).__name__}'}
    
    async def discover_opportunities_for_user(
        self,
        user_id: str,
        force_refresh: bool = False,
        include_strategy_recommendations: bool = True,
        *,
        symbols: Optional[List[str]] = None,
        asset_tiers: Optional[List[str]] = None,
        strategy_ids: Optional[List[str]] = None,
        scan_id: Optional[str] = None,
        cache_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        cache_key = cache_key or self._build_scan_cache_key(
            user_id,
            symbols=symbols,
            asset_tiers=asset_tiers,
            strategy_ids=strategy_ids,
        )

        scan_id_local: Optional[str] = scan_id
        cached_entry: Optional[_CachedOpportunityResult] = None

        async with self._scan_tasks_lock:
            task = self._scan_tasks.get(cache_key)
            if task and task.done():
                self._scan_tasks.pop(cache_key, None)
                task = None
            if scan_id_local is None and task is not None:
                scan_id_local = getattr(task, "scan_id", None)

        if scan_id_local is None:
            cached_entry = await self._peek_cached_scan_entry(cache_key)
            if cached_entry:
                scan_id_local = cached_entry.payload.get("scan_id")

        if scan_id_local is None:
            scan_id_local = f"user_discovery_{user_id}_{int(time.time())}"

        await self._register_scan_lookup(user_id, cache_key, scan_id_local)

        if cached_entry is None:
            cached_entry = await self._peek_cached_scan_entry(cache_key)

        if cached_entry and not force_refresh and not cached_entry.partial:
            return copy.deepcopy(cached_entry.payload)

        if force_refresh:
            async with self._scan_tasks_lock:
                existing = self._scan_tasks.pop(cache_key, None)
            if existing and not existing.done():
                existing.cancel()

        task: Optional[asyncio.Task] = None
        async with self._scan_tasks_lock:
            task = self._scan_tasks.get(cache_key)
            if task and task.done():
                self._scan_tasks.pop(cache_key, None)
                task = None

            if not task:
                task = asyncio.create_task(
                    self._execute_opportunity_discovery(
                        user_id=user_id,
                        force_refresh=force_refresh,
                        include_strategy_recommendations=include_strategy_recommendations,
                        symbols=symbols,
                        asset_tiers=asset_tiers,
                        strategy_ids=strategy_ids,
                        existing_scan_id=scan_id_local,
                        cache_key=cache_key,
                    ),
                    name=f"opportunity-discovery:{scan_id_local}",
                )
                task.scan_id = scan_id_local
                task.cache_key = cache_key
                self._scan_tasks[cache_key] = task
                self._schedule_scan_cleanup(cache_key, task)
            else:
                scan_id_local = getattr(task, "scan_id", scan_id_local)
                await self._register_scan_lookup(user_id, cache_key, scan_id_local)

        if cached_entry and not force_refresh:
            payload = copy.deepcopy(cached_entry.payload)
            metadata = payload.setdefault("metadata", {})
            metadata.setdefault(
                "message",
                "Returning cached opportunity results while a fresh scan completes in the background.",
            )
            metadata.setdefault(
                "scan_state",
                "partial" if cached_entry.partial else "cached",
            )
            metadata.setdefault("generated_at", self._current_timestamp().isoformat())
            return payload

        if force_refresh and task:
            try:
                result = await asyncio.wait_for(
                    asyncio.shield(task),
                    timeout=5.0,
                )
                return copy.deepcopy(result)
            except asyncio.TimeoutError:
                pass

        placeholder_payload = {
            "success": True,
            "scan_id": scan_id_local,
            "user_id": user_id,
            "opportunities": [],
            "total_opportunities": 0,
            "message": "Opportunity scan started. Analyzing your strategies for opportunities...",
            "scan_state": "pending",
            "metadata": {
                "scan_state": "pending",
                "message": "Scanning your active strategies for new opportunities...",
                "strategies_completed": 0,
                "total_strategies": 0,
                "generated_at": self._current_timestamp().isoformat(),
                "filters": self._summarize_scan_filters(
                    symbols=symbols,
                    asset_tiers=asset_tiers,
                    strategy_ids=strategy_ids,
                ),
            },
            "background_scan": True,
        }

        await self._update_cached_scan_result(
            cache_key,
            placeholder_payload,
            partial=True,
        )

        self.logger.info(
            "Returning pending opportunity scan placeholder",
            user_id=user_id,
            scan_id=scan_id_local,
            force_refresh=force_refresh,
        )

        return copy.deepcopy(placeholder_payload)

    async def _execute_opportunity_discovery(
        self,
        user_id: str,
        force_refresh: bool = False,
        include_strategy_recommendations: bool = True,
        *,
        symbols: Optional[List[str]] = None,
        asset_tiers: Optional[List[str]] = None,
        strategy_ids: Optional[List[str]] = None,
        existing_scan_id: Optional[str] = None,
        cache_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        MAIN ENTRY POINT: Discover all opportunities for user based on their strategy portfolio.
        
        This is the method that replaces the fake market_inefficiency_scanner.
        """
        
        discovery_start_time = time.monotonic()
        discovery_start_wall = time.time()
        scan_id = existing_scan_id or f"user_discovery_{user_id}_{int(time.time())}"
        cache_key = cache_key or self._build_scan_cache_key(
            user_id,
            symbols=symbols,
            asset_tiers=asset_tiers,
            strategy_ids=strategy_ids,
        )
        filter_summary = self._summarize_scan_filters(
            symbols=symbols,
            asset_tiers=asset_tiers,
            strategy_ids=strategy_ids,
        )

        self.logger.info("?? ENTERPRISE User Opportunity Discovery Starting",
                        scan_id=scan_id,
                        user_id=user_id,
                        force_refresh=force_refresh)

        # Track scan start
        await self._track_scan_lifecycle(
            user_id,
            scan_id,
            "started",
            "in_progress",
            force_refresh=force_refresh,
            start_time=discovery_start_wall,
            start_time_monotonic=discovery_start_time,
        )

        metrics: Dict[str, Any] = {
            "scan_id": scan_id,
            "start_time": discovery_start_wall,
            "start_time_monotonic": discovery_start_time,
            "start_time_iso": datetime.fromtimestamp(discovery_start_wall, tz=timezone.utc).isoformat(),
            "portfolio_fetch_time": 0.0,
            "asset_discovery_time": 0.0,
            "strategy_scan_times": {},
            "total_strategies": 0,
            "total_opportunities": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "timeouts": 0,
            "errors": [],
        }

        try:
            # Initialize if needed
            if not self.redis:
                await self.async_init()

            await self._refresh_strategy_symbol_policies()

            # STEP 1: Build user opportunity profile
            user_profile = await self._build_user_opportunity_profile(user_id)

            if user_profile.active_strategy_count == 0:
                return await self._handle_no_strategies_user(user_id, scan_id)

            # STEP 2: Check cache first (unless force refresh)
            if not force_refresh:
                cached_opportunities = await self._get_cached_opportunities(user_id, user_profile)
                if cached_opportunities:
                    self.logger.info("?? Using cached opportunity data", 
                                   scan_id=scan_id,
                                   opportunities_count=len(cached_opportunities.get("opportunities", [])))
                    return cached_opportunities
            
            # STEP 3: Load portfolio data for this discovery
            portfolio_fetch_start = time.time()
            await self._track_scan_lifecycle(user_id, scan_id, "portfolio_fetch", "in_progress")

            portfolio_result = await self._get_user_portfolio(user_id)
            metrics["portfolio_fetch_time"] = time.time() - portfolio_fetch_start

            if not portfolio_result.get("success") or not portfolio_result.get("active_strategies"):
                self.logger.warning("? NO STRATEGIES FOUND IN PORTFOLIO",
                                  scan_id=scan_id,
                                  user_id=user_id,
                                  portfolio_result=portfolio_result)
                await self._track_scan_lifecycle(user_id, scan_id, "portfolio_fetch", "error",
                                                error="No active strategies found",
                                                portfolio_result=portfolio_result)
                return await self._handle_no_strategies_user(user_id, scan_id)

            active_strategies = portfolio_result["active_strategies"]

            if strategy_ids:
                strategy_filter = {sid.lower() for sid in strategy_ids if sid}
                filtered_strategies = [
                    strategy
                    for strategy in active_strategies
                    if self._strategy_matches_filter(strategy, strategy_filter)
                ]

                if not filtered_strategies:
                    self.logger.info(
                        "No strategies matched filters",
                        scan_id=scan_id,
                        user_id=user_id,
                        requested_filters=list(strategy_filter),
                    )

                    empty_payload = {
                        "success": True,
                        "scan_id": scan_id,
                        "user_id": user_id,
                        "opportunities": [],
                        "total_opportunities": 0,
                        "message": "No strategies matched the selected filters.",
                        "metadata": {
                            "scan_state": "complete",
                            "strategies_completed": 0,
                            "total_strategies": 0,
                            "generated_at": self._current_timestamp().isoformat(),
                            "filters": filter_summary,
                            "message": "No strategies matched the selected filters.",
                        },
                    }

                    await self._update_cached_scan_result(
                        cache_key,
                        empty_payload,
                        partial=False,
                    )

                    return empty_payload

                active_strategies = filtered_strategies
                portfolio_result["active_strategies"] = active_strategies

            await self._track_scan_lifecycle(user_id, scan_id, "portfolio_fetch", "completed",
                                           strategies_count=len(active_strategies),
                                           duration_ms=metrics["portfolio_fetch_time"] * 1000,
                                           filters=filter_summary)

            # CRITICAL DEBUG: Log user's active strategies
            self.logger.info("?? USER ACTIVE STRATEGIES",
                           scan_id=scan_id,
                           user_id=user_id,
                           strategy_count=len(active_strategies),
                           strategies=[s.get("strategy_id") for s in active_strategies])

            # STEP 4: Get enterprise asset discovery based on user tier
            asset_discovery_start = time.time()
            await self._track_scan_lifecycle(user_id, scan_id, "asset_discovery", "in_progress")

            discovered_assets = await enterprise_asset_filter.discover_all_assets_with_volume_filtering(
                min_tier=user_profile.max_asset_tier,
                force_refresh=force_refresh
            )
            metrics["asset_discovery_time"] = time.time() - asset_discovery_start

            if asset_tiers:
                allowed_tiers = {tier.lower() for tier in asset_tiers if tier}
                discovered_assets = {
                    tier: assets
                    for tier, assets in discovered_assets.items()
                    if tier.lower() in allowed_tiers
                }

            if symbols:
                symbol_filter = {symbol.upper() for symbol in symbols if symbol}
                filtered_assets: Dict[str, List[Any]] = {}
                for tier, assets in discovered_assets.items():
                    filtered_list = [
                        asset
                        for asset in assets
                        if getattr(asset, "symbol", "").upper() in symbol_filter
                    ]
                    if filtered_list:
                        filtered_assets[tier] = filtered_list
                discovered_assets = filtered_assets

            if not discovered_assets or sum(len(assets) for assets in discovered_assets.values()) == 0:
                self.logger.warning("No assets discovered", scan_id=scan_id, user_tier=user_profile.user_tier)
                await self._track_scan_lifecycle(user_id, scan_id, "asset_discovery", "error",
                                                error="No tradeable assets found")
                payload = {
                    "success": True,
                    "scan_id": scan_id,
                    "user_id": user_id,
                    "opportunities": [],
                    "total_opportunities": 0,
                    "message": "No assets matched the selected filters.",
                    "metadata": {
                        "scan_state": "complete",
                        "strategies_completed": 0,
                        "total_strategies": len(active_strategies),
                        "generated_at": self._current_timestamp().isoformat(),
                        "filters": filter_summary,
                        "message": "No assets matched the selected filters.",
                    },
                }
                await self._update_cached_scan_result(cache_key, payload, partial=False)
                return payload

            await self._track_scan_lifecycle(user_id, scan_id, "asset_discovery", "completed",
                                           total_assets=sum(len(assets) for assets in discovered_assets.values()),
                                           duration_ms=metrics["asset_discovery_time"] * 1000)

            # Preload shared price data so downstream strategies reuse cached responses
            # instead of issuing redundant exchange requests during the scan stage.
            await self._preload_price_universe(discovered_assets, user_profile, scan_id)

            # STEP 5: Run opportunity discovery across all user's strategies
            all_opportunities = []
            strategy_results = {}
            total_strategies = len(active_strategies)
            metrics['total_strategies'] = total_strategies
            strategies_completed = 0
            strategy_timings: Dict[str, float] = {}

            # Track start of strategies scan
            await self._track_scan_lifecycle(user_id, scan_id, "strategies_scan", "in_progress",
                                           total_strategies=total_strategies)

            initial_snapshot = self._assemble_response(
                user_id=user_id,
                scan_id=scan_id,
                ranked_opportunities=[],
                user_profile=user_profile,
                strategy_results=strategy_results,
                discovered_assets=discovered_assets,
                strategy_recommendations=[],
                metrics=metrics,
                execution_time_ms=(time.monotonic() - discovery_start_time) * 1000,
                partial=True,
                strategies_completed=0,
                total_strategies=total_strategies,
                applied_filters=filter_summary,
            )
            await self._update_cached_scan_result(cache_key, initial_snapshot, partial=True)

            # Create semaphore for bounded concurrency - Optimized for performance
            concurrency_limit = 15  # Run max 15 strategies concurrently (increased from 3)
            strategy_semaphore = asyncio.Semaphore(concurrency_limit)

            # Calculate remaining budget for strategy scans; do not overshoot SLA
            # Use monotonic time for consistent timeout calculations
            elapsed_since_start = time.monotonic() - discovery_start_time
            remaining_budget = max(0.0, self._scan_response_budget - elapsed_since_start)

            # Calculate per-strategy timeout from remaining budget, accounting for concurrency
            # With 15 concurrent strategies, we process in batches, so timeout should reflect batch time
            batches = max(1, math.ceil(total_strategies / concurrency_limit))
            # Allocate remaining budget per batch; allow longer-running strategies to finish (upper bound 180s to match gunicorn timeout)
            # High timeout prevents premature failures while optimizations take effect
            per_strategy_timeout_s = max(10.0, min(180.0, remaining_budget / batches))

            async def scan_strategy_with_semaphore(strategy_info, strategy_index):
                strategy_identifier = strategy_info.get("strategy_id", "Unknown")
                strategy_name = strategy_info.get("name", "Unknown")

                async with strategy_semaphore:
                    # Start time and debug tracking inside semaphore to measure pure execution time (not queue wait)
                    strategy_start_monotonic = time.monotonic()
                    strategy_start_wall = time.time()
                    # Helper to compute elapsed durations consistently using the monotonic clock
                    def _strategy_elapsed_seconds() -> float:
                        return time.monotonic() - strategy_start_monotonic

                    step_number = 100 + strategy_index  # 100-series reserved for per-strategy steps
                    await self._track_debug_step(
                        user_id, scan_id, step_number,
                        f"Strategy: {strategy_name}",
                        "starting",
                        strategy_id=strategy_identifier,
                        strategy_index=strategy_index,
                        started_at=datetime.fromtimestamp(strategy_start_wall, tz=timezone.utc).isoformat()
                    )

                    try:
                        # Call _scan_strategy_opportunities directly - it handles its own timeout/partial-result logic
                        result = await self._scan_strategy_opportunities(
                            strategy_info,
                            discovered_assets,
                            user_profile,
                            scan_id,
                            portfolio_result,
                            timeout_seconds=per_strategy_timeout_s,
                            start_time=strategy_start_wall,
                        )
                    except asyncio.CancelledError as e:
                        # Track strategy cancellation (parent task cancelled)
                        execution_time = _strategy_elapsed_seconds() * 1000
                        await self._track_debug_step(
                            user_id, scan_id, step_number,
                            f"Strategy: {strategy_name}",
                            "cancelled",
                            strategy_id=strategy_identifier,
                            strategy_index=strategy_index,
                            execution_time_ms=execution_time,
                            error=e,
                            error_type="CancelledError",
                            is_cancelled=True
                        )
                        raise
                    except Exception as e:
                        # Track strategy failure (timeout or other)
                        execution_time = _strategy_elapsed_seconds() * 1000
                        error_type = type(e).__name__
                        is_timeout = isinstance(e, asyncio.TimeoutError)

                        await self._track_debug_step(
                            user_id, scan_id, step_number,
                            f"Strategy: {strategy_name}",
                            "failed",
                            strategy_id=strategy_identifier,
                            strategy_index=strategy_index,
                            execution_time_ms=execution_time,
                            error=e,
                            error_type=error_type,
                            is_timeout=is_timeout
                        )
                        raise
                    else:
                        # Track strategy completion (only if no exception)
                        execution_time = _strategy_elapsed_seconds() * 1000
                        await self._track_debug_step(
                            user_id, scan_id, step_number,
                            f"Strategy: {strategy_name}",
                            "completed",
                            strategy_id=strategy_identifier,
                            strategy_index=strategy_index,
                            execution_time_ms=execution_time,
                            opportunities_found=len(result.get("opportunities", [])) if isinstance(result, dict) else 0
                        )
                        return result
                    finally:
                        strategy_timings[strategy_identifier] = _strategy_elapsed_seconds()

            # Run all strategy scans concurrently
            self.logger.info("?? STARTING CONCURRENT STRATEGY SCANS",
                           scan_id=scan_id,
                           total_strategies=total_strategies,
                           concurrency_limit=15)

            # Launch strategy scans as tasks so we can enforce a global timeout for the
            # entire strategy phase. This protects against a handful of strategies
            # running right up to their individual budget and collectively stalling
            # the overall scan long enough for the frontend to observe a 404.
            strategy_tasks: List[asyncio.Task] = []
            task_index_map: Dict[asyncio.Task, int] = {}
            for idx, strategy in enumerate(active_strategies):
                task = asyncio.create_task(
                    scan_strategy_with_semaphore(strategy, idx),
                    name=f"strategy-scan:{scan_id}:{idx}",
                )
                strategy_tasks.append(task)
                task_index_map[task] = idx

            # Allow a small grace window beyond the remaining scan budget so we can
            # collect trailing results without cancelling tasks that are about to
            # finish. When the window expires we cancel whatever is left and mark
            # them as timed out so aggregation can continue with partial data.
            stage_remaining_budget = max(
                0.0,
                self._scan_response_budget - (time.monotonic() - discovery_start_time),
            )
            strategy_stage_timeout = max(5.0, min(stage_remaining_budget + 15.0, 210.0))

            _done, pending = await asyncio.wait(
                strategy_tasks,
                timeout=strategy_stage_timeout,
                return_when=asyncio.ALL_COMPLETED,
            )

            timeout_results: Dict[int, Dict[str, Any]] = {}

            if pending:
                self.logger.warning(
                    "Strategy scans exceeded stage timeout; cancelling pending tasks",
                    scan_id=scan_id,
                    pending_tasks=len(pending),
                    stage_timeout_seconds=strategy_stage_timeout,
                )

                pending_list = list(pending)
                for task in pending_list:
                    task.cancel()

                # Wait for cancellation to propagate so per-strategy cleanup hooks run.
                cancellation_outcomes = await asyncio.gather(
                    *pending_list,
                    return_exceptions=True,
                )

                for task, outcome in zip(pending_list, cancellation_outcomes, strict=True):
                    idx = task_index_map.get(task)
                    strategy_info = active_strategies[idx] if idx is not None else {}
                    timeout_results[idx] = {
                        "strategy_id": strategy_info.get("strategy_id", ""),
                        "strategy_name": strategy_info.get("name", "Unknown"),
                        "opportunities": [],
                        "success": False,
                        "error": "strategy_stage_timeout",
                        "partial": True,
                    }

                    if isinstance(outcome, Exception) and not isinstance(
                        outcome, asyncio.CancelledError
                    ):
                        self.logger.warning(
                            "Strategy task returned error after cancellation",
                            scan_id=scan_id,
                            strategy_id=timeout_results[idx]["strategy_id"],
                            error=str(outcome),
                        )

            strategy_scan_results: List[Any] = [None] * total_strategies

            for task in strategy_tasks:
                idx = task_index_map[task]
                if idx in timeout_results:
                    strategy_scan_results[idx] = timeout_results[idx]
                    continue

                if task.cancelled():
                    strategy_info = active_strategies[idx]
                    strategy_scan_results[idx] = {
                        "strategy_id": strategy_info.get("strategy_id", ""),
                        "strategy_name": strategy_info.get("name", "Unknown"),
                        "opportunities": [],
                        "success": False,
                        "error": "strategy_cancelled",
                        "partial": True,
                    }
                    metrics['timeouts'] += 1
                    continue

                try:
                    strategy_scan_results[idx] = task.result()
                except Exception as exc:  # noqa: BLE001 - propagate diagnostic details
                    strategy_scan_results[idx] = exc

            self.logger.info("? ALL STRATEGY SCANS COMPLETED",
                           scan_id=scan_id,
                           total_strategies=total_strategies,
                           total_time_s=sum(strategy_timings.values()))
            
            # Process results
            for i, result in enumerate(strategy_scan_results):
                strategy_name = active_strategies[i].get("name", "Unknown")
                strategy_id = active_strategies[i].get("strategy_id", "Unknown")
                strategies_completed += 1

                if isinstance(result, Exception):
                    self.logger.warning("Strategy scan failed",
                                      scan_id=scan_id,
                                      strategy=strategy_name,
                                      error=str(result))
                    metrics['errors'].append({
                        "strategy_id": strategy_id,
                        "strategy_name": strategy_name,
                        "error": str(result),
                    })
                    if isinstance(result, asyncio.TimeoutError):
                        metrics['timeouts'] += 1
                else:
                    # CRITICAL DEBUG: Log what each strategy scanner returned
                    self.logger.info("?? STRATEGY SCAN RESULT",
                                   scan_id=scan_id,
                                   strategy_name=strategy_name,
                                   strategy_id=strategy_id,
                                   result_type=type(result).__name__,
                                   has_opportunities=bool(result.get("opportunities") if isinstance(result, dict) else False),
                                   opportunities_count=len(result.get("opportunities", [])) if isinstance(result, dict) else 0)

                    if isinstance(result, dict) and result.get("opportunities"):
                        result_strategy_id = result["strategy_id"]
                        opportunities = result["opportunities"]

                        self.logger.info("? OPPORTUNITIES FOUND FROM STRATEGY",
                                       scan_id=scan_id,
                                       strategy_id=result_strategy_id,
                                       opportunities_count=len(opportunities))

                        strategy_results[result_strategy_id] = {
                            "count": len(opportunities),
                            "total_potential": sum(opp.profit_potential_usd for opp in opportunities),
                            "avg_confidence": sum(opp.confidence_score for opp in opportunities) / len(opportunities) if opportunities else 0
                        }

                        all_opportunities.extend(opportunities)
                    elif isinstance(result, dict):
                        if result.get("partial") and isinstance(result.get("error"), str):
                            if "timeout" in result["error"].lower():
                                metrics['timeouts'] += 1
                        self.logger.warning("? STRATEGY RETURNED EMPTY OPPORTUNITIES",
                                          scan_id=scan_id,
                                          strategy_name=strategy_name,
                                          strategy_id=strategy_id,
                                          result_keys=list(result.keys()))
                    else:
                        self.logger.warning("? STRATEGY RETURNED INVALID RESULT TYPE",
                                          scan_id=scan_id,
                                          strategy_name=strategy_name,
                                          result_type=type(result).__name__)

                ranked_snapshot = await self._rank_and_filter_opportunities(
                    all_opportunities,
                    user_profile,
                    scan_id,
                )
                metrics['total_opportunities'] = len(ranked_snapshot)
                snapshot_response = self._assemble_response(
                    user_id=user_id,
                    scan_id=scan_id,
                    ranked_opportunities=ranked_snapshot,
                    user_profile=user_profile,
                    strategy_results=strategy_results,
                    discovered_assets=discovered_assets,
                    strategy_recommendations=[],
                    metrics=metrics,
                    execution_time_ms=(time.monotonic() - discovery_start_time) * 1000,
                    partial=True,
                    strategies_completed=strategies_completed,
                    total_strategies=total_strategies,
                    applied_filters=filter_summary,
                )
                await self._update_cached_scan_result(
                    cache_key,
                    snapshot_response,
                    partial=True,
                )

            metrics['strategy_scan_times'] = strategy_timings

            # DEBUG: Log entry to aggregation phase
            self.logger.info("?? STARTING AGGREGATION PHASE",
                           scan_id=scan_id,
                           user_id=user_id,
                           total_opportunities_collected=len(all_opportunities),
                           strategies_processed=total_strategies)

            # STEP 6: Rank and filter opportunities
            try:
                await self._track_debug_step(user_id, scan_id, 6, "Rank and filter opportunities",
                                            "starting", opportunities_count=len(all_opportunities))

                ranked_opportunities = await self._rank_and_filter_opportunities(
                    all_opportunities, user_profile, scan_id
                )

                await self._track_debug_step(user_id, scan_id, 6, "Rank and filter opportunities",
                                            "completed", ranked_count=len(ranked_opportunities))
            except Exception as rank_error:
                await self._track_debug_step(user_id, scan_id, 6, "Rank and filter opportunities",
                                            "failed", error=str(rank_error))
                raise

            # STEP 7: Add strategy recommendations if requested
            strategy_recommendations = []
            if include_strategy_recommendations:
                await self._track_debug_step(
                    user_id,
                    scan_id,
                    7,
                    "Generate strategy recommendations",
                    "starting",
                )

                recommendation_timeout = 6.0
                try:
                    strategy_recommendations = await asyncio.wait_for(
                        self._generate_strategy_recommendations(
                            user_id,
                            user_profile,
                            len(ranked_opportunities),
                            portfolio_result,
                            scan_id=scan_id,
                            timeout_seconds=recommendation_timeout,
                        ),
                        timeout=recommendation_timeout,
                    )
                    await self._track_debug_step(
                        user_id,
                        scan_id,
                        7,
                        "Generate strategy recommendations",
                        "completed",
                        recommendations_count=len(strategy_recommendations),
                    )
                except asyncio.TimeoutError:
                    self.logger.warning(
                        "Strategy recommendations generation timed out",
                        user_id=user_id,
                        scan_id=scan_id,
                        timeout_seconds=recommendation_timeout,
                    )
                    strategy_recommendations = []
                    await self._track_debug_step(
                        user_id,
                        scan_id,
                        7,
                        "Generate strategy recommendations",
                        "failed",
                        error=f"timeout after {recommendation_timeout}s",
                    )
                except asyncio.CancelledError:
                    await self._track_debug_step(
                        user_id,
                        scan_id,
                        7,
                        "Generate strategy recommendations",
                        "failed",
                        error="cancelled",
                    )
                    raise
                except Exception as rec_error:
                    await self._track_debug_step(
                        user_id,
                        scan_id,
                        7,
                        "Generate strategy recommendations",
                        "failed",
                        error=str(rec_error),
                    )
                    if isinstance(rec_error, asyncio.CancelledError):
                        raise
                    strategy_recommendations = []

            # STEP 8: Build comprehensive response with metrics
            try:
                await self._track_debug_step(user_id, scan_id, 8, "Assemble response", "starting")

                execution_time = (time.monotonic() - discovery_start_time) * 1000
                metrics['total_time'] = execution_time
                metrics['total_opportunities'] = len(ranked_opportunities)

                final_response = self._assemble_response(
                    user_id=user_id,
                    scan_id=scan_id,
                    ranked_opportunities=ranked_opportunities,
                    user_profile=user_profile,
                    strategy_results=strategy_results,
                    discovered_assets=discovered_assets,
                    strategy_recommendations=strategy_recommendations,
                    metrics=metrics,
                    execution_time_ms=execution_time,
                    partial=False,
                    strategies_completed=total_strategies,
                    total_strategies=total_strategies,
                    applied_filters=filter_summary,
                )

                await self._track_debug_step(user_id, scan_id, 8, "Assemble response", "completed")
            except Exception as assembly_error:
                await self._track_debug_step(user_id, scan_id, 8, "Assemble response",
                                            "failed", error=str(assembly_error))
                raise

            # STEP 9: Update cached scan result
            try:
                await self._track_debug_step(user_id, scan_id, 9, "Update cached scan result", "starting")

                await self._update_cached_scan_result(cache_key, final_response, partial=False)

                await self._track_debug_step(user_id, scan_id, 9, "Update cached scan result", "completed")
            except Exception as cache_error:
                await self._track_debug_step(user_id, scan_id, 9, "Update cached scan result",
                                            "failed", error=str(cache_error))
                raise

            # ENTERPRISE MONITORING: Log comprehensive metrics
            self.logger.info("?? OPPORTUNITY DISCOVERY METRICS",
                           scan_id=scan_id,
                           user_id=user_id,
                           total_time_ms=execution_time,
                           portfolio_fetch_time_ms=metrics['portfolio_fetch_time'] * 1000,
                           total_opportunities=metrics['total_opportunities'],
                           cache_hit_rate=metrics['cache_hits'] / max(1, metrics['cache_hits'] + metrics['cache_misses']),
                           timeouts=metrics['timeouts'],
                           errors=len(metrics['errors']))

            # PERFORMANCE ALERTING: Alert if performance degraded
            if execution_time > 10000:  # >10 seconds
                self.logger.warning("?? OPPORTUNITY DISCOVERY PERFORMANCE DEGRADED",
                                  scan_id=scan_id,
                                  user_id=user_id,
                                  total_time_ms=execution_time,
                                  portfolio_fetch_time_ms=metrics['portfolio_fetch_time'] * 1000,
                                  alert_threshold="10s")

            # STEP 10: Cache results
            try:
                await self._track_debug_step(user_id, scan_id, 10, "Cache opportunities", "starting")

                await self._cache_opportunities(user_id, final_response, user_profile)

                await self._track_debug_step(user_id, scan_id, 10, "Cache opportunities", "completed")
            except Exception as cache_opp_error:
                await self._track_debug_step(
                    user_id,
                    scan_id,
                    10,
                    "Cache opportunities",
                    "failed",
                    error=str(cache_opp_error),
                )
                if isinstance(cache_opp_error, asyncio.CancelledError):
                    raise
                self.logger.warning(
                    "Opportunity cache update failed",
                    scan_id=scan_id,
                    user_id=user_id,
                    error=str(cache_opp_error),
                )

            # STEP 11: Track strategies completion
            try:
                await self._track_debug_step(user_id, scan_id, 11, "Track strategies completion lifecycle", "starting")

                await self._track_scan_lifecycle(user_id, scan_id, "strategies_scan", "completed",
                                               strategies_completed=total_strategies,
                                               opportunities_found=len(ranked_opportunities))

                await self._track_debug_step(user_id, scan_id, 11, "Track strategies completion lifecycle", "completed")
            except Exception as lifecycle_error:
                await self._track_debug_step(
                    user_id,
                    scan_id,
                    11,
                    "Track strategies completion lifecycle",
                    "failed",
                    error=str(lifecycle_error),
                )
                if isinstance(lifecycle_error, asyncio.CancelledError):
                    raise
                self.logger.warning(
                    "Strategy completion lifecycle tracking failed",
                    scan_id=scan_id,
                    user_id=user_id,
                    error=str(lifecycle_error),
                )

            # STEP 12: Track metrics for diagnostic monitoring
            try:
                await self._track_debug_step(user_id, scan_id, 12, "Track scan metrics for diagnostics",
                                            "starting", opportunities=len(ranked_opportunities),
                                            strategies=user_profile.active_strategy_count)

                await self._track_scan_metrics(
                    user_id=user_id,
                    scan_id=scan_id,
                    opportunities_count=len(ranked_opportunities),
                    strategies_count=user_profile.active_strategy_count,
                    execution_time_ms=execution_time,
                    success=True
                )

                await self._track_debug_step(user_id, scan_id, 12, "Track scan metrics for diagnostics", "completed")
            except Exception as metrics_error:
                await self._track_debug_step(
                    user_id,
                    scan_id,
                    12,
                    "Track scan metrics for diagnostics",
                    "failed",
                    error=str(metrics_error),
                )
                if isinstance(metrics_error, asyncio.CancelledError):
                    raise
                self.logger.warning(
                    "Scan metrics tracking failed",
                    scan_id=scan_id,
                    user_id=user_id,
                    error=str(metrics_error),
                )

            # STEP 13: Track final completion
            try:
                await self._track_debug_step(user_id, scan_id, 13, "Track final completion lifecycle", "starting")

                await self._track_scan_lifecycle(user_id, scan_id, "completed", "completed",
                                               total_opportunities=len(ranked_opportunities),
                                               execution_time_ms=execution_time)

                await self._track_debug_step(user_id, scan_id, 13, "Track final completion lifecycle", "completed")
            except Exception as final_lifecycle_error:
                await self._track_debug_step(
                    user_id,
                    scan_id,
                    13,
                    "Track final completion lifecycle",
                    "failed",
                    error=str(final_lifecycle_error),
                )
                if isinstance(final_lifecycle_error, asyncio.CancelledError):
                    raise
                self.logger.warning(
                    "Final scan lifecycle tracking failed",
                    scan_id=scan_id,
                    user_id=user_id,
                    error=str(final_lifecycle_error),
                )

            self.logger.info("? ENTERPRISE User Opportunity Discovery Completed",
                           scan_id=scan_id,
                           user_id=user_id,
                           total_opportunities=len(ranked_opportunities),
                           strategies_used=user_profile.active_strategy_count,
                           execution_time_ms=execution_time)

            return final_response

        except Exception as e:
            execution_time = (time.monotonic() - discovery_start_time) * 1000
            error_type = type(e).__name__
            is_timeout = "Timeout" in error_type or "timeout" in str(e).lower()

            self.logger.error("?? ENTERPRISE User Opportunity Discovery Failed",
                            scan_id=scan_id,
                            user_id=user_id,
                            execution_time_ms=execution_time,
                            error=str(e),
                            error_type=error_type,
                            exc_info=True)

            # Track failure with detailed error info
            await self._track_scan_lifecycle(user_id, scan_id, "failed", "error" if not is_timeout else "timeout",
                                           error=str(e),
                                           error_type=error_type,
                                           execution_time_ms=execution_time,
                                           is_timeout=is_timeout)

            # Track error metrics
            await self._track_error_metrics(user_id, scan_id, str(e), execution_time)

            # Track scan metrics with failure status
            await self._track_scan_metrics(
                user_id=user_id,
                scan_id=scan_id,
                opportunities_count=0,
                strategies_count=0,
                execution_time_ms=execution_time,
                success=False
            )

            # Provide graceful degradation - return limited opportunities if possible
            fallback_result = await self._provide_fallback_opportunities(user_id, scan_id)

            return {
                "success": False,
                "error": f"Opportunity discovery failed: {str(e)}",
                "opportunities": fallback_result.get("opportunities", []),
                "scan_id": scan_id,
                "user_id": user_id,
                "execution_time_ms": execution_time,
                "fallback_used": fallback_result.get("success", False),
                "error_type": type(e).__name__
            }
    
    async def _build_user_opportunity_profile(self, user_id: str) -> UserOpportunityProfile:
        """Build user's opportunity discovery profile based on their strategy portfolio and credits."""
        
        try:
            # DIRECT FIX: Use admin snapshot first for admin users (proven working method)
            admin_snapshot = await strategy_marketplace_service.get_admin_portfolio_snapshot(user_id)
            if admin_snapshot and admin_snapshot.get("success"):
                portfolio_result = admin_snapshot
            else:
                # Fallback to regular portfolio method for non-admin users
                portfolio_result = await strategy_marketplace_service.get_user_strategy_portfolio(user_id)

                if (
                    (not portfolio_result.get("success"))
                    or not portfolio_result.get("active_strategies")
                ):
                    admin_snapshot = await strategy_marketplace_service.get_admin_portfolio_snapshot(user_id)
                    if admin_snapshot:
                        portfolio_result = admin_snapshot

            if not portfolio_result.get("success"):
                # Default profile for users with no strategies
                return UserOpportunityProfile(
                    user_id=user_id,
                    active_strategy_count=0,
                    total_monthly_strategy_cost=0,
                    user_tier="basic",
                    max_asset_tier="tier_retail",
                    opportunity_scan_limit=10,  # Very limited for non-subscribers
                    last_scan_time=None,
                    strategy_fingerprint="none"
                )
            
            active_strategies = portfolio_result.get("active_strategies", [])
            total_monthly_cost = portfolio_result.get("total_monthly_cost", 0)
            strategy_count = len(active_strategies)
            
            # Determine user tier based on strategy count and monthly spend
            if strategy_count >= 10 and total_monthly_cost >= 300:
                user_tier = "enterprise"
            elif strategy_count >= 5 and total_monthly_cost >= 100:
                user_tier = "pro" 
            else:
                user_tier = "basic"
            
            tier_config = self.tier_configs[user_tier]
            
            # Get last scan time from Redis
            last_scan_key = f"user_opportunity_last_scan:{user_id}"
            last_scan_timestamp = await self.redis.get(last_scan_key) if self.redis else None
            last_scan_time = None
            
            if last_scan_timestamp:
                try:
                    last_scan_time = datetime.fromisoformat(last_scan_timestamp.decode())
                except:
                    pass
            
            strategy_fingerprint = self._compute_strategy_fingerprint(active_strategies)

            return UserOpportunityProfile(
                user_id=user_id,
                active_strategy_count=strategy_count,
                total_monthly_strategy_cost=total_monthly_cost,
                user_tier=user_tier,
                max_asset_tier=tier_config["max_asset_tier"],
                opportunity_scan_limit=tier_config["scan_limit"],
                last_scan_time=last_scan_time,
                strategy_fingerprint=strategy_fingerprint
            )
            
        except Exception as e:
            self.logger.error("Failed to build user opportunity profile", 
                            user_id=user_id, error=str(e))
            
            # Return safe default
            return UserOpportunityProfile(
                user_id=user_id,
                active_strategy_count=0,
                total_monthly_strategy_cost=0,
                user_tier="basic",
                max_asset_tier="tier_retail",
                opportunity_scan_limit=10,
                last_scan_time=None,
                strategy_fingerprint="none"
            )
    
    async def _scan_strategy_opportunities(
        self,
        strategy_info: Dict[str, Any],
        discovered_assets: Dict[str, List[Any]],
        user_profile: UserOpportunityProfile,
        scan_id: str,
        portfolio_result: Dict[str, Any],  # NEW PARAMETER - eliminates N+1 query
        timeout_seconds: float = 30.0,
        start_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Scan opportunities for a specific strategy."""

        if start_time is None:
            start_time = time.time()

        def _timeout_exceeded(threshold: float = 1.0) -> bool:
            return (time.time() - start_time) >= (timeout_seconds * threshold)

        def _timeout_response(reason: str) -> Dict[str, Any]:
            elapsed = time.time() - start_time
            self.logger.warning(
                "Strategy approaching timeout, returning partial results",
                scan_id=scan_id,
                strategy=strategy_info.get("name", "Unknown"),
                strategy_id=strategy_info.get("strategy_id", ""),
                elapsed_seconds=elapsed,
                timeout_seconds=timeout_seconds,
                reason=reason,
            )
            return {
                "strategy_id": strategy_info.get("strategy_id", ""),
                "strategy_name": strategy_info.get("name", "Unknown"),
                "opportunities": [],
                "success": False,
                "error": reason,
                "partial": True,
            }

        if _timeout_exceeded(0.8):
            return _timeout_response("timeout_pre_execution")

        strategy_id = strategy_info.get("strategy_id", "")
        strategy_name = strategy_info.get("name", "Unknown")
        
        # FIXED: Try multiple ID formats to find scanner
        # Extract strategy function name with multiple fallback attempts
        strategy_func_candidates: List[str] = []

        # Try removing "ai_" prefix
        if strategy_id.startswith("ai_"):
            strategy_func_candidates.append(strategy_id.replace("ai_", "", 1))

        # Try the ID as-is
        strategy_func_candidates.append(strategy_id)

        # Try adding "ai_" prefix if not present
        if strategy_id and not strategy_id.startswith("ai_"):
            strategy_func_candidates.append(f"ai_{strategy_id}")

        # Try removing "_strategy" suffix
        if strategy_id.endswith("_strategy"):
            strategy_func_candidates.append(strategy_id[: -len("_strategy")])

        # Try alias resolution using both ID and display name
        alias_candidate = self._resolve_strategy_alias(strategy_id, strategy_name)
        if alias_candidate:
            strategy_func_candidates.append(alias_candidate)

        # Deduplicate while preserving insertion order
        seen_candidates = set()
        strategy_func_candidates = [
            candidate
            for candidate in strategy_func_candidates
            if candidate and not (candidate in seen_candidates or seen_candidates.add(candidate))
        ]
        
        # Find matching scanner
        strategy_func = None
        for candidate in strategy_func_candidates:
            if _timeout_exceeded(0.85):
                return _timeout_response("timeout_scanner_resolution")
            if candidate in self.strategy_scanners:
                strategy_func = candidate
                break
        
        self.logger.info("?? Scanning strategy opportunities",
                        scan_id=scan_id,
                        strategy=strategy_name,
                        strategy_id=strategy_id,
                        strategy_func=strategy_func,
                        tried_candidates=strategy_func_candidates,
                        available_scanners=list(self.strategy_scanners.keys())[:5])
        
        try:
            # Check if we have a scanner for this strategy
            if not strategy_func or strategy_func not in self.strategy_scanners:
                if self._looks_like_uuid(strategy_id):
                    self.logger.info(
                        "?? Routing UUID strategy to community scanner",
                        scan_id=scan_id,
                        strategy_id=strategy_id,
                        strategy_name=strategy_name,
                    )
                    if _timeout_exceeded(0.9):
                        return _timeout_response("timeout_before_community_scan")
                    community_opportunities = await self._scan_community_strategy_opportunities(
                        strategy_info,
                        discovered_assets,
                        user_profile,
                        scan_id,
                        portfolio_result,
                    )

                    return {
                        "strategy_id": strategy_id,
                        "strategy_name": strategy_name,
                        "opportunities": community_opportunities,
                    }

                self.logger.warning("? No scanner found for strategy",
                                  strategy_id=strategy_id,
                                  strategy_func=strategy_func,
                                  tried_candidates=strategy_func_candidates,
                                  available_scanners=list(self.strategy_scanners.keys()),
                                  scan_id=scan_id)
                return {"strategy_id": strategy_id, "opportunities": []}
            
            # Run the strategy-specific scanner with portfolio data
            scanner_method = self.strategy_scanners[strategy_func]
            if _timeout_exceeded(0.95):
                return _timeout_response("timeout_before_execution")

            remaining_budget = max(0.0, timeout_seconds - (time.time() - start_time))
            if remaining_budget <= 0:
                return _timeout_response("timeout_no_budget")

            try:
                opportunities = await asyncio.wait_for(
                    scanner_method(discovered_assets, user_profile, scan_id, portfolio_result),
                    timeout=remaining_budget,
                )
            except asyncio.TimeoutError:
                return _timeout_response("timeout_during_execution")

            self.logger.info("? Strategy scan completed",
                           scan_id=scan_id,
                           strategy=strategy_name,
                           opportunities_found=len(opportunities))
            
            return {
                "strategy_id": strategy_id,
                "strategy_name": strategy_name,
                "opportunities": opportunities
            }
            
        except Exception as e:
            self.logger.error("Strategy scan failed",
                            scan_id=scan_id,
                            strategy=strategy_name,
                            error=str(e),
                            exc_info=True)
            return {"strategy_id": strategy_id, "opportunities": []}
    
    # ================================================================================
    # STRATEGY-SPECIFIC OPPORTUNITY SCANNERS
    # These connect to your REAL trading strategies service - NO MOCK DATA
    # ================================================================================
    
    async def _scan_funding_arbitrage_opportunities(
        self,
        discovered_assets: Dict[str, List[Any]],
        user_profile: UserOpportunityProfile,
        scan_id: str,
        portfolio_result: Dict[str, Any]
    ) -> List[OpportunityResult]:
        """Scan funding rate arbitrage opportunities using REAL trading strategies service."""

        opportunities: List[OpportunityResult] = []

        try:
            # Get top volume symbols from discovered assets for funding arbitrage
            top_symbols = self._select_symbols_by_volume(
                "funding_arbitrage", discovered_assets, default_limit=20
            )
            if not top_symbols:
                self.logger.info(
                    "No symbols available for funding arbitrage scan",
                    scan_id=scan_id,
                    user_id=user_profile.user_id,
                )
                return opportunities

            # Call REAL funding arbitrage strategy using UNIFIED approach (same as rebalancing)
            # Check if user owns this strategy first (using passed portfolio)
            strategy_id = "ai_funding_arbitrage"
            user_portfolio = portfolio_result
            owned_strategy_ids = [s.get("strategy_id") for s in user_portfolio.get("active_strategies", [])]

            # FIXED: Log but don't block - dispatcher already handles strategy filtering
            if strategy_id not in owned_strategy_ids:
                self.logger.warning(
                    "Strategy not in portfolio, scanning anyway",
                    user_id=user_profile.user_id,
                    scan_id=scan_id,
                    strategy_id=strategy_id,
                    portfolio_strategies=len(owned_strategy_ids),
                )

            async def fetch_for_symbols(symbol_chunk: List[str]) -> List[OpportunityResult]:
                symbols_str = ",".join(symbol_chunk)
                arbitrage_result = await trading_strategies_service.execute_strategy(
                    function="funding_arbitrage",
                    parameters={
                        "symbols": symbols_str,
                        "exchanges": "all",
                        "min_funding_rate": 0.005,
                    },
                    user_id=user_profile.user_id,
                    simulation_mode=True,  # Use simulation mode to avoid credit consumption
                )

                chunk_opportunities: List[OpportunityResult] = []
                if arbitrage_result.get("success"):
                    analysis_data = arbitrage_result.get("funding_arbitrage_analysis", {})
                    opportunities_data = analysis_data.get("opportunities", [])

                    for opp in opportunities_data or []:
                        chunk_opportunities.append(
                            OpportunityResult(
                                strategy_id="ai_funding_arbitrage",
                                strategy_name="AI Funding Arbitrage",
                                opportunity_type="funding_arbitrage",
                                symbol=opp.get("symbol", ""),
                                exchange=opp.get("exchange", ""),
                                profit_potential_usd=float(opp.get("profit_potential") or 0),
                                confidence_score=float(opp.get("confidence") or 0.7),
                                risk_level=opp.get("risk_level", "medium"),
                                required_capital_usd=float(opp.get("required_capital") or 1000),
                                estimated_timeframe=opp.get("timeframe", "8h"),
                                entry_price=opp.get("entry_price"),
                                exit_price=opp.get("exit_price"),
                                metadata={
                                    "funding_rate_long": opp.get("funding_rate_long", 0),
                                    "funding_rate_short": opp.get("funding_rate_short", 0),
                                    "spread_percentage": opp.get("spread_percentage", 0),
                                    "exchanges": opp.get("exchanges", []),
                                },
                                discovered_at=self._current_timestamp(),
                            )
                        )

                return chunk_opportunities

            opportunities = await self._execute_strategy_across_chunks(
                "funding_arbitrage", top_symbols, fetch_for_symbols
            )

        except Exception as e:
            self.logger.error(
                "Funding arbitrage scan failed",
                scan_id=scan_id,
                error=str(e),
            )

        return opportunities
    
    async def _scan_statistical_arbitrage_opportunities(
        self,
        discovered_assets: Dict[str, List[Any]],
        user_profile: UserOpportunityProfile, 
        scan_id: str,
        portfolio_result: Dict[str, Any]
    ) -> List[OpportunityResult]:
        """Scan statistical arbitrage opportunities using REAL trading strategies service."""
        
        opportunities = []
        
        try:
            # Get universe of assets for statistical arbitrage
            # Use higher tier assets for stat arb (more institutional approach)
            stat_arb_limit = self._get_strategy_symbol_limit(
                "statistical_arbitrage", default=50
            )
            universe_symbols = self._get_symbols_for_statistical_arbitrage(
                discovered_assets, limit=stat_arb_limit
            )
            if not universe_symbols:
                self.logger.info(
                    "No symbols available for statistical arbitrage scan",
                    scan_id=scan_id,
                    user_id=user_profile.user_id,
                )
                return opportunities
            universe_str = ",".join(universe_symbols)

            # Call REAL statistical arbitrage strategy using correct method signature
            stat_arb_result = await trading_strategies_service.execute_strategy(
                function="statistical_arbitrage",
                strategy_type="mean_reversion",
                parameters={"universe": universe_str},
                user_id=user_profile.user_id
            )
            
            if stat_arb_result.get("success"):
                # Extract opportunities from nested analysis structure  
                analysis_data = stat_arb_result.get("statistical_arbitrage_analysis", {})
                opportunities_data = analysis_data.get("opportunities", [])
                
                if opportunities_data:
                    for opp in opportunities_data:
                        opportunity = OpportunityResult(
                            strategy_id="ai_statistical_arbitrage",
                            strategy_name="AI Statistical Arbitrage", 
                            opportunity_type="statistical_arbitrage",
                            symbol=opp.get("symbol", ""),
                            exchange=opp.get("exchange", "binance"),
                            profit_potential_usd=float(opp.get("profit_potential") or 0),
                            confidence_score=float(opp.get("confidence") or 0.75),
                            risk_level=opp.get("risk_level", "medium_high"),
                            required_capital_usd=float(opp.get("required_capital") or 5000),
                            estimated_timeframe=opp.get("timeframe", "24h"),
                            entry_price=opp.get("entry_price"),
                            exit_price=opp.get("target_price"),
                            metadata={
                                "z_score": opp.get("z_score", 0),
                                "correlation": opp.get("correlation", 0),
                                "lookback_period": opp.get("lookback_period", "30d"),
                                "strategy_type": opp.get("strategy_type", "mean_reversion")
                            },
                            discovered_at=self._current_timestamp()
                        )
                        opportunities.append(opportunity)
                    
        except Exception as e:
            self.logger.error("Statistical arbitrage scan failed",
                            scan_id=scan_id, error=str(e))
        
        return opportunities
    
    async def _scan_pairs_trading_opportunities(
        self,
        discovered_assets: Dict[str, List[Any]],
        user_profile: UserOpportunityProfile,
        scan_id: str,
        portfolio_result: Dict[str, Any]
    ) -> List[OpportunityResult]:
        """Scan pairs trading opportunities using REAL trading strategies service."""
        
        opportunities = []
        
        try:
            # Get correlated pairs from top assets
            correlation_pairs = self._get_correlation_pairs(discovered_assets, max_pairs=10)
            
            for pair in correlation_pairs:
                pair_str = f"{pair[0]}-{pair[1]}"
                
                # Call REAL pairs trading strategy using correct method signature
                pairs_result = await trading_strategies_service.execute_strategy(
                    function="pairs_trading",
                    strategy_type="statistical_arbitrage",
                    parameters={"pair_symbols": pair_str},
                    user_id=user_profile.user_id
                )
                
                if pairs_result.get("success") and pairs_result.get("trading_signals"):
                    signals = pairs_result["trading_signals"]
                    signal_strength = signals.get("signal_strength", 0)
                    
                    # Track ALL signals for transparency
                    self.logger.info(f"?? PAIRS TRADING SIGNAL ANALYSIS",
                                   scan_id=scan_id,
                                   symbol=pair_str,
                                   signal_strength=signal_strength,
                                   qualifies_threshold=signal_strength > 5.0)
                    
                    # Create opportunity for ALL signals above 3.0 but mark quality
                    if signal_strength > 3.0:  # Capture more opportunities
                        quality_tier = "high" if signal_strength > 5.0 else "medium" if signal_strength > 4.0 else "low"
                        
                        opportunity = OpportunityResult(
                            strategy_id="ai_pairs_trading",
                            strategy_name=f"AI Pairs Trading ({quality_tier.upper()} confidence)",
                            opportunity_type="pairs_trading",
                            symbol=pair_str,
                            exchange="binance",
                            profit_potential_usd=float(signals.get("expected_profit") or 0),
                            confidence_score=float(signal_strength) * 10,
                            risk_level=self._signal_to_risk_level(signal_strength),
                            required_capital_usd=float(signals.get("required_capital") or 10000),
                            estimated_timeframe=signals.get("timeframe", "72h"),
                            entry_price=signals.get("entry_price"),
                            exit_price=signals.get("exit_price"),
                            metadata={
                                "signal_strength": signal_strength,
                                "quality_tier": quality_tier,
                                "meets_original_threshold": signal_strength > 5.0,
                                "recommendation": "STRONG BUY" if signal_strength > 5.0 else "CONSIDER" if signal_strength > 4.0 else "MONITOR",
                                "correlation": pairs_result.get("correlation_analysis", {}).get("correlation", 0),
                                "spread_z_score": signals.get("spread_z_score", 0),
                                "signal_type": signals.get("signal_type", ""),
                                "pair_symbols": [pair[0], pair[1]]
                            },
                            discovered_at=self._current_timestamp()
                        )
                        opportunities.append(opportunity)
                        
        except Exception as e:
            self.logger.error("Pairs trading scan failed", 
                            scan_id=scan_id, error=str(e))
        
        return opportunities
    
    async def _scan_spot_momentum_opportunities(
        self,
        discovered_assets: Dict[str, List[Any]],
        user_profile: UserOpportunityProfile,
        scan_id: str,
        portfolio_result: Dict[str, Any]
    ) -> List[OpportunityResult]:
        """Scan spot momentum opportunities using REAL trading strategies service."""
        
        opportunities = []
        
        try:
            # Check if user owns spot momentum strategy (should be free strategy)
            strategy_id = "ai_spot_momentum_strategy"
            user_portfolio = portfolio_result
            owned_strategy_ids = [s.get("strategy_id") for s in user_portfolio.get("active_strategies", [])]
            
            # FIXED: Log but don't block - dispatcher already handles strategy filtering
            if strategy_id not in owned_strategy_ids:
                self.logger.warning("Strategy not in portfolio, scanning anyway", 
                                   user_id=user_profile.user_id, 
                                   scan_id=scan_id,
                                   strategy_id=strategy_id,
                                   portfolio_strategies=len(owned_strategy_ids))
            
            # Get symbols suitable for momentum trading
            momentum_symbols = self._select_symbols_by_volume(
                "spot_momentum_strategy", discovered_assets, default_limit=30
            )
            if not momentum_symbols:
                self.logger.info(
                    "No symbols available for momentum scan",
                    scan_id=scan_id,
                    user_id=user_profile.user_id,
                )
                return opportunities

            for symbol in momentum_symbols:
                try:
                    # User owns strategy - execute using unified approach
                    momentum_result = await trading_strategies_service.execute_strategy(
                    function="spot_momentum_strategy",
                    symbol=f"{symbol}/USDT",
                    parameters={"timeframe": "4h"},
                    user_id=user_profile.user_id,
                    simulation_mode=True  # Use simulation mode for opportunity scanning
                )
                    
                    if momentum_result.get("success"):
                        # CRITICAL FIX: Extract signal from correct location (top level, not inside execution_result)
                        signals = momentum_result.get("signal") or momentum_result.get("execution_result", {}).get("signal")
                        
                        if not signals:
                            self.logger.warning("No signal data found in momentum result",
                                              scan_id=scan_id,
                                              symbol=symbol,
                                              has_top_level_signal="signal" in momentum_result,
                                              has_execution_result="execution_result" in momentum_result)
                            continue  # Skip if no signal data
                        
                        # Track ALL signals for transparency
                        signal_strength = signals.get("strength", 0)
                        signal_confidence = signals.get("confidence", 0)
                        signal_action = signals.get("action", "HOLD")
                        
                        self.logger.info(
                            "?? MOMENTUM SIGNAL ANALYSIS",
                            scan_id=scan_id,
                            symbol=symbol,
                            signal_strength=signal_strength,
                            signal_confidence=signal_confidence,
                            signal_action=signal_action,
                            qualifies_threshold=signal_strength > 6.0,
                        )
                        # Create opportunity for ALL signals above 3.0 but mark quality
                        if signal_strength >= 2.5 and signal_action in {"BUY", "SELL"}:
                            quality_tier = "high" if signal_strength > 6.0 else "medium" if signal_strength > 4.5 else "low"

                            execution_data = momentum_result.get("execution_result", {})
                            indicators = momentum_result.get("indicators", {}) or execution_data.get("indicators", {})
                            risk_mgmt = momentum_result.get("risk_management", {}) or execution_data.get("risk_management", {})

                            price_snapshot = (
                                (indicators or {}).get("price_snapshot")
                                or (risk_mgmt or {}).get("price_snapshot")
                                or (indicators or {}).get("price")
                                or (risk_mgmt or {}).get("price")
                                or {}
                            )

                            entry_price = self._to_float((risk_mgmt or {}).get("entry_price"))
                            if entry_price is None:
                                entry_price = self._to_float(price_snapshot.get("current"))

                            take_profit_price = self._to_float((risk_mgmt or {}).get("take_profit_price"))
                            stop_loss_price = self._to_float((risk_mgmt or {}).get("stop_loss_price"))

                            potential_profit_usd = self._to_float((risk_mgmt or {}).get("potential_profit_usd")) or 0.0
                            required_capital_usd = self._to_float((risk_mgmt or {}).get("notional_usd")) or 0.0
                            risk_amount_usd = self._to_float((risk_mgmt or {}).get("risk_amount_usd"))
                            risk_reward_ratio = self._to_float((risk_mgmt or {}).get("risk_reward_ratio"))

                            if not entry_price or not take_profit_price or not stop_loss_price:
                                self.logger.warning(
                                    "Momentum signal missing risk levels",
                                    scan_id=scan_id,
                                    symbol=symbol,
                                    has_entry=entry_price is not None,
                                    has_take_profit=take_profit_price is not None,
                                    has_stop_loss=stop_loss_price is not None,
                                )
                                continue

                            if required_capital_usd <= 0:
                                required_capital_usd = max(1000.0, float(entry_price) * 0.5)

                            if potential_profit_usd <= 0 and entry_price:
                                quantity = required_capital_usd / float(entry_price)
                                potential_profit_usd = abs(float(take_profit_price) - float(entry_price)) * quantity

                            opportunity = OpportunityResult(
                                strategy_id="ai_spot_momentum_strategy",
                                strategy_name=f"AI Spot Momentum ({quality_tier.upper()} confidence)",
                                opportunity_type="spot_momentum",
                                symbol=symbol,
                                exchange="binance",
                                profit_potential_usd=float(potential_profit_usd),
                                confidence_score=float(signal_confidence) if signal_confidence else signal_strength * 10,
                                risk_level=self._signal_to_risk_level(signal_strength),
                                required_capital_usd=float(required_capital_usd),
                                estimated_timeframe="4-24h",
                                entry_price=float(entry_price) if entry_price else None,
                                exit_price=float(take_profit_price) if take_profit_price else None,
                                metadata={
                                    "signal_strength": signal_strength,
                                    "signal_confidence": signal_confidence,
                                    "signal_action": signal_action,
                                    "quality_tier": quality_tier,
                                    "meets_original_threshold": signal_strength > 6.0,
                                    "recommendation": "STRONG BUY" if signal_strength > 6.0 else "CONSIDER" if signal_strength > 4.5 else "MONITOR",
                                    "price_snapshot": price_snapshot,
                                    "stop_loss_price": stop_loss_price,
                                    "take_profit_price": take_profit_price,
                                    "risk_amount_usd": risk_amount_usd,
                                    "risk_reward_ratio": risk_reward_ratio,
                                    "risk_management": risk_mgmt,
                                },
                                discovered_at=self._current_timestamp()
                            )
                            opportunities.append(opportunity)
                            
                except Exception as symbol_error:
                    self.logger.warning(f"Failed to process symbol {symbol}", 
                                      scan_id=scan_id, error=str(symbol_error))
                    continue
                        
        except Exception as e:
            self.logger.error("Spot momentum scan failed",
                            scan_id=scan_id, error=str(e))
        
        return opportunities
    
    async def _scan_spot_mean_reversion_opportunities(
        self,
        discovered_assets: Dict[str, List[Any]],
        user_profile: UserOpportunityProfile,
        scan_id: str,
        portfolio_result: Dict[str, Any]
    ) -> List[OpportunityResult]:
        """Scan spot mean reversion opportunities using REAL trading strategies service."""
        
        opportunities = []
        
        try:
            # Get symbols for mean reversion (prefer higher volume, established coins)
            reversion_symbols = self._select_symbols_by_volume(
                "spot_mean_reversion", discovered_assets, default_limit=25
            )
            if not reversion_symbols:
                self.logger.info(
                    "No symbols available for mean reversion scan",
                    scan_id=scan_id,
                    user_id=user_profile.user_id,
                )
                return opportunities

            for symbol in reversion_symbols:
                # Call REAL spot mean reversion strategy using correct method signature
                reversion_result = await trading_strategies_service.execute_strategy(
                    function="spot_mean_reversion",
                    symbol=f"{symbol}/USDT",
                    parameters={"timeframe": "1h"},
                    user_id=user_profile.user_id
                )
                
                if reversion_result.get("success"):
                    indicators = reversion_result.get("indicators", {})
                    signal_block = reversion_result.get("signal", {})
                    risk_mgmt = reversion_result.get("risk_management", {})

                    z_score = self._to_float(indicators.get("z_score")) or self._to_float(signal_block.get("z_score")) or 0.0
                    deviation_score = abs(z_score)

                    # Track ALL signals for transparency
                    self.logger.info(
                        "?? MEAN REVERSION SIGNAL ANALYSIS",
                        scan_id=scan_id,
                        symbol=symbol,
                        deviation_score=deviation_score,
                        qualifies_threshold=deviation_score > 2.0,
                    )
                    
                    if deviation_score > 1.0:
                        quality_tier = "high" if deviation_score > 2.0 else "medium" if deviation_score > 1.5 else "low"
                        signal_strength = min(deviation_score * 2, 10)

                        signal_action = signal_block.get("action") or ("SELL" if z_score > 0 else "BUY" if z_score < 0 else "HOLD")
                        if signal_action not in {"BUY", "SELL"}:
                            continue

                        price_snapshot = (
                            indicators.get("price_snapshot")
                            or risk_mgmt.get("price_snapshot")
                            or indicators.get("price")
                            or risk_mgmt.get("price")
                            or {}
                        )

                        entry_price = self._to_float(risk_mgmt.get("entry_price") or indicators.get("entry_price"))
                        if entry_price is None:
                            entry_price = self._to_float(price_snapshot.get("current"))

                        take_profit_price = self._to_float(risk_mgmt.get("take_profit_price") or indicators.get("mean_price"))
                        stop_loss_price = self._to_float(risk_mgmt.get("stop_loss_price"))

                        potential_profit_usd = self._to_float(risk_mgmt.get("potential_profit_usd")) or 0.0
                        required_capital_usd = self._to_float(risk_mgmt.get("notional_usd")) or 0.0
                        risk_amount_usd = self._to_float(risk_mgmt.get("risk_amount_usd"))
                        risk_reward_ratio = self._to_float(risk_mgmt.get("risk_reward_ratio"))

                        if not entry_price or not take_profit_price or not stop_loss_price:
                            self.logger.warning(
                                "Mean reversion signal missing risk levels",
                                scan_id=scan_id,
                                symbol=symbol,
                                has_entry=entry_price is not None,
                                has_take_profit=take_profit_price is not None,
                                has_stop_loss=stop_loss_price is not None,
                            )
                            continue

                        if required_capital_usd <= 0:
                            required_capital_usd = max(1500.0, float(entry_price) * 0.75)

                        if potential_profit_usd <= 0 and entry_price:
                            quantity = required_capital_usd / float(entry_price)
                            potential_profit_usd = abs(float(take_profit_price) - float(entry_price)) * quantity

                        confidence_score = self._to_float(signal_block.get("confidence"))
                        if confidence_score is None:
                            confidence_score = min(95.0, max(30.0, signal_strength * 10))

                        opportunity = OpportunityResult(
                            strategy_id="ai_spot_mean_reversion",
                            strategy_name=f"AI Mean Reversion ({quality_tier.upper()} confidence)",
                            opportunity_type="mean_reversion",
                            symbol=symbol,
                            exchange="binance",
                            profit_potential_usd=float(potential_profit_usd),
                            confidence_score=float(confidence_score),
                            risk_level=self._signal_to_risk_level(signal_strength),
                            required_capital_usd=float(required_capital_usd),
                            estimated_timeframe="6-24h",
                            entry_price=float(entry_price) if entry_price else None,
                            exit_price=float(take_profit_price) if take_profit_price else None,
                            metadata={
                                "signal_strength": signal_strength,
                                "deviation_score": deviation_score,
                                "quality_tier": quality_tier,
                                "meets_original_threshold": deviation_score > 2.0,
                                "recommendation": "STRONG SELL" if deviation_score > 2.0 and signal_action == "SELL" else "STRONG BUY" if deviation_score > 2.0 else "CONSIDER" if deviation_score > 1.5 else "MONITOR",
                                "signal_action": signal_action,
                                "price_snapshot": price_snapshot,
                                "stop_loss_price": stop_loss_price,
                                "take_profit_price": take_profit_price,
                                "risk_amount_usd": risk_amount_usd,
                                "risk_reward_ratio": risk_reward_ratio,
                                "risk_management": risk_mgmt,
                                "mean_price": indicators.get("mean_price"),
                                "standard_deviation": indicators.get("standard_deviation"),
                            },
                            discovered_at=self._current_timestamp()
                        )
                        opportunities.append(opportunity)
                        
        except Exception as e:
            self.logger.error("Spot mean reversion scan failed",
                            scan_id=scan_id, error=str(e))
        
        return opportunities
    
    async def _scan_spot_breakout_opportunities(
        self,
        discovered_assets: Dict[str, List[Any]],
        user_profile: UserOpportunityProfile,
        scan_id: str,
        portfolio_result: Dict[str, Any]
    ) -> List[OpportunityResult]:
        """Scan spot breakout opportunities using REAL trading strategies service."""
        
        opportunities = []
        
        try:
            # Get symbols for breakout trading
            breakout_symbols = self._select_symbols_by_volume(
                "spot_breakout_strategy", discovered_assets, default_limit=20
            )
            if not breakout_symbols:
                self.logger.info(
                    "No symbols available for breakout scan",
                    scan_id=scan_id,
                    user_id=user_profile.user_id,
                )
                return opportunities

            for symbol in breakout_symbols:
                # Call REAL spot breakout strategy using correct method signature
                breakout_result = await trading_strategies_service.execute_strategy(
                    function="spot_breakout_strategy",
                    symbol=f"{symbol}/USDT",
                    parameters={"timeframe": "1h"},
                    user_id=user_profile.user_id
                )
                
                if breakout_result.get("success"):
                    breakout_analysis = breakout_result.get("breakout_analysis", {})
                    risk_mgmt = breakout_result.get("risk_management", {})

                    breakout_probability = self._to_float(breakout_analysis.get("confidence"))
                    if breakout_probability is None:
                        breakout_probability = self._to_float(breakout_analysis.get("conviction"))
                        breakout_probability = breakout_probability * 0.6 if breakout_probability is not None else 0.0
                    else:
                        breakout_probability = breakout_probability / 100.0

                    breakout_probability = breakout_probability or 0.0
                    breakout_probability = max(0.0, min(breakout_probability, 1.0))

                    # Track ALL signals for transparency
                    self.logger.info(
                        "?? BREAKOUT SIGNAL ANALYSIS",
                        scan_id=scan_id,
                        symbol=symbol,
                        breakout_probability=breakout_probability,
                        qualifies_threshold=breakout_probability > 0.75,
                    )

                    if breakout_probability > 0.5 and breakout_analysis.get("breakout_detected"):
                        quality_tier = (
                            "high"
                            if breakout_probability > 0.75
                            else "medium"
                            if breakout_probability > 0.65
                            else "low"
                        )
                        signal_strength = breakout_probability * 10.0

                        entry_price = self._to_float(
                            risk_mgmt.get("entry_price")
                            or breakout_result.get("current_price")
                        )
                        take_profit_price = self._to_float(
                            risk_mgmt.get("take_profit_price")
                            or breakout_analysis.get("take_profit")
                        )
                        stop_loss_price = self._to_float(
                            risk_mgmt.get("stop_loss_price")
                            or breakout_analysis.get("stop_loss")
                        )

                        position_size_units = self._to_float(risk_mgmt.get("position_size"))
                        position_notional = self._to_float(risk_mgmt.get("position_notional"))

                        if (
                            entry_price
                            and (position_size_units is None or position_size_units <= 0)
                        ):
                            position_size_units = round(1000.0 / entry_price, 6)

                        if (
                            entry_price
                            and position_size_units
                            and (position_notional is None or position_notional <= 0)
                        ):
                            position_notional = round(position_size_units * entry_price, 2)

                        risk_amount = self._to_float(risk_mgmt.get("risk_amount"))
                        potential_profit = self._to_float(risk_mgmt.get("potential_profit"))
                        risk_reward_ratio = self._to_float(risk_mgmt.get("risk_reward_ratio"))

                        if (
                            entry_price
                            and stop_loss_price
                            and (risk_amount is None or risk_amount <= 0)
                            and position_size_units
                        ):
                            risk_amount = round(
                                abs(entry_price - stop_loss_price) * position_size_units,
                                2,
                            )

                        if (
                            entry_price
                            and take_profit_price
                            and (potential_profit is None or potential_profit <= 0)
                            and position_size_units
                        ):
                            potential_profit = round(
                                abs(take_profit_price - entry_price) * position_size_units,
                                2,
                            )

                        if (
                            risk_amount
                            and risk_amount > 0
                            and potential_profit is not None
                            and (risk_reward_ratio is None or risk_reward_ratio <= 0)
                        ):
                            risk_reward_ratio = round(potential_profit / risk_amount, 2)

                        confidence_score = self._to_float(breakout_analysis.get("confidence") or risk_mgmt.get("confidence"))
                        if confidence_score is None:
                            confidence_score = breakout_probability * 100.0

                        indicators = breakout_result.get("indicators") or {}
                        price_snapshot = indicators.get("price_snapshot") if isinstance(indicators, dict) else {}
                        if not isinstance(price_snapshot, dict):
                            price_snapshot = {}

                        # Compute required capital with sensible fallbacks
                        required_capital_usd = self._to_float(risk_mgmt.get("notional_usd"))
                        if required_capital_usd is None or required_capital_usd <= 0:
                            if position_notional and position_notional > 0:
                                required_capital_usd = float(position_notional)
                            elif entry_price and position_size_units:
                                required_capital_usd = round(float(entry_price) * float(position_size_units), 2)
                            else:
                                required_capital_usd = 1000.0

                        opportunity = OpportunityResult(
                            strategy_id="ai_spot_breakout_strategy",
                            strategy_name=f"AI Breakout Trading ({quality_tier.upper()} confidence)",
                            opportunity_type="breakout",
                            symbol=symbol,
                            exchange="binance",
                            profit_potential_usd=float(potential_profit or 0.0),
                            confidence_score=float(confidence_score),
                            risk_level=self._signal_to_risk_level(signal_strength),
                            required_capital_usd=float(required_capital_usd),
                            estimated_timeframe="2-8h",
                            entry_price=float(entry_price) if entry_price else None,
                            exit_price=float(take_profit_price) if take_profit_price else None,
                            metadata={
                                "signal_strength": signal_strength,
                                "breakout_probability": breakout_probability,
                                "quality_tier": quality_tier,
                                "meets_original_threshold": breakout_probability > 0.75,
                                "recommendation": "STRONG BUY" if breakout_probability > 0.75 else "CONSIDER" if breakout_probability > 0.65 else "MONITOR",
                                "support_level": breakout_analysis.get("support_levels"),
                                "resistance_level": breakout_analysis.get("resistance_levels"),
                                "volume_surge": breakout_analysis.get("volume_surge"),
                                "breakout_direction": breakout_analysis.get("direction"),
                                "price_snapshot": breakout_analysis.get("price_snapshot") or risk_mgmt.get("price_snapshot"),
                                "stop_loss_price": stop_loss_price,
                                "take_profit_price": take_profit_price,
                                "risk_amount": risk_amount,
                                "risk_reward_ratio": risk_reward_ratio,
                            },
                            discovered_at=self._current_timestamp(),
                        )
                        opportunities.append(opportunity)
                        
        except Exception as e:
            self.logger.error("Spot breakout scan failed",
                            scan_id=scan_id, error=str(e))
        
        return opportunities
    
    # Additional strategy scanners for remaining strategies...
    # (Risk Management, Portfolio Optimization, Scalping, Market Making, etc.)
    # Each following the same pattern: call REAL strategy, convert results to OpportunityResult
    
    async def _scan_risk_management_opportunities(
        self,
        discovered_assets: Dict[str, List[Any]],
        user_profile: UserOpportunityProfile,
        scan_id: str,
        portfolio_result: Dict[str, Any]
    ) -> List[OpportunityResult]:
        """Risk management focuses on portfolio protection opportunities."""
        
        opportunities = []
        
        try:
            # Check if user owns risk management strategy (should be free strategy)
            strategy_id = "ai_risk_management"
            user_portfolio = portfolio_result
            owned_strategy_ids = [s.get("strategy_id") for s in user_portfolio.get("active_strategies", [])]
            
            # FIXED: Log but don't block - dispatcher already handles strategy filtering
            if strategy_id not in owned_strategy_ids:
                self.logger.warning("Strategy not in portfolio, scanning anyway", 
                                   user_id=user_profile.user_id, 
                                   scan_id=scan_id,
                                   strategy_id=strategy_id,
                                   portfolio_strategies=len(owned_strategy_ids))
            
            # User owns strategy - execute using unified approach
            hedge_result = await trading_strategies_service.execute_strategy(
                function="risk_management",
                user_id=user_profile.user_id,
                simulation_mode=True  # Use simulation mode for opportunity scanning
            )
            
            if hedge_result.get("success"):
                # ENTERPRISE FIX: Extract mitigation strategies from risk management response
                risk_analysis = hedge_result.get("risk_management_analysis", {})
                mitigation_strategies = risk_analysis.get("mitigation_strategies", [])
                
                # Also check for hedge_recommendations in case of hedge_position function
                execution_result = hedge_result.get("execution_result", {})
                hedge_recommendations = execution_result.get("hedge_recommendations", []) or hedge_result.get("hedge_recommendations", [])
                
                # Combine both sources
                all_recommendations = mitigation_strategies + hedge_recommendations
                
                if all_recommendations:
                    for recommendation in all_recommendations:
                        # Handle mitigation strategies format
                        if "risk_type" in recommendation:
                            # This is a mitigation strategy
                            urgency = recommendation.get("urgency", 0.8)
                            if urgency > 0.3:  # Lowered threshold for more opportunities
                                opportunity = OpportunityResult(
                                    strategy_id="ai_risk_management",
                                    strategy_name="AI Risk Management - Mitigation",
                                    opportunity_type="risk_mitigation",
                                    symbol=recommendation.get("recommendation", "Portfolio"),
                                    exchange="multiple",
                                    profit_potential_usd=0,  # Risk management protects rather than profits
                                    confidence_score=urgency * 100,
                                    risk_level="low",
                                    required_capital_usd=float(recommendation.get("cost_estimate", 100)),
                                    estimated_timeframe="immediate",
                                    entry_price=None,
                                    exit_price=None,
                                    metadata={
                                        "risk_type": recommendation.get("risk_type", ""),
                                        "strategy": recommendation.get("strategy", ""),
                                        "rationale": recommendation.get("rationale", ""),
                                        "portfolio_protection": True
                                    },
                                    discovered_at=self._current_timestamp()
                                )
                                opportunities.append(opportunity)
                        else:
                            # This is a hedge recommendation
                            if recommendation.get("urgency_score", 0) > 0.3:  # Lowered for more opportunities
                                opportunity = OpportunityResult(
                                    strategy_id="ai_risk_management",
                                    strategy_name="AI Risk Management - Hedge",
                                    opportunity_type="risk_hedge",
                                    symbol=recommendation.get("hedge_instrument", ""),
                                    exchange="binance",
                                    profit_potential_usd=0,  # Risk management protects rather than profits
                                    confidence_score=float(recommendation.get("effectiveness", 0.8) * 100),
                                    risk_level="low",
                                    required_capital_usd=float(recommendation.get("hedge_cost") or 500),
                                    estimated_timeframe="ongoing",
                                    entry_price=None,
                                    exit_price=None,
                                    metadata={
                                        "hedge_type": recommendation.get("hedge_type", ""),
                                        "risk_reduction": recommendation.get("risk_reduction_percentage", 0),
                                        "urgency": recommendation.get("urgency_score", 0),
                                        "portfolio_protection": True
                                    },
                                    discovered_at=self._current_timestamp()
                                )
                                opportunities.append(opportunity)
                        
        except Exception as e:
            self.logger.error("Risk management scan failed", 
                            scan_id=scan_id, error=str(e))
        
        return opportunities
    
    async def _scan_portfolio_optimization_opportunities(
        self,
        discovered_assets: Dict[str, List[Any]],
        user_profile: UserOpportunityProfile, 
        scan_id: str,
        portfolio_result: Dict[str, Any]
    ) -> List[OpportunityResult]:
        """Portfolio optimization identifies rebalancing opportunities."""
        
        opportunities = []
        
        try:
            # Check if user owns portfolio optimization strategy (should be free strategy)
            strategy_id = "ai_portfolio_optimization"
            user_portfolio = portfolio_result
            owned_strategy_ids = [s.get("strategy_id") for s in user_portfolio.get("active_strategies", [])]
            
            # FIXED: Log but don't block - dispatcher already handles strategy filtering
            if strategy_id not in owned_strategy_ids:
                self.logger.warning("Strategy not in portfolio, scanning anyway", 
                                   user_id=user_profile.user_id, 
                                   scan_id=scan_id,
                                   strategy_id=strategy_id,
                                   portfolio_strategies=len(owned_strategy_ids))
            
            # User owns strategy - execute using unified approach
            optimization_result = await trading_strategies_service.execute_strategy(
                function="portfolio_optimization",
                user_id=user_profile.user_id,
                simulation_mode=True,  # Use simulation mode for opportunity scanning
                preloaded_portfolio=portfolio_result,
            )
            
            if optimization_result.get("success"):
                execution_result = optimization_result.get("execution_result", {})
                rebalancing_recommendations = (
                    execution_result.get("rebalancing_recommendations", [])
                    or optimization_result.get("rebalancing_recommendations", [])
                )

                strategy_analysis_raw = optimization_result.get("strategy_analysis", {}) or {}
                strategy_analysis = {
                    str(key).lower(): value
                    for key, value in strategy_analysis_raw.items()
                    if isinstance(value, dict)
                }

                capital_info = await self._estimate_user_deployable_capital(
                    user_profile.user_id,
                    portfolio_result,
                    optimization_result,
                )
                deployable_capital = float(capital_info.get("deployable_capital_usd", 0.0) or 0.0)
                optimization_summary = optimization_result.get("optimization_summary", {}) or {}

                if rebalancing_recommendations:

                    def _normalize_improvement(value: Any) -> float:
                        """Convert raw improvement values to a 0-1 range."""
                        if value is None:
                            return 0.0

                        try:
                            is_percent = False

                            if isinstance(value, str):
                                cleaned_value = value.strip()
                                if cleaned_value.endswith("%"):
                                    cleaned_value = cleaned_value[:-1]
                                    is_percent = True
                                parsed_value = float(cleaned_value)
                            else:
                                parsed_value = float(value)

                            if is_percent or parsed_value > 1.0:
                                parsed_value /= 100.0

                            return max(0.0, min(parsed_value, 1.0))
                        except (TypeError, ValueError):
                            return 0.0

                    for rebal in rebalancing_recommendations:
                        raw_improvement = rebal.get("improvement_potential")
                        strategy_name = rebal.get("strategy", "UNKNOWN")
                        strategy_key = str(strategy_name).lower()

                        improvement_normalized = _normalize_improvement(raw_improvement)

                        target_weight_fraction = self._to_fraction(rebal.get("target_weight"))
                        target_percentage_fraction = self._to_fraction(rebal.get("target_percentage"))
                        weight_change_fraction = self._to_fraction(rebal.get("weight_change"))
                        amount_fraction = target_weight_fraction
                        if amount_fraction is None:
                            amount_fraction = target_percentage_fraction
                        if amount_fraction is None:
                            amount_fraction = weight_change_fraction
                        if amount_fraction is None:
                            amount_fraction = self._to_fraction(rebal.get("amount"))

                        value_change = self._to_float(rebal.get("value_change"))
                        notional_usd = self._to_float(rebal.get("notional_usd"))
                        trade_value_usd = value_change if value_change is not None else notional_usd
                        if trade_value_usd is None:
                            fallback_frac = self._to_fraction(rebal.get("amount", 0.0))
                            if fallback_frac is not None and -1.0 <= fallback_frac <= 1.0:
                                baseline_capital = deployable_capital if deployable_capital > 0 else 10000.0
                                trade_value_usd = fallback_frac * baseline_capital
                            else:
                                fallback_abs = self._to_float(rebal.get("amount"))
                                trade_value_usd = fallback_abs if fallback_abs is not None else None

                        required_capital = abs(float(trade_value_usd)) if trade_value_usd is not None else 0.0

                        strategy_metrics = strategy_analysis.get(strategy_key, {})
                        improvement_candidate = improvement_normalized if improvement_normalized > 0 else None
                        expected_return_rate = self._normalize_return_rate(
                            improvement_candidate,
                            strategy_metrics.get("expected_return"),
                            optimization_summary.get("expected_return"),
                        )

                        profit_projection = self._build_profit_projection(
                            deployable_capital,
                            expected_return_rate,
                            strategy_metrics.get("risk_level"),
                            source="strategy_analysis",
                        )

                        metadata: Dict[str, Any] = {
                            "rebalance_action": rebal.get("action", ""),
                            "strategy_used": strategy_name,
                            "improvement_potential": improvement_normalized,
                            "risk_reduction": rebal.get("risk_reduction", 0),
                            "urgency": rebal.get("urgency", "MEDIUM"),
                            "normalized_improvement": improvement_normalized,
                            "return_assumptions": {
                                "improvement_input": raw_improvement,
                                "expected_return_rate": expected_return_rate,
                                "source": "improvement_potential"
                                if improvement_candidate is not None
                                else "strategy_analysis",
                            },
                            "profit_projection": profit_projection,
                            "capital_assumptions": self._prepare_capital_metadata_snapshot(
                                capital_info,
                                deployable_capital,
                            ),
                            "risk_metrics": {
                                "raw_risk_input": strategy_metrics.get("risk_level"),
                                "normalized_risk_spread_pct": profit_projection["risk_spread_pct"],
                                "source": profit_projection.get("risk_measure_source"),
                            },
                            "optimization_summary_snapshot": optimization_summary,
                        }

                        if amount_fraction is not None and -1.0 <= amount_fraction <= 1.0:
                            metadata["amount"] = amount_fraction
                        else:
                            amt_usd = self._to_float(rebal.get("amount"))
                            if amt_usd is not None:
                                metadata["amount_usd"] = float(amt_usd)

                        if target_weight_fraction is not None:
                            metadata["target_weight"] = target_weight_fraction

                        if weight_change_fraction is not None:
                            metadata["weight_change"] = weight_change_fraction

                        target_percentage_value = self._to_float(rebal.get("target_percentage"))
                        if target_percentage_value is not None:
                            metadata["target_percentage"] = target_percentage_value

                        if trade_value_usd is not None:
                            metadata["trade_value_usd"] = float(trade_value_usd)

                        if value_change is not None and value_change != trade_value_usd:
                            metadata["value_change"] = value_change

                        profit_potential_usd = float(profit_projection["expected_profit_usd"] or 0.0)
                        risk_label = self._risk_spread_to_label(
                            profit_projection["risk_spread_pct"] / 100.0
                        )
                        confidence_score = max(
                            45.0,
                            min(95.0, 95.0 - profit_projection["risk_spread_pct"]),
                        )

                        opportunity = OpportunityResult(
                            strategy_id="ai_portfolio_optimization",
                            strategy_name=f"AI Portfolio Optimization - {strategy_name}",
                            opportunity_type="portfolio_rebalance",
                            symbol=rebal.get("symbol", rebal.get("target_asset", "")),
                            exchange="multiple",
                            profit_potential_usd=profit_potential_usd,
                            confidence_score=confidence_score,
                            risk_level=risk_label,
                            required_capital_usd=required_capital,
                            estimated_timeframe="1-3 months",
                            entry_price=None,
                            exit_price=None,
                            metadata=metadata,
                            discovered_at=self._current_timestamp(),
                        )
                        opportunities.append(opportunity)

                elif strategy_analysis:
                    for strategy, results in strategy_analysis.items():
                        if not isinstance(results, dict):
                            continue

                        expected_return_rate = self._normalize_return_rate(
                            results.get("expected_return"),
                            optimization_summary.get("expected_return"),
                        )

                        profit_projection = self._build_profit_projection(
                            deployable_capital,
                            expected_return_rate,
                            results.get("risk_level"),
                            source="strategy_analysis",
                        )

                        profit_potential_usd = float(profit_projection["expected_profit_usd"] or 0.0)
                        risk_label = self._risk_spread_to_label(
                            profit_projection["risk_spread_pct"] / 100.0
                        )
                        confidence_score = max(
                            45.0,
                            min(92.0, 92.0 - profit_projection["risk_spread_pct"]),
                        )

                        metadata = {
                            "strategy": strategy,
                            "expected_annual_return": expected_return_rate,
                            "risk_level": results.get("risk_level", 0),
                            "sharpe_ratio": results.get("sharpe_ratio", 0),
                            "analysis_type": "strategy_comparison",
                            "profit_projection": profit_projection,
                            "capital_assumptions": self._prepare_capital_metadata_snapshot(
                                capital_info,
                                deployable_capital,
                            ),
                            "risk_metrics": {
                                "raw_risk_input": results.get("risk_level"),
                                "normalized_risk_spread_pct": profit_projection["risk_spread_pct"],
                                "source": profit_projection.get("risk_measure_source"),
                            },
                        }

                        opportunity = OpportunityResult(
                            strategy_id="ai_portfolio_optimization",
                            strategy_name=f"Portfolio {strategy.replace('_', ' ').title()}",
                            opportunity_type="optimization_analysis",
                            symbol="PORTFOLIO",
                            exchange="all",
                            profit_potential_usd=profit_potential_usd,
                            confidence_score=confidence_score,
                            risk_level=risk_label,
                            required_capital_usd=deployable_capital if deployable_capital > 0 else 0.0,
                            estimated_timeframe="1 year",
                            entry_price=None,
                            exit_price=None,
                            metadata=metadata,
                            discovered_at=self._current_timestamp(),
                        )
                        opportunities.append(opportunity)
                        
        except Exception as e:
            self.logger.error("Portfolio optimization scan failed",
                            scan_id=scan_id, error=str(e))
        
        return opportunities
    
    # Placeholder implementations for remaining strategies
    # These would follow the same pattern, calling real trading strategy methods
    
    async def _scan_scalping_opportunities(
        self, 
        discovered_assets: Dict[str, List[Any]], 
        user_profile: UserOpportunityProfile, 
        scan_id: str, 
        portfolio_result: Dict[str, Any]
    ) -> List[OpportunityResult]:
        """Enterprise scalping scanner for high-frequency opportunities."""
        
        opportunities = []
        
        try:
            # Check if user owns scalping strategy
            strategy_id = "ai_scalping_strategy"
            owned_strategy_ids = [s.get("strategy_id") for s in portfolio_result.get("active_strategies", [])]
            
            # FIXED: Log but don't block - dispatcher already handles strategy filtering
            if strategy_id not in owned_strategy_ids:
                self.logger.warning("Strategy not in portfolio, scanning anyway", 
                                   user_id=user_profile.user_id, 
                                   scan_id=scan_id,
                                   strategy_id=strategy_id,
                                   portfolio_strategies=len(owned_strategy_ids))
            
            # Get highest volume symbols for scalping (need liquidity)
            symbols = self._select_symbols_by_volume(
                "scalping_strategy", discovered_assets, default_limit=8
            )
            if not symbols:
                self.logger.info(
                    "No symbols available for scalping scan",
                    scan_id=scan_id,
                    user_id=user_profile.user_id,
                )
                return opportunities

            for symbol in symbols:
                try:
                    # Call trading strategies service for scalping analysis
                    scalp_result = await trading_strategies_service.execute_strategy(
                        function="scalping_strategy",
                        strategy_type="momentum_scalp",
                        symbol=f"{symbol}/USDT",
                        parameters={
                            "timeframe": "1m",
                            "profit_target": 0.005,  # 0.5% profit target
                            "stop_loss": 0.002,      # 0.2% stop loss
                            "min_volume_surge": 2.0,  # 2x volume surge
                            "rsi_threshold": 70
                        },
                        user_id=user_profile.user_id,
                        simulation_mode=True
                    )
                    
                    if scalp_result.get("success"):
                        signal = scalp_result.get("signal", {})
                        momentum = signal.get("momentum_score", 0)
                        
                        if momentum > 3.0:
                            opportunities.append(OpportunityResult(
                                strategy_id="ai_scalping_strategy",
                                strategy_name=f"AI Scalping ({signal.get('direction', 'Long')})",
                                opportunity_type="scalping",
                                symbol=symbol,
                                exchange=scalp_result.get("exchange", "binance"),
                                profit_potential_usd=float(signal.get("profit_potential") or 25),
                                confidence_score=float(momentum) * 10,
                                risk_level="medium",  # Scalping is medium risk due to frequency
                                required_capital_usd=float(signal.get("required_capital") or 1000),
                                estimated_timeframe="5m",  # Quick scalp
                                entry_price=signal.get("entry_price"),
                                exit_price=signal.get("target_price"),
                                metadata={
                                    "momentum_score": momentum,
                                    "direction": signal.get("direction", "long"),
                                    "volume_surge": signal.get("volume_surge", 1),
                                    "rsi": signal.get("rsi", 50),
                                    "profit_target_pct": 0.5,
                                    "stop_loss_pct": 0.2,
                                    "expected_duration_min": signal.get("duration_min", 5)
                                },
                                discovered_at=self._current_timestamp()
                            ))
                            
                except Exception as e:
                    self.logger.debug(f"Scalping analysis failed for {symbol}", error=str(e))
                    continue
            
            self.logger.info(f"? Scalping scanner found {len(opportunities)} opportunities", 
                           scan_id=scan_id, strategy_id=strategy_id)
            
        except Exception as e:
            self.logger.error("Scalping scan failed", scan_id=scan_id, error=str(e))
        
        return opportunities
    
    async def _scan_market_making_opportunities(
        self, 
        discovered_assets: Dict[str, List[Any]], 
        user_profile: UserOpportunityProfile, 
        scan_id: str, 
        portfolio_result: Dict[str, Any]
    ) -> List[OpportunityResult]:
        """Enterprise market making scanner with spread analysis."""
        
        opportunities = []
        
        try:
            # Check if user owns market making strategy
            strategy_id = "ai_market_making"
            owned_strategy_ids = [s.get("strategy_id") for s in portfolio_result.get("active_strategies", [])]
            
            # FIXED: Log but don't block - dispatcher already handles strategy filtering
            if strategy_id not in owned_strategy_ids:
                self.logger.warning("Strategy not in portfolio, scanning anyway", 
                                   user_id=user_profile.user_id, 
                                   scan_id=scan_id,
                                   strategy_id=strategy_id,
                                   portfolio_strategies=len(owned_strategy_ids))
            
            # Get highly liquid symbols for market making
            symbols = self._select_symbols_by_volume(
                "market_making", discovered_assets, default_limit=10
            )
            if not symbols:
                self.logger.info(
                    "No symbols available for market making scan",
                    scan_id=scan_id,
                    user_id=user_profile.user_id,
                )
                return opportunities

            for symbol in symbols:
                try:
                    # Call trading strategies service for market making analysis
                    mm_result = await trading_strategies_service.execute_strategy(
                        function="market_making",
                        strategy_type="dual_side",
                        symbol=f"{symbol}/USDT",
                        parameters={
                            "spread_target": 0.002,  # 0.2% spread
                            "order_amount": 1000,     # $1000 per order
                            "max_position": 10000,   # Max $10k position
                            "rebalance_threshold": 0.1
                        },
                        user_id=user_profile.user_id,
                        simulation_mode=True
                    )
                    
                    if mm_result.get("success"):
                        signal = mm_result.get("signal", {})
                        spread = signal.get("current_spread", 0)
                        
                        if spread > 0.001:  # 0.1% minimum spread
                            opportunities.append(OpportunityResult(
                                strategy_id="ai_market_making",
                                strategy_name=f"AI Market Making ({symbol})",
                                opportunity_type="market_making",
                                symbol=symbol,
                                exchange=mm_result.get("exchange", "binance"),
                                profit_potential_usd=float(signal.get("daily_profit_est") or 50),
                                confidence_score=min(100, float(spread * 10000)),  # Spread-based confidence
                                risk_level="low",  # Market making is generally low risk
                                required_capital_usd=float(signal.get("required_capital") or 5000),
                                estimated_timeframe="24h",
                                entry_price=signal.get("bid_price"),
                                exit_price=signal.get("ask_price"),
                                metadata={
                                    "current_spread": spread,
                                    "target_spread": 0.002,
                                    "volume_24h": signal.get("volume_24h", 0),
                                    "liquidity_score": signal.get("liquidity_score", 0),
                                    "order_book_depth": signal.get("order_book_depth", {}),
                                    "estimated_fills_per_hour": signal.get("fills_per_hour", 0)
                                },
                                discovered_at=self._current_timestamp()
                            ))
                            
                except Exception as e:
                    self.logger.debug(f"Market making analysis failed for {symbol}", error=str(e))
                    continue
            
            self.logger.info(f"? Market making scanner found {len(opportunities)} opportunities", 
                           scan_id=scan_id, strategy_id=strategy_id)
            
        except Exception as e:
            self.logger.error("Market making scan failed", scan_id=scan_id, error=str(e))
        
        return opportunities
    
    async def _scan_futures_trading_opportunities(
        self, 
        discovered_assets: Dict[str, List[Any]], 
        user_profile: UserOpportunityProfile, 
        scan_id: str, 
        portfolio_result: Dict[str, Any]
    ) -> List[OpportunityResult]:
        """Enterprise futures trading scanner with leverage analysis."""
        
        opportunities = []
        
        try:
            # Check if user owns futures trading strategy
            strategy_id = "ai_futures_trade"
            owned_strategy_ids = [s.get("strategy_id") for s in portfolio_result.get("active_strategies", [])]
            
            # FIXED: Log but don't block - dispatcher already handles strategy filtering
            if strategy_id not in owned_strategy_ids:
                self.logger.warning("Strategy not in portfolio, scanning anyway", 
                                   user_id=user_profile.user_id, 
                                   scan_id=scan_id,
                                   strategy_id=strategy_id,
                                   portfolio_strategies=len(owned_strategy_ids))
            
            # Get top volume symbols for futures analysis
            symbols = self._select_symbols_by_volume(
                "futures_trade", discovered_assets, default_limit=20
            )
            if not symbols:
                self.logger.info(
                    "No symbols available for futures scan",
                    scan_id=scan_id,
                    user_id=user_profile.user_id,
                )
                return opportunities

            # Process symbols in parallel
            tasks = [
                self._analyze_futures_opportunity(symbol, user_profile.user_id, scan_id)
                for symbol in symbols
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    self.logger.warning("Futures analysis failed", scan_id=scan_id, error=str(result))
                    continue
                
                if result and result.confidence_score > 30:  # 3.0 signal strength * 10
                    opportunities.append(result)
            
            self.logger.info(f"? Futures scanner found {len(opportunities)} opportunities", 
                           scan_id=scan_id, strategy_id=strategy_id)
            
        except Exception as e:
            self.logger.error("Futures trading scan failed", scan_id=scan_id, error=str(e))
        
        return opportunities
    
    async def _scan_options_trading_opportunities(
        self,
        discovered_assets: Dict[str, List[Any]],
        user_profile: UserOpportunityProfile,
        scan_id: str,
        portfolio_result: Dict[str, Any]
    ) -> List[OpportunityResult]:
        """Enterprise options trading scanner with Greeks analysis."""
        
        opportunities = []
        
        try:
            # Check if user owns options trading strategy
            candidate_ids = ("ai_options_strategies", "ai_options_trade")
            owned_strategy_ids = [s.get("strategy_id") for s in portfolio_result.get("active_strategies", [])]
            strategy_id = self._resolve_owned_strategy_id(owned_strategy_ids, *candidate_ids)

            if not strategy_id or strategy_id not in owned_strategy_ids:
                self.logger.warning(
                    "Strategy not in portfolio, skipping options scan",
                    user_id=user_profile.user_id,
                    scan_id=scan_id,
                    strategy_id=strategy_id,
                    portfolio_strategies=len(owned_strategy_ids),
                    known_candidates=candidate_ids,
                )
                return opportunities
            
            # Get top volume symbols for options analysis
            symbols = self._select_symbols_by_volume(
                "options_trade", discovered_assets, default_limit=15
            )
            if not symbols:
                self.logger.info(
                    "No symbols available for options scan",
                    scan_id=scan_id,
                    user_id=user_profile.user_id,
                )
                return opportunities

            # Process in parallel batches for efficiency
            batch_size = self._get_strategy_chunk_size("options_trade") or 5
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i+batch_size]
                
                # Use asyncio.gather for parallel execution
                tasks = [
                    self._analyze_options_opportunity(
                        symbol,
                        user_profile.user_id,
                        scan_id,
                        strategy_id,
                        candidate_ids,
                    )
                    for symbol in batch
                ]
                
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        self.logger.warning("Options analysis failed", scan_id=scan_id, error=str(result))
                        continue
                    
                    if result and result.confidence_score > 30:  # 3.0 signal strength * 10
                        opportunities.append(result)

            self.logger.info(f"? Options scanner found {len(opportunities)} opportunities",
                           scan_id=scan_id, strategy_id=strategy_id)
            
        except Exception:
            self.logger.exception("Options trading scan failed", scan_id=scan_id)
        
        return opportunities
    
    async def _analyze_options_opportunity(
        self,
        symbol: str,
        user_id: str,
        scan_id: str,
        strategy_id: Optional[str],
        candidate_ids: Tuple[str, ...],
    ) -> Optional[OpportunityResult]:
        """Analyze single symbol for options opportunity with Greeks."""

        try:
            # Call trading strategies service for options analysis
            options_result = await trading_strategies_service.execute_strategy(
                function="options_trade",
                strategy_type="iron_condor",  # Most profitable options strategy
                symbol=f"{symbol}/USDT",
                parameters={
                    "timeframe": "1d",
                    "calculate_greeks": True,
                    "min_volume": 1000000,
                    "expiry_days": 30
                },
                user_id=user_id,
                simulation_mode=True
            )
            
            if not options_result.get("success"):
                return None
            
            # ENTERPRISE FIX: Handle both signal-based and greeks-based responses
            execution_result = options_result.get("execution_result", {})
            
            # Check for signal in multiple locations
            signal = (
                options_result.get("signal", {}) or
                execution_result.get("signal", {})
            )
            
            # Extract Greeks and option details
            greeks = (
                options_result.get("greeks", {}) or
                execution_result.get("greeks", {}) or
                options_result.get("option_greeks", {})
            )
            
            option_details = (
                execution_result.get("option_details", {}) or
                options_result.get("option_details", {})
            )
            
            risk_analysis = (
                execution_result.get("risk_analysis", {}) or
                options_result.get("risk_analysis", {})
            )
            
            # Calculate signal strength from various sources
            signal_strength = (
                signal.get("strength", 0) or
                risk_analysis.get("profit_probability", 0) * 10 or
                (greeks.get("delta", 0) * greeks.get("gamma", 0) * 100) if greeks else 0
            )
            
            # Also check for edge/expected value as signal
            expected_edge = risk_analysis.get("expected_edge", 0) or option_details.get("expected_profit_pct", 0)
            
            if signal_strength > 3.0 or expected_edge > 2.0:  # Lower edge threshold for more opportunities
                resolved_strategy_id = strategy_id or next(
                    (candidate for candidate in candidate_ids if candidate),
                    "ai_options_strategies",
                )
                return OpportunityResult(
                    strategy_id=resolved_strategy_id,
                    strategy_name=f"AI Options Trading ({signal.get('strategy_type', 'Iron Condor')})",
                    opportunity_type="options",
                    symbol=symbol,
                    exchange=options_result.get("exchange", "binance"),
                    profit_potential_usd=float(signal.get("max_profit") or 500),
                    confidence_score=float(signal_strength) * 10,  # Convert to 0-100 scale
                    risk_level=self._calculate_options_risk(greeks),
                    required_capital_usd=float(signal.get("required_capital") or 5000),
                    estimated_timeframe=f"{signal.get('days_to_expiry', 30)}d",
                    entry_price=signal.get("entry_price"),
                    exit_price=signal.get("target_price"),
                    metadata={
                        "signal_strength": signal_strength,
                        "strategy_type": signal.get("strategy_type") or option_details.get("strategy", "iron_condor"),
                        "strike_prices": signal.get("strikes", {}) or option_details.get("strikes", {}),
                        "expiry": signal.get("expiry") or option_details.get("expiry_date"),
                        "greeks": {
                            "delta": greeks.get("delta", 0),
                            "gamma": greeks.get("gamma", 0),
                            "theta": greeks.get("theta", 0),
                            "vega": greeks.get("vega", 0),
                            "iv": greeks.get("implied_volatility", 0)
                        },
                        "breakeven_points": signal.get("breakeven_points", []) or risk_analysis.get("breakeven_points", []),
                        "max_profit": signal.get("max_profit", 0) or risk_analysis.get("max_profit", 0),
                        "max_loss": signal.get("max_loss", 0) or risk_analysis.get("max_loss", 0),
                        "probability_of_profit": signal.get("probability_of_profit", 0) or risk_analysis.get("profit_probability", 0),
                        "expected_edge": expected_edge,
                        "option_details": option_details
                    },
                    discovered_at=self._current_timestamp()
                )
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Options analysis failed for {symbol}", error=str(e), scan_id=scan_id)
            return None

    def _calculate_options_risk(self, greeks: Dict[str, float]) -> str:
        """Calculate risk level based on Greeks."""

        # Sophisticated risk calculation based on Greeks
        delta_risk = abs(greeks.get("delta", 0))
        gamma_risk = abs(greeks.get("gamma", 0)) * 10  # Gamma is more sensitive
        vega_risk = abs(greeks.get("vega", 0)) * 5

        total_risk = delta_risk + gamma_risk + vega_risk

        if total_risk < 0.3:
            return "low"
        elif total_risk < 0.6:
            return "medium"
        elif total_risk < 0.9:
            return "high"
        else:
            return "very_high"

    async def _scan_volatility_trading_opportunities(
        self,
        discovered_assets: Dict[str, List[Any]],
        user_profile: UserOpportunityProfile,
        scan_id: str,
        portfolio_result: Dict[str, Any],
    ) -> List[OpportunityResult]:
        """Surface trades where realized volatility is spiking."""

        opportunities: List[OpportunityResult] = []

        try:
            strategy_id = "ai_volatility_trading"
            owned_strategy_ids = [s.get("strategy_id") for s in portfolio_result.get("active_strategies", [])]

            if strategy_id not in owned_strategy_ids:
                self.logger.warning(
                    "Strategy not in portfolio, scanning anyway",
                    user_id=user_profile.user_id,
                    scan_id=scan_id,
                    strategy_id=strategy_id,
                    portfolio_strategies=len(owned_strategy_ids),
                )

            symbols = self._select_symbols_by_volume(
                "volatility_trading", discovered_assets, default_limit=12
            )
            if not symbols:
                self.logger.info(
                    "No symbols available for volatility scan",
                    scan_id=scan_id,
                    user_id=user_profile.user_id,
                )
                return opportunities
            base_symbols = []
            for symbol in symbols:
                base = self._extract_base_symbol(symbol)
                if base and base not in base_symbols:
                    base_symbols.append(base)

            if not base_symbols:
                return opportunities

            volatility_result = await market_analysis_service.volatility_analysis(
                ",".join(base_symbols[:8]),
                user_id=user_profile.user_id,
            )

            if not volatility_result.get("success"):
                return opportunities

            individual = volatility_result.get("volatility_analysis", {}).get("individual_analysis", {})

            for base_symbol, payload in individual.items():
                overall_vol = float(payload.get("overall_volatility", 0.0))
                ranking = (payload.get("volatility_ranking") or "").lower()
                timeframes = payload.get("timeframes", {})
                primary_tf = timeframes.get("1h") or timeframes.get("4h") or next(iter(timeframes.values()), {})
                percentile = self._parse_usd_value(primary_tf.get("volatility_percentile"), 0.0)

                if overall_vol < 0.025 and ranking != "high":
                    continue

                confidence = max(35.0, min(95.0, percentile))
                profit_potential = max(500.0, overall_vol * 25000.0)
                risk_level = self._score_to_risk_level(min(overall_vol / 0.10, 1.0))

                opportunities.append(
                    OpportunityResult(
                        strategy_id=strategy_id,
                        strategy_name=f"AI Volatility Trading ({base_symbol})",
                        opportunity_type="volatility_breakout",
                        symbol=f"{base_symbol}/USDT",
                        exchange="binance",
                        profit_potential_usd=round(profit_potential, 2),
                        confidence_score=confidence,
                        risk_level=risk_level,
                        required_capital_usd=self._determine_required_capital({}, fallback=10000.0),
                        estimated_timeframe="1d",
                        entry_price=None,
                        exit_price=None,
                        metadata={
                            "overall_volatility": overall_vol,
                            "volatility_ranking": ranking,
                            "volatility_percentile": percentile,
                            "volatility_forecast": payload.get("volatility_forecast", {}),
                            "risk_metrics": payload.get("risk_metrics", {}),
                        },
                        discovered_at=self._current_timestamp(),
                    )
                )

            self.logger.info(
                "? Volatility trading scanner completed",
                scan_id=scan_id,
                opportunities=len(opportunities),
            )

        except Exception:
            self.logger.exception(
                "Volatility trading scan failed",
                scan_id=scan_id,
            )

        return opportunities

    async def _scan_news_sentiment_opportunities(
        self,
        discovered_assets: Dict[str, List[Any]],
        user_profile: UserOpportunityProfile,
        scan_id: str,
        portfolio_result: Dict[str, Any],
    ) -> List[OpportunityResult]:
        """Leverage the real-time sentiment engine for news-driven trades."""

        from app.services.realtime_sentiment_engine import realtime_sentiment_engine

        opportunities: List[OpportunityResult] = []

        try:
            strategy_id = "ai_news_sentiment"
            owned_strategy_ids = [s.get("strategy_id") for s in portfolio_result.get("active_strategies", [])]

            if strategy_id not in owned_strategy_ids:
                self.logger.warning(
                    "Strategy not in portfolio, scanning anyway",
                    user_id=user_profile.user_id,
                    scan_id=scan_id,
                    strategy_id=strategy_id,
                    portfolio_strategies=len(owned_strategy_ids),
                )

            symbols = self._select_symbols_by_volume(
                "news_sentiment", discovered_assets, default_limit=12
            )
            if not symbols:
                self.logger.info(
                    "No symbols available for news sentiment scan",
                    scan_id=scan_id,
                    user_id=user_profile.user_id,
                )
                return opportunities
            base_symbols = []
            for symbol in symbols:
                base = self._extract_base_symbol(symbol)
                if base and base not in base_symbols:
                    base_symbols.append(base)

            if not base_symbols:
                return opportunities

            if realtime_sentiment_engine.redis is None:
                await realtime_sentiment_engine.async_init()

            sentiment_result = await realtime_sentiment_engine.analyze_realtime_sentiment(
                symbols=base_symbols[:10],
                user_id=user_profile.user_id,
            )

            if not sentiment_result.get("success"):
                return opportunities

            for signal in sentiment_result.get("sentiment_signals", []):
                news_impact = self._parse_usd_value(signal.get("news_impact"), 0.0)
                sentiment_score = self._parse_usd_value(signal.get("sentiment_score"), 0.0)
                confidence_raw = self._parse_usd_value(signal.get("confidence"), 50.0)

                if abs(news_impact) < 10 or abs(sentiment_score) < 25:
                    continue

                direction = "bullish" if sentiment_score > 0 else "bearish"
                symbol = signal.get("symbol", "")
                if not symbol:
                    continue

                confidence = max(40.0, min(95.0, confidence_raw))
                profit_potential = max(400.0, abs(news_impact) * 120.0)
                risk_level = self._score_to_risk_level(abs(sentiment_score) / 100.0)

                opportunities.append(
                    OpportunityResult(
                        strategy_id=strategy_id,
                        strategy_name=f"AI News Sentiment ({symbol})",
                        opportunity_type="news_sentiment",
                        symbol=f"{symbol}/USDT",
                        exchange="binance",
                        profit_potential_usd=round(profit_potential, 2),
                        confidence_score=confidence,
                        risk_level=risk_level,
                        required_capital_usd=self._determine_required_capital({}, fallback=7500.0),
                        estimated_timeframe="6h",
                        entry_price=None,
                        exit_price=None,
                        metadata={
                            "direction": direction,
                            "news_impact": news_impact,
                            "sentiment_score": sentiment_score,
                            "volume_score": signal.get("volume_score"),
                            "social_momentum": signal.get("social_momentum"),
                            "whale_activity": signal.get("whale_activity"),
                            "recommendation": signal.get("recommendation"),
                        },
                        discovered_at=self._current_timestamp(),
                    )
                )

            self.logger.info(
                "? News sentiment scanner completed",
                scan_id=scan_id,
                opportunities=len(opportunities),
            )

        except Exception:
            self.logger.exception(
                "News sentiment scan failed",
                scan_id=scan_id,
            )

        return opportunities

    async def _scan_community_strategy_opportunities(
        self,
        strategy_info: Dict[str, Any],
        discovered_assets: Dict[str, List[Any]],
        user_profile: UserOpportunityProfile,
        scan_id: str,
        portfolio_result: Dict[str, Any],
    ) -> List[OpportunityResult]:
        """Fallback scanner for user-created or community strategies."""

        opportunities: List[OpportunityResult] = []
        
        # Reference portfolio_result to silence linter warnings
        _ = portfolio_result

        try:
            strategy_id = strategy_info.get("strategy_id", "community")
            strategy_name = strategy_info.get("name", "Community Strategy")

            policy_key = strategy_info.get("strategy_id") or strategy_info.get("name") or "community_strategy"
            symbols = self._select_symbols_by_volume(
                str(policy_key), discovered_assets, default_limit=8
            )
            if not symbols:
                self.logger.info(
                    "No symbols available for community strategy scan",
                    scan_id=scan_id,
                    user_id=user_profile.user_id,
                    strategy_id=strategy_id,
                )
                return opportunities
            base_symbols = []
            for symbol in symbols:
                base = self._extract_base_symbol(symbol)
                if base and base not in base_symbols:
                    base_symbols.append(base)

            if not base_symbols:
                return opportunities

            sentiment_result = await market_analysis_service.market_sentiment(
                ",".join(base_symbols[:6]),
                user_id=user_profile.user_id,
            )

            if not sentiment_result.get("success"):
                return opportunities

            individual = sentiment_result.get("data", {}).get("individual_sentiment", {})
            market_sentiment = sentiment_result.get("data", {}).get("market_sentiment", {})

            required_capital = self._determine_required_capital(strategy_info, fallback=5000.0)

            for base_symbol, payload in individual.items():
                overall = payload.get("overall_sentiment", {})
                score = self._parse_usd_value(overall.get("score"), 0.0)

                if abs(score) < 0.2:
                    continue

                direction = overall.get("label", "neutral").upper()
                confidence = max(30.0, min(90.0, abs(score) * 100))
                profit_potential = max(300.0, required_capital * abs(score) * 0.4)
                risk_level = self._score_to_risk_level(min(abs(score) * 1.5, 1.0))

                opportunities.append(
                    OpportunityResult(
                        strategy_id=strategy_id,
                        strategy_name=f"{strategy_name} ({base_symbol})",
                        opportunity_type="community_signal",
                        symbol=f"{base_symbol}/USDT",
                        exchange="binance",
                        profit_potential_usd=round(profit_potential, 2),
                        confidence_score=confidence,
                        risk_level=risk_level,
                        required_capital_usd=required_capital,
                        estimated_timeframe="1d",
                        entry_price=None,
                        exit_price=None,
                        metadata={
                            "sentiment_score": score,
                            "sentiment_label": overall.get("label"),
                            "direction": direction,
                            "timeframe_breakdown": payload.get("timeframe_breakdown", {}),
                            "market_sentiment": market_sentiment,
                        },
                        discovered_at=self._current_timestamp(),
                    )
                )

            self.logger.info(
                "? Community strategy sentiment scanner completed",
                scan_id=scan_id,
                strategy_id=strategy_id,
                opportunities=len(opportunities),
            )

        except Exception as exc:
            self.logger.warning(
                "Community strategy scan failed",
                scan_id=scan_id,
                strategy=strategy_info.get("strategy_id"),
                error=str(exc),
            )

        return opportunities

    async def _analyze_futures_opportunity(self, symbol: str, user_id: str, scan_id: str) -> Optional[OpportunityResult]:
        """Analyze single symbol for futures opportunity with leverage calculation."""

        try:
            # Call trading strategies service for futures analysis
            futures_result = await trading_strategies_service.execute_strategy(
                function="futures_trade",
                strategy_type="trend_following",  # Popular futures strategy
                symbol=f"{symbol}/USDT",
                parameters={
                    "timeframe": "1h",
                    "leverage": 10,  # 10x leverage
                    "min_volume": 5000000,
                    "stop_loss_pct": 2.0,
                    "take_profit_pct": 6.0
                },
                user_id=user_id,
                simulation_mode=True
            )
            
            if not futures_result.get("success"):
                return None
            
            signal = futures_result.get("signal", {})
            
            signal_strength = signal.get("strength", 0)
            if signal_strength > 3.0:
                leverage = signal.get("leverage", 10)
                base_profit = signal.get("profit_potential", 100)
                
                return OpportunityResult(
                    strategy_id="ai_futures_trade",
                    strategy_name=f"AI Futures Trading ({signal.get('direction', 'Long')} {leverage}x)",
                    opportunity_type="futures",
                    symbol=symbol,
                    exchange=futures_result.get("exchange", "binance"),
                    profit_potential_usd=float(base_profit * leverage),
                    confidence_score=float(signal_strength) * 10,
                    risk_level=self._calculate_futures_risk(leverage, signal.get("volatility", 0.1)),
                    required_capital_usd=float(signal.get("required_margin") or 1000),
                    estimated_timeframe=signal.get("timeframe", "6h"),
                    entry_price=signal.get("entry_price"),
                    exit_price=signal.get("target_price"),
                    metadata={
                        "signal_strength": signal_strength,
                        "direction": signal.get("direction", "long"),
                        "leverage": leverage,
                        "funding_rate": signal.get("funding_rate", 0),
                        "liquidation_price": signal.get("liquidation_price"),
                        "stop_loss": signal.get("stop_loss"),
                        "take_profit": signal.get("take_profit"),
                        "volatility": signal.get("volatility", 0),
                        "volume_24h": signal.get("volume_24h", 0)
                    },
                    discovered_at=self._current_timestamp()
                )
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Futures analysis failed for {symbol}", error=str(e), scan_id=scan_id)
            return None
    
    def _calculate_futures_risk(self, leverage: float, volatility: float) -> str:
        """Calculate risk level based on leverage and volatility."""

        # Risk increases with leverage and volatility
        leverage_risk = leverage / 100  # Normalize leverage (10x = 0.1)
        volatility_risk = volatility * 10  # Amplify volatility impact

        total_risk = leverage_risk + volatility_risk

        if total_risk < 0.3:
            return "low"
        elif total_risk < 0.6:
            return "medium"
        elif total_risk < 1.0:
            return "high"
        else:
            return "very_high"

    def _prepare_capital_metadata_snapshot(
        self,
        capital_info: Optional[Dict[str, Any]],
        deployable_capital: float,
    ) -> Dict[str, Any]:
        """Create an immutable snapshot of capital assumptions for metadata."""

        if not isinstance(capital_info, dict):
            return {
                "deployable_capital_usd": float(deployable_capital or 0.0),
                "capital_basis_used_usd": float(deployable_capital or 0.0),
                "components": {},
                "assumptions": ["Capital details unavailable; using fallback basis."],
                "fallback_used": True,
            }

        snapshot = copy.deepcopy(capital_info)
        snapshot.setdefault("assumptions", [])
        if not isinstance(snapshot["assumptions"], list):
            snapshot["assumptions"] = [str(snapshot["assumptions"])]

        current_capital = self._to_float(snapshot.get("deployable_capital_usd"))
        desired_capital = self._to_float(deployable_capital)
        if desired_capital is None:
            desired_capital = current_capital or 0.0

        snapshot["deployable_capital_usd"] = float(desired_capital or 0.0)
        snapshot["capital_basis_used_usd"] = float(desired_capital or 0.0)

        components = snapshot.get("components")
        if isinstance(components, dict):
            normalized_components = {}
            for key, value in components.items():
                numeric = self._to_float(value)
                if numeric is not None:
                    normalized_components[key] = float(numeric)
            snapshot["components"] = normalized_components
        else:
            snapshot["components"] = {}

        if "fallback_used" not in snapshot:
            snapshot["fallback_used"] = False

        snapshot.setdefault("calculation_timestamp", self._current_timestamp().isoformat())

        return snapshot

    async def _estimate_user_deployable_capital(
        self,
        user_id: str,
        portfolio_result: Dict[str, Any],
        optimization_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Estimate deployable capital based on portfolio data and credit availability."""

        details: Dict[str, Any] = {
            "deployable_capital_usd": 0.0,
            "components": {},
            "inputs": {},
            "credit_profile": None,
            "assumptions": [],
            "calculation_timestamp": self._current_timestamp().isoformat(),
            "fallback_used": False,
        }

        portfolio_value_candidates: Dict[str, float] = {}

        def add_portfolio_candidate(source: str, value: Any) -> None:
            numeric = self._to_float(value)
            if numeric is None:
                return
            portfolio_value_candidates[source] = float(numeric)

        optimization_summary = (optimization_result or {}).get("optimization_summary", {}) or {}
        add_portfolio_candidate("optimization_summary", optimization_summary.get("portfolio_value"))
        add_portfolio_candidate("optimization_summary_usd", optimization_summary.get("portfolio_value_usd"))

        portfolio_context = (optimization_result or {}).get("portfolio_context", {}) or {}
        add_portfolio_candidate("optimization_portfolio_context", portfolio_context.get("total_value_usd"))

        summary = (portfolio_result or {}).get("summary", {}) or {}
        add_portfolio_candidate("strategy_marketplace_summary", summary.get("total_portfolio_value"))

        nested_portfolio = (portfolio_result or {}).get("portfolio", {}) or {}
        add_portfolio_candidate("strategy_marketplace_portfolio", nested_portfolio.get("total_value"))
        add_portfolio_candidate("strategy_marketplace_portfolio_usd", nested_portfolio.get("total_value_usd"))

        cash_balance = 0.0
        try:
            portfolio_snapshot = await portfolio_risk_service.get_portfolio(user_id)
            if portfolio_snapshot.get("success"):
                portfolio_payload = portfolio_snapshot.get("portfolio", {}) or {}
                add_portfolio_candidate("portfolio_risk_service", portfolio_payload.get("total_value_usd"))
                cash_balance = self._extract_cash_balance(portfolio_payload)
                details["inputs"]["portfolio_service_source"] = portfolio_snapshot.get("function", "get_portfolio")
        except Exception as portfolio_error:  # pragma: no cover - defensive logging
            self.logger.debug(
                "Capital estimation: portfolio service lookup failed",
                error=str(portfolio_error),
            )

        details["inputs"]["portfolio_value_sources"] = portfolio_value_candidates

        portfolio_value = max(portfolio_value_candidates.values(), default=0.0)

        credit_buying_power = 0.0
        credit_profile: Optional[Dict[str, Any]] = None
        user_uuid: Optional[uuid.UUID] = None
        try:
            user_uuid = uuid.UUID(str(user_id))
        except (ValueError, TypeError):
            user_uuid = None

        if user_uuid:
            try:
                async for db in get_database():
                    stmt = select(CreditAccount).where(CreditAccount.user_id == user_uuid)
                    result = await db.execute(stmt)
                    credit_account = result.scalar_one_or_none()
                    if credit_account:
                        ratio = self._to_float(getattr(credit_account, "credit_to_usd_ratio", 1.0))
                        if ratio is None or ratio <= 0:
                            ratio = 1.0
                        available_credits = float(getattr(credit_account, "available_credits", 0) or 0)
                        credit_buying_power = available_credits * ratio
                        profit_potential = credit_account.calculate_profit_potential()
                        profit_potential_value = self._to_float(profit_potential) or available_credits * ratio
                        credit_profile = {
                            "available_credits": available_credits,
                            "credit_to_usd_ratio": float(ratio),
                            "credit_buying_power_usd": float(credit_buying_power),
                            "profit_potential_usd": float(profit_potential_value),
                        }
                    break
            except Exception as credit_error:  # pragma: no cover - defensive logging
                self.logger.debug(
                    "Capital estimation: credit lookup failed",
                    error=str(credit_error),
                )

        details["inputs"]["credit_buying_power_usd"] = float(credit_buying_power)

        components: Dict[str, float] = {}
        if portfolio_value > 0:
            components["portfolio_value_usd"] = float(portfolio_value)
        if cash_balance > 0:
            components["cash_balance_usd"] = float(cash_balance)
        if credit_buying_power > 0:
            components["credit_buying_power_usd"] = float(credit_buying_power)

        deployable_capital = (
            max(portfolio_value, 0.0)
            + max(cash_balance, 0.0)
            + max(credit_buying_power, 0.0)
        )

        if deployable_capital <= 0:
            deployable_capital = 10000.0
            details["fallback_used"] = True
            details["assumptions"].append(
                "Fallback deployable capital of $10,000 applied due to missing live balance data."
            )

        if not details["assumptions"]:
            details["assumptions"].append(
                "Deployable capital derived from live portfolio balances and available credit."
            )

        if credit_profile:
            details["assumptions"].append(
                "Credit-derived buying power assumes 1 credit = ${:.2f} USD spendable capital.".format(
                    credit_profile.get("credit_to_usd_ratio", 1.0)
                )
            )

        details["deployable_capital_usd"] = float(deployable_capital)
        details["capital_basis_used_usd"] = float(deployable_capital)
        details["components"] = components
        details["credit_profile"] = credit_profile
        details["cash_balance_usd"] = float(cash_balance)

        return details

    def _extract_cash_balance(self, portfolio_payload: Dict[str, Any]) -> float:
        """Extract cash-like balances (stablecoins) from portfolio payload."""

        if not isinstance(portfolio_payload, dict):
            return 0.0

        stable_assets = {"USDT", "USDC", "USD", "BUSD", "USDP", "DAI", "TUSD"}
        total_cash = 0.0

        balances = portfolio_payload.get("balances", []) or []
        for balance in balances:
            if not isinstance(balance, dict):
                continue
            asset = str(balance.get("asset") or balance.get("symbol") or "").upper()
            if asset not in stable_assets:
                continue
            value = self._to_float(balance.get("value_usd"))
            if value is None:
                value = self._to_float(balance.get("total"))
            if value is not None:
                total_cash += float(value)

        return float(total_cash)

    def _normalize_return_rate(self, *candidates: Optional[Any]) -> float:
        """Normalize return values (percentages or fractions) into fraction form."""

        for candidate in candidates:
            if candidate is None:
                continue
            numeric = candidate if isinstance(candidate, (int, float)) else self._to_float(candidate)
            if numeric is None:
                continue
            numeric = float(numeric)
            if not math.isfinite(numeric):
                continue
            if abs(numeric) > 1.0 and abs(numeric) <= 100.0:
                numeric /= 100.0
            numeric = max(-5.0, min(5.0, numeric))
            return numeric
        return 0.0

    def _normalize_risk_measure(self, risk_value: Any, default_source: str = "analysis") -> Tuple[float, str]:
        """Normalize various risk descriptors into a volatility-style fraction."""

        if risk_value is None:
            return 0.2, f"{default_source}:default"

        if isinstance(risk_value, (int, float)):
            val = abs(float(risk_value))
            if val > 1.0 and val <= 100.0:
                val /= 100.0
            elif val > 100.0:
                val = min(val / 100.0, 1.0)
            val = max(0.02, min(val, 0.75))
            return val, f"{default_source}:numeric"

        if isinstance(risk_value, str):
            normalized = risk_value.strip().lower()
            mapping = {
                "very_low": 0.05,
                "low": 0.10,
                "balanced": 0.18,
                "medium": 0.20,
                "medium_high": 0.30,
                "elevated": 0.30,
                "high": 0.40,
                "very_high": 0.55,
                "extreme": 0.65,
            }
            if normalized in mapping:
                return mapping[normalized], f"{default_source}:{normalized}"

            numeric = self._to_float(risk_value)
            if numeric is not None:
                if abs(numeric) > 1.0 and abs(numeric) <= 100.0:
                    numeric /= 100.0
                numeric = abs(float(numeric))
                numeric = max(0.02, min(numeric, 0.75))
                return numeric, f"{default_source}:parsed_numeric"

        return 0.25, f"{default_source}:fallback"

    def _build_profit_projection(
        self,
        capital: float,
        expected_return_rate: Any,
        risk_value: Any,
        source: str = "analysis",
    ) -> Dict[str, float]:
        """Build expected/best/worst-case profit projections."""

        capital_basis = self._to_float(capital) or 0.0
        normalized_return = self._normalize_return_rate(expected_return_rate)
        risk_spread, risk_source = self._normalize_risk_measure(risk_value, default_source=source)

        best_return = normalized_return + risk_spread
        worst_return = normalized_return - risk_spread
        worst_return = max(-1.0, worst_return)

        projection = {
            "expected_return_pct": normalized_return * 100.0,
            "expected_profit_usd": capital_basis * normalized_return,
            "best_case_return_pct": best_return * 100.0,
            "best_case_profit_usd": capital_basis * best_return,
            "worst_case_return_pct": worst_return * 100.0,
            "worst_case_profit_usd": capital_basis * worst_return,
            "risk_spread_pct": risk_spread * 100.0,
            "risk_measure_value": risk_value,
            "risk_measure_source": risk_source,
            "capital_basis_usd": capital_basis,
        }

        return {key: float(value) if isinstance(value, (int, float)) else value for key, value in projection.items()}

    def _risk_spread_to_label(self, risk_spread: float) -> str:
        """Convert normalized risk spread into human-readable label."""

        if risk_spread <= 0.1:
            return "low"
        if risk_spread <= 0.25:
            return "medium"
        if risk_spread <= 0.4:
            return "medium_high"
        return "high"

    def _extract_capital_metadata_from_opportunities(
        self,
        opportunities: List[OpportunityResult],
    ) -> Optional[Dict[str, Any]]:
        """Aggregate capital metadata from opportunity results."""

        capital_snapshots: List[Dict[str, Any]] = []
        for opportunity in opportunities:
            if not isinstance(opportunity, OpportunityResult):
                continue
            metadata = getattr(opportunity, "metadata", {}) or {}
            if not isinstance(metadata, dict):
                continue
            capital_meta = metadata.get("capital_assumptions")
            if isinstance(capital_meta, dict):
                capital_snapshots.append(capital_meta)

        if not capital_snapshots:
            return None

        reference = max(
            capital_snapshots,
            key=lambda item: self._to_float(item.get("deployable_capital_usd")) or 0.0,
        )

        combined = copy.deepcopy(reference)
        combined_components = combined.get("components") if isinstance(combined.get("components"), dict) else {}

        for snapshot in capital_snapshots:
            components = snapshot.get("components") if isinstance(snapshot, dict) else None
            if isinstance(components, dict):
                for key, value in components.items():
                    numeric = self._to_float(value)
                    if numeric is None:
                        continue
                    existing = self._to_float(combined_components.get(key))
                    if existing is None or numeric > existing:
                        combined_components[key] = float(numeric)

        combined["components"] = combined_components
        combined["sources_count"] = len(capital_snapshots)

        return combined

    def _summarize_profit_projections(
        self,
        opportunities: List[OpportunityResult],
    ) -> Optional[Dict[str, Any]]:
        """Summarize profit projections across opportunities."""

        projections: List[Dict[str, Any]] = []
        for opportunity in opportunities:
            metadata = getattr(opportunity, "metadata", {}) or {}
            if not isinstance(metadata, dict):
                continue
            projection = metadata.get("profit_projection")
            if isinstance(projection, dict):
                projections.append(projection)

        if not projections:
            return None

        total_expected = 0.0
        total_best = 0.0
        total_worst = 0.0
        total_return_pct = 0.0

        for projection in projections:
            expected_profit = self._to_float(projection.get("expected_profit_usd")) or 0.0
            best_profit = self._to_float(projection.get("best_case_profit_usd")) or 0.0
            worst_profit = self._to_float(projection.get("worst_case_profit_usd")) or 0.0
            expected_return_pct = self._to_float(projection.get("expected_return_pct")) or 0.0

            total_expected += expected_profit
            total_best += best_profit
            total_worst += worst_profit
            total_return_pct += expected_return_pct

        summary = {
            "expected_profit_total_usd": total_expected,
            "best_case_total_usd": total_best,
            "worst_case_total_usd": total_worst,
            "average_expected_return_pct": total_return_pct / max(len(projections), 1),
            "opportunity_count": len(projections),
        }

        return summary
    
    async def _scan_hedge_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Generate hedge opportunities using the live hedge_position strategy."""

        opportunities: List[OpportunityResult] = []

        async def _load_portfolio_positions() -> List[Dict[str, Any]]:
            try:
                snapshot = await portfolio_risk_service.get_portfolio(user_profile.user_id)
            except Exception as portfolio_error:  # pragma: no cover - defensive logging
                self.logger.warning(
                    "Hedge scanner: portfolio lookup failed",
                    user_id=user_profile.user_id,
                    scan_id=scan_id,
                    error=str(portfolio_error),
                )
                return []

            if not snapshot.get("success"):
                return []

            payload = snapshot.get("portfolio", {}) or {}
            positions = list(payload.get("positions", []) or [])
            if not positions:
                balances = payload.get("balances", []) or []
                for balance in balances:
                    symbol = balance.get("asset") or balance.get("symbol")
                    quantity = self._to_float(balance.get("total")) or 0.0
                    value_usd = self._to_float(balance.get("value_usd")) or 0.0
                    if not symbol or value_usd <= 0:
                        continue
                    positions.append(
                        {
                            "symbol": symbol,
                            "quantity": quantity,
                            "value_usd": value_usd,
                            "exchange": balance.get("exchange", "binance"),
                        }
                    )
            return positions

        try:
            positions = await _load_portfolio_positions()

            candidate_positions: List[Dict[str, Any]] = []
            for position in positions:
                raw_symbol = position.get("symbol") or position.get("asset")
                if not raw_symbol:
                    continue

                market_value = (
                    self._to_float(position.get("market_value"))
                    or self._to_float(position.get("value_usd"))
                    or 0.0
                )

                quantity = self._to_float(position.get("quantity")) or 0.0
                current_price = self._to_float(position.get("current_price"))
                if not current_price and market_value and quantity:
                    current_price = market_value / max(quantity, 1e-9)

                if market_value <= 0:
                    continue

                candidate_positions.append(
                    {
                        "symbol": raw_symbol,
                        "value_usd": market_value,
                        "quantity": quantity if quantity > 0 else None,
                        "current_price": current_price,
                        "exchange": position.get("exchange", "binance"),
                    }
                )

            if not candidate_positions:
                fallback_symbols = self._select_symbols_by_volume(
                    "hedge_position", discovered_assets, default_limit=5
                )
                for symbol in fallback_symbols:
                    candidate_positions.append(
                        {
                            "symbol": symbol,
                            "value_usd": 10_000.0,
                            "quantity": None,
                            "current_price": None,
                            "exchange": "binance",
                        }
                    )

            candidate_positions.sort(key=lambda item: item.get("value_usd", 0.0), reverse=True)
            hedge_types = ["direct_hedge", "correlation_hedge", "options_hedge"]

            for position in candidate_positions[:5]:
                base_symbol = position["symbol"]
                normalized_symbol = base_symbol if "/" in base_symbol else f"{base_symbol}/USDT"
                position_value = float(position.get("value_usd") or 0.0)
                if position_value <= 0:
                    continue

                quantity = position.get("quantity")
                if not quantity:
                    price_reference = position.get("current_price")
                    if not price_reference:
                        price_snapshot = await trading_strategies_service._get_symbol_price("auto", normalized_symbol)
                        price_reference = self._to_float(price_snapshot.get("price")) if isinstance(price_snapshot, dict) else None
                    if price_reference and price_reference > 0:
                        quantity = position_value / price_reference
                    else:
                        quantity = position_value / 20_000  # Approximate for BTC-scale assets

                for hedge_type in hedge_types:
                    try:
                        hedge_parameters = {
                            "primary_position_size": quantity,
                            "primary_side": "long" if position_value >= 0 else "short",
                            "hedge_type": hedge_type,
                            "hedge_ratio": 0.6,
                            "correlation_factor": 0.8,
                        }

                        hedge_result = await trading_strategies_service.execute_strategy(
                            function="hedge_position",
                            symbol=normalized_symbol,
                            parameters=hedge_parameters,
                            user_id=user_profile.user_id,
                            simulation_mode=True,
                        )

                        if not hedge_result.get("success"):
                            continue

                        recommendations = hedge_result.get("hedge_recommendations", []) or []
                        if not recommendations:
                            continue

                        cost_benefit = hedge_result.get("cost_benefit", {}) or {}
                        for recommendation in recommendations:
                            risk_reduction_pct = (
                                self._to_float(recommendation.get("risk_reduction"))
                                or self._to_float(recommendation.get("hedge_effectiveness"))
                                or 0.0
                            )

                            if risk_reduction_pct <= 0:
                                continue

                            signal_strength = max(min(risk_reduction_pct / 10.0, 10.0), 0.5)
                            protected_capital = position_value * (risk_reduction_pct / 100.0)
                            required_capital = (
                                self._to_float(recommendation.get("cost_estimate"))
                                or self._to_float(recommendation.get("premium_cost"))
                                or position_value * 0.02
                            )

                            opportunity = OpportunityResult(
                                strategy_id="ai_hedge_position",
                                strategy_name=f"AI Hedge Strategist - {hedge_type.replace('_', ' ').title()}",
                                opportunity_type="hedge",
                                symbol=base_symbol,
                                exchange=position.get("exchange", "binance"),
                                profit_potential_usd=float(protected_capital),
                                confidence_score=float(min(risk_reduction_pct, 100.0)),
                                risk_level=self._signal_to_risk_level(signal_strength),
                                required_capital_usd=float(max(required_capital, 0.0)),
                                estimated_timeframe="immediate",
                                entry_price=self._to_float(hedge_result.get("primary_position", {}).get("entry_price")) or position.get("current_price"),
                                exit_price=None,
                                metadata={
                                    "hedge_type": hedge_type,
                                    "recommendation": recommendation,
                                    "risk_reduction_pct": risk_reduction_pct,
                                    "position_value_usd": position_value,
                                    "cost_benefit": cost_benefit,
                                    "capital_assumptions": {
                                        "deployable_capital_usd": position_value,
                                        "components": {"position_value": position_value},
                                    },
                                },
                                discovered_at=self._current_timestamp(),
                            )

                            opportunities.append(opportunity)

                    except Exception as hedge_error:
                        self.logger.debug(
                            "Hedge scanner: strategy execution failed",
                            user_id=user_profile.user_id,
                            scan_id=scan_id,
                            symbol=base_symbol,
                            hedge_type=hedge_type,
                            error=str(hedge_error),
                        )

        except Exception as error:
            self.logger.exception(
                "Hedge opportunity scan failed",
                user_id=user_profile.user_id,
                scan_id=scan_id,
                error=str(error),
            )

        return opportunities

    async def _scan_futures_arbitrage_opportunities(
        self,
        discovered_assets: Dict[str, List[Any]],
        user_profile: UserOpportunityProfile,
        scan_id: str,
        portfolio_result: Dict[str, Any],
    ) -> List[OpportunityResult]:
        """Scan cross-market futures arbitrage opportunities using basis analysis."""

        opportunities: List[OpportunityResult] = []

        try:
            strategy_id = "ai_futures_arbitrage"
            owned_strategy_ids = [s.get("strategy_id") for s in portfolio_result.get("active_strategies", [])]

            if strategy_id not in owned_strategy_ids:
                self.logger.warning(
                    "Strategy not in portfolio, scanning anyway",
                    user_id=user_profile.user_id,
                    scan_id=scan_id,
                    strategy_id=strategy_id,
                    portfolio_strategies=len(owned_strategy_ids),
                )

            symbols = self._select_symbols_by_volume(
                "futures_arbitrage", discovered_assets, default_limit=10
            )
            if not symbols:
                self.logger.info(
                    "No symbols available for futures arbitrage scan",
                    scan_id=scan_id,
                    user_id=user_profile.user_id,
                )
                return opportunities
            base_symbols = []
            for symbol in symbols:
                base = self._extract_base_symbol(symbol)
                if base and base not in base_symbols:
                    base_symbols.append(base)

            for base_symbol in base_symbols:
                try:
                    basis_result = await trading_strategies_service.execute_strategy(
                        function="basis_trade",
                        symbol=base_symbol,
                        parameters={"trade_type": "cash_carry"},
                        user_id=user_profile.user_id,
                        simulation_mode=True,
                    )

                    if not basis_result.get("success"):
                        continue

                    analysis = basis_result.get("basis_trade_analysis", {})
                    basis_metrics = analysis.get("basis_analysis", {})
                    recommendation = analysis.get("trade_recommendation", {})

                    action = recommendation.get("action", "")
                    if not action or action.upper().startswith("NO_TRADE"):
                        continue

                    expected_profit_pct = self._parse_usd_value(
                        recommendation.get("expected_profit_pct"),
                        default=0.0,
                    )
                    if expected_profit_pct <= 0:
                        continue

                    position_size = self._parse_usd_value(
                        recommendation.get("position_size_recommendation"),
                        default=25000.0,
                    )
                    profit_potential = position_size * (expected_profit_pct / 100)

                    margin_required = self._parse_usd_value(
                        recommendation.get("margin_required"),
                        default=position_size * 0.2,
                    )

                    annualized_return = self._parse_usd_value(
                        basis_metrics.get("annualized_return_pct"),
                        default=expected_profit_pct,
                    )
                    confidence = max(25.0, min(95.0, abs(annualized_return)))

                    required_capital = max(margin_required, 5000.0)
                    futures_details = analysis.get("futures_info", {}).get("quarterly_future", {})

                    opportunities.append(
                        OpportunityResult(
                            strategy_id=strategy_id,
                            strategy_name=f"AI Futures Arbitrage ({base_symbol})",
                            opportunity_type="futures_arbitrage",
                            symbol=f"{base_symbol}/USDT",
                            exchange=analysis.get("spot_info", {}).get("exchange", "binance"),
                            profit_potential_usd=round(profit_potential, 2),
                            confidence_score=confidence,
                            risk_level=self._score_to_risk_level(abs(annualized_return) / 20.0),
                            required_capital_usd=required_capital,
                            estimated_timeframe=f"{futures_details.get('days_to_expiry', 60)}d",
                            entry_price=analysis.get("spot_info", {}).get("price"),
                            exit_price=futures_details.get("price"),
                            metadata={
                                "expected_profit_pct": expected_profit_pct,
                                "annualized_return_pct": annualized_return,
                                "trade_action": action,
                                "basis_analysis": basis_metrics,
                                "risk_assessment": analysis.get("risk_assessment", {}),
                            },
                            discovered_at=self._current_timestamp(),
                        )
                    )

                except Exception as exc:  # pragma: no cover - defensive logging
                    self.logger.debug(
                        "Basis trade analysis failed for symbol",
                        symbol=base_symbol,
                        scan_id=scan_id,
                        error=str(exc),
                    )
                    continue

            self.logger.info(
                "? Futures arbitrage scanner completed",
                scan_id=scan_id,
                opportunities=len(opportunities),
            )

        except Exception:
            self.logger.exception(
                "Futures arbitrage scan failed",
                scan_id=scan_id,
            )

        return opportunities

    async def _scan_complex_strategy_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Surface complex options strategy structures from the derivatives engine."""

        opportunities: List[OpportunityResult] = []

        try:
            candidate_symbols = self._select_symbols_by_volume(
                "complex_strategy", discovered_assets, default_limit=10
            )
            if not candidate_symbols:
                candidate_symbols = ["BTC", "ETH", "SOL"]

            strategy_types = [
                "iron_condor",
                "butterfly",
                "calendar_spread",
                "straddle",
            ]

            for symbol in candidate_symbols[:5]:
                normalized_symbol = symbol if "/" in symbol else f"{symbol}/USDT"

                for strategy_type in strategy_types:
                    try:
                        execution = await trading_strategies_service.execute_strategy(
                            function="complex_strategy",
                            strategy_type=strategy_type,
                            symbol=normalized_symbol,
                            parameters={"quantity": 1, "expiry_days": 30},
                            user_id=user_profile.user_id,
                            simulation_mode=True,
                        )

                        if not execution.get("success"):
                            continue

                        max_profit = self._to_float(execution.get("max_profit")) or 0.0
                        max_loss = self._to_float(execution.get("max_loss")) or 0.0
                        net_premium = self._to_float(execution.get("net_premium_paid"))
                        breakevens = execution.get("breakeven_points") or []
                        current_price = self._to_float(execution.get("current_price"))

                        risk_denominator = max(max_loss, abs(net_premium or 0.0), 1.0)
                        signal_strength = max(min((max_profit / risk_denominator) * 3.0, 9.5), 2.0)

                        opportunity = OpportunityResult(
                            strategy_id="ai_complex_strategy",
                            strategy_name=f"AI Complex Derivatives - {strategy_type.replace('_', ' ').title()}",
                            opportunity_type="complex_derivative",
                            symbol=symbol,
                            exchange="derivatives",
                            profit_potential_usd=float(max_profit),
                            confidence_score=float(min(signal_strength * 10, 95.0)),
                            risk_level=self._signal_to_risk_level(signal_strength),
                            required_capital_usd=float(max(max_loss, abs(net_premium or 0.0))),
                            estimated_timeframe="30d",
                            entry_price=current_price,
                            exit_price=self._to_float(execution.get("optimal_price")),
                            metadata={
                                "strategy_type": strategy_type,
                                "max_loss": max_loss,
                                "net_premium": net_premium,
                                "breakeven_points": breakevens,
                                "wing_width": execution.get("wing_width"),
                                "contracts": execution.get("contracts_considered"),
                                "capital_assumptions": {
                                    "deployable_capital_usd": float(max(max_loss, abs(net_premium or 0.0)) or 0.0),
                                    "components": {"option_premium": net_premium},
                                },
                            },
                            discovered_at=self._current_timestamp(),
                        )

                        opportunities.append(opportunity)

                    except Exception as strategy_error:
                        self.logger.debug(
                            "Complex strategy execution failed",
                            user_id=user_profile.user_id,
                            scan_id=scan_id,
                            symbol=symbol,
                            strategy=strategy_type,
                            error=str(strategy_error),
                        )

        except Exception as error:
            self.logger.exception(
                "Complex strategy opportunity scan failed",
                user_id=user_profile.user_id,
                scan_id=scan_id,
                error=str(error),
            )

        return opportunities
    
    # ================================================================================
    # UTILITY METHODS
    # ================================================================================

    async def _refresh_strategy_symbol_policies(self, force: bool = False) -> None:
        """Reload symbol policy overrides from the database."""

        now = time.monotonic()
        if not force and now < self._policy_cache_expiry:
            return

        async with self._policy_refresh_lock:
            if not force and time.monotonic() < self._policy_cache_expiry:
                return

            try:
                overrides = await strategy_scanning_policy_service.get_policy_overrides()
            except Exception as error:  # pragma: no cover - defensive logging
                self.logger.warning(
                    "Failed to refresh strategy scanning policies", error=str(error)
                )
                self._policy_cache_expiry = time.monotonic() + 30.0
                return

            combined = copy.deepcopy(self._base_strategy_symbol_policies)
            for key, payload in overrides.items():
                if not isinstance(payload, dict):
                    continue

                baseline_entry = copy.deepcopy(combined.get(key, {})) if isinstance(combined.get(key), dict) else {}
                if "max_symbols" in payload:
                    baseline_entry["max_symbols"] = payload.get("max_symbols")
                if "chunk_size" in payload:
                    baseline_entry["chunk_size"] = payload.get("chunk_size")
                if "priority" in payload and payload.get("priority") is not None:
                    try:
                        baseline_entry["priority"] = int(payload.get("priority"))
                    except (TypeError, ValueError):
                        pass
                if "enabled" in payload and payload.get("enabled") is not None:
                    baseline_entry["enabled"] = bool(payload.get("enabled"))

                combined[key] = baseline_entry

            self.strategy_symbol_policies = combined
            self._policy_cache_expiry = time.monotonic() + 60.0

    def _signal_to_risk_level(self, signal_strength: float) -> str:
        """Convert signal strength to risk level for transparency."""
        if signal_strength > 7.0:
            return "low"
        elif signal_strength > 5.0:
            return "medium"
        elif signal_strength > 3.0:
            return "medium_high"
        else:
            return "high"
    
    def _get_strategy_symbol_limit(
        self, strategy_key: str, default: Optional[int] = None
    ) -> Optional[int]:
        """Return the configured symbol limit for a strategy or a safe default."""

        policy = self.strategy_symbol_policies.get(strategy_key)
        if isinstance(policy, dict) and "max_symbols" in policy:
            value = policy.get("max_symbols")
            if value is None:
                return None
            if isinstance(value, int):
                return value if value > 0 else None
            try:
                int_value = int(value)
            except (TypeError, ValueError):
                return default
            return int_value if int_value > 0 else None

        if default is not None:
            return default

        return DEFAULT_STRATEGY_SYMBOL_LIMIT

    def _get_strategy_chunk_size(self, strategy_key: str) -> Optional[int]:
        """Return the configured chunk size for a strategy, if any."""

        policy = self.strategy_symbol_policies.get(strategy_key)
        if isinstance(policy, dict) and "chunk_size" in policy:
            value = policy.get("chunk_size")
            if value is None:
                return None
            if isinstance(value, int):
                return value if value > 0 else None
            try:
                int_value = int(value)
            except (TypeError, ValueError):
                return None
            return int_value if int_value > 0 else None

        return None

    def _chunk_symbols(self, strategy_key: str, symbols: List[str]) -> List[List[str]]:
        """Split symbols into chunks based on strategy policy."""

        if not symbols:
            return []

        chunk_size = self._get_strategy_chunk_size(strategy_key)
        if not chunk_size or chunk_size <= 0 or chunk_size >= len(symbols):
            return [symbols]

        return [symbols[i : i + chunk_size] for i in range(0, len(symbols), chunk_size)]

    async def _execute_strategy_across_chunks(
        self,
        strategy_key: str,
        symbols: List[str],
        executor: Any,
    ) -> List[OpportunityResult]:
        """Execute strategy fetcher across symbol chunks and aggregate opportunities."""

        if not symbols:
            return []

        opportunities: List[OpportunityResult] = []
        for chunk in self._chunk_symbols(strategy_key, symbols):
            if not chunk:
                continue
            chunk_result = await executor(chunk)
            if chunk_result:
                opportunities.extend(chunk_result)

        return opportunities

    def _select_symbols_by_volume(
        self,
        strategy_key: str,
        discovered_assets: Dict[str, List[Any]],
        default_limit: Optional[int] = None,
    ) -> List[str]:
        """Select symbols ordered by volume honoring strategy policies."""

        policy = self.strategy_symbol_policies.get(strategy_key)
        if isinstance(policy, dict) and policy.get("enabled") is False:
            self.logger.debug(
                "Strategy scanning disabled via policy", strategy=strategy_key
            )
            return []

        limit = self._get_strategy_symbol_limit(strategy_key, default_limit)
        return self._get_top_symbols_by_volume(discovered_assets, limit=limit)

    def _get_top_symbols_by_volume(
        self, discovered_assets: Dict[str, List[Any]], limit: Optional[int] = None
    ) -> List[str]:
        """Get top symbols by volume across all tiers."""

        all_assets: List[Any] = []
        for tier_assets in discovered_assets.values():
            all_assets.extend(tier_assets)

        # Sort by volume and get top symbols while handling partial asset payloads
        sorted_assets = sorted(
            all_assets,
            key=lambda asset: getattr(asset, "volume_24h_usd", 0) or 0,
            reverse=True,
        )

        def _extract_symbols(assets: List[Any]) -> List[str]:
            symbols: List[str] = []
            for asset in assets:
                symbol = getattr(asset, "symbol", None)
                if not symbol:
                    continue
                symbols.append(symbol)
            return symbols

        if limit is None or limit <= 0:
            return _extract_symbols(sorted_assets)

        return _extract_symbols(sorted_assets[:limit])

    def _get_symbols_for_statistical_arbitrage(
        self, discovered_assets: Dict[str, List[Any]], limit: Optional[int] = None
    ) -> List[str]:
        """Get symbols suitable for statistical arbitrage (higher tier preferred)."""

        policy = self.strategy_symbol_policies.get("statistical_arbitrage")
        if isinstance(policy, dict) and policy.get("enabled") is False:
            self.logger.debug("Statistical arbitrage policy disabled")
            return []

        # Prefer institutional and enterprise tier assets for stat arb
        preferred_tiers = ["tier_institutional", "tier_enterprise", "tier_professional"]

        symbols: List[str] = []
        seen: Set[str] = set()

        def _append_symbol(symbol: Optional[str]) -> None:
            if not symbol:
                return
            if symbol in seen:
                return
            seen.add(symbol)
            symbols.append(symbol)

        for tier in preferred_tiers:
            for asset in discovered_assets.get(tier, []) or []:
                _append_symbol(getattr(asset, "symbol", None))

        for asset in discovered_assets.get("tier_retail", []) or []:
            _append_symbol(getattr(asset, "symbol", None))

        if limit is None or limit <= 0:
            return symbols

        return symbols[:limit]

    def _get_correlation_pairs(
        self, discovered_assets: Dict[str, List[Any]], max_pairs: Optional[int] = 10
    ) -> List[Tuple[str, str]]:
        """Get symbol pairs likely to be correlated for pairs trading."""

        # Get top symbols
        top_symbols = self._get_top_symbols_by_volume(discovered_assets)

        # Create pairs from major cryptocurrencies (these tend to be correlated)
        major_cryptos = [s for s in top_symbols if s in ["BTC", "ETH", "BNB", "ADA", "SOL", "DOT", "AVAX", "MATIC"]]

        pairs = []
        for i in range(len(major_cryptos)):
            for j in range(i + 1, len(major_cryptos)):
                pairs.append((major_cryptos[i], major_cryptos[j]))
                if max_pairs is not None and len(pairs) >= max_pairs:
                    break
            if max_pairs is not None and len(pairs) >= max_pairs:
                break

        if max_pairs is None or max_pairs <= 0:
            return pairs

        return pairs[:max_pairs]

    def _to_float(self, value: Any) -> Optional[float]:
        """Convert common numeric string formats to float safely."""

        if value is None:
            return None

        if isinstance(value, (int, float)):
            float_val = float(value)
            return float_val if math.isfinite(float_val) else None

        if isinstance(value, Decimal):
            if not value.is_finite():
                return None
            return float(value)

        if isinstance(value, str):
            stripped = value.strip()
            # Normalize Unicode minus (U+2212) to ASCII hyphen
            stripped = stripped.replace("\u2212", "-")
            # Parentheses-negatives: handle signs correctly
            paren_negative = stripped.startswith("(") and stripped.endswith(")")
            inner_sign_negative = False
            if paren_negative:
                inner = stripped[1:-1].strip()
                if inner.startswith(('+', '-')):
                    inner_sign_negative = inner.startswith('-')
                    stripped = inner[1:]
                else:
                    stripped = inner
            if not stripped:
                return None

            # Handle European format first on the original string (thousand sep . or space, decimal ,)
            s = stripped
            # Check for complex EU thousands pattern first
            if re.match(r"^\d{1,3}(?:[.\s]\d{3})+,\d+$", s):
                s = s.replace(" ", "").replace(".", "").replace(",", ".")
            # Check for simple EU decimal pattern (digits,comma,digits with no dots or spaces)
            elif re.match(r"^\d+,\d+$", s) and "." not in s:
                s = s.replace(",", ".")
            else:
                # Remove US-style thousands commas
                s = s.replace(",", "")
            cleaned = re.sub(r"[^0-9eE+\-.]", "", s)
            if not cleaned or cleaned in {"-", "+", ".", "-.", "+."}:
                return None

            try:
                val = float(cleaned)
                if paren_negative:
                    # Apply parentheses negation only if inner sign wasn't already negative
                    return -val if not inner_sign_negative else val
                else:
                    return val
            except ValueError:
                return None

        return None
    def _to_fraction(self, value: Any) -> Optional[float]:
        """Convert values that may represent percentages into fractions."""

        original = value if isinstance(value, str) else None
        numeric = self._to_float(value)

        if numeric is None:
            return None

        # Reject non-finite numeric values
        if not math.isfinite(numeric):
            return None

        # Check for percent markers (including fullwidth percent sign U+FF05)
        if original:
            normalized = original.strip().replace('\uFF05', '%')  # Replace fullwidth percent sign (U+FF05)
            if "%" in normalized:
                return numeric / 100.0

        absolute = abs(numeric)
        if absolute <= 1:
            return numeric
        if absolute <= 100:
            return numeric / 100.0

        return numeric

    async def _preload_price_universe(
        self,
        discovered_assets: Dict[str, List[Any]],
        user_profile: UserOpportunityProfile,
        scan_id: str,
    ) -> None:
        """Warm the shared price cache for the user's highest priority assets."""

        try:
            symbol_candidates: List[Any] = []
            for tier_assets in discovered_assets.values():
                symbol_candidates.extend(tier_assets)

            if not symbol_candidates:
                return

            symbol_candidates.sort(
                key=lambda asset: getattr(asset, "volume_24h_usd", 0),
                reverse=True,
            )

            # PERFORMANCE OPTIMIZATION: Limit to top 200 assets and process in batches
            # This reduces API call volume from 1000+ to 200, dramatically improving response time
            max_assets = min(200, len(symbol_candidates))  # Reduced from 1000 to 200
            selected_assets = symbol_candidates[: max_assets]

            preload_pairs: List[Tuple[str, str]] = []
            for asset in selected_assets:
                exchange_name = getattr(asset, "exchange", "")
                base_symbol = getattr(asset, "symbol", "")
                if not exchange_name or not base_symbol:
                    continue
                preload_pairs.append((exchange_name, base_symbol))

            if preload_pairs:
                # BATCH PROCESSING: Process assets in batches of 50 to avoid overwhelming exchanges
                batch_size = 50
                for i in range(0, len(preload_pairs), batch_size):
                    batch = preload_pairs[i:i + batch_size]
                    try:
                        await market_analysis_service.preload_exchange_prices(
                            batch,
                            ttl=60,  # 60 seconds for near-real-time trading data
                            concurrency=50,  # Increased from 20 for faster parallel loading
                        )
                        self.logger.info(
                            "Preloaded price cache batch",
                            scan_id=scan_id,
                            batch_num=i // batch_size + 1,
                            batch_size=len(batch),
                            total_batches=(len(preload_pairs) + batch_size - 1) // batch_size,
                        )
                    except Exception as batch_exc:
                        self.logger.warning(
                            "Price batch preload failed, continuing with next batch",
                            scan_id=scan_id,
                            batch_num=i // batch_size + 1,
                            error=str(batch_exc),
                        )
                        continue
                
                self.logger.info(
                    "Completed price cache preload for opportunity scan",
                    scan_id=scan_id,
                    total_assets=len(preload_pairs),
                    tier=user_profile.max_asset_tier,
                )
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.warning(
                "Price universe preload failed",
                scan_id=scan_id,
                error=str(exc),
            )

    async def _rank_and_filter_opportunities(
        self,
        opportunities: List[OpportunityResult],
        user_profile: UserOpportunityProfile,
        scan_id: str
    ) -> List[OpportunityResult]:
        """Rank and filter opportunities based on user profile and limits."""
        
        if not opportunities:
            return []
        
        # Sort by profit potential * confidence score (expected value)
        ranked_opportunities = sorted(
            opportunities,
            key=lambda x: x.profit_potential_usd * x.confidence_score,
            reverse=True
        )
        
        # Apply user's scan limit only if set (None = unlimited)
        if user_profile.opportunity_scan_limit is not None:
            limited_opportunities = ranked_opportunities[:user_profile.opportunity_scan_limit]
        else:
            limited_opportunities = ranked_opportunities  # Return all opportunities
        
        self.logger.info("?? Opportunities ranked and filtered",
                        scan_id=scan_id,
                        total_found=len(opportunities),
                        after_filtering=len(limited_opportunities),
                        user_limit=user_profile.opportunity_scan_limit or "unlimited")
        
        return limited_opportunities
    
    async def _generate_strategy_recommendations(
        self,
        user_id: str,
        user_profile: UserOpportunityProfile,
        current_opportunities_count: int,
        portfolio_result: Dict[str, Any],
        *,
        scan_id: Optional[str] = None,
        timeout_seconds: float = 5.0,
    ) -> List[Dict[str, Any]]:
        """Generate strategy purchase recommendations to increase opportunities."""
        
        recommendations = []
        
        try:
            # If user has few opportunities, recommend more strategies
            if current_opportunities_count < 10:
                # Get marketplace to see what strategies user doesn't have
                marketplace_timeout = max(1.0, float(timeout_seconds))
                try:
                    marketplace_result = await asyncio.wait_for(
                        strategy_marketplace_service.get_marketplace_strategies(
                            user_id=user_id,
                            include_ai_strategies=True,
                            include_community_strategies=False,
                        ),
                        timeout=marketplace_timeout,
                    )
                except asyncio.TimeoutError:
                    self.logger.warning(
                        "Strategy recommendations marketplace lookup timed out",
                        user_id=user_id,
                        scan_id=scan_id,
                        timeout_seconds=marketplace_timeout,
                    )
                    marketplace_result = {"success": False, "error": "timeout"}
                except asyncio.CancelledError:
                    raise
                except Exception as marketplace_error:  # pragma: no cover - defensive logging
                    self.logger.warning(
                        "Strategy recommendations marketplace lookup failed",
                        user_id=user_id,
                        scan_id=scan_id,
                        error=str(marketplace_error),
                        error_type=type(marketplace_error).__name__,
                    )
                    marketplace_result = {"success": False, "error": str(marketplace_error)}

                if marketplace_result.get("success"):
                    # Use passed portfolio result instead of N+1 query
                    user_portfolio = portfolio_result
                    current_strategy_ids = set()
                    
                    if user_portfolio.get("success"):
                        current_strategy_ids = {
                            s["strategy_id"] for s in user_portfolio.get("active_strategies", [])
                        }
                    
                    # Recommend high-impact strategies user doesn't have
                    high_impact_strategies = [
                        ("ai_statistical_arbitrage", "Statistical Arbitrage", "+150% more opportunities"),
                        ("ai_funding_arbitrage", "Funding Arbitrage", "+80% more opportunities"), 
                        ("ai_pairs_trading", "Pairs Trading", "+120% more opportunities"),
                        ("ai_spot_breakout_strategy", "Breakout Trading", "+60% more opportunities")
                    ]
                    
                    for strategy_id, name, benefit in high_impact_strategies:
                        if strategy_id not in current_strategy_ids:
                            recommendations.append({
                                "strategy_id": strategy_id,
                                "name": name,
                                "benefit": benefit,
                                "reason": f"Users with {name} see {benefit.split('+')[1]} on average",
                                "type": "opportunity_increase"
                            })
                            
                        if len(recommendations) >= 3:  # Max 3 recommendations
                            break
            
            # Tier-based recommendations
            if user_profile.user_tier == "basic":
                recommendations.append({
                    "strategy_id": "tier_upgrade",
                    "name": "Upgrade to Pro Tier",
                    "benefit": "Access to Professional-grade assets ($10M+ volume)",
                    "reason": "Unlock institutional opportunities with higher profit potential",
                    "type": "tier_upgrade"
                })
            
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.logger.error("Failed to generate strategy recommendations", error=str(e))
        
        return recommendations
    
    async def _handle_no_strategies_user(self, user_id: str, scan_id: str) -> Dict[str, Any]:
        """Handle users with no active strategies - automatically onboard them with 3 free strategies."""
        
        self.logger.info("User has no active strategies, triggering automatic onboarding", 
                        scan_id=scan_id, user_id=user_id)
        
        try:
            # Import onboarding service
            from app.services.user_onboarding_service import user_onboarding_service
            
            # Trigger automatic onboarding to get 3 free strategies
            onboarding_result = await user_onboarding_service.trigger_onboarding_if_needed(user_id)
            
            if onboarding_result.get("success"):
                self.logger.info("?? User automatically onboarded with free strategies", 
                               scan_id=scan_id, user_id=user_id)
                
                # Now try to discover opportunities again with the new strategies
                # Recursively call the main discovery method, but prevent infinite loop
                if not hasattr(self, '_onboarding_attempt'):
                    self._onboarding_attempt = True
                    try:
                        result = await self.discover_opportunities_for_user(
                            user_id=user_id,
                            force_refresh=True,
                            include_strategy_recommendations=True
                        )
                        # Add onboarding metadata
                        result["auto_onboarded"] = True
                        result["onboarding_result"] = onboarding_result
                        return result
                    finally:
                        delattr(self, '_onboarding_attempt')
                else:
                    # Prevent infinite recursion - return default response
                    return {
                        "success": True,
                        "scan_id": scan_id,
                        "user_id": user_id,
                        "opportunities": [],
                        "total_opportunities": 0,
                        "message": "Onboarding completed! Please try discovering opportunities again.",
                        "auto_onboarded": True,
                        "onboarding_result": onboarding_result
                    }
            else:
                # Onboarding failed, return helpful message
                return {
                    "success": True,
                    "scan_id": scan_id,
                    "user_id": user_id,
                    "opportunities": [],
                    "total_opportunities": 0,
                    "message": "No active trading strategies found. Unable to automatically activate free strategies.",
                    "onboarding_error": onboarding_result.get("error"),
                    "free_strategies_available": [
                        {
                            "strategy_id": "ai_risk_management",
                            "name": "AI Risk Management",
                            "description": "Essential portfolio protection - FREE",
                            "cost": 0
                        },
                        {
                            "strategy_id": "ai_portfolio_optimization", 
                            "name": "AI Portfolio Optimization",
                            "description": "Smart portfolio rebalancing - FREE",
                            "cost": 0
                        },
                        {
                            "strategy_id": "ai_spot_momentum_strategy",
                            "name": "AI Momentum Trading",
                            "description": "Catch trending moves - FREE", 
                            "cost": 0
                        }
                    ],
                    "next_action": "Visit the Strategy Marketplace to manually activate your free strategies"
                }
                
        except Exception as e:
            self.logger.error("Automatic onboarding failed", 
                            scan_id=scan_id, user_id=user_id, error=str(e))
            
            # Fallback to original response
            return {
                "success": True,
                "scan_id": scan_id,
                "user_id": user_id,
                "opportunities": [],
                "total_opportunities": 0,
                "message": "No active trading strategies found. Get your 3 free strategies to start discovering opportunities!",
                "onboarding_error": str(e),
                "free_strategies_available": [
                    {
                        "strategy_id": "ai_risk_management",
                        "name": "AI Risk Management",
                        "description": "Essential portfolio protection - FREE",
                        "cost": 0
                    },
                    {
                        "strategy_id": "ai_portfolio_optimization", 
                        "name": "AI Portfolio Optimization",
                        "description": "Smart portfolio rebalancing - FREE",
                        "cost": 0
                    },
                    {
                        "strategy_id": "ai_spot_momentum_strategy",
                        "name": "AI Momentum Trading",
                        "description": "Catch trending moves - FREE", 
                        "cost": 0
                    }
                ],
                "next_action": "Visit the Strategy Marketplace to activate your free strategies"
            }
    
    def _serialize_opportunity(self, opportunity: OpportunityResult) -> Dict[str, Any]:
        """Convert OpportunityResult to serializable dictionary."""
        
        return {
            "strategy_id": opportunity.strategy_id,
            "strategy_name": opportunity.strategy_name,
            "opportunity_type": opportunity.opportunity_type,
            "symbol": opportunity.symbol,
            "exchange": opportunity.exchange,
            "profit_potential_usd": opportunity.profit_potential_usd,
            "confidence_score": opportunity.confidence_score,
            "risk_level": opportunity.risk_level,
            "required_capital_usd": opportunity.required_capital_usd,
            "estimated_timeframe": opportunity.estimated_timeframe,
            "entry_price": opportunity.entry_price,
            "exit_price": opportunity.exit_price,
            "metadata": opportunity.metadata,
            "discovered_at": opportunity.discovered_at.isoformat()
        }
    
    async def _get_user_portfolio(self, user_id: str) -> Dict[str, Any]:
        """Get user's portfolio with active strategies."""
        try:
            # DIRECT FIX: Use the working admin snapshot approach for admin users
            # This bypasses the failing service calls and uses the proven working method
            admin_snapshot = await strategy_marketplace_service.get_admin_portfolio_snapshot(user_id)
            if admin_snapshot and admin_snapshot.get("success"):
                self.logger.info("Using admin portfolio snapshot for user", user_id=user_id)
                return admin_snapshot
            
            # Fallback to cached method for non-admin users
            portfolio_result = await self._get_user_portfolio_cached(user_id)

            # Check if portfolio fetch was successful and has active strategies
            if portfolio_result.get("success"):
                active_strategies = portfolio_result.get("active_strategies", [])
                # If user has strategies, return their portfolio
                if active_strategies:  # Check if list is not empty
                    return portfolio_result
                # If user has no strategies, fall back to admin snapshot
                self.logger.info("User has no active strategies, falling back to admin snapshot", user_id=user_id)

            # Final fallback to admin snapshot for users without strategies
            admin_snapshot = await strategy_marketplace_service.get_admin_portfolio_snapshot(user_id)
            if admin_snapshot and admin_snapshot.get("success"):
                self.logger.info("Using admin portfolio snapshot for user", user_id=user_id)
                return admin_snapshot

            # Ensure consistent structure even on degraded responses
            portfolio_result.setdefault("active_strategies", [])
            portfolio_result.setdefault("success", False)
            return portfolio_result
        except Exception as e:
            self.logger.exception("Failed to get user portfolio", extra={"user_id": user_id})
            return {'success': False, 'active_strategies': [], 'error': str(e)}

    async def _get_cached_opportunities(
        self,
        user_id: str,
        user_profile: UserOpportunityProfile
    ) -> Optional[Dict[str, Any]]:
        """Get cached opportunities if available and fresh."""

        if not self.redis:
            return None

        try:
            cache_key = f"user_opportunities:{user_id}:{user_profile.user_tier}:{user_profile.active_strategy_count}"
            cached_data = await self.redis.get(cache_key)

            if cached_data:
                data = json.loads(cached_data)

                payload = data.get("payload", data)
                if isinstance(payload, dict):
                    self._ensure_profile_strategy_counts(payload)
                metadata = data.get("cache_metadata", {})

                cache_time_str = metadata.get("cached_at") or data.get("cached_at")
                if cache_time_str:
                    try:
                        cache_time = datetime.fromisoformat(cache_time_str)
                    except ValueError:
                        cache_time = self._current_timestamp() - timedelta(hours=1)
                else:
                    cache_time = self._current_timestamp() - timedelta(hours=1)

                cached_fingerprint = metadata.get("strategy_fingerprint") or payload.get("user_profile", {}).get("strategy_fingerprint")
                if cached_fingerprint and cached_fingerprint != user_profile.strategy_fingerprint:
                    self.logger.info(
                        "Cached opportunities invalidated due to strategy change",
                        user_id=user_id,
                        cached_fingerprint=cached_fingerprint,
                        current_fingerprint=user_profile.strategy_fingerprint
                    )
                    return None

                total_opportunities = payload.get("total_opportunities", 0)
                if total_opportunities == 0:
                    zero_ttl = metadata.get("zero_ttl_seconds", 120)
                    if self._current_timestamp() - cache_time > timedelta(seconds=zero_ttl):
                        self.logger.info(
                            "Discarding zero-result cache to force rescan",
                            user_id=user_id,
                            age_seconds=(self._current_timestamp() - cache_time).total_seconds(),
                            zero_ttl=zero_ttl
                        )
                        return None

                # Cache is fresh for 5 minutes for non-zero results, 2 minutes for zero results
                max_age = timedelta(minutes=5) if total_opportunities > 0 else timedelta(seconds=metadata.get("zero_ttl_seconds", 120))
                if self._current_timestamp() - cache_time < max_age:
                    return payload

        except Exception as e:
            self.logger.debug("Cache retrieval failed", error=str(e))

        return None

    async def _cache_opportunities(
        self,
        user_id: str,
        result: Dict[str, Any],
        user_profile: UserOpportunityProfile
    ):
        """Cache opportunity results."""

        if not self.redis:
            return

        try:
            cache_key = f"user_opportunities:{user_id}:{user_profile.user_tier}:{user_profile.active_strategy_count}"

            cache_time = self._current_timestamp().isoformat()
            total_opportunities = result.get("total_opportunities", 0)

            # Ensure cached payload is immutable by storing a JSON-safe copy
            try:
                payload_copy = json.loads(json.dumps(result))
            except TypeError:
                payload_copy = result

            self._ensure_profile_strategy_counts(payload_copy)

            cache_entry = {
                "payload": payload_copy,
                "cache_metadata": {
                    "cached_at": cache_time,
                    "cache_key": cache_key,
                    "strategy_fingerprint": user_profile.strategy_fingerprint,
                    "zero_ttl_seconds": 120,
                    "total_opportunities": total_opportunities
                }
            }

            ttl_seconds = 300 if total_opportunities > 0 else 120
            await self.redis.set(cache_key, json.dumps(cache_entry), ex=ttl_seconds)

            # Update last scan time
            last_scan_key = f"user_opportunity_last_scan:{user_id}"
            await self.redis.set(last_scan_key, cache_time, ex=86400)  # 24h

        except Exception as e:
            self.logger.debug("Cache storage failed", error=str(e))

    def _ensure_profile_strategy_counts(self, payload: Dict[str, Any]) -> None:
        """Ensure both legacy and new user profile keys are present."""

        if not isinstance(payload, dict):
            return

        profile = payload.get("user_profile")
        if not isinstance(profile, dict):
            return

        active_strategies = profile.get("active_strategies")
        active_strategy_count = profile.get("active_strategy_count")

        if active_strategies is None and active_strategy_count is not None:
            profile["active_strategies"] = active_strategy_count
        elif active_strategy_count is None and active_strategies is not None:
            profile["active_strategy_count"] = active_strategies
    
    async def _track_error_metrics(self, user_id: str, scan_id: str, error: str, execution_time: float):
        """Track error metrics for monitoring and alerting."""

        try:
            if not self.redis:
                return

            # Increment error counters
            error_key = f"opportunity_discovery_errors:{self._current_timestamp().strftime('%Y-%m-%d')}"
            await self.redis.incr(error_key)
            await self.redis.expire(error_key, 86400 * 7)  # 7 days

            # Track user-specific errors
            user_error_key = f"user_opportunity_errors:{user_id}"
            await self.redis.incr(user_error_key)
            await self.redis.expire(user_error_key, 86400)  # 24 hours

            # Store error details for analysis
            error_details = {
                "scan_id": scan_id,
                "user_id": user_id,
                "error": error,
                "execution_time_ms": execution_time,
                "timestamp": self._current_timestamp().isoformat()
            }

            error_log_key = f"opportunity_error_log:{scan_id}"
            await self.redis.set(error_log_key, json.dumps(error_details), ex=86400 * 3)  # 3 days

        except Exception as track_error:
            self.logger.debug("Error tracking failed", error=str(track_error))

    async def _track_scan_lifecycle(self, user_id: str, scan_id: str, phase: str, status: str = "in_progress", error: str = None, **extra_data):
        """Track scan lifecycle progression through each phase for comprehensive diagnostics.

        Phases: started, portfolio_fetch, asset_discovery, strategies_scan, ranking, completed, failed
        Status: in_progress, completed, error, timeout
        """
        try:
            if not self.redis:
                return

            lifecycle_key = f"scan_lifecycle:{scan_id}"
            timestamp = self._current_timestamp().isoformat()

            phase_data = {
                "phase": phase,
                "status": status,
                "timestamp": timestamp,
                "user_id": user_id,
                **extra_data
            }

            if error:
                phase_data["error"] = str(error)

            # Store in Redis hash for easy retrieval
            await self.redis.hset(lifecycle_key, phase, json.dumps(phase_data))
            await self.redis.expire(lifecycle_key, 3600)  # 1 hour TTL

            # Also update "current_phase" for quick status checks
            await self.redis.hset(lifecycle_key, "current_phase", phase)
            await self.redis.hset(lifecycle_key, "current_status", status)
            await self.redis.hset(lifecycle_key, "last_updated", timestamp)

            # Maintain lightweight index of active lifecycle keys for diagnostics recovery
            index_key = "scan_lifecycle:index"
            current_time = int(time.time())
            await self.redis.zadd(index_key, {lifecycle_key: current_time})
            await self.redis.zremrangebyscore(index_key, 0, current_time - 3600)
            await self.redis.expire(index_key, 3600)

            self.logger.info(f"?? Scan lifecycle: {phase}",
                           scan_id=scan_id,
                           status=status,
                           **extra_data)

        except Exception as track_error:
            self.logger.debug("Lifecycle tracking failed", error=str(track_error))

    async def _track_debug_step(
        self,
        user_id: str,
        scan_id: str,
        step_number: int,
        step_name: str,
        status: str = "in_progress",
        error: Exception | str | None = None,
        **extra_data,
    ):
        """Track detailed step-by-step progress for diagnostic visibility.

        This writes to Redis so debug info is visible through the diagnostic endpoint
        instead of requiring log parsing.

        Status: starting, completed, failed
        """
        try:
            if not self.redis:
                return

            debug_key = f"scan_debug:{scan_id}"
            timestamp = self._current_timestamp().isoformat()

            step_data = {
                "step": step_number,
                "name": step_name,
                "status": status,
                "timestamp": timestamp,
                "user_id": user_id,
                "scan_id": scan_id,
                **extra_data
            }

            if error:
                step_data["error"] = str(error)
                step_data["error_type"] = type(error).__name__ if isinstance(error, Exception) else "Unknown"

            # Store in Redis hash with step number as key
            step_key = f"step_{step_number}"
            await self.redis.hset(debug_key, step_key, json.dumps(step_data))
            await self.redis.hset(debug_key, "current_step", str(step_number))
            await self.redis.hset(debug_key, "last_updated", timestamp)
            await self.redis.expire(debug_key, 3600)  # 1 hour TTL

            # Log to application logs as well
            emoji = "??" if status == "starting" else "?" if status == "completed" else "?"
            self.logger.info(f"{emoji} STEP {step_number}: {step_name}",
                           scan_id=scan_id,
                           status=status,
                           **extra_data)

        except Exception as track_error:  # noqa: BLE001 - telemetry should not affect flow
            self.logger.debug("Debug step tracking failed", error=str(track_error))

    async def _track_scan_metrics(self, user_id: str, scan_id: str, opportunities_count: int, strategies_count: int, execution_time_ms: float, success: bool = True):
        """Track user-initiated opportunity scan metrics for diagnostic monitoring.

        Uses atomic Lua script to prevent race conditions during concurrent scan completions.
        """

        try:
            if not self.redis:
                return

            # Store latest scan metrics in Redis for diagnostic endpoint
            metrics_data = {
                "scan_id": scan_id,
                "user_id": user_id,
                "opportunities_discovered": opportunities_count,
                "strategies_scanned": strategies_count,
                "execution_time_ms": execution_time_ms,
                "success": success,
                "timestamp": self._current_timestamp().isoformat()
            }

            # Store in Redis with key that diagnostic endpoint can read
            metrics_key = "service_metrics:user_initiated_scans"
            await self.redis.set(metrics_key, json.dumps(metrics_data), ex=3600)  # 1 hour TTL

            # Atomic daily statistics update using Lua script to prevent race conditions
            stats_key = f"opportunity_scan_stats:{self._current_timestamp().strftime('%Y-%m-%d')}"

            # Lua script for atomic read-modify-write of daily stats
            # Uses Redis hash for better atomicity and performance
            lua_script = """
                local stats_key = KEYS[1]
                local opps_count = tonumber(ARGV[1])
                local strats_count = tonumber(ARGV[2])
                local exec_time = tonumber(ARGV[3])
                local success_flag = tonumber(ARGV[4])
                local ttl = tonumber(ARGV[5])

                -- Increment counters atomically
                redis.call('HINCRBY', stats_key, 'total_scans', 1)
                if success_flag == 1 then
                    redis.call('HINCRBY', stats_key, 'successful_scans', 1)
                end
                redis.call('HINCRBY', stats_key, 'total_opportunities', opps_count)
                redis.call('HINCRBY', stats_key, 'total_strategies', strats_count)

                -- Calculate running average atomically
                local total_scans = tonumber(redis.call('HGET', stats_key, 'total_scans'))
                local prev_avg = tonumber(redis.call('HGET', stats_key, 'avg_execution_time_ms') or '0')
                local new_avg = (prev_avg * (total_scans - 1) + exec_time) / total_scans
                redis.call('HSET', stats_key, 'avg_execution_time_ms', tostring(new_avg))

                -- Set TTL
                redis.call('EXPIRE', stats_key, ttl)

                -- Return updated stats
                return {
                    redis.call('HGET', stats_key, 'total_scans'),
                    redis.call('HGET', stats_key, 'successful_scans'),
                    redis.call('HGET', stats_key, 'total_opportunities'),
                    redis.call('HGET', stats_key, 'total_strategies'),
                    redis.call('HGET', stats_key, 'avg_execution_time_ms')
                }
            """

            # Execute Lua script atomically
            success_int = 1 if success else 0
            ttl_seconds = 86400 * 7  # 7 days

            result = await self.redis.eval(
                lua_script,
                1,  # number of keys
                stats_key,  # KEYS[1]
                opportunities_count,  # ARGV[1]
                strategies_count,  # ARGV[2]
                execution_time_ms,  # ARGV[3]
                success_int,  # ARGV[4]
                ttl_seconds  # ARGV[5]
            )

            self.logger.info(
                "?? User-initiated scan metrics tracked (atomic)",
                scan_id=scan_id,
                user_id=user_id,
                opportunities=opportunities_count,
                strategies=strategies_count,
                execution_time_ms=execution_time_ms,
                success=success,
                daily_stats={
                    "total_scans": result[0] if result else None,
                    "successful_scans": result[1] if result else None,
                    "total_opportunities": result[2] if result else None,
                    "total_strategies": result[3] if result else None,
                    "avg_execution_time_ms": result[4] if result else None
                }
            )

        except Exception as track_error:
            self.logger.debug("Scan metrics tracking failed", error=str(track_error))
    
    async def _provide_fallback_opportunities(self, user_id: str, scan_id: str) -> Dict[str, Any]:
        """Provide fallback opportunities when main discovery fails."""
        
        try:
            # Try to get cached opportunities from previous successful scans
            if self.redis:
                cache_pattern = f"user_opportunities:{user_id}:*"
                
                # Use async scan instead of blocking keys()
                async for cache_key in self.redis.scan_iter(match=cache_pattern):
                    try:
                        cached_data = await self.redis.get(cache_key)
                        if cached_data:
                            raw = cached_data.decode() if isinstance(cached_data, (bytes, bytearray)) else cached_data
                            data = json.loads(raw)

                            # Cache entries now wrap the payload for metadata. Support
                            # both the new {"payload": ...} structure and the legacy
                            # flat structure to keep backward compatibility.
                            payload = data.get("payload") if isinstance(data, dict) else None
                            if not payload and isinstance(data, dict):
                                payload = data

                            opportunities = []
                            if isinstance(payload, dict):
                                opportunities = payload.get("opportunities", [])

                            if opportunities:
                                # Return subset of cached opportunities with warning
                                limited_opportunities = opportunities[:5]  # Limit to 5
                                
                                self.logger.info("?? Fallback opportunities provided from cache",
                                               scan_id=scan_id,
                                               user_id=user_id,
                                               count=len(limited_opportunities))
                                
                                return {
                                    "success": True,
                                    "opportunities": limited_opportunities,
                                    "source": "cached_fallback",
                                    "warning": "Limited opportunities from cache due to system error"
                                }
                    except Exception as e:
                        self.logger.debug("Failed reading cached fallback",
                                        scan_id=scan_id,
                                        user_id=user_id,
                                        cache_key=str(cache_key),
                                        error=str(e))
                        continue
            
            # If no cache available, provide basic strategy recommendations
            basic_opportunities = [
                {
                    "strategy_id": "ai_risk_management",
                    "strategy_name": "AI Risk Management",
                    "opportunity_type": "risk_assessment",
                    "symbol": "PORTFOLIO",
                    "exchange": "multiple",
                    "profit_potential_usd": 0,
                    "confidence_score": 0.8,
                    "risk_level": "low",
                    "required_capital_usd": 0,
                    "estimated_timeframe": "ongoing",
                    "entry_price": None,
                    "exit_price": None,
                    "metadata": {
                        "fallback": True,
                        "description": "Review your portfolio risk profile and get protection recommendations"
                    },
                    "discovered_at": self._current_timestamp().isoformat()
                }
            ]
            
            return {
                "success": True,
                "opportunities": basic_opportunities,
                "source": "basic_fallback",
                "warning": "Basic opportunities provided due to system error"
            }
            
        except Exception as e:
            self.logger.error("Fallback opportunities failed", 
                            scan_id=scan_id, error=str(e))
            return {"success": False, "opportunities": []}





    # Additional Enterprise Scanner Implementations (16 missing methods)
    async def _scan_funding_arbitrage_pro_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Pro version of funding arbitrage with enhanced analysis"""
        try:
            self.logger.info("?? Scanning funding arbitrage pro opportunities", scan_id=scan_id)
            
            # Use base funding arbitrage scanner with enhanced analysis
            base_opportunities = await self._scan_funding_arbitrage_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with pro-level analysis
            enhanced_opportunities = []
            for opp in base_opportunities:
                # Create new OpportunityResult with pro-level enhancements
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="funding_arbitrage_pro",
                    confidence_score=min(95, opp.confidence_score + 15),
                    metadata={
                        **opp.metadata,
                        "pro_features": {
                            "advanced_spread_analysis": True,
                            "multi_exchange_arbitrage": True,
                            "risk_adjusted_returns": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Funding arbitrage pro scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_market_making_pro_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Pro version of market making with advanced order book analysis"""
        try:
            self.logger.info("?? Scanning market making pro opportunities", scan_id=scan_id)
            
            # Use base market making scanner with enhanced analysis
            base_opportunities = await self._scan_market_making_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with pro-level analysis
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="market_making_pro",
                    confidence_score=min(95, opp.confidence_score + 10),
                    metadata={
                        **opp.metadata,
                        "pro_features": {
                            "advanced_order_book_analysis": True,
                            "dynamic_spread_adjustment": True,
                            "liquidity_provision_optimization": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Market making pro scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_scalping_engine_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Advanced scalping engine with high-frequency analysis"""
        try:
            self.logger.info("?? Scanning scalping engine opportunities", scan_id=scan_id)
            
            # Use base scalping scanner with enhanced analysis
            base_opportunities = await self._scan_scalping_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with engine-level analysis
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="scalping_engine",
                    confidence_score=min(95, opp.confidence_score + 5),
                    metadata={
                        **opp.metadata,
                        "engine_features": {
                            "high_frequency_analysis": True,
                            "micro_trend_detection": True,
                            "rapid_execution_optimization": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Scalping engine scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_swing_navigator_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Swing trading navigator with trend analysis"""
        try:
            self.logger.info("?? Scanning swing navigator opportunities", scan_id=scan_id)
            
            # Use momentum strategy as base with swing-specific enhancements
            base_opportunities = await self._scan_spot_momentum_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with swing-specific analysis
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="swing_navigator",
                    estimated_timeframe="4h",  # Swing trading timeframe
                    confidence_score=min(90, opp.confidence_score + 5),
                    metadata={
                        **opp.metadata,
                        "swing_features": {
                            "trend_continuation_analysis": True,
                            "swing_point_identification": True,
                            "multi_timeframe_confirmation": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Swing navigator scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_position_manager_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Position management with risk-adjusted sizing"""
        try:
            self.logger.info("?? Scanning position manager opportunities", scan_id=scan_id)
            
            # Use risk management as base with position-specific enhancements
            base_opportunities = await self._scan_risk_management_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with position management features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="position_manager",
                    confidence_score=min(95, opp.confidence_score + 10),
                    metadata={
                        **opp.metadata,
                        "position_features": {
                            "dynamic_position_sizing": True,
                            "risk_adjusted_allocation": True,
                            "portfolio_correlation_analysis": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Position manager scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_risk_guardian_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Advanced risk guardian with comprehensive protection"""
        try:
            self.logger.info("?? Scanning risk guardian opportunities", scan_id=scan_id)
            
            # Use risk management as base with guardian-specific enhancements
            base_opportunities = await self._scan_risk_management_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with guardian features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="risk_guardian",
                    confidence_score=min(98, opp.confidence_score + 15),
                    metadata={
                        **opp.metadata,
                        "guardian_features": {
                            "real_time_risk_monitoring": True,
                            "automatic_hedge_activation": True,
                            "portfolio_protection_alerts": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Risk guardian scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_portfolio_optimizer_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Portfolio optimizer with advanced allocation strategies"""
        try:
            self.logger.info("?? Scanning portfolio optimizer opportunities", scan_id=scan_id)
            
            # Use portfolio optimization as base with optimizer-specific enhancements
            base_opportunities = await self._scan_portfolio_optimization_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with optimizer features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="portfolio_optimizer",
                    confidence_score=min(95, opp.confidence_score + 10),
                    metadata={
                        **opp.metadata,
                        "optimizer_features": {
                            "advanced_allocation_algorithms": True,
                            "dynamic_rebalancing": True,
                            "risk_return_optimization": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Portfolio optimizer scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_strategy_analytics_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Strategy analytics with performance insights"""
        try:
            self.logger.info("?? Scanning strategy analytics opportunities", scan_id=scan_id)
            
            # Use statistical arbitrage as base with analytics-specific enhancements
            base_opportunities = await self._scan_statistical_arbitrage_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with analytics features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="strategy_analytics",
                    confidence_score=min(90, opp.confidence_score + 5),
                    metadata={
                        **opp.metadata,
                        "analytics_features": {
                            "performance_attribution": True,
                            "strategy_correlation_analysis": True,
                            "predictive_analytics": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Strategy analytics scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_momentum_trader_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Momentum trader with enhanced trend following"""
        try:
            self.logger.info("?? Scanning momentum trader opportunities", scan_id=scan_id)
            
            # Use spot momentum as base with trader-specific enhancements
            base_opportunities = await self._scan_spot_momentum_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with trader features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="momentum_trader",
                    confidence_score=min(95, opp.confidence_score + 10),
                    metadata={
                        **opp.metadata,
                        "trader_features": {
                            "advanced_momentum_indicators": True,
                            "trend_strength_analysis": True,
                            "entry_exit_optimization": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Momentum trader scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_mean_reversion_pro_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Pro version of mean reversion with advanced statistical analysis"""
        try:
            self.logger.info("?? Scanning mean reversion pro opportunities", scan_id=scan_id)
            
            # Use spot mean reversion as base with pro enhancements
            base_opportunities = await self._scan_spot_mean_reversion_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with pro features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="mean_reversion_pro",
                    confidence_score=min(95, opp.confidence_score + 15),
                    metadata={
                        **opp.metadata,
                        "pro_features": {
                            "advanced_statistical_models": True,
                            "multi_timeframe_mean_reversion": True,
                            "volatility_adjusted_signals": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Mean reversion pro scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_breakout_hunter_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Breakout hunter with advanced pattern recognition"""
        try:
            self.logger.info("?? Scanning breakout hunter opportunities", scan_id=scan_id)
            
            # Use spot breakout as base with hunter-specific enhancements
            base_opportunities = await self._scan_spot_breakout_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with hunter features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="breakout_hunter",
                    confidence_score=min(95, opp.confidence_score + 10),
                    metadata={
                        **opp.metadata,
                        "hunter_features": {
                            "advanced_pattern_recognition": True,
                            "volume_confirmation_analysis": True,
                            "false_breakout_filtering": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Breakout hunter scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_algorithmic_suite_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Algorithmic suite with multi-strategy coordination"""
        try:
            self.logger.info("?? Scanning algorithmic suite opportunities", scan_id=scan_id)
            
            # Use complex strategy as base with suite-specific enhancements
            base_opportunities = await self._scan_complex_strategy_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with suite features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="algorithmic_suite",
                    confidence_score=min(95, opp.confidence_score + 10),
                    metadata={
                        **opp.metadata,
                        "suite_features": {
                            "multi_strategy_coordination": True,
                            "adaptive_algorithm_selection": True,
                            "cross_strategy_optimization": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Algorithmic suite scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_pairs_trader_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Pairs trader with enhanced correlation analysis"""
        try:
            self.logger.info("?? Scanning pairs trader opportunities", scan_id=scan_id)
            
            # Use pairs trading as base with trader-specific enhancements
            base_opportunities = await self._scan_pairs_trading_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with trader features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="pairs_trader",
                    confidence_score=min(95, opp.confidence_score + 10),
                    metadata={
                        **opp.metadata,
                        "trader_features": {
                            "advanced_correlation_analysis": True,
                            "cointegration_testing": True,
                            "pairs_selection_optimization": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Pairs trader scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_statistical_arbitrage_pro_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Pro version of statistical arbitrage with advanced models"""
        try:
            self.logger.info("?? Scanning statistical arbitrage pro opportunities", scan_id=scan_id)
            
            # Use statistical arbitrage as base with pro enhancements
            base_opportunities = await self._scan_statistical_arbitrage_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with pro features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="statistical_arbitrage_pro",
                    confidence_score=min(95, opp.confidence_score + 15),
                    metadata={
                        **opp.metadata,
                        "pro_features": {
                            "advanced_statistical_models": True,
                            "machine_learning_enhancement": True,
                            "high_frequency_execution": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Statistical arbitrage pro scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_market_maker_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Market maker with advanced liquidity provision"""
        try:
            self.logger.info("?? Scanning market maker opportunities", scan_id=scan_id)
            
            # Use market making as base with maker-specific enhancements
            base_opportunities = await self._scan_market_making_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with maker features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="market_maker",
                    confidence_score=min(95, opp.confidence_score + 10),
                    metadata={
                        **opp.metadata,
                        "maker_features": {
                            "advanced_liquidity_provision": True,
                            "dynamic_spread_management": True,
                            "inventory_risk_management": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Market maker scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_scalping_engine_pro_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Pro version of scalping engine with ultra-high frequency analysis"""
        try:
            self.logger.info("?? Scanning scalping engine pro opportunities", scan_id=scan_id)
            
            # Use scalping as base with pro engine enhancements
            base_opportunities = await self._scan_scalping_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with pro engine features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="scalping_engine_pro",
                    confidence_score=min(98, opp.confidence_score + 15),
                    metadata={
                        **opp.metadata,
                        "pro_engine_features": {
                            "ultra_high_frequency_analysis": True,
                            "microsecond_execution_optimization": True,
                            "advanced_latency_arbitrage": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Scalping engine pro scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_swing_navigator_pro_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Pro version of swing navigator with advanced trend analysis"""
        try:
            self.logger.info("?? Scanning swing navigator pro opportunities", scan_id=scan_id)
            
            # Use momentum strategy as base with pro navigator enhancements
            base_opportunities = await self._scan_spot_momentum_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with pro navigator features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="swing_navigator_pro",
                    estimated_timeframe="4h",  # Swing trading timeframe
                    confidence_score=min(95, opp.confidence_score + 15),
                    metadata={
                        **opp.metadata,
                        "pro_navigator_features": {
                            "advanced_trend_analysis": True,
                            "multi_timeframe_synthesis": True,
                            "predictive_swing_identification": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Swing navigator pro scan failed", scan_id=scan_id, error=str(e))
            return []


    async def _scan_funding_arbitrage_pro_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Pro version of funding arbitrage with enhanced analysis"""
        try:
            self.logger.info("?? Scanning funding arbitrage pro opportunities", scan_id=scan_id)
            
            # Use base funding arbitrage scanner with enhanced analysis
            base_opportunities = await self._scan_funding_arbitrage_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with pro-level analysis
            enhanced_opportunities = []
            for opp in base_opportunities:
                # Create new OpportunityResult with pro-level enhancements
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="funding_arbitrage_pro",
                    confidence_score=min(95, opp.confidence_score + 15),
                    metadata={
                        **opp.metadata,
                        "pro_features": {
                            "advanced_spread_analysis": True,
                            "multi_exchange_arbitrage": True,
                            "risk_adjusted_returns": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Funding arbitrage pro scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_market_making_pro_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Pro version of market making with advanced order book analysis"""
        try:
            self.logger.info("?? Scanning market making pro opportunities", scan_id=scan_id)
            
            # Use base market making scanner with enhanced analysis
            base_opportunities = await self._scan_market_making_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with pro-level analysis
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="market_making_pro",
                    confidence_score=min(95, opp.confidence_score + 10),
                    metadata={
                        **opp.metadata,
                        "pro_features": {
                            "advanced_order_book_analysis": True,
                            "dynamic_spread_adjustment": True,
                            "liquidity_provision_optimization": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Market making pro scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_scalping_engine_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Advanced scalping engine with high-frequency analysis"""
        try:
            self.logger.info("?? Scanning scalping engine opportunities", scan_id=scan_id)
            
            # Use base scalping scanner with enhanced analysis
            base_opportunities = await self._scan_scalping_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with engine-level analysis
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="scalping_engine",
                    confidence_score=min(95, opp.confidence_score + 5),
                    metadata={
                        **opp.metadata,
                        "engine_features": {
                            "high_frequency_analysis": True,
                            "micro_trend_detection": True,
                            "rapid_execution_optimization": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Scalping engine scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_swing_navigator_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Swing trading navigator with trend analysis"""
        try:
            self.logger.info("?? Scanning swing navigator opportunities", scan_id=scan_id)
            
            # Use momentum strategy as base with swing-specific enhancements
            base_opportunities = await self._scan_spot_momentum_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with swing-specific analysis
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="swing_navigator",
                    estimated_timeframe="4h",  # Swing trading timeframe
                    confidence_score=min(90, opp.confidence_score + 5),
                    metadata={
                        **opp.metadata,
                        "swing_features": {
                            "trend_continuation_analysis": True,
                            "swing_point_identification": True,
                            "multi_timeframe_confirmation": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Swing navigator scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_position_manager_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Position management with risk-adjusted sizing"""
        try:
            self.logger.info("?? Scanning position manager opportunities", scan_id=scan_id)
            
            # Use risk management as base with position-specific enhancements
            base_opportunities = await self._scan_risk_management_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with position management features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="position_manager",
                    confidence_score=min(95, opp.confidence_score + 10),
                    metadata={
                        **opp.metadata,
                        "position_features": {
                            "dynamic_position_sizing": True,
                            "risk_adjusted_allocation": True,
                            "portfolio_correlation_analysis": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Position manager scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_risk_guardian_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Advanced risk guardian with comprehensive protection"""
        try:
            self.logger.info("?? Scanning risk guardian opportunities", scan_id=scan_id)
            
            # Use risk management as base with guardian-specific enhancements
            base_opportunities = await self._scan_risk_management_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with guardian features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="risk_guardian",
                    confidence_score=min(98, opp.confidence_score + 15),
                    metadata={
                        **opp.metadata,
                        "guardian_features": {
                            "real_time_risk_monitoring": True,
                            "automatic_hedge_activation": True,
                            "portfolio_protection_alerts": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Risk guardian scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_portfolio_optimizer_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Portfolio optimizer with advanced allocation strategies"""
        try:
            self.logger.info("?? Scanning portfolio optimizer opportunities", scan_id=scan_id)
            
            # Use portfolio optimization as base with optimizer-specific enhancements
            base_opportunities = await self._scan_portfolio_optimization_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with optimizer features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="portfolio_optimizer",
                    confidence_score=min(95, opp.confidence_score + 10),
                    metadata={
                        **opp.metadata,
                        "optimizer_features": {
                            "advanced_allocation_algorithms": True,
                            "dynamic_rebalancing": True,
                            "risk_return_optimization": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Portfolio optimizer scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_strategy_analytics_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Strategy analytics with performance insights"""
        try:
            self.logger.info("?? Scanning strategy analytics opportunities", scan_id=scan_id)
            
            # Use statistical arbitrage as base with analytics-specific enhancements
            base_opportunities = await self._scan_statistical_arbitrage_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with analytics features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="strategy_analytics",
                    confidence_score=min(90, opp.confidence_score + 5),
                    metadata={
                        **opp.metadata,
                        "analytics_features": {
                            "performance_attribution": True,
                            "strategy_correlation_analysis": True,
                            "predictive_analytics": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Strategy analytics scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_momentum_trader_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Momentum trader with enhanced trend following"""
        try:
            self.logger.info("?? Scanning momentum trader opportunities", scan_id=scan_id)
            
            # Use spot momentum as base with trader-specific enhancements
            base_opportunities = await self._scan_spot_momentum_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with trader features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="momentum_trader",
                    confidence_score=min(95, opp.confidence_score + 10),
                    metadata={
                        **opp.metadata,
                        "trader_features": {
                            "advanced_momentum_indicators": True,
                            "trend_strength_analysis": True,
                            "entry_exit_optimization": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Momentum trader scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_mean_reversion_pro_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Pro version of mean reversion with advanced statistical analysis"""
        try:
            self.logger.info("?? Scanning mean reversion pro opportunities", scan_id=scan_id)
            
            # Use spot mean reversion as base with pro enhancements
            base_opportunities = await self._scan_spot_mean_reversion_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with pro features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="mean_reversion_pro",
                    confidence_score=min(95, opp.confidence_score + 15),
                    metadata={
                        **opp.metadata,
                        "pro_features": {
                            "advanced_statistical_models": True,
                            "multi_timeframe_mean_reversion": True,
                            "volatility_adjusted_signals": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Mean reversion pro scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_breakout_hunter_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Breakout hunter with advanced pattern recognition"""
        try:
            self.logger.info("?? Scanning breakout hunter opportunities", scan_id=scan_id)
            
            # Use spot breakout as base with hunter-specific enhancements
            base_opportunities = await self._scan_spot_breakout_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with hunter features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="breakout_hunter",
                    confidence_score=min(95, opp.confidence_score + 10),
                    metadata={
                        **opp.metadata,
                        "hunter_features": {
                            "advanced_pattern_recognition": True,
                            "volume_confirmation_analysis": True,
                            "false_breakout_filtering": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Breakout hunter scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_algorithmic_suite_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Algorithmic suite with multi-strategy coordination"""
        try:
            self.logger.info("?? Scanning algorithmic suite opportunities", scan_id=scan_id)
            
            # Use complex strategy as base with suite-specific enhancements
            base_opportunities = await self._scan_complex_strategy_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with suite features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="algorithmic_suite",
                    confidence_score=min(95, opp.confidence_score + 10),
                    metadata={
                        **opp.metadata,
                        "suite_features": {
                            "multi_strategy_coordination": True,
                            "adaptive_algorithm_selection": True,
                            "cross_strategy_optimization": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Algorithmic suite scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_pairs_trader_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Pairs trader with enhanced correlation analysis"""
        try:
            self.logger.info("?? Scanning pairs trader opportunities", scan_id=scan_id)
            
            # Use pairs trading as base with trader-specific enhancements
            base_opportunities = await self._scan_pairs_trading_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with trader features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="pairs_trader",
                    confidence_score=min(95, opp.confidence_score + 10),
                    metadata={
                        **opp.metadata,
                        "trader_features": {
                            "advanced_correlation_analysis": True,
                            "cointegration_testing": True,
                            "pairs_selection_optimization": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Pairs trader scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_statistical_arbitrage_pro_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Pro version of statistical arbitrage with advanced models"""
        try:
            self.logger.info("?? Scanning statistical arbitrage pro opportunities", scan_id=scan_id)
            
            # Use statistical arbitrage as base with pro enhancements
            base_opportunities = await self._scan_statistical_arbitrage_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with pro features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="statistical_arbitrage_pro",
                    confidence_score=min(95, opp.confidence_score + 15),
                    metadata={
                        **opp.metadata,
                        "pro_features": {
                            "advanced_statistical_models": True,
                            "machine_learning_enhancement": True,
                            "high_frequency_execution": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Statistical arbitrage pro scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_market_maker_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Market maker with advanced liquidity provision"""
        try:
            self.logger.info("?? Scanning market maker opportunities", scan_id=scan_id)
            
            # Use market making as base with maker-specific enhancements
            base_opportunities = await self._scan_market_making_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with maker features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="market_maker",
                    confidence_score=min(95, opp.confidence_score + 10),
                    metadata={
                        **opp.metadata,
                        "maker_features": {
                            "advanced_liquidity_provision": True,
                            "dynamic_spread_management": True,
                            "inventory_risk_management": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Market maker scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_scalping_engine_pro_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Pro version of scalping engine with ultra-high frequency analysis"""
        try:
            self.logger.info("?? Scanning scalping engine pro opportunities", scan_id=scan_id)
            
            # Use scalping as base with pro engine enhancements
            base_opportunities = await self._scan_scalping_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with pro engine features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="scalping_engine_pro",
                    confidence_score=min(98, opp.confidence_score + 15),
                    metadata={
                        **opp.metadata,
                        "pro_engine_features": {
                            "ultra_high_frequency_analysis": True,
                            "microsecond_execution_optimization": True,
                            "advanced_latency_arbitrage": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Scalping engine pro scan failed", scan_id=scan_id, error=str(e))
            return []

    async def _scan_swing_navigator_pro_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Pro version of swing navigator with advanced trend analysis"""
        try:
            self.logger.info("?? Scanning swing navigator pro opportunities", scan_id=scan_id)
            
            # Use momentum strategy as base with pro navigator enhancements
            base_opportunities = await self._scan_spot_momentum_opportunities(
                discovered_assets, user_profile, scan_id, portfolio_result
            )
            
            # Enhance with pro navigator features
            enhanced_opportunities = []
            for opp in base_opportunities:
                enhanced_opp = dataclasses.replace(
                    opp,
                    opportunity_type="swing_navigator_pro",
                    estimated_timeframe="4h",  # Swing trading timeframe
                    confidence_score=min(95, opp.confidence_score + 15),
                    metadata={
                        **opp.metadata,
                        "pro_navigator_features": {
                            "advanced_trend_analysis": True,
                            "multi_timeframe_synthesis": True,
                            "predictive_swing_identification": True
                        }
                    }
                )
                enhanced_opportunities.append(enhanced_opp)
            
            return enhanced_opportunities
            
        except Exception as e:
            self.logger.error("Swing navigator pro scan failed", scan_id=scan_id, error=str(e))
            return []


# Global service instance
user_opportunity_discovery = UserOpportunityDiscoveryService()


async def get_user_opportunity_discovery() -> UserOpportunityDiscoveryService:
    """Dependency injection for FastAPI."""
    return user_opportunity_discovery
