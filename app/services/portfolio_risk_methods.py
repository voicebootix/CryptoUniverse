"""
Portfolio Risk Service Additional Methods

Contains the remaining service methods to complete the Portfolio Risk Service implementation.
"""

import json
from typing import Dict, List, Any
from datetime import datetime

from app.services.portfolio_risk import OptimizationStrategy, TradingMode


async def optimize_allocation(self, user_id: str, strategy: str = "adaptive", constraints: Dict[str, Any] = None) -> Dict[str, Any]:
    """Optimize portfolio allocation using specified strategy."""
    
    request_id = self._generate_request_id()
    self.logger.info("Optimizing allocation", user_id=user_id, strategy=strategy, request_id=request_id)
    
    try:
        # Get portfolio data
        portfolio = await self.portfolio_connector.get_consolidated_portfolio(user_id)
        
        if not portfolio.get("positions"):
            return {
                "success": False,
                "error": "No positions found for optimization",
                "function": "optimize_allocation",
                "request_id": request_id
            }
        
        # Convert strategy string to enum
        try:
            optimization_strategy = OptimizationStrategy(strategy)
        except ValueError:
            optimization_strategy = OptimizationStrategy.ADAPTIVE
        
        # Run optimization
        optimization_result = await self.optimization_engine.optimize_portfolio(
            portfolio, optimization_strategy, constraints
        )
        
        # Update metrics
        if optimization_result.rebalancing_needed:
            self.service_metrics["successful_optimizations"] += 1
        
        return {
            "success": True,
            "function": "optimize_allocation",
            "request_id": request_id,
            "optimization_result": {
                "strategy": optimization_result.strategy.value,
                "weights": optimization_result.weights,
                "expected_return": optimization_result.expected_return,
                "expected_volatility": optimization_result.expected_volatility,
                "sharpe_ratio": optimization_result.sharpe_ratio,
                "max_drawdown_estimate": optimization_result.max_drawdown_estimate,
                "confidence": optimization_result.confidence,
                "rebalancing_needed": optimization_result.rebalancing_needed
            },
            "rebalancing_trades": optimization_result.suggested_trades,
            "current_portfolio": {
                "total_value_usd": portfolio.get("total_value_usd", 0),
                "positions_count": len(portfolio.get("positions", []))
            },
            "optimization_metadata": {
                "strategy_used": optimization_result.strategy.value,
                "constraints_applied": constraints or {},
                "optimization_confidence": optimization_result.confidence
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        self.logger.error("Allocation optimization failed", error=str(e), user_id=user_id, exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "function": "optimize_allocation",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }


async def position_sizing(self, opportunity: str, user_id: str, mode: str = "balanced") -> Dict[str, Any]:
    """Calculate intelligent position sizing for trading opportunity."""
    
    request_id = self._generate_request_id()
    self.logger.info("Calculating position sizing", user_id=user_id, request_id=request_id)
    
    try:
        # Parse opportunity data
        try:
            opportunity_data = json.loads(opportunity) if isinstance(opportunity, str) else opportunity
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Invalid opportunity format. Must be valid JSON.",
                "function": "position_sizing",
                "request_id": request_id
            }
        
        # Convert mode string to enum
        try:
            trading_mode = TradingMode(mode)
        except ValueError:
            trading_mode = TradingMode.BALANCED
        
        # Get portfolio data
        portfolio = await self.portfolio_connector.get_consolidated_portfolio(user_id)
        
        # Calculate position size
        sizing_result = await self.position_sizing_engine.calculate_position_size(
            opportunity_data, portfolio, trading_mode
        )
        
        return {
            "success": True,
            "function": "position_sizing",
            "request_id": request_id,
            "position_sizing": sizing_result,
            "portfolio_context": {
                "total_value_usd": portfolio.get("total_value_usd", 0),
                "existing_positions": len(portfolio.get("positions", [])),
                "available_capital": portfolio.get("total_value_usd", 0) * 0.1  # Assume 10% available
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        self.logger.error("Position sizing failed", error=str(e), user_id=user_id, exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "function": "position_sizing",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }


async def correlation_analysis(self, user_id: str, lookback_days: int = 90) -> Dict[str, Any]:
    """Analyze portfolio correlations and diversification."""
    
    request_id = self._generate_request_id()
    self.logger.info("Performing correlation analysis", user_id=user_id, request_id=request_id)
    
    try:
        # Get portfolio data
        portfolio = await self.portfolio_connector.get_consolidated_portfolio(user_id)
        
        if len(portfolio.get("positions", [])) < 2:
            return {
                "success": False,
                "error": "Minimum 2 positions required for correlation analysis",
                "function": "correlation_analysis",
                "request_id": request_id
            }
        
        # Perform correlation analysis
        correlation_result = await self.correlation_engine.analyze_portfolio_correlations(
            portfolio, lookback_days
        )
        
        return {
            "success": True,
            "function": "correlation_analysis",
            "request_id": request_id,
            "correlation_analysis": correlation_result,
            "analysis_parameters": {
                "lookback_days": lookback_days,
                "positions_analyzed": len(portfolio.get("positions", []))
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        self.logger.error("Correlation analysis failed", error=str(e), user_id=user_id, exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "function": "correlation_analysis",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }


async def stress_test(self, user_id: str, scenarios: List[str] = None) -> Dict[str, Any]:
    """Run portfolio stress tests under various market scenarios."""
    
    request_id = self._generate_request_id()
    self.logger.info("Running stress tests", user_id=user_id, request_id=request_id)
    
    try:
        # Get portfolio data
        portfolio = await self.portfolio_connector.get_consolidated_portfolio(user_id)
        
        if not portfolio.get("positions"):
            return {
                "success": False,
                "error": "No positions found for stress testing",
                "function": "stress_test",
                "request_id": request_id
            }
        
        # Run stress tests
        stress_results = await self.stress_testing_engine.run_stress_tests(
            portfolio, scenarios
        )
        
        return {
            "success": True,
            "function": "stress_test",
            "request_id": request_id,
            "stress_test_results": stress_results,
            "portfolio_context": {
                "total_value_usd": portfolio.get("total_value_usd", 0),
                "positions_count": len(portfolio.get("positions", []))
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        self.logger.error("Stress testing failed", error=str(e), user_id=user_id, exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "function": "stress_test",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }


async def complete_assessment(self, user_id: str, include_optimization: bool = True, include_stress_test: bool = True) -> Dict[str, Any]:
    """Perform comprehensive portfolio risk and optimization assessment."""
    
    request_id = self._generate_request_id()
    self.logger.info("Performing complete assessment", user_id=user_id, request_id=request_id)
    
    try:
        # Get portfolio data
        portfolio = await self.portfolio_connector.get_consolidated_portfolio(user_id)
        
        if not portfolio.get("positions"):
            return {
                "success": False,
                "error": "No positions found for assessment",
                "function": "complete_assessment",
                "request_id": request_id
            }
        
        assessment_results = {
            "portfolio": portfolio,
            "risk_analysis": None,
            "correlation_analysis": None,
            "optimization": None,
            "stress_test": None
        }
        
        # Always include risk analysis
        risk_result = await self.risk_analysis(user_id)
        if risk_result.get("success"):
            assessment_results["risk_analysis"] = risk_result.get("risk_metrics")
        
        # Always include correlation analysis if sufficient positions
        if len(portfolio.get("positions", [])) >= 2:
            correlation_result = await self.correlation_analysis(user_id)
            if correlation_result.get("success"):
                assessment_results["correlation_analysis"] = correlation_result.get("correlation_analysis")
        
        # Optional optimization
        if include_optimization:
            optimization_result = await self.optimize_allocation(user_id, "adaptive")
            if optimization_result.get("success"):
                assessment_results["optimization"] = optimization_result.get("optimization_result")
        
        # Optional stress testing
        if include_stress_test:
            stress_result = await self.stress_test(user_id)
            if stress_result.get("success"):
                assessment_results["stress_test"] = stress_result.get("stress_test_results")
        
        # Generate comprehensive recommendations
        comprehensive_recommendations = await self._generate_comprehensive_recommendations(
            assessment_results
        )
        
        # Calculate overall portfolio score
        portfolio_score = await self._calculate_portfolio_score(assessment_results)
        
        return {
            "success": True,
            "function": "complete_assessment",
            "request_id": request_id,
            "assessment_results": assessment_results,
            "comprehensive_recommendations": comprehensive_recommendations,
            "portfolio_score": portfolio_score,
            "assessment_summary": {
                "total_value_usd": portfolio.get("total_value_usd", 0),
                "positions_count": len(portfolio.get("positions", [])),
                "analysis_completeness": {
                    "risk_analysis": assessment_results["risk_analysis"] is not None,
                    "correlation_analysis": assessment_results["correlation_analysis"] is not None,
                    "optimization": assessment_results["optimization"] is not None,
                    "stress_test": assessment_results["stress_test"] is not None
                },
                "overall_health": "HEALTHY" if portfolio_score["overall_score"] > 7 else "NEEDS_ATTENTION" if portfolio_score["overall_score"] > 4 else "HIGH_RISK"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        self.logger.error("Complete assessment failed", error=str(e), user_id=user_id, exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "function": "complete_assessment",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
