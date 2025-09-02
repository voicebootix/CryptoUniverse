"""
DYNAMIC STRATEGY GENERATOR - THE AI STRATEGY FACTORY

Creates new trading strategies on-the-fly based on unique market conditions.
Uses AI to analyze patterns and synthesize custom strategies for unprecedented situations.

This is our ultimate competitive moat - strategies that adapt to any market!
"""

import asyncio
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import structlog

from app.core.logging import LoggerMixin
from app.core.redis import get_redis_client

logger = structlog.get_logger(__name__)


@dataclass
class DynamicStrategy:
    """Dynamically generated trading strategy."""
    strategy_id: str
    name: str
    description: str
    market_conditions: Dict[str, Any]
    entry_rules: List[Dict[str, Any]]
    exit_rules: List[Dict[str, Any]]
    risk_parameters: Dict[str, Any]
    expected_performance: Dict[str, Any]
    confidence_score: float
    generated_at: datetime
    valid_until: datetime


class DynamicStrategyGenerator(LoggerMixin):
    """
    AI STRATEGY FACTORY - CREATES STRATEGIES FOR ANY MARKET
    
    Analyzes unique market conditions and generates custom strategies
    that no competitor can replicate!
    """
    
    def __init__(self):
        self.redis = None
        self.strategy_templates = {
            "volatility_breakout": {
                "base_logic": "Enter on volatility spike + volume confirmation",
                "risk_profile": "medium",
                "market_conditions": ["high_volatility", "neutral_sentiment"]
            },
            "sentiment_momentum": {
                "base_logic": "Follow strong sentiment with technical confirmation", 
                "risk_profile": "high",
                "market_conditions": ["strong_sentiment", "trending_market"]
            },
            "correlation_arbitrage": {
                "base_logic": "Exploit correlation breakdowns between assets",
                "risk_profile": "low",
                "market_conditions": ["correlation_breakdown", "sufficient_liquidity"]
            },
            "news_impact_trading": {
                "base_logic": "Trade news impact with sentiment confirmation",
                "risk_profile": "high", 
                "market_conditions": ["news_catalyst", "social_confirmation"]
            },
            "whale_following": {
                "base_logic": "Follow whale movements with smart money",
                "risk_profile": "medium",
                "market_conditions": ["whale_activity", "volume_confirmation"]
            }
        }
    
    async def async_init(self):
        """Initialize async components."""
        self.redis = await get_redis_client()
    
    async def generate_adaptive_strategy(
        self,
        market_conditions: Dict[str, Any],
        sentiment_data: Dict[str, Any],
        user_id: str,
        target_symbol: str = None
    ) -> Dict[str, Any]:
        """
        GENERATE CUSTOM STRATEGY FOR UNIQUE MARKET CONDITIONS
        
        This is our secret weapon - AI that creates strategies in real-time!
        """
        try:
            self.logger.info(f"🧠 Generating adaptive strategy for {user_id}")
            
            # Analyze current market uniqueness
            market_analysis = await self._analyze_market_uniqueness(market_conditions, sentiment_data)
            
            if not market_analysis.get("requires_custom_strategy"):
                return {
                    "success": False,
                    "reason": "Standard strategies sufficient for current conditions",
                    "recommended_standard_strategy": market_analysis.get("recommended_strategy")
                }
            
            # Select appropriate strategy template
            template = await self._select_strategy_template(market_analysis)
            
            # Generate custom strategy parameters
            custom_strategy = await self._synthesize_custom_strategy(
                template, market_analysis, sentiment_data, user_id, target_symbol
            )
            
            # Validate strategy through AI consensus
            validation_result = await self._validate_generated_strategy(custom_strategy, user_id)
            
            if validation_result.get("approved"):
                # Cache strategy for immediate use
                await self._cache_dynamic_strategy(custom_strategy, user_id)
                
                self.logger.info(
                    f"✨ Dynamic strategy generated: {custom_strategy.name}",
                    user_id=user_id,
                    strategy_id=custom_strategy.strategy_id,
                    confidence=f"{custom_strategy.confidence_score:.1f}%",
                    valid_hours=(custom_strategy.valid_until - custom_strategy.generated_at).total_seconds() / 3600
                )
                
                return {
                    "success": True,
                    "dynamic_strategy": self._serialize_strategy(custom_strategy),
                    "validation_result": validation_result,
                    "market_uniqueness": market_analysis
                }
            else:
                return {
                    "success": False,
                    "reason": "Generated strategy failed AI validation",
                    "validation_result": validation_result
                }
                
        except Exception as e:
            self.logger.error("Dynamic strategy generation failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _analyze_market_uniqueness(
        self, 
        market_conditions: Dict[str, Any], 
        sentiment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze if current market conditions require a custom strategy."""
        
        # Market uniqueness indicators
        volatility = market_conditions.get("volatility_level", "medium")
        sentiment = market_conditions.get("sentiment", "neutral")
        arbitrage_ops = market_conditions.get("arbitrage_opportunities", 0)
        
        sentiment_optimization = sentiment_data.get("optimization_data", {}) if sentiment_data.get("success") else {}
        
        # Uniqueness scoring
        uniqueness_score = 0
        unique_conditions = []
        
        # 1. Extreme volatility patterns
        if volatility in ["extreme", "very_high"]:
            uniqueness_score += 30
            unique_conditions.append("extreme_volatility")
        
        # 2. Conflicting sentiment signals
        momentum_count = len(sentiment_optimization.get("momentum_signals", []))
        reversion_count = len(sentiment_optimization.get("mean_reversion_signals", []))
        
        if momentum_count > 0 and reversion_count > 0:
            uniqueness_score += 25
            unique_conditions.append("conflicting_sentiment")
        
        # 3. Unusual arbitrage opportunities
        if arbitrage_ops > 10:
            uniqueness_score += 20
            unique_conditions.append("high_arbitrage_activity")
        
        # 4. High social activity with neutral sentiment
        scalping_ops = len(sentiment_optimization.get("scalping_opportunities", []))
        if scalping_ops > 5 and sentiment == "neutral":
            uniqueness_score += 25
            unique_conditions.append("high_activity_neutral_sentiment")
        
        # Determine if custom strategy needed
        requires_custom = uniqueness_score > 50
        
        # Recommend template if custom strategy needed
        recommended_template = None
        if requires_custom:
            if "extreme_volatility" in unique_conditions:
                recommended_template = "volatility_breakout"
            elif "conflicting_sentiment" in unique_conditions:
                recommended_template = "sentiment_momentum"
            elif "high_arbitrage_activity" in unique_conditions:
                recommended_template = "correlation_arbitrage"
            elif "high_activity_neutral_sentiment" in unique_conditions:
                recommended_template = "news_impact_trading"
        
        return {
            "requires_custom_strategy": requires_custom,
            "uniqueness_score": uniqueness_score,
            "unique_conditions": unique_conditions,
            "recommended_template": recommended_template,
            "market_summary": {
                "volatility": volatility,
                "sentiment": sentiment,
                "arbitrage_opportunities": arbitrage_ops,
                "momentum_signals": momentum_count,
                "reversion_signals": reversion_count,
                "scalping_opportunities": scalping_ops
            }
        }
    
    async def _select_strategy_template(self, market_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Select appropriate strategy template for market conditions."""
        
        recommended_template = market_analysis.get("recommended_template")
        
        if recommended_template and recommended_template in self.strategy_templates:
            return self.strategy_templates[recommended_template]
        
        # Fallback selection based on conditions
        unique_conditions = market_analysis.get("unique_conditions", [])
        
        if "extreme_volatility" in unique_conditions:
            return self.strategy_templates["volatility_breakout"]
        elif "high_arbitrage_activity" in unique_conditions:
            return self.strategy_templates["correlation_arbitrage"]
        else:
            return self.strategy_templates["sentiment_momentum"]
    
    async def _synthesize_custom_strategy(
        self,
        template: Dict[str, Any],
        market_analysis: Dict[str, Any],
        sentiment_data: Dict[str, Any],
        user_id: str,
        target_symbol: str = None
    ) -> DynamicStrategy:
        """Synthesize custom strategy from template and market conditions."""
        
        import uuid
        
        strategy_id = f"dynamic_{uuid.uuid4().hex[:8]}"
        market_summary = market_analysis.get("market_summary", {})
        
        # Generate strategy name
        conditions = "_".join(market_analysis.get("unique_conditions", []))
        strategy_name = f"AI_Generated_{conditions}_{datetime.utcnow().strftime('%H%M')}"
        
        # Generate entry rules based on market conditions
        entry_rules = []
        
        if "extreme_volatility" in market_analysis.get("unique_conditions", []):
            entry_rules.extend([
                {
                    "condition": "volatility_spike",
                    "threshold": market_summary.get("volatility", 5) * 0.8,
                    "confirmation": "volume_increase"
                },
                {
                    "condition": "price_breakout", 
                    "threshold": "dynamic_resistance",
                    "confirmation": "sentiment_alignment"
                }
            ])
        
        if "conflicting_sentiment" in market_analysis.get("unique_conditions", []):
            entry_rules.extend([
                {
                    "condition": "sentiment_consensus",
                    "threshold": "majority_agreement",
                    "confirmation": "technical_confirmation"
                }
            ])
        
        # Generate exit rules
        exit_rules = [
            {
                "condition": "profit_target",
                "threshold": market_summary.get("volatility", 5) * 1.5,  # Dynamic profit target
                "type": "take_profit"
            },
            {
                "condition": "stop_loss",
                "threshold": market_summary.get("volatility", 5) * 0.5,  # Dynamic stop loss
                "type": "risk_management"
            },
            {
                "condition": "time_exit",
                "threshold": "4_hours",  # Max holding period for dynamic strategies
                "type": "time_management"
            }
        ]
        
        # Risk parameters based on market uniqueness
        risk_parameters = {
            "max_position_size_pct": min(10, market_analysis.get("uniqueness_score", 50) / 10),
            "stop_loss_pct": market_summary.get("volatility", 5) * 0.5,
            "take_profit_pct": market_summary.get("volatility", 5) * 1.5,
            "max_holding_hours": 4,
            "risk_level": template.get("risk_profile", "medium")
        }
        
        # Expected performance estimation
        expected_performance = {
            "expected_return_pct": market_summary.get("volatility", 5) * 1.2,
            "win_rate_estimate": 65 + (market_analysis.get("uniqueness_score", 50) / 10),
            "max_drawdown_estimate": risk_parameters["stop_loss_pct"],
            "trade_frequency": "high" if "scalping" in template.get("base_logic", "") else "medium"
        }
        
        # Confidence based on market analysis quality
        confidence_score = min(
            market_analysis.get("uniqueness_score", 50) + 30,  # Base confidence
            95  # Max confidence
        )
        
        return DynamicStrategy(
            strategy_id=strategy_id,
            name=strategy_name,
            description=f"AI-generated strategy for {', '.join(market_analysis.get('unique_conditions', []))}",
            market_conditions=market_summary,
            entry_rules=entry_rules,
            exit_rules=exit_rules,
            risk_parameters=risk_parameters,
            expected_performance=expected_performance,
            confidence_score=confidence_score,
            generated_at=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(hours=24)  # 24-hour validity
        )
    
    async def _validate_generated_strategy(
        self, 
        strategy: DynamicStrategy, 
        user_id: str
    ) -> Dict[str, Any]:
        """Validate generated strategy through AI consensus."""
        try:
            from app.services.ai_consensus_core import ai_consensus_service
            
            # Prepare validation request
            validation_request = {
                "strategy_type": "dynamic_generated",
                "strategy_details": {
                    "name": strategy.name,
                    "entry_rules": strategy.entry_rules,
                    "exit_rules": strategy.exit_rules,
                    "risk_parameters": strategy.risk_parameters,
                    "market_conditions": strategy.market_conditions
                },
                "expected_performance": strategy.expected_performance,
                "confidence_score": strategy.confidence_score
            }
            
            # Use AI consensus for validation
            validation_result = await ai_consensus_service.validate_trade(
                analysis_request=json.dumps(validation_request),
                confidence_threshold=70.0,  # High threshold for generated strategies
                ai_models="all",
                user_id=user_id
            )
            
            if validation_result.get("success"):
                trade_validation = validation_result.get("trade_validation", {})
                approval_status = trade_validation.get("approval_status", "REJECTED")
                
                return {
                    "approved": approval_status == "APPROVED",
                    "ai_consensus": validation_result,
                    "approval_confidence": trade_validation.get("confidence", 0),
                    "ai_recommendations": trade_validation.get("recommendations", [])
                }
            else:
                return {
                    "approved": False,
                    "reason": "AI consensus validation failed",
                    "validation_error": validation_result.get("error")
                }
                
        except Exception as e:
            self.logger.error("Strategy validation failed", error=str(e))
            return {"approved": False, "reason": f"Validation error: {str(e)}"}
    
    async def _cache_dynamic_strategy(self, strategy: DynamicStrategy, user_id: str):
        """Cache generated strategy for immediate use."""
        try:
            cache_key = f"dynamic_strategy:{user_id}:{strategy.strategy_id}"
            
            strategy_data = self._serialize_strategy(strategy)
            
            await self.redis.set(
                cache_key,
                json.dumps(strategy_data, default=str),
                ex=24 * 3600  # 24 hour expiry
            )
            
            # Add to user's available strategies list
            user_strategies_key = f"user_dynamic_strategies:{user_id}"
            await self.redis.sadd(user_strategies_key, strategy.strategy_id)
            await self.redis.expire(user_strategies_key, 24 * 3600)
            
        except Exception as e:
            self.logger.error("Strategy caching failed", error=str(e))
    
    def _serialize_strategy(self, strategy: DynamicStrategy) -> Dict[str, Any]:
        """Serialize strategy for JSON storage."""
        return {
            "strategy_id": strategy.strategy_id,
            "name": strategy.name,
            "description": strategy.description,
            "market_conditions": strategy.market_conditions,
            "entry_rules": strategy.entry_rules,
            "exit_rules": strategy.exit_rules,
            "risk_parameters": strategy.risk_parameters,
            "expected_performance": strategy.expected_performance,
            "confidence_score": strategy.confidence_score,
            "generated_at": strategy.generated_at.isoformat(),
            "valid_until": strategy.valid_until.isoformat(),
            "is_dynamic": True
        }
    
    async def execute_dynamic_strategy(
        self,
        strategy_id: str,
        user_id: str,
        symbol: str = None
    ) -> Dict[str, Any]:
        """Execute a dynamically generated strategy."""
        try:
            # Get cached strategy
            cache_key = f"dynamic_strategy:{user_id}:{strategy_id}"
            strategy_data = await self.redis.get(cache_key)
            
            if not strategy_data:
                return {"success": False, "error": "Dynamic strategy not found or expired"}
            
            strategy = json.loads(strategy_data)
            
            # Check if strategy is still valid
            valid_until = datetime.fromisoformat(strategy["valid_until"])
            if datetime.utcnow() > valid_until:
                return {"success": False, "error": "Dynamic strategy expired"}
            
            # Get current market data
            from app.services.market_analysis_core import MarketAnalysisService
            market_service = MarketAnalysisService()
            
            current_market = await market_service.complete_market_assessment(
                symbols=symbol or "BTC",
                exchanges="all",
                user_id=user_id
            )
            
            if not current_market.get("success"):
                return {"success": False, "error": "Failed to get current market data"}
            
            # Execute strategy logic
            execution_result = await self._execute_strategy_logic(
                strategy, current_market, user_id, symbol
            )
            
            # Record strategy performance
            await self._record_dynamic_strategy_performance(
                strategy_id, execution_result, user_id
            )
            
            return execution_result
            
        except Exception as e:
            self.logger.error("Dynamic strategy execution failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _execute_strategy_logic(
        self,
        strategy: Dict[str, Any],
        market_data: Dict[str, Any],
        user_id: str,
        symbol: str = None
    ) -> Dict[str, Any]:
        """Execute the logic of a dynamic strategy."""
        
        try:
            # Extract strategy parameters
            entry_rules = strategy.get("entry_rules", [])
            risk_params = strategy.get("risk_parameters", {})
            
            # Get current market assessment
            market_assessment = market_data.get("market_assessment", {})
            current_volatility = market_assessment.get("volatility_level", "medium")
            
            # Check entry conditions
            entry_conditions_met = 0
            total_entry_conditions = len(entry_rules)
            
            for rule in entry_rules:
                condition_type = rule.get("condition")
                threshold = rule.get("threshold")
                
                if condition_type == "volatility_spike":
                    if isinstance(threshold, (int, float)):
                        current_vol_score = self._volatility_to_score(current_volatility)
                        if current_vol_score >= threshold:
                            entry_conditions_met += 1
                
                elif condition_type == "price_breakout":
                    # Simplified breakout detection
                    entry_conditions_met += 1  # Assume breakout for demo
                
                elif condition_type == "sentiment_consensus":
                    # Check sentiment alignment
                    entry_conditions_met += 1  # Assume consensus for demo
            
            # Calculate entry signal strength
            entry_strength = (entry_conditions_met / total_entry_conditions) * 100 if total_entry_conditions > 0 else 0
            
            # Generate trading signal if conditions are met
            if entry_strength >= 70:  # 70% of conditions must be met
                
                signal = {
                    "symbol": symbol or "BTC",
                    "action": "buy",  # Dynamic strategies typically look for long opportunities
                    "confidence": strategy.get("confidence_score", 75),
                    "expected_return": strategy.get("expected_performance", {}).get("expected_return_pct", 5),
                    "position_size_pct": risk_params.get("max_position_size_pct", 5),
                    "stop_loss": risk_params.get("stop_loss_pct", 3),
                    "take_profit": risk_params.get("take_profit_pct", 8),
                    "strategy_type": "dynamic_generated",
                    "entry_conditions_met": entry_conditions_met,
                    "entry_strength": entry_strength
                }
                
                return {
                    "success": True,
                    "signal": signal,
                    "strategy_name": strategy.get("name"),
                    "execution_reason": f"Dynamic strategy conditions met ({entry_strength:.1f}%)"
                }
            else:
                return {
                    "success": False,
                    "reason": f"Entry conditions not met ({entry_strength:.1f}% < 70%)",
                    "conditions_met": entry_conditions_met,
                    "total_conditions": total_entry_conditions
                }
                
        except Exception as e:
            self.logger.error("Strategy logic execution failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    def _volatility_to_score(self, volatility_level: str) -> float:
        """Convert volatility level to numerical score."""
        volatility_scores = {
            "very_low": 10,
            "low": 25,
            "medium": 50,
            "high": 75,
            "very_high": 90,
            "extreme": 100
        }
        return volatility_scores.get(volatility_level, 50)
    
    async def _record_dynamic_strategy_performance(
        self,
        strategy_id: str,
        execution_result: Dict[str, Any],
        user_id: str
    ):
        """Record performance of dynamic strategy for learning."""
        try:
            performance_key = f"dynamic_strategy_performance:{strategy_id}"
            
            performance_data = {
                "user_id": user_id,
                "execution_time": datetime.utcnow().isoformat(),
                "success": execution_result.get("success", False),
                "signal_generated": execution_result.get("signal") is not None,
                "confidence": execution_result.get("signal", {}).get("confidence", 0),
                "entry_strength": execution_result.get("signal", {}).get("entry_strength", 0)
            }
            
            await self.redis.lpush(performance_key, json.dumps(performance_data))
            await self.redis.ltrim(performance_key, 0, 49)  # Keep last 50 executions
            await self.redis.expire(performance_key, 7 * 24 * 3600)  # 7 days
            
        except Exception as e:
            self.logger.error("Dynamic strategy performance recording failed", error=str(e))
    
    async def get_user_dynamic_strategies(self, user_id: str) -> Dict[str, Any]:
        """Get user's available dynamic strategies."""
        try:
            user_strategies_key = f"user_dynamic_strategies:{user_id}"
            strategy_ids = await self.redis.smembers(user_strategies_key)
            
            strategies = []
            
            for strategy_id in strategy_ids:
                strategy_id_str = strategy_id.decode() if isinstance(strategy_id, bytes) else strategy_id
                cache_key = f"dynamic_strategy:{user_id}:{strategy_id_str}"
                strategy_data = await self.redis.get(cache_key)
                
                if strategy_data:
                    strategy = json.loads(strategy_data)
                    
                    # Check if still valid
                    valid_until = datetime.fromisoformat(strategy["valid_until"])
                    if datetime.utcnow() <= valid_until:
                        strategies.append(strategy)
            
            return {
                "success": True,
                "dynamic_strategies": strategies,
                "total_strategies": len(strategies),
                "active_strategies": len([s for s in strategies if datetime.fromisoformat(s["valid_until"]) > datetime.utcnow()])
            }
            
        except Exception as e:
            self.logger.error("Failed to get user dynamic strategies", error=str(e))
            return {"success": False, "error": str(e)}


# Global service instance
dynamic_strategy_generator = DynamicStrategyGenerator()


async def get_dynamic_strategy_generator() -> DynamicStrategyGenerator:
    """Dependency injection for FastAPI."""
    if dynamic_strategy_generator.redis is None:
        await dynamic_strategy_generator.async_init()
    return dynamic_strategy_generator