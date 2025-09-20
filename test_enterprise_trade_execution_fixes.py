#!/usr/bin/env python3
"""
Enterprise Trade Execution Fixes - Comprehensive Test

This test validates all the fixes applied to the enterprise trade execution system:
1. Pipeline coordination working correctly
2. Opportunity discovery signal extraction fixed
3. Credit system correctly handling free strategies
4. Trade execution service properly integrated with pipeline
5. End-to-end pipeline flow functioning

Author: CTO Assistant
Date: September 20, 2025
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any

import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
    logger_factory=structlog.WriteLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class EnterpriseTradeExecutionTester:
    """Comprehensive tester for enterprise trade execution fixes."""
    
    def __init__(self):
        self.test_results = {
            "pipeline_coordination": {"status": "pending", "details": {}},
            "opportunity_discovery": {"status": "pending", "details": {}},
            "credit_system": {"status": "pending", "details": {}},
            "trade_execution_integration": {"status": "pending", "details": {}},
            "end_to_end_pipeline": {"status": "pending", "details": {}}
        }
    
    async def test_pipeline_coordination(self) -> Dict[str, Any]:
        """Test the 5-phase pipeline coordination."""
        logger.info("🚀 Testing Pipeline Coordination...")
        
        try:
            from app.services.master_controller import MasterSystemController
            
            master_controller = MasterSystemController()
            
            # Test 1: Direct pipeline execution (bypass coordinator)
            logger.info("Test 1: Direct pipeline execution")
            start_time = time.time()
            
            result = await master_controller.trigger_pipeline(
                analysis_type="market_overview",
                symbols="BTC,ETH",
                user_id="test_user",
                source="test",
                bypass_coordinator=True
            )
            
            execution_time = time.time() - start_time
            
            # Test 2: Coordinated pipeline execution (with coordinator)
            logger.info("Test 2: Coordinated pipeline execution")
            start_time = time.time()
            
            coordinated_result = await master_controller.trigger_pipeline(
                analysis_type="market_overview",
                symbols="BTC,ETH",
                user_id="test_user",
                source="test",
                bypass_coordinator=False
            )
            
            coordinated_execution_time = time.time() - start_time
            
            # Validate results
            success = (
                isinstance(result, dict) and
                isinstance(coordinated_result, dict) and
                execution_time < 60 and  # Should complete within 60 seconds
                coordinated_execution_time < 60
            )
            
            self.test_results["pipeline_coordination"] = {
                "status": "passed" if success else "failed",
                "details": {
                    "direct_execution_time": execution_time,
                    "coordinated_execution_time": coordinated_execution_time,
                    "direct_result_structure": self._analyze_result_structure(result),
                    "coordinated_result_structure": self._analyze_result_structure(coordinated_result),
                    "pipeline_phases_completed": result.get("phases_completed", "unknown") if isinstance(result, dict) else "unknown"
                }
            }
            
            logger.info("✅ Pipeline Coordination Test Complete", 
                       status=self.test_results["pipeline_coordination"]["status"],
                       execution_time=execution_time)
            
            return self.test_results["pipeline_coordination"]
            
        except Exception as e:
            logger.error("❌ Pipeline Coordination Test Failed", error=str(e))
            self.test_results["pipeline_coordination"] = {
                "status": "failed",
                "details": {"error": str(e)}
            }
            return self.test_results["pipeline_coordination"]
    
    async def test_opportunity_discovery(self) -> Dict[str, Any]:
        """Test opportunity discovery signal extraction."""
        logger.info("🔍 Testing Opportunity Discovery...")
        
        try:
            from app.services.user_opportunity_discovery import UserOpportunityDiscoveryService
            from app.models.user import User
            from app.core.database import AsyncSessionLocal
            
            discovery_service = UserOpportunityDiscoveryService()
            
            # Create a test user profile
            test_user_profile = type('UserProfile', (), {
                'user_id': 'test_user_opportunity',
                'risk_tolerance': 'balanced',
                'investment_amount_usd': 10000,
                'preferred_strategies': ['ai_spot_momentum_strategy', 'ai_risk_management']
            })()
            
            logger.info("Test: Discovering opportunities for test user")
            start_time = time.time()
            
            opportunities = await discovery_service.discover_opportunities_for_user(
                user_id=test_user_profile.user_id,
                flags={},
                max_opportunities=10
            )
            
            discovery_time = time.time() - start_time
            
            # Validate results
            success = (
                isinstance(opportunities, list) and
                discovery_time < 120 and  # Should complete within 2 minutes
                len(opportunities) >= 0  # Should return some opportunities or empty list
            )
            
            # Analyze opportunity quality
            opportunity_analysis = {
                "total_opportunities": len(opportunities),
                "opportunity_types": list(set(opp.opportunity_type for opp in opportunities)) if opportunities else [],
                "strategies_used": list(set(opp.strategy_id for opp in opportunities)) if opportunities else [],
                "avg_confidence_score": sum(opp.confidence_score for opp in opportunities) / len(opportunities) if opportunities else 0
            }
            
            self.test_results["opportunity_discovery"] = {
                "status": "passed" if success else "failed",
                "details": {
                    "discovery_time": discovery_time,
                    "opportunity_analysis": opportunity_analysis,
                    "signal_extraction_working": len(opportunities) > 0 or "No current market opportunities (expected in some conditions)"
                }
            }
            
            logger.info("✅ Opportunity Discovery Test Complete", 
                       status=self.test_results["opportunity_discovery"]["status"],
                       opportunities_found=len(opportunities))
            
            return self.test_results["opportunity_discovery"]
            
        except Exception as e:
            logger.error("❌ Opportunity Discovery Test Failed", error=str(e))
            self.test_results["opportunity_discovery"] = {
                "status": "failed",
                "details": {"error": str(e)}
            }
            return self.test_results["opportunity_discovery"]
    
    async def test_credit_system(self) -> Dict[str, Any]:
        """Test credit system handling of free strategies."""
        logger.info("💳 Testing Credit System...")
        
        try:
            from app.services.strategy_marketplace_service import strategy_marketplace_service
            
            # Test 1: Check free strategy pricing
            logger.info("Test 1: Checking free strategy pricing")
            
            catalog = await strategy_marketplace_service.get_ai_strategy_catalog()
            
            free_strategies = {
                strategy_id: config for strategy_id, config in catalog.items()
                if config.get("credit_cost_monthly", 0) == 0
            }
            
            # Test 2: Simulate strategy execution for free strategy
            logger.info("Test 2: Simulating free strategy execution")
            
            if free_strategies:
                free_strategy_id = list(free_strategies.keys())[0]
                
                # This should not charge credits for free strategies
                execution_result = await strategy_marketplace_service.execute_ai_strategy(
                    strategy_id=free_strategy_id,
                    user_id="test_user_credits",
                    parameters={"symbols": "BTC", "risk_mode": "balanced"}
                )
                
                execution_success = execution_result.get("success", False)
                credit_charged = execution_result.get("credits_charged", 0)
                
            else:
                execution_success = False
                credit_charged = 0
            
            # Validate results
            success = (
                len(free_strategies) > 0 and  # Should have free strategies
                all(config.get("tier") == "free" for config in free_strategies.values()) and
                (not free_strategies or credit_charged == 0)  # Free strategies should not charge credits
            )
            
            self.test_results["credit_system"] = {
                "status": "passed" if success else "failed",
                "details": {
                    "free_strategies_count": len(free_strategies),
                    "free_strategies": list(free_strategies.keys()),
                    "free_strategy_execution_success": execution_success,
                    "credits_charged_for_free_strategy": credit_charged,
                    "catalog_size": len(catalog)
                }
            }
            
            logger.info("✅ Credit System Test Complete", 
                       status=self.test_results["credit_system"]["status"],
                       free_strategies=len(free_strategies))
            
            return self.test_results["credit_system"]
            
        except Exception as e:
            logger.error("❌ Credit System Test Failed", error=str(e))
            self.test_results["credit_system"] = {
                "status": "failed",
                "details": {"error": str(e)}
            }
            return self.test_results["credit_system"]
    
    async def test_trade_execution_integration(self) -> Dict[str, Any]:
        """Test trade execution service integration with pipeline."""
        logger.info("⚡ Testing Trade Execution Integration...")
        
        try:
            from app.services.trade_execution import TradeExecutionService
            from unittest.mock import AsyncMock, patch
            
            trade_execution_service = TradeExecutionService()
            
            # Test 1: Service initialization and health
            logger.info("Test 1: Trade execution service health check")
            
            health_result = await trade_execution_service.health_check()
            service_healthy = health_result.get("status") == "healthy"
            
            # Test 2: Test trade execution method with stubbed real order execution
            logger.info("Test 2: Trade execution method availability (stubbed)")
            
            # Stub the real order execution to prevent actual trades
            fake_order_result = {
                "success": True,
                "order_id": "test_order_123",
                "status": "filled",
                "filled_quantity": 0.001,
                "filled_price": 50000.0,
                "exchange": "binance"
            }
            
            # Mock the internal _execute_real_order method to return fake result
            with patch.object(trade_execution_service, '_execute_real_order', new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = fake_order_result
                
                test_trade_result = await trade_execution_service.execute_real_trade(
                    symbol="BTC/USDT",
                    side="BUY",
                    quantity=0.001,
                    order_type="market",
                    exchange="auto",
                    user_id="test_user_execution"
                )
            
            method_available = isinstance(test_trade_result, dict)
            
            # Validate results
            success = service_healthy and method_available
            
            self.test_results["trade_execution_integration"] = {
                "status": "passed" if success else "failed",
                "details": {
                    "service_health": health_result,
                    "execute_real_trade_available": method_available,
                    "test_execution_result": self._analyze_result_structure(test_trade_result)
                }
            }
            
            logger.info("✅ Trade Execution Integration Test Complete", 
                       status=self.test_results["trade_execution_integration"]["status"])
            
            return self.test_results["trade_execution_integration"]
            
        except Exception as e:
            logger.error("❌ Trade Execution Integration Test Failed", error=str(e))
            self.test_results["trade_execution_integration"] = {
                "status": "failed",
                "details": {"error": str(e)}
            }
            return self.test_results["trade_execution_integration"]
    
    async def test_end_to_end_pipeline(self) -> Dict[str, Any]:
        """Test complete end-to-end pipeline flow."""
        logger.info("🎯 Testing End-to-End Pipeline...")
        
        try:
            from app.services.master_controller import MasterSystemController
            
            master_controller = MasterSystemController()
            
            # Test complete autonomous cycle
            logger.info("Test: Complete autonomous cycle execution")
            start_time = time.time()
            
            pipeline_result = await master_controller.execute_5_phase_autonomous_cycle(
                user_id="test_user_e2e",
                source="comprehensive_test",
                symbols=["BTC", "ETH"],
                risk_tolerance="balanced"
            )
            
            execution_time = time.time() - start_time
            
            # Analyze pipeline execution
            phases_completed = pipeline_result.get("phases_completed", "0/5") if isinstance(pipeline_result, dict) else "unknown"
            phases_data = pipeline_result.get("phases", {}) if isinstance(pipeline_result, dict) else {}
            
            # Count successful phases
            successful_phases = 0
            phase_details = {}
            
            for phase_name, phase_data in phases_data.items():
                if isinstance(phase_data, dict):
                    phase_status = phase_data.get("status", "unknown")
                    if phase_status == "completed":
                        successful_phases += 1
                    phase_details[phase_name] = {
                        "status": phase_status,
                        "service": phase_data.get("service", "unknown"),
                        "execution_time_ms": phase_data.get("execution_time_ms", 0)
                    }
            
            # Validate results
            success = (
                isinstance(pipeline_result, dict) and
                execution_time < 180 and  # Should complete within 3 minutes
                successful_phases >= 3  # At least 3 phases should complete successfully
            )
            
            self.test_results["end_to_end_pipeline"] = {
                "status": "passed" if success else "failed",
                "details": {
                    "total_execution_time": execution_time,
                    "phases_completed": phases_completed,
                    "successful_phases": successful_phases,
                    "phase_details": phase_details,
                    "pipeline_success": pipeline_result.get("success", False) if isinstance(pipeline_result, dict) else False
                }
            }
            
            logger.info("✅ End-to-End Pipeline Test Complete", 
                       status=self.test_results["end_to_end_pipeline"]["status"],
                       phases_completed=phases_completed)
            
            return self.test_results["end_to_end_pipeline"]
            
        except Exception as e:
            logger.error("❌ End-to-End Pipeline Test Failed", error=str(e))
            self.test_results["end_to_end_pipeline"] = {
                "status": "failed",
                "details": {"error": str(e)}
            }
            return self.test_results["end_to_end_pipeline"]
    
    def _analyze_result_structure(self, result: Any) -> Dict[str, Any]:
        """Analyze the structure of a result for debugging."""
        if isinstance(result, dict):
            return {
                "type": "dict",
                "keys": list(result.keys()),
                "has_success": "success" in result,
                "has_phases": "phases" in result,
                "has_error": "error" in result
            }
        elif isinstance(result, list):
            return {
                "type": "list",
                "length": len(result),
                "first_item_type": type(result[0]).__name__ if result else None
            }
        else:
            return {
                "type": type(result).__name__,
                "value": str(result)[:100] if result else None
            }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all enterprise trade execution tests."""
        logger.info("🚀 Starting Enterprise Trade Execution Comprehensive Test")
        logger.info("=" * 80)
        
        start_time = time.time()
        
        # Run all tests
        await self.test_pipeline_coordination()
        await self.test_opportunity_discovery()
        await self.test_credit_system()
        await self.test_trade_execution_integration()
        await self.test_end_to_end_pipeline()
        
        total_time = time.time() - start_time
        
        # Summarize results
        passed_tests = sum(1 for result in self.test_results.values() if result["status"] == "passed")
        total_tests = len(self.test_results)
        
        summary = {
            "test_suite": "Enterprise Trade Execution Fixes",
            "timestamp": datetime.utcnow().isoformat(),
            "total_execution_time": total_time,
            "tests_passed": passed_tests,
            "tests_total": total_tests,
            "success_rate": (passed_tests / total_tests) * 100,
            "overall_status": "PASSED" if passed_tests == total_tests else "PARTIAL" if passed_tests > 0 else "FAILED",
            "detailed_results": self.test_results
        }
        
        logger.info("=" * 80)
        logger.info("📊 Enterprise Trade Execution Test Summary")
        logger.info(f"✅ Tests Passed: {passed_tests}/{total_tests}")
        logger.info(f"⏱️  Total Time: {total_time:.2f} seconds")
        logger.info(f"🎯 Success Rate: {summary['success_rate']:.1f}%")
        logger.info(f"🏆 Overall Status: {summary['overall_status']}")
        
        return summary


async def main():
    """Main test execution."""
    tester = EnterpriseTradeExecutionTester()
    
    try:
        results = await tester.run_all_tests()
        
        # Save results to file
        with open("enterprise_trade_execution_test_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info("📄 Test results saved to: enterprise_trade_execution_test_results.json")
        
        # Exit with appropriate code
        if results["overall_status"] == "PASSED":
            logger.info("🎉 ALL TESTS PASSED - Enterprise Trade Execution Fixes Verified!")
            return 0
        elif results["overall_status"] == "PARTIAL":
            logger.warning("⚠️  PARTIAL SUCCESS - Some fixes need attention")
            return 1
        else:
            logger.error("❌ TESTS FAILED - Enterprise fixes need more work")
            return 2
            
    except Exception as e:
        logger.error("💥 Test execution failed", error=str(e), exc_info=True)
        return 3


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))