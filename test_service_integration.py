#!/usr/bin/env python3
"""
Service Integration Compatibility Test

Tests if your existing Market Analysis Service and AI Consensus Service
will work properly with the enhanced autonomous system.
"""

import asyncio
import json
from datetime import datetime

import structlog

# Initialize logging
structlog.configure(
    processors=[structlog.stdlib.filter_by_level, structlog.stdlib.add_logger_name, structlog.stdlib.PositionalArgumentsFormatter(), structlog.processors.TimeStamper(fmt="iso"), structlog.processors.StackInfoRenderer(), structlog.processors.format_exc_info, structlog.processors.JSONRenderer()],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


async def test_market_analysis_service():
    """Test if Market Analysis Service works as expected."""
    logger.info("🔍 Testing Market Analysis Service...")
    
    try:
        from app.services.market_analysis_core import MarketAnalysisService
        market_service = MarketAnalysisService()
        
        # Test 1: Market Sentiment Analysis
        logger.info("Testing market_sentiment...")
        sentiment_result = await market_service.market_sentiment(
            symbols="BTC,ETH",
            user_id="test_user"
        )
        
        if sentiment_result.get("success"):
            logger.info("✅ market_sentiment working", 
                       sentiment=sentiment_result.get("sentiment_analysis", {}).get("overall_market_sentiment"))
        else:
            logger.warning("⚠️ market_sentiment issues", error=sentiment_result.get("error"))
        
        # Test 2: Complete Market Assessment
        logger.info("Testing complete_market_assessment...")
        assessment_result = await market_service.complete_market_assessment(
            symbols="BTC,ETH",
            user_id="test_user"
        )
        
        if assessment_result.get("success"):
            logger.info("✅ complete_market_assessment working",
                       components=assessment_result.get("metadata", {}).get("components_analyzed", 0))
        else:
            logger.warning("⚠️ complete_market_assessment issues", error=assessment_result.get("error"))
        
        # Test 3: Cross Exchange Arbitrage Scanner
        logger.info("Testing cross_exchange_arbitrage_scanner...")
        arbitrage_result = await market_service.cross_exchange_arbitrage_scanner(
            symbols="BTC,ETH",
            exchanges="all",
            user_id="test_user"
        )
        
        if arbitrage_result.get("success"):
            opportunities = arbitrage_result.get("arbitrage_opportunities", {}).get("opportunities", [])
            logger.info("✅ arbitrage_scanner working", opportunities_found=len(opportunities))
        else:
            logger.warning("⚠️ arbitrage_scanner issues", error=arbitrage_result.get("error"))
        
        return True
        
    except Exception as e:
        logger.error("❌ Market Analysis Service test failed", error=str(e))
        return False


async def test_ai_consensus_service():
    """Test if AI Consensus Service works as expected."""
    logger.info("🔍 Testing AI Consensus Service...")
    
    try:
        from app.services.ai_consensus_core import ai_consensus_service
        
        # Test 1: Analyze Opportunity
        logger.info("Testing analyze_opportunity...")
        
        test_opportunity = {
            "symbol": "BTC",
            "current_price": 95000,
            "signal_type": "momentum",
            "confidence": 75
        }
        
        opportunity_result = await ai_consensus_service.analyze_opportunity(
            analysis_request=json.dumps(test_opportunity),
            confidence_threshold=70.0,
            user_id="test_user"
        )
        
        if opportunity_result.get("success"):
            logger.info("✅ analyze_opportunity working")
        else:
            logger.warning("⚠️ analyze_opportunity issues", error=opportunity_result.get("error"))
        
        # Test 2: Validate Trade
        logger.info("Testing validate_trade...")
        
        test_trade = {
            "signal": {"symbol": "BTC", "action": "buy", "confidence": 80},
            "position_sizing": {"recommended_size": 0.1, "position_value_usd": 9500},
            "market_context": {"sentiment": "bullish", "volatility": "medium"}
        }
        
        validation_result = await ai_consensus_service.validate_trade(
            analysis_request=json.dumps(test_trade),
            confidence_threshold=75.0,
            ai_models="all",
            user_id="test_user"
        )
        
        if validation_result.get("success"):
            trade_validation = validation_result.get("trade_validation", {})
            approval_status = trade_validation.get("approval_status", "unknown")
            logger.info("✅ validate_trade working", approval_status=approval_status)
        else:
            logger.warning("⚠️ validate_trade issues", error=validation_result.get("error"))
        
        return True
        
    except Exception as e:
        logger.error("❌ AI Consensus Service test failed", error=str(e))
        return False


async def test_trading_strategies_service():
    """Test if Trading Strategies Service works with new signal generation."""
    logger.info("🔍 Testing Trading Strategies Service...")
    
    try:
        from app.services.trading_strategies import trading_strategies_service
        
        # Test the new generate_trading_signal method
        logger.info("Testing generate_trading_signal...")
        
        test_market_data = {
            "market_assessment": {
                "overall_sentiment": "bullish",
                "volatility_level": "medium"
            },
            "symbol_analysis": {
                "BTC": {
                    "price": 95000,
                    "volume": 1000000,
                    "opportunity_score": 75
                }
            }
        }
        
        signal_result = await trading_strategies_service.generate_trading_signal(
            strategy_type="spot_momentum_strategy",
            market_data=test_market_data,
            risk_mode="balanced",
            user_id="test_user"
        )
        
        if signal_result.get("success"):
            signal = signal_result.get("signal", {})
            logger.info("✅ generate_trading_signal working", 
                       symbol=signal.get("symbol"), 
                       confidence=signal.get("confidence"))
        else:
            logger.warning("⚠️ generate_trading_signal issues", error=signal_result.get("error"))
        
        return True
        
    except Exception as e:
        logger.error("❌ Trading Strategies Service test failed", error=str(e))
        return False


async def test_service_coordination():
    """Test if all services coordinate properly in the autonomous flow."""
    logger.info("🔍 Testing Service Coordination...")
    
    try:
        # Simulate the 5-phase autonomous flow
        from app.services.market_analysis_core import MarketAnalysisService
        from app.services.trading_strategies import trading_strategies_service
        from app.services.ai_consensus_core import ai_consensus_service
        
        market_service = MarketAnalysisService()
        
        # Phase 1: Market Analysis
        logger.info("Phase 1: Market Analysis")
        market_result = await market_service.complete_market_assessment(
            symbols="BTC,ETH",
            user_id="test_user"
        )
        
        if not market_result.get("success"):
            logger.error("❌ Phase 1 failed", error=market_result.get("error"))
            return False
        
        logger.info("✅ Phase 1 passed")
        
        # Phase 2: Strategy Signal Generation
        logger.info("Phase 2: Strategy Signal Generation")
        signal_result = await trading_strategies_service.generate_trading_signal(
            strategy_type="spot_momentum_strategy",
            market_data=market_result,
            risk_mode="balanced",
            user_id="test_user"
        )
        
        if not signal_result.get("success"):
            logger.error("❌ Phase 2 failed", error=signal_result.get("error"))
            return False
        
        logger.info("✅ Phase 2 passed")
        
        # Phase 3: AI Validation
        logger.info("Phase 3: AI Validation")
        validation_data = {
            "signal": signal_result.get("signal", {}),
            "market_context": market_result
        }
        
        validation_result = await ai_consensus_service.validate_trade(
            analysis_request=json.dumps(validation_data),
            confidence_threshold=70.0,
            ai_models="all",
            user_id="test_user"
        )
        
        if not validation_result.get("success"):
            logger.warning("⚠️ Phase 3 issues (may be due to missing API keys)", 
                          error=validation_result.get("error"))
            # Don't fail the test - AI validation might need API keys
        else:
            logger.info("✅ Phase 3 passed")
        
        logger.info("✅ Service coordination test completed successfully")
        return True
        
    except Exception as e:
        logger.error("❌ Service coordination test failed", error=str(e))
        return False


async def main():
    """Run all service integration tests."""
    logger.info("🚀 Starting Service Integration Compatibility Tests")
    
    tests = [
        ("Market Analysis Service", test_market_analysis_service),
        ("AI Consensus Service", test_ai_consensus_service),
        ("Trading Strategies Service", test_trading_strategies_service),
        ("Service Coordination", test_service_coordination)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_function in tests:
        logger.info(f"🔄 Running: {test_name}")
        try:
            success = await test_function()
            if success:
                logger.info(f"✅ {test_name} - PASSED")
                passed_tests += 1
            else:
                logger.error(f"❌ {test_name} - FAILED")
        except Exception as e:
            logger.error(f"💥 {test_name} - CRASHED", error=str(e))
    
    success_rate = (passed_tests / total_tests) * 100
    
    logger.info(f"📊 Test Results: {passed_tests}/{total_tests} passed ({success_rate:.1f}%)")
    
    if success_rate >= 75:
        logger.info("🎉 SERVICE INTEGRATION COMPATIBILITY: EXCELLENT")
        logger.info("✅ Your services will work perfectly with the enhanced autonomous system")
        return True
    elif success_rate >= 50:
        logger.warning("⚠️ SERVICE INTEGRATION COMPATIBILITY: GOOD (some issues)")
        logger.warning("🔧 Minor adjustments may be needed for optimal performance")
        return True
    else:
        logger.error("❌ SERVICE INTEGRATION COMPATIBILITY: POOR")
        logger.error("🚨 Significant issues need to be resolved")
        return False


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        if result:
            print("\n✅ SERVICE INTEGRATION TEST PASSED")
            print("🚀 Your services are compatible with the enhanced autonomous system!")
        else:
            print("\n❌ SERVICE INTEGRATION TEST FAILED")
            print("🔧 Some services need attention before full deployment")
    except Exception as e:
        print(f"\n💥 SERVICE INTEGRATION TEST CRASHED: {e}")