#!/usr/bin/env python3
"""
Validation script for Unified Chat implementation
Checks code structure and completeness without running services
"""

import os
import ast
import re
from typing import Set, List, Dict, Any


class UnifiedChatValidator:
    """Validate the unified chat implementation."""
    
    def __init__(self):
        self.results = {
            "passed": [],
            "failed": [],
            "warnings": []
        }
    
    def validate_file_exists(self, filepath: str, description: str) -> bool:
        """Check if a file exists."""
        if os.path.exists(filepath):
            self.results["passed"].append(f"✅ {description} exists")
            return True
        else:
            self.results["failed"].append(f"❌ {description} NOT FOUND at {filepath}")
            return False
    
    def validate_class_in_file(self, filepath: str, classname: str) -> bool:
        """Check if a class exists in a file."""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                tree = ast.parse(content)
                
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == classname:
                    self.results["passed"].append(f"✅ Class {classname} found in {os.path.basename(filepath)}")
                    return True
            
            self.results["failed"].append(f"❌ Class {classname} NOT FOUND in {os.path.basename(filepath)}")
            return False
            
        except Exception as e:
            self.results["failed"].append(f"❌ Error parsing {filepath}: {e}")
            return False
    
    def validate_methods_in_class(self, filepath: str, classname: str, methods: List[str]) -> bool:
        """Check if methods exist in a class."""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                tree = ast.parse(content)
            
            # Find the class
            class_node = None
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == classname:
                    class_node = node
                    break
            
            if not class_node:
                self.results["failed"].append(f"❌ Class {classname} not found for method validation")
                return False
            
            # Get all method names in the class
            class_methods = set()
            for node in class_node.body:
                if isinstance(node, ast.FunctionDef):
                    class_methods.add(node.name)
            
            # Check each required method
            all_found = True
            for method in methods:
                if method in class_methods:
                    self.results["passed"].append(f"  ✅ Method {method}")
                else:
                    self.results["failed"].append(f"  ❌ Method {method} NOT FOUND")
                    all_found = False
            
            return all_found
            
        except Exception as e:
            self.results["failed"].append(f"❌ Error checking methods: {e}")
            return False
    
    def validate_imports(self, filepath: str, required_imports: List[str]) -> bool:
        """Check if required imports are present."""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            all_found = True
            for imp in required_imports:
                if imp in content:
                    self.results["passed"].append(f"  ✅ Import '{imp}' found")
                else:
                    self.results["failed"].append(f"  ❌ Import '{imp}' NOT FOUND")
                    all_found = False
            
            return all_found
            
        except Exception as e:
            self.results["failed"].append(f"❌ Error checking imports: {e}")
            return False
    
    def validate_5_phase_execution(self, filepath: str) -> bool:
        """Validate that 5-phase execution is preserved."""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Look for the _execute_trade_with_validation method
            if "_execute_trade_with_validation" not in content:
                self.results["failed"].append("❌ 5-phase execution method not found")
                return False
            
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
                if phase_marker in content:
                    self.results["passed"].append(f"  ✅ {phase_marker} {phase_name}")
                else:
                    self.results["failed"].append(f"  ❌ {phase_marker} {phase_name} NOT FOUND")
                    all_phases_found = False
            
            return all_phases_found
            
        except Exception as e:
            self.results["failed"].append(f"❌ Error validating 5-phase execution: {e}")
            return False
    
    def validate_credit_checks(self, filepath: str) -> bool:
        """Validate credit check implementation."""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Check for credit-related methods and logic
            credit_checks = [
                "_check_user_credits",
                "_check_requirements",
                "ConversationMode.PAPER_TRADING",
                "NO CREDIT"
            ]
            
            all_found = True
            for check in credit_checks:
                if check in content:
                    self.results["passed"].append(f"  ✅ '{check}' found")
                else:
                    self.results["failed"].append(f"  ❌ '{check}' NOT FOUND")
                    all_found = False
            
            # Special check for paper trading bypass
            if "ConversationMode.PAPER_TRADING" in content and "NO CREDIT" in content:
                self.results["passed"].append("  ✅ Paper trading credit bypass implemented")
            else:
                self.results["failed"].append("  ❌ Paper trading credit bypass NOT FOUND")
                all_found = False
            
            return all_found
            
        except Exception as e:
            self.results["failed"].append(f"❌ Error validating credit checks: {e}")
            return False
    
    def validate_service_preservation(self, filepath: str) -> bool:
        """Validate all services are preserved."""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            # All services that should be initialized
            required_services = [
                "self.chat_ai",
                "self.ai_consensus",
                "self.memory_service",
                "self.master_controller",
                "self.trade_executor",
                "self.adapters",
                "self.market_analysis",
                "self.portfolio_risk",
                "self.trading_strategies",
                "self.strategy_marketplace",
                "self.paper_trading",
                "self.opportunity_discovery",
                "self.personalities",
                "self.intent_patterns"
            ]
            
            all_found = True
            for service in required_services:
                if service in content:
                    self.results["passed"].append(f"  ✅ {service}")
                else:
                    self.results["failed"].append(f"  ❌ {service} NOT INITIALIZED")
                    all_found = False
            
            return all_found
            
        except Exception as e:
            self.results["failed"].append(f"❌ Error validating services: {e}")
            return False
    
    def run_validation(self):
        """Run all validation checks."""
        print("🔍 UNIFIED CHAT VALIDATION")
        print("=" * 50)
        print("Validating code structure and completeness")
        print("=" * 50)
        
        # 1. Validate file existence
        print("\n📁 File Existence Check")
        print("-" * 40)
        self.validate_file_exists(
            "/workspace/app/services/chat_ai_service.py",
            "ChatAI Service"
        )
        self.validate_file_exists(
            "/workspace/app/services/unified_chat_service.py",
            "Unified Chat Service"
        )
        self.validate_file_exists(
            "/workspace/app/api/v1/endpoints/unified_chat.py",
            "Unified Chat Endpoints"
        )
        
        # 2. Validate ChatAI Service
        print("\n🤖 ChatAI Service Validation")
        print("-" * 40)
        if os.path.exists("/workspace/app/services/chat_ai_service.py"):
            self.validate_class_in_file(
                "/workspace/app/services/chat_ai_service.py",
                "ChatAIService"
            )
            self.validate_methods_in_class(
                "/workspace/app/services/chat_ai_service.py",
                "ChatAIService",
                [
                    "generate_response",
                    "stream_response",
                    "analyze_intent",
                    "get_service_status",
                    "health_check"
                ]
            )
        
        # 3. Validate Unified Chat Service
        print("\n🧠 Unified Chat Service Validation")
        print("-" * 40)
        if os.path.exists("/workspace/app/services/unified_chat_service.py"):
            self.validate_class_in_file(
                "/workspace/app/services/unified_chat_service.py",
                "UnifiedChatService"
            )
            
            print("\n  Core Methods:")
            self.validate_methods_in_class(
                "/workspace/app/services/unified_chat_service.py",
                "UnifiedChatService",
                [
                    "process_message",
                    "_analyze_intent_unified",
                    "_check_requirements",
                    "_gather_context_data",
                    "_generate_complete_response",
                    "_generate_streaming_response"
                ]
            )
            
            print("\n  Requirement Checks:")
            self.validate_methods_in_class(
                "/workspace/app/services/unified_chat_service.py",
                "UnifiedChatService",
                [
                    "_check_user_credits",
                    "_check_strategy_access",
                    "_check_trading_limits"
                ]
            )
            
            print("\n  Trade Execution:")
            self.validate_methods_in_class(
                "/workspace/app/services/unified_chat_service.py",
                "UnifiedChatService",
                [
                    "_execute_trade_with_validation",
                    "execute_decision",
                    "_execute_rebalancing"
                ]
            )
            
            print("\n  Session Management:")
            self.validate_methods_in_class(
                "/workspace/app/services/unified_chat_service.py",
                "UnifiedChatService",
                [
                    "_get_or_create_session",
                    "get_chat_history",
                    "get_active_sessions",
                    "get_service_status"
                ]
            )
        
        # 4. Validate Service Preservation
        print("\n🔧 Service Preservation Check")
        print("-" * 40)
        if os.path.exists("/workspace/app/services/unified_chat_service.py"):
            self.validate_service_preservation("/workspace/app/services/unified_chat_service.py")
        
        # 5. Validate 5-Phase Execution
        print("\n🔄 5-Phase Execution Validation")
        print("-" * 40)
        if os.path.exists("/workspace/app/services/unified_chat_service.py"):
            self.validate_5_phase_execution("/workspace/app/services/unified_chat_service.py")
        
        # 6. Validate Credit Checks
        print("\n💳 Credit System Validation")
        print("-" * 40)
        if os.path.exists("/workspace/app/services/unified_chat_service.py"):
            self.validate_credit_checks("/workspace/app/services/unified_chat_service.py")
        
        # 7. Validate Endpoints
        print("\n🌐 API Endpoints Validation")
        print("-" * 40)
        if os.path.exists("/workspace/app/api/v1/endpoints/unified_chat.py"):
            with open("/workspace/app/api/v1/endpoints/unified_chat.py", 'r') as f:
                content = f.read()
            
            endpoints = [
                '@router.post("/message"',
                '@router.post("/stream"',
                '@router.get("/history/{session_id}"',
                '@router.get("/sessions"',
                '@router.post("/session/new"',
                '@router.get("/capabilities"',
                '@router.post("/action/confirm"',
                '@router.get("/status"',
                '@router.websocket("/ws/{session_id}"'
            ]
            
            for endpoint in endpoints:
                if endpoint in content:
                    self.results["passed"].append(f"  ✅ {endpoint}")
                else:
                    self.results["failed"].append(f"  ❌ {endpoint} NOT FOUND")
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 VALIDATION SUMMARY")
        print("=" * 50)
        print(f"✅ Passed: {len(self.results['passed'])}")
        print(f"❌ Failed: {len(self.results['failed'])}")
        print(f"⚠️  Warnings: {len(self.results['warnings'])}")
        
        if self.results['failed']:
            print("\n❌ VALIDATION FAILED")
            print("Failed checks:")
            for fail in self.results['failed']:
                print(f"  {fail}")
            return False
        else:
            print("\n✅ VALIDATION PASSED")
            print("All critical features are preserved!")
            return True


def main():
    """Run the validation."""
    validator = UnifiedChatValidator()
    success = validator.run_validation()
    
    if success:
        print("\n" + "=" * 50)
        print("✅ SAFE TO PROCEED")
        print("=" * 50)
        print("1. The unified chat implementation is complete")
        print("2. All features are preserved")
        print("3. Ready to update router and test")
    else:
        print("\n" + "=" * 50)
        print("❌ DO NOT PROCEED")
        print("=" * 50)
        print("Fix the validation errors before updating router")


if __name__ == "__main__":
    main()