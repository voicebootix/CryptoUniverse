"""
Enterprise API Cost Tracking System
Comprehensive monitoring and cost optimization for all APIs used in the platform.

Tracks costs across:
- AI Models: OpenAI GPT-4, Anthropic Claude, Google Gemini
- Exchanges: Binance, Coinbase, Kraken, KuCoin, etc.
- Market Data: CoinGecko, CoinMarketCap, Messari
- Other Services: Email, SMS, Cloud services

NO MOCK DATA - REAL COST TRACKING WITH OPTIMIZATION
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from decimal import Decimal
import uuid

import structlog
from app.core.config import get_settings
from app.core.logging import LoggerMixin
from app.core.redis import get_redis_client

settings = get_settings()
logger = structlog.get_logger(__name__)


class APIProvider(str, Enum):
    """All API providers used in the platform."""
    
    # AI Models
    OPENAI_GPT4 = "openai_gpt4"
    ANTHROPIC_CLAUDE = "anthropic_claude"
    GOOGLE_GEMINI = "google_gemini"
    
    # Cryptocurrency Exchanges
    BINANCE_API = "binance_api"
    COINBASE_API = "coinbase_api"
    KRAKEN_API = "kraken_api"
    KUCOIN_API = "kucoin_api"
    BYBIT_API = "bybit_api"
    OKEX_API = "okex_api"
    
    # Market Data Providers
    COINGECKO_API = "coingecko_api"
    COINMARKETCAP_API = "coinmarketcap_api"
    MESSARI_API = "messari_api"
    CRYPTOCOMPARE_API = "cryptocompare_api"
    
    # Communication Services
    TELEGRAM_API = "telegram_api"
    SENDGRID_EMAIL = "sendgrid_email"
    TWILIO_SMS = "twilio_sms"
    
    # Cloud Services
    REDIS_CLOUD = "redis_cloud"
    POSTGRESQL_CLOUD = "postgresql_cloud"
    
    # Other Services
    NEWS_API = "news_api"
    SENTIMENT_API = "sentiment_api"


class CostCategory(str, Enum):
    """Cost categories for better organization."""
    AI_MODELS = "ai_models"
    EXCHANGE_APIS = "exchange_apis"
    MARKET_DATA = "market_data"
    COMMUNICATION = "communication"
    INFRASTRUCTURE = "infrastructure"
    OTHER = "other"


@dataclass
class APICall:
    """Individual API call record."""
    call_id: str
    provider: APIProvider
    endpoint: str
    method: str
    cost_usd: float
    user_id: Optional[str]
    tokens_used: Optional[int]
    response_time_ms: float
    response_size_bytes: Optional[int]
    success: bool
    error_message: Optional[str]
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass
class CostSummary:
    """Cost summary for a time period."""
    period: str
    total_cost_usd: float
    total_calls: int
    successful_calls: int
    failed_calls: int
    avg_response_time_ms: float
    cost_by_provider: Dict[str, float]
    cost_by_category: Dict[str, float]
    cost_by_user: Dict[str, float]
    optimization_opportunities: List[str]


@dataclass
class RateLimitStatus:
    """Rate limit status for API provider."""
    provider: APIProvider
    current_usage: int
    limit: int
    reset_time: datetime
    usage_percentage: float
    is_approaching_limit: bool


class APICostTracker(LoggerMixin):
    """
    Enterprise API Cost Tracking System
    
    Features:
    - Real-time cost tracking across all APIs
    - Per-user cost attribution
    - Rate limit monitoring
    - Cost optimization suggestions
    - Budget alerts and controls
    - Detailed analytics and reporting
    """
    
    def __init__(self):
        # Provider cost configurations (real rates)
        self.provider_costs = {
            # AI Models (per token/request)
            APIProvider.OPENAI_GPT4: {
                "cost_per_1k_input_tokens": 0.01,
                "cost_per_1k_output_tokens": 0.03,
                "category": CostCategory.AI_MODELS
            },
            APIProvider.ANTHROPIC_CLAUDE: {
                "cost_per_1k_input_tokens": 0.015,
                "cost_per_1k_output_tokens": 0.075,
                "category": CostCategory.AI_MODELS
            },
            APIProvider.GOOGLE_GEMINI: {
                "cost_per_1k_input_tokens": 0.0025,
                "cost_per_1k_output_tokens": 0.0075,
                "category": CostCategory.AI_MODELS
            },
            
            # Exchange APIs (per request)
            APIProvider.BINANCE_API: {
                "cost_per_request": 0.0001,
                "category": CostCategory.EXCHANGE_APIS
            },
            APIProvider.COINBASE_API: {
                "cost_per_request": 0.0002,
                "category": CostCategory.EXCHANGE_APIS
            },
            APIProvider.KRAKEN_API: {
                "cost_per_request": 0.0001,
                "category": CostCategory.EXCHANGE_APIS
            },
            
            # Market Data APIs
            APIProvider.COINGECKO_API: {
                "cost_per_request": 0.0,  # Free tier
                "cost_per_request_premium": 0.001,
                "category": CostCategory.MARKET_DATA
            },
            APIProvider.COINMARKETCAP_API: {
                "cost_per_request": 0.0005,
                "category": CostCategory.MARKET_DATA
            }
        }
        
        # Rate limit configurations
        self.rate_limits = {
            APIProvider.OPENAI_GPT4: {"requests_per_minute": 3500, "tokens_per_minute": 90000},
            APIProvider.ANTHROPIC_CLAUDE: {"requests_per_minute": 1000, "tokens_per_minute": 40000},
            APIProvider.GOOGLE_GEMINI: {"requests_per_minute": 1500, "tokens_per_minute": 32000},
            APIProvider.BINANCE_API: {"requests_per_minute": 1200, "weight_per_minute": 6000},
            APIProvider.COINBASE_API: {"requests_per_minute": 10000, "requests_per_second": 10}
        }
        
        # Budget thresholds
        self.budget_alerts = {
            "daily_warning": 50.0,    # $50/day warning
            "daily_critical": 100.0,  # $100/day critical
            "monthly_warning": 1000.0, # $1000/month warning
            "monthly_critical": 2000.0 # $2000/month critical
        }
        
        # In-memory cache for real-time tracking
        self.realtime_costs = {}
        self.rate_limit_status = {}
        
        self.logger.info("💰 API Cost Tracker initialized with enterprise monitoring")
    
    async def track_api_call(
        self,
        provider: APIProvider,
        endpoint: str,
        method: str = "GET",
        cost_usd: Optional[float] = None,
        user_id: Optional[str] = None,
        tokens_used: Optional[int] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        response_time_ms: float = 0,
        response_size_bytes: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Track individual API call with comprehensive metrics.
        
        Args:
            provider: API provider enum
            endpoint: API endpoint called
            method: HTTP method
            cost_usd: Actual cost (if known), otherwise calculated
            user_id: User who triggered the call
            tokens_used: Total tokens (for AI models)
            input_tokens: Input tokens (for AI models)
            output_tokens: Output tokens (for AI models)
            response_time_ms: Response time in milliseconds
            response_size_bytes: Response size
            success: Whether the call succeeded
            error_message: Error message if failed
            metadata: Additional metadata
            
        Returns:
            call_id: Unique identifier for this API call
        """
        
        call_id = f"{provider.value}_{int(datetime.utcnow().timestamp())}_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.utcnow()
        
        try:
            # Calculate cost if not provided
            if cost_usd is None:
                cost_usd = await self._calculate_cost(
                    provider, tokens_used, input_tokens, output_tokens
                )
            
            # Create API call record
            api_call = APICall(
                call_id=call_id,
                provider=provider,
                endpoint=endpoint,
                method=method,
                cost_usd=cost_usd,
                user_id=user_id,
                tokens_used=tokens_used,
                response_time_ms=response_time_ms,
                response_size_bytes=response_size_bytes,
                success=success,
                error_message=error_message,
                timestamp=timestamp,
                metadata=metadata or {}
            )
            
            # Store the call record
            await self._store_api_call(api_call)
            
            # Update real-time aggregations
            await self._update_realtime_costs(api_call)
            
            # Update rate limit tracking
            await self._update_rate_limits(provider)
            
            # Check budget thresholds
            await self._check_budget_alerts(user_id)
            
            # Send real-time cost update via WebSocket
            await self._broadcast_cost_update(api_call)
            
            return call_id
            
        except Exception as e:
            self.logger.error(
                "Failed to track API call",
                provider=provider.value,
                endpoint=endpoint,
                error=str(e)
            )
            return call_id
    
    async def _calculate_cost(
        self,
        provider: APIProvider,
        tokens_used: Optional[int],
        input_tokens: Optional[int],
        output_tokens: Optional[int]
    ) -> float:
        """Calculate cost based on provider pricing."""
        
        try:
            provider_config = self.provider_costs.get(provider, {})
            
            # AI model costs (token-based)
            if provider in [APIProvider.OPENAI_GPT4, APIProvider.ANTHROPIC_CLAUDE, APIProvider.GOOGLE_GEMINI]:
                if input_tokens and output_tokens:
                    input_cost = (input_tokens / 1000) * provider_config.get("cost_per_1k_input_tokens", 0)
                    output_cost = (output_tokens / 1000) * provider_config.get("cost_per_1k_output_tokens", 0)
                    return input_cost + output_cost
                elif tokens_used:
                    # Estimate 70% input, 30% output for mixed token cost
                    avg_cost_per_1k = (
                        provider_config.get("cost_per_1k_input_tokens", 0) * 0.7 +
                        provider_config.get("cost_per_1k_output_tokens", 0) * 0.3
                    )
                    return (tokens_used / 1000) * avg_cost_per_1k
            
            # Fixed cost per request for other APIs
            else:
                return provider_config.get("cost_per_request", 0.0)
            
        except Exception as e:
            self.logger.error("Cost calculation failed", provider=provider.value, error=str(e))
            return 0.0
        
        return 0.0
    
    async def _store_api_call(self, api_call: APICall):
        """Store API call record in Redis."""
        
        try:
            redis = await get_redis_client()
            if not redis:
                return
            
            # Store individual call record
            call_key = f"api_call:{api_call.call_id}"
            call_data = asdict(api_call)
            call_data["timestamp"] = api_call.timestamp.isoformat()
            
            await redis.set(call_key, json.dumps(call_data, default=str), ex=86400 * 7)  # 7 days
            
            # Add to time-based indices for efficient querying
            date_key = api_call.timestamp.strftime("%Y-%m-%d")
            hour_key = api_call.timestamp.strftime("%Y-%m-%d-%H")
            
            # Daily index
            await redis.sadd(f"api_calls:daily:{date_key}", api_call.call_id)
            await redis.expire(f"api_calls:daily:{date_key}", 86400 * 7)
            
            # Hourly index
            await redis.sadd(f"api_calls:hourly:{hour_key}", api_call.call_id)
            await redis.expire(f"api_calls:hourly:{hour_key}", 86400 * 7)
            
            # Provider index
            await redis.sadd(f"api_calls:provider:{api_call.provider.value}:{date_key}", api_call.call_id)
            await redis.expire(f"api_calls:provider:{api_call.provider.value}:{date_key}", 86400 * 7)
            
            # User index (if user_id provided)
            if api_call.user_id:
                await redis.sadd(f"api_calls:user:{api_call.user_id}:{date_key}", api_call.call_id)
                await redis.expire(f"api_calls:user:{api_call.user_id}:{date_key}", 86400 * 7)
            
        except Exception as e:
            self.logger.error("Failed to store API call", call_id=api_call.call_id, error=str(e))
    
    async def _update_realtime_costs(self, api_call: APICall):
        """Update real-time cost aggregations."""
        
        try:
            redis = await get_redis_client()
            if not redis:
                return
            
            # Update real-time counters
            now = datetime.utcnow()
            date_key = now.strftime("%Y-%m-%d")
            hour_key = now.strftime("%Y-%m-%d-%H")
            minute_key = now.strftime("%Y-%m-%d-%H-%M")
            
            # Increment counters
            pipe = redis.pipeline()
            
            # Daily totals
            pipe.incrbyfloat(f"cost:daily:{date_key}", api_call.cost_usd)
            pipe.incr(f"calls:daily:{date_key}")
            pipe.expire(f"cost:daily:{date_key}", 86400 * 7)
            pipe.expire(f"calls:daily:{date_key}", 86400 * 7)
            
            # Hourly totals
            pipe.incrbyfloat(f"cost:hourly:{hour_key}", api_call.cost_usd)
            pipe.incr(f"calls:hourly:{hour_key}")
            pipe.expire(f"cost:hourly:{hour_key}", 86400 * 2)
            pipe.expire(f"calls:hourly:{hour_key}", 86400 * 2)
            
            # Per-minute for real-time monitoring
            pipe.incrbyfloat(f"cost:minute:{minute_key}", api_call.cost_usd)
            pipe.incr(f"calls:minute:{minute_key}")
            pipe.expire(f"cost:minute:{minute_key}", 3600)
            pipe.expire(f"calls:minute:{minute_key}", 3600)
            
            # Provider-specific totals
            pipe.incrbyfloat(f"cost:provider:{api_call.provider.value}:{date_key}", api_call.cost_usd)
            pipe.incr(f"calls:provider:{api_call.provider.value}:{date_key}")
            pipe.expire(f"cost:provider:{api_call.provider.value}:{date_key}", 86400 * 7)
            pipe.expire(f"calls:provider:{api_call.provider.value}:{date_key}", 86400 * 7)
            
            # User-specific totals (if user_id provided)
            if api_call.user_id:
                pipe.incrbyfloat(f"cost:user:{api_call.user_id}:{date_key}", api_call.cost_usd)
                pipe.incr(f"calls:user:{api_call.user_id}:{date_key}")
                pipe.expire(f"cost:user:{api_call.user_id}:{date_key}", 86400 * 7)
                pipe.expire(f"calls:user:{api_call.user_id}:{date_key}", 86400 * 7)
            
            # Success/failure tracking
            if api_call.success:
                pipe.incr(f"success:daily:{date_key}")
                pipe.expire(f"success:daily:{date_key}", 86400 * 7)
            else:
                pipe.incr(f"failure:daily:{date_key}")
                pipe.expire(f"failure:daily:{date_key}", 86400 * 7)
            
            await pipe.execute()
            
        except Exception as e:
            self.logger.error("Failed to update realtime costs", error=str(e))
    
    async def _update_rate_limits(self, provider: APIProvider):
        """Update rate limit tracking for provider."""
        
        try:
            redis = await get_redis_client()
            if not redis:
                return
            
            # Track requests per minute
            minute_key = datetime.utcnow().strftime("%Y-%m-%d-%H-%M")
            rate_key = f"rate_limit:{provider.value}:{minute_key}"
            
            current_count = await redis.incr(rate_key)
            await redis.expire(rate_key, 60)  # Expire after 1 minute
            
            # Check if approaching rate limit
            provider_limits = self.rate_limits.get(provider, {})
            requests_per_minute = provider_limits.get("requests_per_minute", float('inf'))
            
            usage_percentage = (current_count / requests_per_minute) * 100
            is_approaching_limit = usage_percentage > 80  # Alert at 80%
            
            # Store rate limit status
            self.rate_limit_status[provider] = RateLimitStatus(
                provider=provider,
                current_usage=current_count,
                limit=requests_per_minute,
                reset_time=datetime.utcnow().replace(second=0, microsecond=0) + timedelta(minutes=1),
                usage_percentage=usage_percentage,
                is_approaching_limit=is_approaching_limit
            )
            
            # Alert if approaching limit
            if is_approaching_limit:
                await self._send_rate_limit_alert(provider, usage_percentage)
            
        except Exception as e:
            self.logger.error("Failed to update rate limits", provider=provider.value, error=str(e))
    
    async def _check_budget_alerts(self, user_id: Optional[str]):
        """Check if budget thresholds are exceeded."""
        
        try:
            redis = await get_redis_client()
            if not redis:
                return
            
            date_key = datetime.utcnow().strftime("%Y-%m-%d")
            month_key = datetime.utcnow().strftime("%Y-%m")
            
            # Get current daily and monthly costs
            daily_cost = float(await redis.get(f"cost:daily:{date_key}") or 0)
            monthly_cost = 0.0
            
            # Calculate monthly cost by summing daily costs
            for day in range(1, 32):  # Check up to 31 days
                try:
                    day_key = datetime.utcnow().replace(day=day).strftime("%Y-%m-%d")
                    day_cost = float(await redis.get(f"cost:daily:{day_key}") or 0)
                    monthly_cost += day_cost
                except Exception as e:
                    self.logger.debug(
                        "Failed to get daily cost for monthly calculation",
                        day=day,
                        day_key=day_key,
                        error=str(e)
                    )
                    continue
            
            # Check thresholds
            alerts_sent = []
            
            # Daily alerts
            if daily_cost >= self.budget_alerts["daily_critical"]:
                await self._send_budget_alert("daily_critical", daily_cost, user_id)
                alerts_sent.append("daily_critical")
            elif daily_cost >= self.budget_alerts["daily_warning"]:
                await self._send_budget_alert("daily_warning", daily_cost, user_id)
                alerts_sent.append("daily_warning")
            
            # Monthly alerts
            if monthly_cost >= self.budget_alerts["monthly_critical"]:
                await self._send_budget_alert("monthly_critical", monthly_cost, user_id)
                alerts_sent.append("monthly_critical")
            elif monthly_cost >= self.budget_alerts["monthly_warning"]:
                await self._send_budget_alert("monthly_warning", monthly_cost, user_id)
                alerts_sent.append("monthly_warning")
            
        except Exception as e:
            self.logger.error("Failed to check budget alerts", error=str(e))
    
    async def _broadcast_cost_update(self, api_call: APICall):
        """Broadcast real-time cost update via WebSocket."""
        
        try:
            from app.services.websocket import manager
            
            # Prepare cost update message
            cost_update = {
                "type": "api_cost_update",
                "data": {
                    "provider": api_call.provider.value,
                    "cost_usd": api_call.cost_usd,
                    "user_id": api_call.user_id,
                    "success": api_call.success,
                    "timestamp": api_call.timestamp.isoformat()
                }
            }
            
            # Broadcast to admin cost dashboard subscribers
            await manager.broadcast_cost_update(cost_update)
            
        except Exception as e:
            self.logger.error("Failed to broadcast cost update", error=str(e))
    
    async def get_cost_dashboard(self, period: str = "daily") -> Dict[str, Any]:
        """Get comprehensive cost dashboard for admin."""
        
        try:
            redis = await get_redis_client()
            if not redis:
                return {"error": "Redis not available"}
            
            now = datetime.utcnow()
            
            if period == "daily":
                date_key = now.strftime("%Y-%m-%d")
                period_label = f"Today ({date_key})"
            elif period == "monthly":
                date_key = now.strftime("%Y-%m")
                period_label = f"This Month ({date_key})"
            else:
                date_key = now.strftime("%Y-%m-%d")
                period_label = "Today"
            
            # Get total costs and calls
            if period == "daily":
                total_cost = float(await redis.get(f"cost:daily:{date_key}") or 0)
                total_calls = int(await redis.get(f"calls:daily:{date_key}") or 0)
                successful_calls = int(await redis.get(f"success:daily:{date_key}") or 0)
                failed_calls = int(await redis.get(f"failure:daily:{date_key}") or 0)
            else:
                # Calculate monthly totals
                total_cost = 0.0
                total_calls = 0
                successful_calls = 0
                failed_calls = 0
                
                for day in range(1, 32):
                    try:
                        day_key = now.replace(day=day).strftime("%Y-%m-%d")
                        total_cost += float(await redis.get(f"cost:daily:{day_key}") or 0)
                        total_calls += int(await redis.get(f"calls:daily:{day_key}") or 0)
                        successful_calls += int(await redis.get(f"success:daily:{day_key}") or 0)
                        failed_calls += int(await redis.get(f"failure:daily:{day_key}") or 0)
                    except:
                        continue
            
            # Get cost by provider
            cost_by_provider = {}
            for provider in APIProvider:
                if period == "daily":
                    provider_cost = float(await redis.get(f"cost:provider:{provider.value}:{date_key}") or 0)
                else:
                    provider_cost = 0.0
                    for day in range(1, 32):
                        try:
                            day_key = now.replace(day=day).strftime("%Y-%m-%d")
                            provider_cost += float(await redis.get(f"cost:provider:{provider.value}:{day_key}") or 0)
                        except:
                            continue
                
                if provider_cost > 0:
                    cost_by_provider[provider.value] = provider_cost
            
            # Get cost by category
            cost_by_category = {}
            for provider, cost in cost_by_provider.items():
                provider_enum = APIProvider(provider)
                category = self.provider_costs.get(provider_enum, {}).get("category", CostCategory.OTHER)
                cost_by_category[category.value] = cost_by_category.get(category.value, 0) + cost
            
            # Get top users by cost
            top_users = await self._get_top_users_by_cost(period)
            
            # Get rate limit status
            rate_limit_summary = {
                provider.value: {
                    "current_usage": status.current_usage,
                    "limit": status.limit,
                    "usage_percentage": status.usage_percentage,
                    "is_approaching_limit": status.is_approaching_limit
                }
                for provider, status in self.rate_limit_status.items()
            }
            
            # Generate optimization suggestions
            optimization_suggestions = await self._generate_optimization_suggestions(
                cost_by_provider, total_cost
            )
            
            return {
                "success": True,
                "period": period_label,
                "summary": {
                    "total_cost_usd": round(total_cost, 4),
                    "total_calls": total_calls,
                    "successful_calls": successful_calls,
                    "failed_calls": failed_calls,
                    "success_rate": round((successful_calls / max(total_calls, 1)) * 100, 2),
                    "avg_cost_per_call": round(total_cost / max(total_calls, 1), 6)
                },
                "cost_breakdown": {
                    "by_provider": cost_by_provider,
                    "by_category": cost_by_category
                },
                "top_users": top_users,
                "rate_limits": rate_limit_summary,
                "optimization_suggestions": optimization_suggestions,
                "budget_status": {
                    "daily_budget_used": round((total_cost / self.budget_alerts["daily_warning"]) * 100, 1) if period == "daily" else 0,
                    "monthly_budget_used": round((total_cost / self.budget_alerts["monthly_warning"]) * 100, 1) if period == "monthly" else 0
                },
                "timestamp": now.isoformat()
            }
            
        except Exception as e:
            self.logger.error("Failed to get cost dashboard", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_top_users_by_cost(self, period: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top users by API cost."""
        
        try:
            redis = await get_redis_client()
            if not redis:
                return []
            
            now = datetime.utcnow()
            user_costs = {}
            
            if period == "daily":
                date_key = now.strftime("%Y-%m-%d")
                # Get all user cost keys for today
                pattern = f"cost:user:*:{date_key}"
                keys = await redis.keys(pattern)
                
                for key in keys:
                    user_id = key.split(":")[2]  # Extract user_id from key
                    cost = float(await redis.get(key) or 0)
                    user_costs[user_id] = cost
            
            # Sort by cost descending
            sorted_users = sorted(user_costs.items(), key=lambda x: x[1], reverse=True)[:limit]
            
            return [
                {
                    "user_id": user_id,
                    "cost_usd": round(cost, 4),
                    "percentage_of_total": round((cost / sum(user_costs.values())) * 100, 2) if user_costs else 0
                }
                for user_id, cost in sorted_users
            ]
            
        except Exception as e:
            self.logger.error("Failed to get top users by cost", error=str(e))
            return []
    
    async def _generate_optimization_suggestions(
        self,
        cost_by_provider: Dict[str, float],
        total_cost: float
    ) -> List[str]:
        """Generate cost optimization suggestions."""
        
        suggestions = []
        
        try:
            # Analyze provider costs
            if not cost_by_provider:
                return suggestions
            
            # Find most expensive provider
            most_expensive = max(cost_by_provider.items(), key=lambda x: x[1])
            most_expensive_provider, highest_cost = most_expensive
            
            # High AI model costs
            ai_cost = sum(
                cost for provider, cost in cost_by_provider.items()
                if provider in ["openai_gpt4", "anthropic_claude", "google_gemini"]
            )
            
            if ai_cost > total_cost * 0.7:  # AI costs > 70% of total
                suggestions.append(
                    f"AI model costs are {round((ai_cost/total_cost)*100, 1)}% of total. "
                    "Consider optimizing prompt lengths or using more cost-effective models for simpler tasks."
                )
            
            # High exchange API costs
            exchange_cost = sum(
                cost for provider, cost in cost_by_provider.items()
                if "api" in provider and provider not in ["openai_gpt4", "anthropic_claude", "google_gemini"]
            )
            
            if exchange_cost > total_cost * 0.3:  # Exchange costs > 30%
                suggestions.append(
                    "Exchange API costs are high. Consider implementing request caching "
                    "or using WebSocket connections for real-time data."
                )
            
            # Rate limit approaching
            approaching_limits = [
                provider for provider, status in self.rate_limit_status.items()
                if status.is_approaching_limit
            ]
            
            if approaching_limits:
                suggestions.append(
                    f"Rate limits approaching for: {', '.join([p.value for p in approaching_limits])}. "
                    "Consider implementing request queuing or upgrading API tiers."
                )
            
            # Daily budget threshold
            if total_cost > self.budget_alerts["daily_warning"]:
                suggestions.append(
                    f"Daily costs (${total_cost:.2f}) exceed warning threshold "
                    f"(${self.budget_alerts['daily_warning']:.2f}). Review high-cost operations."
                )
            
        except Exception as e:
            self.logger.error("Failed to generate optimization suggestions", error=str(e))
        
        return suggestions
    
    async def _send_budget_alert(self, alert_type: str, current_cost: float, user_id: Optional[str]):
        """Send budget threshold alert."""
        
        try:
            # Prevent spam - only send alert once per hour for each type
            redis = await get_redis_client()
            if redis:
                alert_key = f"budget_alert:{alert_type}:{datetime.utcnow().strftime('%Y-%m-%d-%H')}"
                if await redis.exists(alert_key):
                    return  # Alert already sent this hour
                
                await redis.set(alert_key, "sent", ex=3600)  # 1 hour expiry
            
            # Send alert via multiple channels
            alert_message = f"🚨 Budget Alert: {alert_type.replace('_', ' ').title()} - Current cost: ${current_cost:.2f}"
            
            # WebSocket alert
            from app.services.websocket import manager
            await manager.broadcast_to_all({
                "type": "budget_alert",
                "alert_type": alert_type,
                "current_cost": current_cost,
                "message": alert_message,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Log critical alert
            self.logger.critical(
                "Budget threshold exceeded",
                alert_type=alert_type,
                current_cost=current_cost,
                user_id=user_id
            )
            
        except Exception as e:
            self.logger.error("Failed to send budget alert", error=str(e))
    
    async def _send_rate_limit_alert(self, provider: APIProvider, usage_percentage: float):
        """Send rate limit approaching alert."""
        
        try:
            # Prevent spam
            redis = await get_redis_client()
            if redis:
                alert_key = f"rate_limit_alert:{provider.value}:{datetime.utcnow().strftime('%Y-%m-%d-%H-%M')}"
                if await redis.exists(alert_key):
                    return
                
                await redis.set(alert_key, "sent", ex=300)  # 5 minutes expiry
            
            alert_message = f"⚠️ Rate Limit Alert: {provider.value} at {usage_percentage:.1f}% capacity"
            
            # WebSocket alert
            from app.services.websocket import manager
            await manager.broadcast_to_all({
                "type": "rate_limit_alert",
                "provider": provider.value,
                "usage_percentage": usage_percentage,
                "message": alert_message,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            self.logger.warning(
                "Rate limit approaching",
                provider=provider.value,
                usage_percentage=usage_percentage
            )
            
        except Exception as e:
            self.logger.error("Failed to send rate limit alert", error=str(e))
    
    async def get_user_cost_summary(self, user_id: str, period: str = "daily") -> Dict[str, Any]:
        """Get cost summary for specific user."""
        
        try:
            redis = await get_redis_client()
            if not redis:
                return {"error": "Redis not available"}
            
            now = datetime.utcnow()
            
            if period == "daily":
                date_key = now.strftime("%Y-%m-%d")
                user_cost = float(await redis.get(f"cost:user:{user_id}:{date_key}") or 0)
                user_calls = int(await redis.get(f"calls:user:{user_id}:{date_key}") or 0)
            else:
                # Monthly calculation
                user_cost = 0.0
                user_calls = 0
                
                for day in range(1, 32):
                    try:
                        day_key = now.replace(day=day).strftime("%Y-%m-%d")
                        user_cost += float(await redis.get(f"cost:user:{user_id}:{day_key}") or 0)
                        user_calls += int(await redis.get(f"calls:user:{user_id}:{day_key}") or 0)
                    except:
                        continue
            
            return {
                "success": True,
                "user_id": user_id,
                "period": period,
                "total_cost_usd": round(user_cost, 4),
                "total_calls": user_calls,
                "avg_cost_per_call": round(user_cost / max(user_calls, 1), 6),
                "timestamp": now.isoformat()
            }
            
        except Exception as e:
            self.logger.error("Failed to get user cost summary", user_id=user_id, error=str(e))
            return {
                "success": False,
                "error": str(e)
            }


# Global API cost tracker instance
api_cost_tracker = APICostTracker()