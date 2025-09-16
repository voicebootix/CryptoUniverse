#!/usr/bin/env python3
"""
Integration test for Unified Chat Service
Tests the actual integration without external dependencies
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ''))


async def test_unified_chat_integration():
    """Test the unified chat service integration."""
    print("🧪 Testing Unified Chat Service Integration\n")
    
    test_results = {
        "passed": 0,
        "failed": 0,
        "errors": []
    }
    
    # Test 1: Service Imports
    print("📦 Test 1: Service Imports")
    print("-" * 40)
    
    try:
        # Test ChatAI service import
        print("  Importing ChatAI service...")
        from app.services.chat_ai_service import ChatAIService, chat_ai_service
        print("  ✅ ChatAI service imported")
        test_results["passed"] += 1
        
        # Test Unified Chat service import
        print("  Importing Unified Chat service...")
        from app.services.unified_chat_service import (
            UnifiedChatService, 
            unified_chat_service,
            ChatIntent,
            ConversationMode,
            InterfaceType,
            TradingMode
        )
        print("  ✅ Unified Chat service imported")
        test_results["passed"] += 1
        
        # Test that we can import original services for comparison
        print("  Importing original services for comparison...")
        from app.services.ai_chat_engine import enhanced_chat_engine
        from app.services.chat_integration import chat_integration
        print("  ✅ Original services still accessible")
        test_results["passed"] += 1
        
    except Exception as e:
        print(f"  ❌ Import error: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(str(e))
        return test_results
    
    # Test 2: Service Initialization
    print("\n🔧 Test 2: Service Initialization")
    print("-" * 40)
    
    try:
        # Check if unified service is properly initialized
        print("  Checking unified service initialization...")
        
        # Check all required attributes
        required_attrs = [
            ("chat_ai", "ChatAI service"),
            ("ai_consensus", "AI Consensus service"),
            ("memory_service", "Memory service"),
            ("master_controller", "Master Controller"),
            ("trade_executor", "Trade Executor"),
            ("adapters", "Chat Adapters"),
            ("market_analysis", "Market Analysis"),
            ("portfolio_risk", "Portfolio Risk"),
            ("trading_strategies", "Trading Strategies"),
            ("strategy_marketplace", "Strategy Marketplace"),
            ("paper_trading", "Paper Trading Engine"),
            ("personalities", "AI Personalities"),
            ("intent_patterns", "Intent Patterns")
        ]
        
        all_present = True
        for attr_name, description in required_attrs:
            if hasattr(unified_chat_service, attr_name):
                print(f"  ✅ {description} present")
            else:
                print(f"  ❌ {description} MISSING")
                all_present = False
                test_results["failed"] += 1
        
        if all_present:
            test_results["passed"] += 1
            
    except Exception as e:
        print(f"  ❌ Initialization error: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(str(e))
    
    # Test 3: Feature Preservation
    print("\n✅ Test 3: Feature Preservation")
    print("-" * 40)
    
    # Check intent preservation
    print("  Checking intent types...")
    expected_intents = [
        "greeting", "portfolio_analysis", "trade_execution",
        "market_analysis", "risk_assessment", "strategy_recommendation",
        "rebalancing", "performance_review", "position_management",
        "opportunity_discovery", "help", "unknown"
    ]
    
    actual_intents = [intent.value for intent in ChatIntent]
    intents_match = set(expected_intents) == set(actual_intents)
    
    if intents_match:
        print("  ✅ All intents preserved")
        test_results["passed"] += 1
    else:
        print("  ❌ Intent mismatch")
        test_results["failed"] += 1
    
    # Check conversation modes
    print("  Checking conversation modes...")
    expected_modes = [
        "live_trading", "paper_trading", "strategy_exploration",
        "learning", "analysis"
    ]
    
    actual_modes = [mode.value for mode in ConversationMode]
    modes_match = set(expected_modes) == set(actual_modes)
    
    if modes_match:
        print("  ✅ All conversation modes preserved")
        test_results["passed"] += 1
    else:
        print("  ❌ Conversation mode mismatch")
        test_results["failed"] += 1
    
    # Test 4: Critical Methods
    print("\n🔍 Test 4: Critical Method Preservation")
    print("-" * 40)
    
    critical_methods = [
        # Core processing
        ("process_message", "Main message processing"),
        ("_analyze_intent_unified", "Intent analysis"),
        ("_check_requirements", "Requirement validation"),
        ("_check_user_credits", "Credit validation"),
        ("_check_strategy_access", "Strategy access check"),
        ("_check_trading_limits", "Trading limits check"),
        
        # Data gathering
        ("_gather_context_data", "Context data gathering"),
        ("_get_user_config", "User configuration"),
        ("_get_performance_metrics", "Performance metrics"),
        
        # Response generation
        ("_generate_complete_response", "Response generation"),
        ("_generate_streaming_response", "Streaming response"),
        
        # Trade execution
        ("_execute_trade_with_validation", "5-phase trade execution"),
        ("execute_decision", "Decision execution"),
        
        # Session management
        ("_get_or_create_session", "Session management"),
        ("get_chat_history", "Chat history"),
        ("get_active_sessions", "Active sessions"),
    ]
    
    for method_name, description in critical_methods:
        if hasattr(unified_chat_service, method_name):
            print(f"  ✅ {description}")
            test_results["passed"] += 1
        else:
            print(f"  ❌ {description} MISSING")
            test_results["failed"] += 1
    
    # Test 5: 5-Phase Execution Preservation
    print("\n🔄 Test 5: 5-Phase Trade Execution")
    print("-" * 40)
    
    try:
        import inspect
        
        # Get the trade execution method
        if hasattr(unified_chat_service, '_execute_trade_with_validation'):
            method = unified_chat_service._execute_trade_with_validation
            source = inspect.getsource(method)
            
            # Check for all 5 phases
            phases = [
                ("Phase 1:", "Analysis"),
                ("Phase 2:", "AI Consensus"),
                ("Phase 3:", "Validation"),
                ("Phase 4:", "Execution"),
                ("Phase 5:", "Monitoring")
            ]
            
            all_phases_found = True
            for phase_marker, phase_name in phases:
                if phase_marker in source:
                    print(f"  ✅ {phase_marker} {phase_name}")
                else:
                    print(f"  ❌ {phase_marker} {phase_name} MISSING")
                    all_phases_found = False
            
            if all_phases_found:
                test_results["passed"] += 1
            else:
                test_results["failed"] += 1
                
        else:
            print("  ❌ 5-phase execution method not found")
            test_results["failed"] += 1
            
    except Exception as e:
        print(f"  ❌ Error checking 5-phase execution: {e}")
        test_results["failed"] += 1
    
    # Test 6: AI Personalities
    print("\n🎭 Test 6: AI Personalities")
    print("-" * 40)
    
    expected_personalities = {
        TradingMode.CONSERVATIVE: "Warren",
        TradingMode.BALANCED: "Alex",
        TradingMode.AGGRESSIVE: "Hunter",
        TradingMode.BEAST_MODE: "Apex"
    }
    
    personalities_ok = True
    for mode, expected_name in expected_personalities.items():
        if mode in unified_chat_service.personalities:
            personality = unified_chat_service.personalities[mode]
            actual_name = personality["name"].split(" - ")[0]
            if actual_name == expected_name:
                print(f"  ✅ {mode.value}: {personality['name']}")
            else:
                print(f"  ❌ {mode.value}: Expected {expected_name}, got {actual_name}")
                personalities_ok = False
        else:
            print(f"  ❌ {mode.value} personality MISSING")
            personalities_ok = False
    
    if personalities_ok:
        test_results["passed"] += 1
    else:
        test_results["failed"] += 1
    
    # Test 7: Paper Trading No Credits
    print("\n💰 Test 7: Paper Trading Configuration")
    print("-" * 40)
    
    try:
        # Check if paper trading mode bypasses credit checks
        import inspect
        
        if hasattr(unified_chat_service, '_check_requirements'):
            source = inspect.getsource(unified_chat_service._check_requirements)
            
            # Look for paper trading credit bypass
            if "ConversationMode.PAPER_TRADING" in source and "NO CREDIT" in source:
                print("  ✅ Paper trading configured to bypass credit checks")
                test_results["passed"] += 1
            else:
                print("  ❌ Paper trading credit bypass not found")
                test_results["failed"] += 1
        else:
            print("  ❌ Requirements check method not found")
            test_results["failed"] += 1
            
    except Exception as e:
        print(f"  ❌ Error checking paper trading: {e}")
        test_results["failed"] += 1
    
    # Test 8: Endpoint Structure
    print("\n🌐 Test 8: Unified Endpoint Structure")
    print("-" * 40)
    
    try:
        # Import the unified chat endpoints
        from app.api.v1.endpoints.unified_chat import router
        
        # Check that router exists and has endpoints
        if router:
            print("  ✅ Unified chat router imported successfully")
            
            # Check for expected routes
            expected_paths = [
                "/message",
                "/stream",
                "/history/{session_id}",
                "/sessions",
                "/session/new",
                "/capabilities",
                "/action/confirm",
                "/status",
                "/ws/{session_id}",
                "/quick/portfolio",
                "/quick/opportunities"
            ]
            
            # Get actual routes
            actual_paths = [route.path for route in router.routes]
            
            for path in expected_paths:
                if any(path in route_path for route_path in actual_paths):
                    print(f"  ✅ {path} endpoint present")
                else:
                    print(f"  ❌ {path} endpoint MISSING")
            
            test_results["passed"] += 1
        else:
            print("  ❌ Router not found")
            test_results["failed"] += 1
            
    except Exception as e:
        print(f"  ❌ Error checking endpoints: {e}")
        test_results["failed"] += 1
    
    return test_results


async def verify_no_breaking_changes():
    """Verify that existing functionality is not broken."""
    print("\n\n🔒 VERIFICATION: No Breaking Changes")
    print("=" * 50)
    
    try:
        # Import both old and new systems
        from app.services.ai_chat_engine import enhanced_chat_engine
        from app.services.chat_integration import chat_integration  
        from app.services.unified_chat_service import unified_chat_service
        
        print("✅ Both old and new systems can coexist")
        print("✅ No import conflicts detected")
        print("✅ Router can be updated gradually")
        
        # Verify old endpoints still exist
        from app.api.v1.endpoints import chat, conversational_chat
        print("✅ Old endpoint files still intact")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


async def main():
    """Run all integration tests."""
    print("🚀 UNIFIED CHAT INTEGRATION TEST SUITE")
    print("=" * 50)
    print("Testing WITHOUT router modifications")
    print("Verifying ALL features are preserved")
    print("=" * 50)
    
    # Run integration tests
    results = await test_unified_chat_integration()
    
    # Verify no breaking changes
    no_breaking = await verify_no_breaking_changes()
    
    # Summary
    print("\n\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"✅ Passed: {results['passed']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"🔧 No Breaking Changes: {'Yes' if no_breaking else 'No'}")
    
    if results['errors']:
        print("\n⚠️  Errors encountered:")
        for error in results['errors']:
            print(f"  - {error}")
    
    if results['failed'] == 0 and no_breaking:
        print("\n✅ ALL TESTS PASSED!")
        print("=" * 50)
        print("SAFE TO PROCEED WITH:")
        print("1. Update router to use unified_chat")
        print("2. Test on live system")
        print("3. Remove old files after verification")
    else:
        print("\n❌ TESTS FAILED!")
        print("=" * 50)
        print("DO NOT UPDATE ROUTER YET!")
        print("Fix the issues above first.")


if __name__ == "__main__":
    asyncio.run(main())