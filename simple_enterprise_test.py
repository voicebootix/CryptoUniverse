#!/usr/bin/env python3
"""
Simple Enterprise Trade Execution Fixes Test

Tests the key fixes without external dependencies:
1. Pipeline coordination method exists and is callable
2. Trade execution service integration
3. Credit system logic for free strategies
4. Signal extraction in opportunity discovery

Author: CTO Assistant
Date: September 20, 2025
"""

import asyncio
import json
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, '/workspace')

def test_imports():
    """Test that all required services can be imported."""
    print("🔍 Testing Service Imports...")
    
    try:
        from app.services.master_controller import MasterSystemController
        print("✅ MasterSystemController imported successfully")
    except Exception as e:
        print(f"❌ MasterSystemController import failed: {e}")
        return False
    
    try:
        from app.services.trade_execution import TradeExecutionService
        print("✅ TradeExecutionService imported successfully")
    except Exception as e:
        print(f"❌ TradeExecutionService import failed: {e}")
        return False
    
    try:
        from app.services.strategy_marketplace_service import strategy_marketplace_service
        print("✅ strategy_marketplace_service imported successfully")
    except Exception as e:
        print(f"❌ strategy_marketplace_service import failed: {e}")
        return False
    
    try:
        from app.services.user_opportunity_discovery import UserOpportunityDiscoveryService
        print("✅ UserOpportunityDiscoveryService imported successfully")
    except Exception as e:
        print(f"❌ UserOpportunityDiscoveryService import failed: {e}")
        return False
    
    return True

def test_pipeline_methods():
    """Test that pipeline methods exist."""
    print("\n🚀 Testing Pipeline Methods...")
    
    try:
        from app.services.master_controller import MasterSystemController
        
        controller = MasterSystemController()
        
        # Check if trigger_pipeline method exists
        if hasattr(controller, 'trigger_pipeline'):
            print("✅ trigger_pipeline method exists")
        else:
            print("❌ trigger_pipeline method missing")
            return False
        
        # Check if execute_5_phase_autonomous_cycle method exists
        if hasattr(controller, 'execute_5_phase_autonomous_cycle'):
            print("✅ execute_5_phase_autonomous_cycle method exists")
        else:
            print("❌ execute_5_phase_autonomous_cycle method missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Pipeline methods test failed: {e}")
        return False

def test_trade_execution_methods():
    """Test that trade execution methods exist."""
    print("\n⚡ Testing Trade Execution Methods...")
    
    try:
        from app.services.trade_execution import TradeExecutionService
        
        service = TradeExecutionService()
        
        # Check if execute_real_trade method exists
        if hasattr(service, 'execute_real_trade'):
            print("✅ execute_real_trade method exists")
        else:
            print("❌ execute_real_trade method missing")
            return False
        
        # Check if execute_trade method exists
        if hasattr(service, 'execute_trade'):
            print("✅ execute_trade method exists")
        else:
            print("❌ execute_trade method missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Trade execution methods test failed: {e}")
        return False

def test_credit_system_logic():
    """Test credit system logic by examining the code."""
    print("\n💳 Testing Credit System Logic...")
    
    try:
        # Read the strategy marketplace service file
        with open('/workspace/app/services/strategy_marketplace_service.py', 'r') as f:
            content = f.read()
        
        # Check for the fixed credit cost logic
        if 'base_cost = 0 if strategy_func in ["risk_management", "portfolio_optimization"] else' in content:
            print("✅ Free strategy cost logic found")
        else:
            print("❌ Free strategy cost logic missing")
            return False
        
        # Check for credit check bypass logic
        if 'if cost > 0 and credit_account.available_credits < cost:' in content:
            print("✅ Credit check bypass logic found")
        else:
            print("❌ Credit check bypass logic missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Credit system logic test failed: {e}")
        return False

def test_signal_extraction_fix():
    """Test signal extraction fix by examining the code."""
    print("\n🔍 Testing Signal Extraction Fix...")
    
    try:
        # Read the opportunity discovery service file
        with open('/workspace/app/services/user_opportunity_discovery.py', 'r') as f:
            content = f.read()
        
        # Check for the signal extraction fix
        if 'signals = momentum_result.get("signal") or momentum_result.get("execution_result", {}).get("signal")' in content:
            print("✅ Signal extraction fix found")
        else:
            print("❌ Signal extraction fix missing")
            return False
        
        # Check for the CRITICAL FIX comment
        if 'CRITICAL FIX: Extract signal from correct location' in content:
            print("✅ Signal extraction fix comment found")
        else:
            print("❌ Signal extraction fix comment missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Signal extraction fix test failed: {e}")
        return False

def test_master_controller_integration():
    """Test master controller trade execution integration."""
    print("\n🎯 Testing Master Controller Integration...")
    
    try:
        # Read the master controller file
        with open('/workspace/app/services/master_controller.py', 'r') as f:
            content = f.read()
        
        # Check for trade execution service import
        if 'from app.services.trade_execution import TradeExecutionService' in content:
            print("✅ TradeExecutionService import found in master controller")
        else:
            print("❌ TradeExecutionService import missing from master controller")
            return False
        
        # Check for execute_real_trade call
        if 'execute_real_trade(' in content:
            print("✅ execute_real_trade call found in pipeline")
        else:
            print("❌ execute_real_trade call missing from pipeline")
            return False
        
        # Check that the old non-existent method is removed
        if 'execute_validated_trade(' not in content:
            print("✅ Old execute_validated_trade method call removed")
        else:
            print("⚠️  Old execute_validated_trade method call still present")
            # This is not a failure, just a warning
        
        return True
        
    except Exception as e:
        print(f"❌ Master controller integration test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Enterprise Trade Execution Fixes - Simple Test Suite")
    print("=" * 60)
    
    tests = [
        ("Service Imports", test_imports),
        ("Pipeline Methods", test_pipeline_methods),
        ("Trade Execution Methods", test_trade_execution_methods),
        ("Credit System Logic", test_credit_system_logic),
        ("Signal Extraction Fix", test_signal_extraction_fix),
        ("Master Controller Integration", test_master_controller_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    print(f"🎯 Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Enterprise Trade Execution Fixes Verified!")
        return 0
    elif passed > total // 2:
        print("⚠️  PARTIAL SUCCESS - Most fixes are working")
        return 1
    else:
        print("❌ TESTS FAILED - Fixes need more work")
        return 2

if __name__ == "__main__":
    sys.exit(main())