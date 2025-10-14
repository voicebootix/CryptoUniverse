#!/usr/bin/env python3
"""
Simple Strategy Testing - Test strategy scanners without full app dependencies
"""

import asyncio
import json
import sys
import traceback
from datetime import datetime
from typing import Dict, List, Any

# Mock the required classes and functions
class MockOpportunityResult:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class MockUserOpportunityProfile:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.active_strategy_count = 14
        self.total_monthly_strategy_cost = 0
        self.user_tier = "enterprise"
        self.max_asset_tier = "tier_professional"
        self.opportunity_scan_limit = 100
        self.last_scan_time = None
        self.strategy_fingerprint = "test"

class MockTradingStrategiesService:
    async def execute_strategy(self, function: str, **kwargs):
        """Mock trading strategies service responses"""
        
        # Simulate different responses based on function
        if function == "portfolio_optimization":
            return {
                "success": True,
                "execution_result": {
                    "rebalancing_recommendations": [
                        {
                            "strategy": "BTC",
                            "improvement_potential": "15%",
                            "target_weight": "0.4",
                            "value_change": 1000
                        }
                    ]
                },
                "optimization_summary": {
                    "portfolio_value": 5000,
                    "expected_return": 0.12
                }
            }
        elif function == "risk_management":
            return {
                "success": True,
                "risk_management_analysis": {
                    "mitigation_strategies": [
                        {
                            "risk_type": "volatility",
                            "strategy": "Hedge with BTC options",
                            "urgency": 0.8,
                            "cost_estimate": 200
                        }
                    ]
                }
            }
        elif function == "spot_momentum_strategy":
            return {
                "success": True,
                "signal": {
                    "strength": 7.5,
                    "confidence": 0.85,
                    "action": "BUY",
                    "direction": "long"
                },
                "execution_result": {
                    "indicators": {
                        "price": {"current": 45000}
                    },
                    "risk_management": {
                        "take_profit": 500,
                        "take_profit_price": 46000
                    }
                }
            }
        elif function == "funding_arbitrage":
            return {
                "success": True,
                "funding_arbitrage_analysis": {
                    "opportunities": [
                        {
                            "symbol": "BTC/USDT",
                            "exchange": "binance",
                            "profit_potential": 150,
                            "confidence": 0.75,
                            "risk_level": "medium",
                            "required_capital": 2000,
                            "timeframe": "8h",
                            "entry_price": 45000,
                            "exit_price": 45150,
                            "funding_rate_long": 0.01,
                            "funding_rate_short": 0.005,
                            "spread_percentage": 0.5
                        }
                    ]
                }
            }
        elif function == "statistical_arbitrage":
            return {
                "success": True,
                "statistical_arbitrage_analysis": {
                    "opportunities": [
                        {
                            "symbol": "ETH/USDT",
                            "exchange": "binance",
                            "profit_potential": 200,
                            "confidence": 0.8,
                            "risk_level": "medium_high",
                            "required_capital": 5000,
                            "timeframe": "24h",
                            "entry_price": 3000,
                            "target_price": 3200,
                            "z_score": 2.5,
                            "correlation": 0.85,
                            "lookback_period": "30d"
                        }
                    ]
                }
            }
        elif function == "pairs_trading":
            return {
                "success": True,
                "trading_signals": {
                    "signal_strength": 6.5,
                    "expected_profit": 300,
                    "required_capital": 10000,
                    "timeframe": "72h",
                    "entry_price": 45000,
                    "exit_price": 46000,
                    "spread_z_score": 2.1,
                    "signal_type": "mean_reversion"
                },
                "correlation_analysis": {
                    "correlation": 0.92
                }
            }
        elif function == "spot_mean_reversion":
            return {
                "success": True,
                "signals": {
                    "deviation_score": 2.3,
                    "confidence": 0.78,
                    "reversion_target": 250,
                    "min_capital": 2000,
                    "entry_price": 3000,
                    "mean_price": 3250,
                    "rsi": 25,
                    "bollinger_position": 0.1
                }
            }
        elif function == "spot_breakout_strategy":
            return {
                "success": True,
                "breakout_signals": {
                    "breakout_probability": 0.85,
                    "profit_potential": 400,
                    "min_capital": 3000,
                    "breakout_price": 46000,
                    "target_price": 48000,
                    "support_level": 44000,
                    "resistance_level": 46000,
                    "volume_surge": 3.2,
                    "direction": "up"
                }
            }
        elif function == "scalping_strategy":
            return {
                "success": True,
                "signal": {
                    "momentum_score": 8.2,
                    "direction": "long",
                    "profit_potential": 50,
                    "required_capital": 1000,
                    "entry_price": 45000,
                    "target_price": 45050,
                    "volume_surge": 2.5,
                    "rsi": 75,
                    "duration_min": 5
                }
            }
        elif function == "market_making":
            return {
                "success": True,
                "signal": {
                    "current_spread": 0.0025,
                    "daily_profit_est": 75,
                    "required_capital": 5000,
                    "bid_price": 44950,
                    "ask_price": 45050,
                    "volume_24h": 1000000,
                    "liquidity_score": 0.9,
                    "order_book_depth": {"bids": 100, "asks": 100},
                    "fills_per_hour": 15
                }
            }
        elif function == "futures_trade":
            return {
                "success": True,
                "signal": {
                    "leverage_score": 8.5,
                    "trend_strength": 7.8,
                    "profit_potential": 800,
                    "required_capital": 2000,
                    "entry_price": 45000,
                    "target_price": 47000,
                    "stop_loss_price": 44000,
                    "leverage": 10,
                    "margin_required": 200
                }
            }
        elif function == "options_trade":
            return {
                "success": True,
                "signal": {
                    "greeks_score": 7.2,
                    "iv_rank": 0.65,
                    "profit_potential": 600,
                    "required_capital": 3000,
                    "strike_price": 46000,
                    "expiry_days": 30,
                    "delta": 0.6,
                    "gamma": 0.02,
                    "theta": -0.5,
                    "vega": 0.3
                }
            }
        else:
            return {
                "success": False,
                "error": f"Unknown function: {function}"
            }

# Mock the service class
class MockUserOpportunityDiscoveryService:
    def __init__(self):
        self.trading_strategies_service = MockTradingStrategiesService()
        self.logger = self
        
    def info(self, msg, **kwargs):
        print(f"INFO: {msg}")
    
    def warning(self, msg, **kwargs):
        print(f"WARNING: {msg}")
    
    def error(self, msg, **kwargs):
        print(f"ERROR: {msg}")
    
    def debug(self, msg, **kwargs):
        print(f"DEBUG: {msg}")
    
    def _get_top_symbols_by_volume(self, discovered_assets, limit=10):
        """Mock method to get top symbols"""
        return ["BTC", "ETH", "ADA", "SOL", "DOT", "MATIC", "AVAX", "LINK", "UNI", "ATOM"][:limit]
    
    def _get_symbols_for_statistical_arbitrage(self, discovered_assets, limit=50):
        """Mock method for statistical arbitrage symbols"""
        return ["BTC", "ETH", "ADA", "SOL", "DOT", "MATIC", "AVAX", "LINK", "UNI", "ATOM"][:limit]
    
    def _get_correlation_pairs(self, discovered_assets, max_pairs=10):
        """Mock method for correlation pairs"""
        return [("BTC", "ETH"), ("ADA", "SOL"), ("DOT", "MATIC"), ("AVAX", "LINK")]
    
    def _signal_to_risk_level(self, signal_strength):
        """Convert signal strength to risk level"""
        if signal_strength > 8:
            return "high"
        elif signal_strength > 5:
            return "medium"
        else:
            return "low"
    
    def _to_fraction(self, value):
        """Convert value to fraction"""
        if value is None:
            return None
        try:
            if isinstance(value, str) and value.endswith('%'):
                return float(value[:-1]) / 100
            return float(value)
        except:
            return None
    
    def _to_float(self, value):
        """Convert value to float"""
        if value is None:
            return None
        try:
            return float(value)
        except:
            return None
    
    async def _estimate_user_deployable_capital(self, user_id, portfolio_result, optimization_result):
        """Mock capital estimation"""
        return {"deployable_capital_usd": 5000.0}

    # Portfolio Optimization Scanner
    async def _scan_portfolio_optimization_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Test portfolio optimization scanner"""
        opportunities = []
        
        try:
            optimization_result = await self.trading_strategies_service.execute_strategy(
                function="portfolio_optimization",
                user_id=user_profile.user_id,
                simulation_mode=True
            )
            
            if optimization_result.get("success"):
                execution_result = optimization_result.get("execution_result", {})
                rebalancing_recommendations = execution_result.get("rebalancing_recommendations", [])
                
                for rebal in rebalancing_recommendations:
                    opportunity = MockOpportunityResult(
                        strategy_id="ai_portfolio_optimization",
                        strategy_name="AI Portfolio Optimization",
                        opportunity_type="portfolio_rebalancing",
                        symbol=rebal.get("strategy", "UNKNOWN"),
                        exchange="multiple",
                        profit_potential_usd=float(rebal.get("value_change", 0)),
                        confidence_score=75.0,
                        risk_level="medium",
                        required_capital_usd=1000.0,
                        estimated_timeframe="24h",
                        entry_price=None,
                        exit_price=None,
                        metadata={"improvement_potential": rebal.get("improvement_potential")},
                        discovered_at=datetime.utcnow()
                    )
                    opportunities.append(opportunity)
            
        except Exception as e:
            self.error(f"Portfolio optimization scan failed: {e}")
        
        return opportunities

    # Risk Management Scanner
    async def _scan_risk_management_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Test risk management scanner"""
        opportunities = []
        
        try:
            hedge_result = await self.trading_strategies_service.execute_strategy(
                function="risk_management",
                user_id=user_profile.user_id,
                simulation_mode=True
            )
            
            if hedge_result.get("success"):
                risk_analysis = hedge_result.get("risk_management_analysis", {})
                mitigation_strategies = risk_analysis.get("mitigation_strategies", [])
                
                for recommendation in mitigation_strategies:
                    urgency = recommendation.get("urgency", 0.8)
                    if urgency > 0.3:
                        opportunity = MockOpportunityResult(
                            strategy_id="ai_risk_management",
                            strategy_name="AI Risk Management - Mitigation",
                            opportunity_type="risk_mitigation",
                            symbol=recommendation.get("recommendation", "Portfolio"),
                            exchange="multiple",
                            profit_potential_usd=0,
                            confidence_score=urgency * 100,
                            risk_level="low",
                            required_capital_usd=float(recommendation.get("cost_estimate", 100)),
                            estimated_timeframe="immediate",
                            entry_price=None,
                            exit_price=None,
                            metadata={
                                "risk_type": recommendation.get("risk_type", ""),
                                "strategy": recommendation.get("strategy", ""),
                                "portfolio_protection": True
                            },
                            discovered_at=datetime.utcnow()
                        )
                        opportunities.append(opportunity)
            
        except Exception as e:
            self.error(f"Risk management scan failed: {e}")
        
        return opportunities

    # Spot Momentum Scanner
    async def _scan_spot_momentum_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Test spot momentum scanner"""
        opportunities = []
        
        try:
            momentum_symbols = self._get_top_symbols_by_volume(discovered_assets, limit=5)
            
            for symbol in momentum_symbols:
                momentum_result = await self.trading_strategies_service.execute_strategy(
                    function="spot_momentum_strategy",
                    symbol=f"{symbol}/USDT",
                    parameters={"timeframe": "4h"},
                    user_id=user_profile.user_id,
                    simulation_mode=True
                )
                
                if momentum_result.get("success"):
                    signals = momentum_result.get("signal", {})
                    signal_strength = signals.get("strength", 0)
                    signal_confidence = signals.get("confidence", 0)
                    
                    if signal_strength >= 2.5:
                        execution_data = momentum_result.get("execution_result", {})
                        indicators = execution_data.get("indicators", {})
                        risk_mgmt = execution_data.get("risk_management", {})
                        
                        opportunity = MockOpportunityResult(
                            strategy_id="ai_spot_momentum_strategy",
                            strategy_name="AI Spot Momentum",
                            opportunity_type="spot_momentum",
                            symbol=symbol,
                            exchange="binance",
                            profit_potential_usd=float(risk_mgmt.get("take_profit", 100)),
                            confidence_score=float(signal_confidence) * 100 if signal_confidence else signal_strength * 10,
                            risk_level=self._signal_to_risk_level(signal_strength),
                            required_capital_usd=1000.0,
                            estimated_timeframe="4-24h",
                            entry_price=float((indicators.get("price") or {}).get("current", 0)) if indicators.get("price") else None,
                            exit_price=float(risk_mgmt.get("take_profit_price", 0)) if risk_mgmt.get("take_profit_price") else None,
                            metadata={
                                "signal_strength": signal_strength,
                                "signal_confidence": signal_confidence,
                                "signal_action": signals.get("action", "HOLD")
                            },
                            discovered_at=datetime.utcnow()
                        )
                        opportunities.append(opportunity)
            
        except Exception as e:
            self.error(f"Spot momentum scan failed: {e}")
        
        return opportunities

    # Funding Arbitrage Scanner
    async def _scan_funding_arbitrage_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Test funding arbitrage scanner"""
        opportunities = []
        
        try:
            top_symbols = self._get_top_symbols_by_volume(discovered_assets, limit=5)
            symbols_str = ",".join(top_symbols)
            
            arbitrage_result = await self.trading_strategies_service.execute_strategy(
                function="funding_arbitrage",
                parameters={
                    "symbols": symbols_str,
                    "exchanges": "all",
                    "min_funding_rate": 0.005
                },
                user_id=user_profile.user_id,
                simulation_mode=True
            )
            
            if arbitrage_result.get("success"):
                analysis_data = arbitrage_result.get("funding_arbitrage_analysis", {})
                opportunities_data = analysis_data.get("opportunities", [])
                
                for opp in opportunities_data:
                    opportunity = MockOpportunityResult(
                        strategy_id="ai_funding_arbitrage",
                        strategy_name="AI Funding Arbitrage",
                        opportunity_type="funding_arbitrage",
                        symbol=opp.get("symbol", ""),
                        exchange=opp.get("exchange", ""),
                        profit_potential_usd=float(opp.get("profit_potential", 0)),
                        confidence_score=float(opp.get("confidence", 0.7) * 100),
                        risk_level=opp.get("risk_level", "medium"),
                        required_capital_usd=float(opp.get("required_capital", 1000)),
                        estimated_timeframe=opp.get("timeframe", "8h"),
                        entry_price=opp.get("entry_price"),
                        exit_price=opp.get("exit_price"),
                        metadata={
                            "funding_rate_long": opp.get("funding_rate_long", 0),
                            "funding_rate_short": opp.get("funding_rate_short", 0),
                            "spread_percentage": opp.get("spread_percentage", 0)
                        },
                        discovered_at=datetime.utcnow()
                    )
                    opportunities.append(opportunity)
            
        except Exception as e:
            self.error(f"Funding arbitrage scan failed: {e}")
        
        return opportunities

    # Statistical Arbitrage Scanner
    async def _scan_statistical_arbitrage_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Test statistical arbitrage scanner"""
        opportunities = []
        
        try:
            universe_symbols = self._get_symbols_for_statistical_arbitrage(discovered_assets, limit=10)
            universe_str = ",".join(universe_symbols)
            
            stat_arb_result = await self.trading_strategies_service.execute_strategy(
                function="statistical_arbitrage",
                strategy_type="mean_reversion",
                parameters={"universe": universe_str},
                user_id=user_profile.user_id
            )
            
            if stat_arb_result.get("success"):
                analysis_data = stat_arb_result.get("statistical_arbitrage_analysis", {})
                opportunities_data = analysis_data.get("opportunities", [])
                
                for opp in opportunities_data:
                    opportunity = MockOpportunityResult(
                        strategy_id="ai_statistical_arbitrage",
                        strategy_name="AI Statistical Arbitrage",
                        opportunity_type="statistical_arbitrage",
                        symbol=opp.get("symbol", ""),
                        exchange=opp.get("exchange", "binance"),
                        profit_potential_usd=float(opp.get("profit_potential", 0)),
                        confidence_score=float(opp.get("confidence", 0.75) * 100),
                        risk_level=opp.get("risk_level", "medium_high"),
                        required_capital_usd=float(opp.get("required_capital", 5000)),
                        estimated_timeframe=opp.get("timeframe", "24h"),
                        entry_price=opp.get("entry_price"),
                        exit_price=opp.get("target_price"),
                        metadata={
                            "z_score": opp.get("z_score", 0),
                            "correlation": opp.get("correlation", 0),
                            "strategy_type": opp.get("strategy_type", "mean_reversion")
                        },
                        discovered_at=datetime.utcnow()
                    )
                    opportunities.append(opportunity)
            
        except Exception as e:
            self.error(f"Statistical arbitrage scan failed: {e}")
        
        return opportunities

    # Pairs Trading Scanner
    async def _scan_pairs_trading_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Test pairs trading scanner"""
        opportunities = []
        
        try:
            correlation_pairs = self._get_correlation_pairs(discovered_assets, max_pairs=3)
            
            for pair in correlation_pairs:
                pair_str = f"{pair[0]}-{pair[1]}"
                
                pairs_result = await self.trading_strategies_service.execute_strategy(
                    function="pairs_trading",
                    strategy_type="statistical_arbitrage",
                    parameters={"pair_symbols": pair_str},
                    user_id=user_profile.user_id
                )
                
                if pairs_result.get("success") and pairs_result.get("trading_signals"):
                    signals = pairs_result["trading_signals"]
                    signal_strength = signals.get("signal_strength", 0)
                    
                    if signal_strength > 3.0:
                        opportunity = MockOpportunityResult(
                            strategy_id="ai_pairs_trading",
                            strategy_name="AI Pairs Trading",
                            opportunity_type="pairs_trading",
                            symbol=pair_str,
                            exchange="binance",
                            profit_potential_usd=float(signals.get("expected_profit", 0)),
                            confidence_score=float(signal_strength) * 10,
                            risk_level=self._signal_to_risk_level(signal_strength),
                            required_capital_usd=float(signals.get("required_capital", 10000)),
                            estimated_timeframe=signals.get("timeframe", "72h"),
                            entry_price=signals.get("entry_price"),
                            exit_price=signals.get("exit_price"),
                            metadata={
                                "signal_strength": signal_strength,
                                "correlation": pairs_result.get("correlation_analysis", {}).get("correlation", 0),
                                "spread_z_score": signals.get("spread_z_score", 0)
                            },
                            discovered_at=datetime.utcnow()
                        )
                        opportunities.append(opportunity)
            
        except Exception as e:
            self.error(f"Pairs trading scan failed: {e}")
        
        return opportunities

    # Placeholder scanners
    async def _scan_spot_mean_reversion_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Test spot mean reversion scanner"""
        opportunities = []
        
        try:
            reversion_symbols = self._get_top_symbols_by_volume(discovered_assets, limit=5)
            
            for symbol in reversion_symbols:
                reversion_result = await self.trading_strategies_service.execute_strategy(
                    function="spot_mean_reversion",
                    symbol=f"{symbol}/USDT",
                    parameters={"timeframe": "1h"},
                    user_id=user_profile.user_id
                )
                
                if reversion_result.get("success") and reversion_result.get("signals"):
                    signals = reversion_result["signals"]
                    deviation_score = abs(float(signals.get("deviation_score", 0)))
                    
                    if deviation_score > 1.0:
                        signal_strength = min(deviation_score * 2, 10)
                        
                        opportunity = MockOpportunityResult(
                            strategy_id="ai_spot_mean_reversion",
                            strategy_name="AI Mean Reversion",
                            opportunity_type="mean_reversion",
                            symbol=symbol,
                            exchange="binance",
                            profit_potential_usd=float(signals.get("reversion_target", 0)),
                            confidence_score=float(signals.get("confidence", 0.75) * 100),
                            risk_level=self._signal_to_risk_level(signal_strength),
                            required_capital_usd=float(signals.get("min_capital", 2000)),
                            estimated_timeframe="6-24h",
                            entry_price=signals.get("entry_price"),
                            exit_price=signals.get("mean_price"),
                            metadata={
                                "signal_strength": signal_strength,
                                "deviation_score": signals.get("deviation_score", 0),
                                "rsi": signals.get("rsi", 0)
                            },
                            discovered_at=datetime.utcnow()
                        )
                        opportunities.append(opportunity)
            
        except Exception as e:
            self.error(f"Spot mean reversion scan failed: {e}")
        
        return opportunities

    async def _scan_spot_breakout_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Test spot breakout scanner"""
        opportunities = []
        
        try:
            breakout_symbols = self._get_top_symbols_by_volume(discovered_assets, limit=5)
            
            for symbol in breakout_symbols:
                breakout_result = await self.trading_strategies_service.execute_strategy(
                    function="spot_breakout_strategy",
                    symbol=f"{symbol}/USDT",
                    parameters={"timeframe": "1h"},
                    user_id=user_profile.user_id
                )
                
                if breakout_result.get("success") and breakout_result.get("breakout_signals"):
                    signals = breakout_result["breakout_signals"]
                    breakout_probability = signals.get("breakout_probability", 0)
                    
                    if breakout_probability > 0.5:
                        signal_strength = breakout_probability * 10
                        
                        opportunity = MockOpportunityResult(
                            strategy_id="ai_spot_breakout_strategy",
                            strategy_name="AI Breakout Trading",
                            opportunity_type="breakout",
                            symbol=symbol,
                            exchange="binance",
                            profit_potential_usd=float(signals.get("profit_potential", 0)),
                            confidence_score=float(breakout_probability) * 100,
                            risk_level=self._signal_to_risk_level(signal_strength),
                            required_capital_usd=float(signals.get("min_capital", 3000)),
                            estimated_timeframe="2-8h",
                            entry_price=signals.get("breakout_price"),
                            exit_price=signals.get("target_price"),
                            metadata={
                                "signal_strength": signal_strength,
                                "breakout_probability": breakout_probability,
                                "support_level": signals.get("support_level", 0),
                                "resistance_level": signals.get("resistance_level", 0)
                            },
                            discovered_at=datetime.utcnow()
                        )
                        opportunities.append(opportunity)
            
        except Exception as e:
            self.error(f"Spot breakout scan failed: {e}")
        
        return opportunities

    async def _scan_scalping_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Test scalping scanner"""
        opportunities = []
        
        try:
            symbols = self._get_top_symbols_by_volume(discovered_assets, limit=3)
            
            for symbol in symbols:
                scalp_result = await self.trading_strategies_service.execute_strategy(
                    function="scalping_strategy",
                    strategy_type="momentum_scalp",
                    symbol=f"{symbol}/USDT",
                    parameters={
                        "timeframe": "1m",
                        "profit_target": 0.005,
                        "stop_loss": 0.002,
                        "min_volume_surge": 2.0,
                        "rsi_threshold": 70
                    },
                    user_id=user_profile.user_id,
                    simulation_mode=True
                )
                
                if scalp_result.get("success"):
                    signal = scalp_result.get("signal", {})
                    momentum = signal.get("momentum_score", 0)
                    
                    if momentum > 3.0:
                        opportunity = MockOpportunityResult(
                            strategy_id="ai_scalping_strategy",
                            strategy_name=f"AI Scalping ({signal.get('direction', 'Long')})",
                            opportunity_type="scalping",
                            symbol=symbol,
                            exchange="binance",
                            profit_potential_usd=float(signal.get("profit_potential", 25)),
                            confidence_score=float(momentum) * 10,
                            risk_level="medium",
                            required_capital_usd=float(signal.get("required_capital", 1000)),
                            estimated_timeframe="5m",
                            entry_price=signal.get("entry_price"),
                            exit_price=signal.get("target_price"),
                            metadata={
                                "momentum_score": momentum,
                                "direction": signal.get("direction", "long"),
                                "volume_surge": signal.get("volume_surge", 1),
                                "rsi": signal.get("rsi", 50)
                            },
                            discovered_at=datetime.utcnow()
                        )
                        opportunities.append(opportunity)
            
        except Exception as e:
            self.error(f"Scalping scan failed: {e}")
        
        return opportunities

    async def _scan_market_making_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Test market making scanner"""
        opportunities = []
        
        try:
            symbols = self._get_top_symbols_by_volume(discovered_assets, limit=3)
            
            for symbol in symbols:
                mm_result = await self.trading_strategies_service.execute_strategy(
                    function="market_making",
                    strategy_type="dual_side",
                    symbol=f"{symbol}/USDT",
                    parameters={
                        "spread_target": 0.002,
                        "order_amount": 1000,
                        "max_position": 10000,
                        "rebalance_threshold": 0.1
                    },
                    user_id=user_profile.user_id,
                    simulation_mode=True
                )
                
                if mm_result.get("success"):
                    signal = mm_result.get("signal", {})
                    spread = signal.get("current_spread", 0)
                    
                    if spread > 0.001:
                        opportunity = MockOpportunityResult(
                            strategy_id="ai_market_making",
                            strategy_name=f"AI Market Making ({symbol})",
                            opportunity_type="market_making",
                            symbol=symbol,
                            exchange="binance",
                            profit_potential_usd=float(signal.get("daily_profit_est", 50)),
                            confidence_score=min(100, float(spread * 10000)),
                            risk_level="low",
                            required_capital_usd=float(signal.get("required_capital", 5000)),
                            estimated_timeframe="24h",
                            entry_price=signal.get("bid_price"),
                            exit_price=signal.get("ask_price"),
                            metadata={
                                "current_spread": spread,
                                "target_spread": 0.002,
                                "volume_24h": signal.get("volume_24h", 0),
                                "liquidity_score": signal.get("liquidity_score", 0)
                            },
                            discovered_at=datetime.utcnow()
                        )
                        opportunities.append(opportunity)
            
        except Exception as e:
            self.error(f"Market making scan failed: {e}")
        
        return opportunities

    async def _scan_futures_trading_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Test futures trading scanner"""
        opportunities = []
        
        try:
            symbols = self._get_top_symbols_by_volume(discovered_assets, limit=3)
            
            for symbol in symbols:
                futures_result = await self.trading_strategies_service.execute_strategy(
                    function="futures_trade",
                    strategy_type="trend_following",
                    symbol=f"{symbol}/USDT",
                    parameters={
                        "timeframe": "1h",
                        "leverage": 10,
                        "min_volume": 5000000,
                        "stop_loss_pct": 2.0,
                        "take_profit_pct": 6.0
                    },
                    user_id=user_profile.user_id,
                    simulation_mode=True
                )
                
                if futures_result.get("success"):
                    signal = futures_result.get("signal", {})
                    leverage_score = signal.get("leverage_score", 0)
                    
                    if leverage_score > 5.0:
                        opportunity = MockOpportunityResult(
                            strategy_id="ai_futures_trade",
                            strategy_name="AI Futures Trading",
                            opportunity_type="futures_trading",
                            symbol=symbol,
                            exchange="binance",
                            profit_potential_usd=float(signal.get("profit_potential", 0)),
                            confidence_score=float(leverage_score) * 10,
                            risk_level="high",
                            required_capital_usd=float(signal.get("required_capital", 2000)),
                            estimated_timeframe="24h",
                            entry_price=signal.get("entry_price"),
                            exit_price=signal.get("target_price"),
                            metadata={
                                "leverage_score": leverage_score,
                                "trend_strength": signal.get("trend_strength", 0),
                                "leverage": signal.get("leverage", 10),
                                "margin_required": signal.get("margin_required", 0)
                            },
                            discovered_at=datetime.utcnow()
                        )
                        opportunities.append(opportunity)
            
        except Exception as e:
            self.error(f"Futures trading scan failed: {e}")
        
        return opportunities

    async def _scan_options_trading_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Test options trading scanner"""
        opportunities = []
        
        try:
            symbols = self._get_top_symbols_by_volume(discovered_assets, limit=3)
            
            for symbol in symbols:
                options_result = await self.trading_strategies_service.execute_strategy(
                    function="options_trade",
                    strategy_type="iron_condor",
                    symbol=f"{symbol}/USDT",
                    parameters={
                        "timeframe": "1d",
                        "calculate_greeks": True,
                        "min_volume": 1000000,
                        "expiry_days": 30
                    },
                    user_id=user_profile.user_id,
                    simulation_mode=True
                )
                
                if options_result.get("success"):
                    signal = options_result.get("signal", {})
                    greeks_score = signal.get("greeks_score", 0)
                    
                    if greeks_score > 5.0:
                        opportunity = MockOpportunityResult(
                            strategy_id="ai_options_trade",
                            strategy_name="AI Options Trading",
                            opportunity_type="options_trading",
                            symbol=symbol,
                            exchange="binance",
                            profit_potential_usd=float(signal.get("profit_potential", 0)),
                            confidence_score=float(greeks_score) * 10,
                            risk_level="high",
                            required_capital_usd=float(signal.get("required_capital", 3000)),
                            estimated_timeframe="30d",
                            entry_price=signal.get("strike_price"),
                            exit_price=None,
                            metadata={
                                "greeks_score": greeks_score,
                                "iv_rank": signal.get("iv_rank", 0),
                                "delta": signal.get("delta", 0),
                                "gamma": signal.get("gamma", 0),
                                "theta": signal.get("theta", 0),
                                "vega": signal.get("vega", 0)
                            },
                            discovered_at=datetime.utcnow()
                        )
                        opportunities.append(opportunity)
            
        except Exception as e:
            self.error(f"Options trading scan failed: {e}")
        
        return opportunities

    # Placeholder scanners
    async def _scan_hedge_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Hedge position strategy scanner - placeholder for real implementation."""
        return []
    
    async def _scan_complex_strategy_opportunities(self, discovered_assets, user_profile, scan_id, portfolio_result):
        """Complex strategy scanner - placeholder for real implementation."""
        return []

async def test_all_strategies():
    """Test all strategy scanners individually."""
    
    print("🚀 INDIVIDUAL STRATEGY TESTING (MOCK VERSION)")
    print("Testing each strategy scanner to see if they work at runtime")
    
    # Initialize the mock service
    service = MockUserOpportunityDiscoveryService()
    
    # Create test user profile
    user_profile = MockUserOpportunityProfile("test-user-123")
    
    # Mock discovered assets
    discovered_assets = {
        "binance": [
            {"symbol": "BTC/USDT", "volume_24h": 1000000},
            {"symbol": "ETH/USDT", "volume_24h": 800000},
            {"symbol": "ADA/USDT", "volume_24h": 500000}
        ],
        "coinbase": [
            {"symbol": "BTC/USD", "volume_24h": 900000},
            {"symbol": "ETH/USD", "volume_24h": 700000}
        ]
    }
    
    scan_id = f"test_scan_{int(datetime.now().timestamp())}"
    
    # Test each strategy
    strategy_tests = [
        ("Portfolio Optimization", service._scan_portfolio_optimization_opportunities),
        ("Risk Management", service._scan_risk_management_opportunities),
        ("Spot Momentum", service._scan_spot_momentum_opportunities),
        ("Spot Mean Reversion", service._scan_spot_mean_reversion_opportunities),
        ("Spot Breakout", service._scan_spot_breakout_opportunities),
        ("Scalping", service._scan_scalping_opportunities),
        ("Pairs Trading", service._scan_pairs_trading_opportunities),
        ("Statistical Arbitrage", service._scan_statistical_arbitrage_opportunities),
        ("Market Making", service._scan_market_making_opportunities),
        ("Futures Trading", service._scan_futures_trading_opportunities),
        ("Options Trading", service._scan_options_trading_opportunities),
        ("Funding Arbitrage", service._scan_funding_arbitrage_opportunities),
        ("Hedge Position", service._scan_hedge_opportunities),
        ("Complex Strategy", service._scan_complex_strategy_opportunities)
    ]
    
    results = []
    
    for strategy_name, scanner_method in strategy_tests:
        print(f"\n{'='*60}")
        print(f"🧪 TESTING: {strategy_name}")
        print(f"{'='*60}")
        
        try:
            print(f"📞 Calling {strategy_name} scanner...")
            start_time = datetime.now()
            
            # Call the strategy scanner
            opportunities = await scanner_method(
                discovered_assets=discovered_assets,
                user_profile=user_profile,
                scan_id=scan_id,
                portfolio_result={"active_strategies": []}
            )
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            print(f"⏱️  Execution time: {execution_time:.2f} seconds")
            print(f"📊 Opportunities found: {len(opportunities)}")
            
            if opportunities:
                print(f"✅ SUCCESS: {strategy_name} generated {len(opportunities)} opportunities")
                
                # Show first opportunity details
                first_opp = opportunities[0]
                print(f"   📈 First opportunity:")
                print(f"      Symbol: {first_opp.symbol}")
                print(f"      Type: {first_opp.opportunity_type}")
                print(f"      Profit Potential: ${first_opp.profit_potential_usd}")
                print(f"      Confidence: {first_opp.confidence_score}%")
                print(f"      Risk Level: {first_opp.risk_level}")
                
                result = {
                    "strategy": strategy_name,
                    "status": "SUCCESS",
                    "opportunities_count": len(opportunities),
                    "execution_time": execution_time,
                    "error": None,
                    "sample_opportunity": {
                        "symbol": first_opp.symbol,
                        "type": first_opp.opportunity_type,
                        "profit": first_opp.profit_potential_usd,
                        "confidence": first_opp.confidence_score
                    }
                }
            else:
                print(f"⚠️  WARNING: {strategy_name} returned 0 opportunities")
                result = {
                    "strategy": strategy_name,
                    "status": "NO_OPPORTUNITIES",
                    "opportunities_count": 0,
                    "execution_time": execution_time,
                    "error": "No opportunities generated",
                    "sample_opportunity": None
                }
            
            results.append(result)
            
        except Exception as e:
            print(f"❌ ERROR: {strategy_name} failed with exception")
            print(f"   Error type: {type(e).__name__}")
            print(f"   Error message: {str(e)}")
            print(f"   Traceback:")
            traceback.print_exc()
            
            result = {
                "strategy": strategy_name,
                "status": "ERROR",
                "opportunities_count": 0,
                "execution_time": 0,
                "error": f"{type(e).__name__}: {str(e)}",
                "sample_opportunity": None
            }
            results.append(result)
    
    # Summary
    print(f"\n{'='*80}")
    print("📊 STRATEGY TESTING SUMMARY")
    print(f"{'='*80}")
    
    successful = [r for r in results if r["status"] == "SUCCESS"]
    no_opportunities = [r for r in results if r["status"] == "NO_OPPORTUNITIES"]
    errors = [r for r in results if r["status"] == "ERROR"]
    
    print(f"✅ Successful strategies: {len(successful)}/{len(results)}")
    print(f"⚠️  No opportunities: {len(no_opportunities)}/{len(results)}")
    print(f"❌ Error strategies: {len(errors)}/{len(results)}")
    
    if successful:
        print(f"\n✅ WORKING STRATEGIES:")
        for result in successful:
            print(f"   - {result['strategy']}: {result['opportunities_count']} opportunities ({result['execution_time']:.2f}s)")
    
    if no_opportunities:
        print(f"\n⚠️  NO OPPORTUNITIES (but no errors):")
        for result in no_opportunities:
            print(f"   - {result['strategy']}: {result['error']}")
    
    if errors:
        print(f"\n❌ FAILING STRATEGIES:")
        for result in errors:
            print(f"   - {result['strategy']}: {result['error']}")
    
    # Save detailed results
    with open(f'/workspace/strategy_test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to strategy_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

if __name__ == "__main__":
    asyncio.run(test_all_strategies())